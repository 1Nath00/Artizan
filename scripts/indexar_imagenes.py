"""Indexa en ChromaDB las pinturas configuradas para búsqueda visual."""

from __future__ import annotations

import argparse
from concurrent.futures import Executor, Future, ThreadPoolExecutor, as_completed
import logging
from pathlib import Path
import sys
import time
from typing import Any

import httpx
from PIL import Image
from sqlmodel import Session
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import engine
from app.images import image_search

logger = logging.getLogger(__name__)

DownloadResult = tuple[list[dict[str, Any]], list[Image.Image], set[int], float]
DownloadFutures = dict[Future[tuple[Image.Image, float]], dict[str, Any]]


def _registrar_fallos(path: Path, failed_ids: set[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(f"{pintura_id}\n" for pintura_id in sorted(failed_ids)),
        encoding="utf-8",
    )


def _descargar_una(
    row: dict[str, Any],
    client: httpx.Client,
) -> tuple[Image.Image, float]:
    started_at = time.perf_counter()
    image = image_search.descargar_y_abrir_imagen(
        row["url"],
        timeout=15.0,
        retries=2,
        client=client,
    )
    return image, time.perf_counter() - started_at


def _iniciar_descarga(
    rows: list[dict[str, Any]],
    executor: Executor,
    client: httpx.Client,
) -> DownloadFutures:
    futures = {
        executor.submit(
            _descargar_una,
            row,
            client,
        ): row
        for row in rows
    }
    return futures


def _esperar_descargas(
    futures: DownloadFutures,
) -> DownloadResult:
    """Espera un lote ya enviado al executor y recoge sus resultados."""
    successful_rows: list[dict[str, Any]] = []
    images: list[Image.Image] = []
    failed_ids: set[int] = set()
    elapsed_values: list[float] = []
    for future in as_completed(futures):
        row = futures[future]
        try:
            image, elapsed = future.result()
        except Exception:
            failed_ids.add(row["id"])
            logger.exception("Falló la descarga de la pintura id=%s", row["id"])
        else:
            successful_rows.append(row)
            images.append(image)
            elapsed_values.append(elapsed)
    return successful_rows, images, failed_ids, max(elapsed_values, default=0.0)


def _indexar_lote(
    successful_rows: list[dict[str, Any]],
    images: list[Image.Image],
) -> tuple[int, set[int], float]:
    started_at = time.perf_counter()
    failed_ids: set[int] = set()
    indexed = 0
    try:
        indexed = image_search.upsert_pinturas(successful_rows, images)
    except Exception:
        logger.exception(
            "Falló el lote de embeddings; se reintenta cada pintura por separado."
        )
        for row, image in zip(successful_rows, images):
            try:
                indexed += image_search.upsert_pinturas([row], [image])
            except Exception:
                failed_ids.add(row["id"])
                logger.exception("Falló el embedding de la pintura id=%s", row["id"])
    return indexed, failed_ids, time.perf_counter() - started_at


def indexar(
    *,
    batch_size: int = 32,
    workers: int = 8,
    failed_file: Path = Path("failed_ids.txt"),
) -> dict[str, int]:
    """Indexa por lotes con prefetch de red y devuelve el resumen."""
    with Session(engine) as session:
        rows = image_search.consultar_pinturas_indexables(session)

    existing = image_search.ids_indexados([row["id"] for row in rows])
    pending = [row for row in rows if str(row["id"]) not in existing]
    failed_ids: set[int] = set()
    indexed = 0
    progress = tqdm(total=len(pending), desc="Indexando embeddings", unit="pintura")
    try:
        with httpx.Client(follow_redirects=True) as client, ThreadPoolExecutor(
            max_workers=workers
        ) as executor:
            current = 0
            downloads: DownloadFutures | None = None
            if pending:
                downloads = _iniciar_descarga(pending[:batch_size], executor, client)

            while current < len(pending):
                batch = pending[current : current + batch_size]
                if downloads is None:
                    downloads = _iniciar_descarga(batch, executor, client)
                successful_rows, images, download_failures, download_elapsed = (
                    _esperar_descargas(downloads)
                )

                next_start = current + batch_size
                if next_start < len(pending):
                    downloads = _iniciar_descarga(
                        pending[next_start : next_start + batch_size],
                        executor,
                        client,
                    )
                else:
                    downloads = None

                batch_indexed, embedding_failures, embedding_elapsed = _indexar_lote(
                    successful_rows, images
                )
                failed_ids.update(download_failures)
                failed_ids.update(embedding_failures)
                indexed += batch_indexed
                completed = len(download_failures) + batch_indexed + len(embedding_failures)
                progress.update(completed)
                logger.info(
                    "Lote %s: descarga=%.2fs embeddings=%.2fs "
                    "indexadas=%s fallidas=%s",
                    current // batch_size + 1,
                    download_elapsed,
                    embedding_elapsed,
                    batch_indexed,
                    len(download_failures) + len(embedding_failures),
                )
                current = next_start
    finally:
        progress.close()
        _registrar_fallos(failed_file, failed_ids)

    result = {
        "indexadas": indexed,
        "omitidas": len(existing),
        "fallidas": len(failed_ids),
    }
    logger.info(
        "Indexación finalizada: indexadas=%s omitidas=%s fallidas=%s",
        result["indexadas"],
        result["omitidas"],
        result["fallidas"],
    )
    return result


def main() -> None:
    """Procesa argumentos del script y ejecuta la indexación."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--failed-file", type=Path, default=Path("failed_ids.txt"))
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Borra y recrea solo la colección visual antes de indexar.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirma --reset sin solicitar entrada interactiva.",
    )
    args = parser.parse_args()
    if args.batch_size < 1 or args.workers < 1:
        parser.error("--batch-size y --workers deben ser mayores que cero.")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        if args.reset and not args.yes:
            confirmation = input(
                "Esto borrará únicamente la colección de imágenes. "
                "Escribe 'SI' para continuar: "
            )
            if confirmation.strip().upper() != "SI":
                logger.info("Reindexación cancelada.")
                return
        image_search.get_image_model()
        logger.info(
            "Modelo preparado: %s; dispositivo=%s",
            image_search.config.MODELO_EMBEDDINGS_IMAGEN,
            image_search.get_image_device(),
        )
        if args.reset:
            image_search.reset_image_collection()
        indexar(
            batch_size=args.batch_size,
            workers=args.workers,
            failed_file=args.failed_file,
        )
    except KeyboardInterrupt:
        print(
            "Interrumpido por el usuario. Puedes reanudar ejecutando de nuevo el script."
        )
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()
