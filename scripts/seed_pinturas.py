"""Import the three pending dataset styles without changing existing paintings."""

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import sys
from typing import TypedDict
from urllib.parse import urlsplit
from uuid import uuid4

import cloudinary
import cloudinary.uploader
import httpx
from sqlmodel import Session, create_engine, select

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import (
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
    CLOUDINARY_CLOUD_NAME,
    DATABASE_URL,
)
from app.categorias.models import Categoria
from app.pinturas.models import Pintura

DATASET_DIR = Path(__file__).resolve().parent.parent / "dataset"
CATEGORIAS = {
    "Impressionism": "impresionismo",
    "Expressionism": "expresionismo",
    "Pop_Art": "pop-art",
}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
_YEAR_RE = re.compile(r"-(\d{4})(?:\(\d+\)|(?:-\d+))*$")


class PaintingMetadata(TypedDict):
    autor: str
    nombre: str
    año: int | None


@dataclass(frozen=True)
class UploadedImage:
    url: str
    public_id: str
    owned: bool


@dataclass
class ImportResult:
    created: int = 0
    skipped: int = 0
    planned: int = 0
    verified: int = 0
    undated: int = 0
    errors: int = 0


def parse_filename(filename: str) -> PaintingMetadata:
    """Accept the actual autor_titulo[-year] dataset and unambiguous title-author-year."""
    base = Path(filename).stem
    if "_" in base:
        autor_raw, painting_raw = base.split("_", 1)
        match = _YEAR_RE.search(painting_raw)
        year = int(match.group(1)) if match else None
        nombre_raw = painting_raw[: match.start()] if match else painting_raw
    else:
        parts = base.split("-")
        if len(parts) != 3 or not re.fullmatch(r"\d{4}", parts[2]):
            raise ValueError(f"Nombre de archivo ambiguo o invalido: {filename}")
        nombre_raw, autor_raw, year_raw = parts
        year = int(year_raw)

    autor = autor_raw.replace("-", " ").strip().title()
    nombre = nombre_raw.replace("-", " ").replace("_", " ").strip().title()
    if not autor or not nombre or (year is not None and year == 0):
        raise ValueError(f"Metadatos incompletos o invalidos: {filename}")
    return {"autor": autor, "nombre": nombre, "año": year}


def upload_image(filepath: Path, categoria: str) -> UploadedImage:
    """Use a stable ID for retries; mark newly created assets for compensation."""
    stem = filepath.stem
    autor_raw = stem.split("_")[0] if "_" in stem else stem
    public_id = f"artizan/pinturas/{categoria}/{autor_raw}/{stem}"
    token = uuid4().hex
    result = cloudinary.uploader.upload(
        str(filepath),
        public_id=public_id,
        overwrite=False,
        resource_type="image",
        context={"artizan_import_token": token},
        timeout=120,
    )
    if result.get("public_id") != public_id:
        raise RuntimeError(f"Cloudinary devolvio otro public_id para {filepath.name}")
    # An existing asset must never be deleted when a later database write fails.
    custom_context = (result.get("context") or {}).get("custom") or {}
    return UploadedImage(
        url=result["secure_url"],
        public_id=public_id,
        owned=custom_context.get("artizan_import_token") == token,
    )


def verify_image(url: str, filepath: Path) -> None:
    """Check URL access and byte-for-byte correspondence with the dataset file."""
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("La URL de la imagen debe ser HTTPS y absoluta.")
    with httpx.stream("GET", url, timeout=30, follow_redirects=True) as response:
        response.raise_for_status()
        if not response.headers.get("content-type", "").lower().startswith("image/"):
            raise ValueError("La URL no devuelve una imagen.")
        remote_digest = hashlib.sha256()
        size = 0
        for chunk in response.iter_bytes():
            remote_digest.update(chunk)
            size += len(chunk)
        if not size:
            raise ValueError("La URL devuelve una imagen vacia.")
    local_digest = hashlib.sha256()
    with filepath.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            local_digest.update(chunk)
    if local_digest.digest() != remote_digest.digest():
        raise ValueError("La imagen de la URL no coincide con el archivo del dataset.")


def _cleanup_upload(uploaded: UploadedImage) -> None:
    if not uploaded.owned:
        print(f"  CONSERVADA imagen preexistente o de propiedad no confirmada: {uploaded.public_id}")
        return
    result = cloudinary.uploader.destroy(
        uploaded.public_id, resource_type="image", invalidate=True, timeout=30
    )
    if result.get("result") not in {"ok", "not found"}:
        raise RuntimeError(f"No se pudo retirar la imagen: {uploaded.public_id}")


def run_import(
    session: Session,
    dataset_dir: Path,
    *,
    dry_run: bool = False,
    verify_only: bool = False,
) -> ImportResult:
    if dry_run and verify_only:
        raise ValueError("dry_run y verify_only son excluyentes.")
    result = ImportResult()
    categories: dict[str, int] = {}
    files_by_folder: dict[str, list[Path]] = {}
    for folder_name, slug in CATEGORIAS.items():
        folder = dataset_dir / folder_name
        if not folder.is_dir():
            raise RuntimeError(f"Carpeta no encontrada: {folder}")
        files = sorted(
            path for path in folder.iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        )
        if not files:
            raise RuntimeError(f"No hay imagenes en {folder}")
        category = session.exec(select(Categoria).where(Categoria.slug == slug)).one_or_none()
        if category is None or category.id is None:
            raise RuntimeError(f"No existe la categoria '{slug}'.")
        categories[folder_name] = category.id
        files_by_folder[folder_name] = files

    filename_counts = Counter(
        path.name for files in files_by_folder.values() for path in files
    )
    existing_by_filename = {
        row.filename_original: row
        for row in session.exec(
            select(
                Pintura.filename_original,
                Pintura.categoria_id,
                Pintura.autor,
                Pintura.nombre,
                Pintura.año,
                Pintura.url_imagen,
            )
        )
    }
    for folder_name, files in files_by_folder.items():
        print(f"\n{folder_name}: {len(files)} imagenes")
        for filepath in files:
            uploaded = None
            committed = False
            try:
                parsed = parse_filename(filepath.name)
                if parsed["año"] is None:
                    result.undated += 1
                    print(f"  SIN_ANIO {folder_name}/{filepath.name}")
                existing = existing_by_filename.get(filepath.name)
                if existing is not None:
                    if existing.categoria_id != categories[folder_name]:
                        raise ValueError("El archivo ya pertenece a otra categoria; no se modifica.")
                    if (existing.autor, existing.nombre, existing.año) != (
                        parsed["autor"], parsed["nombre"], parsed["año"]
                    ):
                        raise ValueError("Los metadatos existentes difieren; no se modifican.")
                    if not dry_run:
                        verify_image(existing.url_imagen, filepath)
                        result.verified += 1
                    result.skipped += 1
                    continue
                if filename_counts[filepath.name] > 1:
                    raise ValueError("Archivo repetido entre estilos; se omiten todas las copias nuevas.")
                if verify_only:
                    raise ValueError("No existe un registro para la imagen.")
                if dry_run:
                    result.planned += 1
                    continue

                uploaded = upload_image(filepath, folder_name)
                verify_image(uploaded.url, filepath)
                pintura = Pintura(
                    **parsed,
                    categoria_id=categories[folder_name],
                    url_imagen=uploaded.url,
                    filename_original=filepath.name,
                )
                session.add(pintura)
                session.commit()
                committed = True
                session.refresh(pintura)
                if pintura.url_imagen != uploaded.url or pintura.categoria_id != categories[folder_name]:
                    raise RuntimeError("El registro guardado no coincide con la imagen.")
                result.created += 1
                result.verified += 1
                print(f"  OK {folder_name}/{filepath.name}")
            except Exception as exc:
                session.rollback()
                result.errors += 1
                print(f"  ERROR {folder_name}/{filepath.name}: {exc}")
                if uploaded is not None and not committed:
                    # A lost commit response may still mean the row was persisted.
                    try:
                        persisted = session.exec(
                            select(Pintura).where(Pintura.url_imagen == uploaded.url)
                        ).first()
                        if persisted is None:
                            _cleanup_upload(uploaded)
                    except Exception as cleanup_exc:
                        session.rollback()
                        print(f"  ERROR_RECUPERACION {uploaded.public_id}: {cleanup_exc}")

    print(
        f"\nCreadas: {result.created} | Existentes: {result.skipped} | "
        f"Pendientes validas: {result.planned} | Verificadas: {result.verified} | "
        f"Sin anio: {result.undated} | Errores: {result.errors}"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Validar sin escribir ni acceder a Cloudinary.")
    mode.add_argument("--verify-only", action="store_true", help="Verificar registros y URLs sin escribir.")
    args = parser.parse_args()
    if not args.dry_run and not args.verify_only:
        if not all((CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET)):
            print("ERROR: Falta configuracion de Cloudinary.")
            return 1
        cloudinary.config(
            cloud_name=CLOUDINARY_CLOUD_NAME,
            api_key=CLOUDINARY_API_KEY,
            api_secret=CLOUDINARY_API_SECRET,
            secure=True,
        )
    engine = create_engine(DATABASE_URL)
    try:
        with Session(engine) as session:
            result = run_import(
                session, DATASET_DIR, dry_run=args.dry_run, verify_only=args.verify_only
            )
        return 1 if result.errors else 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
