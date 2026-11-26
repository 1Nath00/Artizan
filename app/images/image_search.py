"""Servicios para indexar e identificar pinturas mediante embeddings de imagen."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
import logging
import re
from threading import Lock
import time
from typing import Any, Literal
from urllib.parse import urlsplit, urlunsplit

import httpx
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import text
from sqlmodel import Session

from app import config
from app.images.identification_schemas import (
    CandidatoPintura,
    IdentificarImagenResponse,
    PinturaIdentificada,
)

logger = logging.getLogger(__name__)

_model: Any = None
_processor: Any = None
_device: Any = None
_model_lock = Lock()
_encode_lock = Lock()


class ImageSearchError(RuntimeError):
    """Error esperado al consultar o mantener el índice de imágenes."""


class InvalidImageError(ImageSearchError):
    """La entrada o la URL no contiene una imagen utilizable."""


class ImageSearchConfigurationError(ImageSearchError):
    """La búsqueda visual todavía no está configurada."""


@dataclass(frozen=True)
class ImageMatch:
    """Resultado vectorial de ChromaDB."""

    pintura_id: int
    score: float


def get_image_model() -> Any:
    """Carga y reutiliza el modelo DINOv2 por proceso."""
    global _model, _processor, _device

    if _model is not None:
        return _model
    with _model_lock:
        if _model is None:
            import torch
            from transformers import AutoImageProcessor, AutoModel

            model_name = config.MODELO_EMBEDDINGS_IMAGEN
            if torch.cuda.is_available():
                _device = torch.device("cuda")
            else:
                _device = torch.device("cpu")
                if config.TORCH_NUM_THREADS is not None:
                    torch.set_num_threads(config.TORCH_NUM_THREADS)
            logger.info(
                "Cargando modelo de embeddings de imagen %s en %s (solo_local=%s)",
                model_name,
                _device,
                config.MODELO_SOLO_LOCAL,
            )
            try:
                _processor = AutoImageProcessor.from_pretrained(
                    model_name,
                    local_files_only=config.MODELO_SOLO_LOCAL,
                )
                loaded_model = AutoModel.from_pretrained(
                    model_name,
                    local_files_only=config.MODELO_SOLO_LOCAL,
                    torch_dtype=torch.float16 if _device.type == "cuda" else None,
                )
            except OSError as exc:
                if config.MODELO_SOLO_LOCAL:
                    raise ImageSearchConfigurationError(
                        "No se encontró el modelo de imágenes "
                        f"'{model_name}' en la caché local. Descárgalo primero o "
                        "configura MODELO_SOLO_LOCAL=false."
                    ) from exc
                raise ImageSearchConfigurationError(
                    f"No se pudo cargar el modelo de imágenes '{model_name}'."
                ) from exc
            _model = loaded_model.to(_device)
            _model.eval()
        return _model


def get_image_processor() -> Any:
    """Devuelve el procesador asociado al modelo DINOv2 cargado."""
    get_image_model()
    if _processor is None:
        raise ImageSearchConfigurationError("El procesador de imágenes no está inicializado.")
    return _processor


def get_image_device() -> Any:
    """Devuelve el dispositivo elegido para la inferencia visual."""
    get_image_model()
    if _device is None:
        raise ImageSearchConfigurationError("El dispositivo de imágenes no está inicializado.")
    return _device


@lru_cache(maxsize=1)
def get_image_collection() -> Any:
    """Obtiene una única colección visual separada de la colección RAG."""
    try:
        import chromadb

        client = chromadb.PersistentClient(path=config.RAG_DB_DIR)
        try:
            collection = client.get_collection(config.NOMBRE_COLECCION_IMAGENES)
        except Exception:
            collection = client.create_collection(
                config.NOMBRE_COLECCION_IMAGENES,
                metadata={
                    "hnsw:space": "cosine",
                    "modelo": config.MODELO_EMBEDDINGS_IMAGEN,
                },
            )
        indexed_model = (collection.metadata or {}).get("modelo")
        if indexed_model != config.MODELO_EMBEDDINGS_IMAGEN:
            raise ImageSearchConfigurationError(
                "La colección de imágenes fue creada con el modelo "
                f"'{indexed_model or 'desconocido'}', pero está configurado "
                f"'{config.MODELO_EMBEDDINGS_IMAGEN}'. Los vectores de modelos "
                "distintos no son compatibles; ejecuta scripts/indexar_imagenes.py "
                "con --reset para reindexar."
            )
        return collection
    except ImageSearchConfigurationError:
        raise
    except Exception as exc:
        raise ImageSearchError("No fue posible abrir el índice visual de pinturas.") from exc


def reset_image_collection() -> None:
    """Borra y recrea únicamente la colección visual configurada."""
    try:
        import chromadb

        client = chromadb.PersistentClient(path=config.RAG_DB_DIR)
        try:
            client.delete_collection(config.NOMBRE_COLECCION_IMAGENES)
        except Exception:
            pass
        get_image_collection.cache_clear()
        get_image_collection()
    except Exception:
        get_image_collection.cache_clear()
        raise


def inicializar_servicio_imagenes() -> None:
    """Precalienta el modelo y crea la colección al iniciar la aplicación."""
    if not config.CATEGORIA_IDS_INDEXAR:
        logger.warning(
            "La identificación visual está deshabilitada: configura CATEGORIA_IDS_INDEXAR."
        )
        return
    get_image_model()
    get_image_collection()


def preparar_imagen(image: Image.Image) -> Image.Image:
    """Normaliza orientación, color y tamaño antes de inferir."""
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")
    image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
    return image


def abrir_imagen(content: bytes) -> Image.Image:
    """Decodifica bytes de imagen y rechaza archivos corruptos o vacíos."""
    if not content:
        raise InvalidImageError("El archivo de imagen está vacío.")
    try:
        with Image.open(BytesIO(content)) as image:
            image.load()
            return preparar_imagen(image)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise InvalidImageError("El archivo no contiene una imagen válida.") from exc


def embedding_imagen(image: Image.Image) -> list[float]:
    """Genera un embedding DINOv2 normalizado para una imagen PIL."""
    return embeddings_imagenes([image])[0]


def embeddings_imagenes(images: list[Image.Image]) -> list[list[float]]:
    """Genera embeddings DINOv2 normalizados en sub-lotes."""
    if not images:
        return []
    import torch
    import torch.nn.functional as functional

    model = get_image_model()
    processor = get_image_processor()
    device = get_image_device()
    embeddings: list[list[float]] = []
    with _encode_lock:
        with torch.inference_mode():
            for start in range(0, len(images), 32):
                batch = [
                    preparar_imagen(image.copy())
                    for image in images[start : start + 32]
                ]
                inputs = processor(images=batch, return_tensors="pt")
                inputs = {
                    name: tensor.to(device)
                    for name, tensor in inputs.items()
                }
                if device.type == "cuda":
                    with torch.autocast(device_type="cuda", dtype=torch.float16):
                        output = model(**inputs)
                else:
                    output = model(**inputs)
                cls_vectors = output.last_hidden_state[:, 0, :]
                normalized = functional.normalize(cls_vectors.float(), p=2, dim=1)
                embeddings.extend(normalized.cpu().tolist())
    return embeddings


def cloudinary_lightweight_url(url: str) -> str:
    """Inserta una transformación liviana en URLs de imágenes Cloudinary."""
    parsed = urlsplit(url)
    if (
        "cloudinary" not in parsed.netloc.lower()
        or "/upload/" not in parsed.path
        or "/upload/w_448,c_limit/" in parsed.path
    ):
        return url
    suffix = parsed.path.split("/upload/", 1)[1]
    first_segment = suffix.split("/", 1)[0]
    if re.search(r"(?:^|,)(?:[a-z]{1,3}_[^,]+)(?:,|$)", first_segment):
        return url
    path = parsed.path.replace("/upload/", "/upload/w_448,c_limit/", 1)
    return urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, parsed.fragment))


def descargar_y_abrir_imagen(
    url: str,
    *,
    timeout: float = 15.0,
    retries: int = 2,
    client: httpx.Client | None = None,
) -> Image.Image:
    """Descarga una imagen remota con reintentos explícitos."""
    if not url.strip():
        raise InvalidImageError("La pintura no tiene una URL de imagen.")
    owned_client = client is None
    http_client = client or httpx.Client(follow_redirects=True)
    last_error: Exception | None = None
    try:
        for attempt in range(retries + 1):
            try:
                response = http_client.get(
                    cloudinary_lightweight_url(url),
                    timeout=timeout,
                )
                response.raise_for_status()
                return abrir_imagen(response.content)
            except (httpx.HTTPError, InvalidImageError) as exc:
                last_error = exc
                if attempt < retries:
                    time.sleep(0.5 * (attempt + 1))
        raise ImageSearchError(f"No se pudo descargar la imagen: {url}") from last_error
    finally:
        if owned_client:
            http_client.close()


def _column(name: str) -> str:
    if not name or '"' in name or "\x00" in name:
        raise ImageSearchConfigurationError("Nombre de columna de pinturas inválido.")
    return f'"{name}"'


def obtener_pinturas_por_ids(
    session: Session,
    pintura_ids: list[int],
) -> dict[int, PinturaIdentificada]:
    """Consulta datos públicos desde PostgreSQL y conserva IDs solicitados."""
    ids = list(dict.fromkeys(pintura_ids))
    if not ids:
        return {}
    columns = [
        config.PINTURA_ID_COLUMNA,
        config.PINTURA_URL_COLUMNA,
        config.PINTURA_AUTOR_COLUMNA,
        config.PINTURA_ANIO_COLUMNA,
        config.PINTURA_DESCRIPCION_COLUMNA,
        config.PINTURA_CATEGORIA_ID_COLUMNA,
    ]
    parameters = {f"id_{index}": pintura_id for index, pintura_id in enumerate(ids)}
    placeholders = ", ".join(f":id_{index}" for index in range(len(ids)))
    statement = text(
        f"SELECT {', '.join(_column(column) for column in columns)} "
        f"FROM {_column(config.PINTURAS_TABLA)} "
        f"WHERE {_column(config.PINTURA_ID_COLUMNA)} IN ({placeholders})"
    )
    rows = session.exec(statement, params=parameters).mappings()
    result: dict[int, PinturaIdentificada] = {}
    for row in rows:
        pintura_id = int(row[config.PINTURA_ID_COLUMNA])
        result[pintura_id] = PinturaIdentificada(
            id=pintura_id,
            imagen_url=str(row[config.PINTURA_URL_COLUMNA]),
            autor=str(row[config.PINTURA_AUTOR_COLUMNA]),
            anio=row[config.PINTURA_ANIO_COLUMNA],
            descripcion=row[config.PINTURA_DESCRIPCION_COLUMNA],
            categoria_id=int(row[config.PINTURA_CATEGORIA_ID_COLUMNA]),
        )
    return result


def consultar_pinturas_indexables(session: Session) -> list[dict[str, Any]]:
    """Obtiene id, URL y categoría de las pinturas configuradas."""
    categoria_ids = config.CATEGORIA_IDS_INDEXAR
    if not categoria_ids:
        raise ImageSearchConfigurationError(
            "Configura CATEGORIA_IDS_INDEXAR con los IDs de Barroco y Cubismo."
        )
    parameters = {
        f"categoria_{index}": categoria_id
        for index, categoria_id in enumerate(categoria_ids)
    }
    placeholders = ", ".join(f":categoria_{index}" for index in range(len(categoria_ids)))
    statement = text(
        f"SELECT {_column(config.PINTURA_ID_COLUMNA)}, "
        f"{_column(config.PINTURA_URL_COLUMNA)}, "
        f"{_column(config.PINTURA_CATEGORIA_ID_COLUMNA)} "
        f"FROM {_column(config.PINTURAS_TABLA)} "
        f"WHERE {_column(config.PINTURA_CATEGORIA_ID_COLUMNA)} IN ({placeholders}) "
        f"AND {_column(config.PINTURA_URL_COLUMNA)} IS NOT NULL "
        f"AND TRIM({_column(config.PINTURA_URL_COLUMNA)}) <> '' "
        f"ORDER BY {_column(config.PINTURA_ID_COLUMNA)}"
    )
    return [
        {
            "id": int(row[config.PINTURA_ID_COLUMNA]),
            "url": str(row[config.PINTURA_URL_COLUMNA]),
            "categoria_id": int(row[config.PINTURA_CATEGORIA_ID_COLUMNA]),
        }
        for row in session.exec(statement, params=parameters).mappings()
    ]


def ids_indexados(pintura_ids: list[int]) -> set[str]:
    """Devuelve los IDs ya presentes en Chroma en consultas acotadas."""
    if not pintura_ids:
        return set()
    collection = get_image_collection()
    existing: set[str] = set()
    for index in range(0, len(pintura_ids), 500):
        batch = [str(pintura_id) for pintura_id in pintura_ids[index : index + 500]]
        existing.update(collection.get(ids=batch).get("ids", []))
    return existing


def upsert_pinturas(
    rows: list[dict[str, Any]],
    images: list[Image.Image],
) -> int:
    """Calcula embeddings y actualiza un lote en ChromaDB."""
    if len(rows) != len(images):
        raise ImageSearchError("La cantidad de pinturas e imágenes no coincide.")
    if not rows:
        return 0
    embeddings = embeddings_imagenes(images)
    get_image_collection().upsert(
        ids=[str(row["id"]) for row in rows],
        embeddings=embeddings,
        metadatas=[{"categoria_id": int(row["categoria_id"])} for row in rows],
    )
    return len(rows)


def _obtener_pintura_indexable(
    session: Session,
    pintura_id: int,
) -> dict[str, Any] | None:
    categoria_ids = config.CATEGORIA_IDS_INDEXAR
    if not categoria_ids:
        raise ImageSearchConfigurationError(
            "Configura CATEGORIA_IDS_INDEXAR antes de indexar una pintura."
        )
    parameters: dict[str, int] = {"pintura_id": pintura_id}
    parameters.update(
        {
            f"categoria_{index}": categoria_id
            for index, categoria_id in enumerate(categoria_ids)
        }
    )
    placeholders = ", ".join(f":categoria_{index}" for index in range(len(categoria_ids)))
    statement = text(
        f"SELECT {_column(config.PINTURA_ID_COLUMNA)}, "
        f"{_column(config.PINTURA_URL_COLUMNA)}, "
        f"{_column(config.PINTURA_CATEGORIA_ID_COLUMNA)} "
        f"FROM {_column(config.PINTURAS_TABLA)} "
        f"WHERE {_column(config.PINTURA_ID_COLUMNA)} = :pintura_id "
        f"AND {_column(config.PINTURA_CATEGORIA_ID_COLUMNA)} IN ({placeholders}) "
        f"AND {_column(config.PINTURA_URL_COLUMNA)} IS NOT NULL "
        f"AND TRIM({_column(config.PINTURA_URL_COLUMNA)}) <> ''"
    )
    row = session.exec(statement, params=parameters).mappings().first()
    if row is None:
        return None
    return {
        "id": int(row[config.PINTURA_ID_COLUMNA]),
        "url": str(row[config.PINTURA_URL_COLUMNA]),
        "categoria_id": int(row[config.PINTURA_CATEGORIA_ID_COLUMNA]),
    }


def indexar_pintura(session: Session, pintura_id: int) -> bool:
    """Indexa una pintura existente o la retira si su categoría no aplica."""
    if not config.CATEGORIA_IDS_INDEXAR:
        raise ImageSearchConfigurationError(
            "Configura CATEGORIA_IDS_INDEXAR antes de indexar una pintura."
        )
    row = _obtener_pintura_indexable(session, pintura_id)
    if row is None:
        eliminar_pintura_del_indice(pintura_id)
        return False
    image = descargar_y_abrir_imagen(row["url"])
    upsert_pinturas([row], [image])
    return True


def eliminar_pintura_del_indice(pintura_id: int) -> None:
    """Elimina una pintura del índice visual por su identificador."""
    get_image_collection().delete(ids=[str(pintura_id)])


def buscar_similares(embedding: list[float], limit: int = 5) -> list[ImageMatch]:
    """Busca vecinos y convierte distancia coseno en similitud."""
    collection = get_image_collection()
    if collection.count() == 0:
        return []
    try:
        result = collection.query(
            query_embeddings=[embedding],
            n_results=min(limit, collection.count()),
            include=["distances", "metadatas"],
        )
    except Exception as exc:
        raise ImageSearchError("No fue posible consultar el índice visual.") from exc
    ids = (result.get("ids") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    matches: list[ImageMatch] = []
    for raw_id, distance in zip(ids, distances):
        try:
            matches.append(ImageMatch(pintura_id=int(raw_id), score=1.0 - float(distance)))
        except (TypeError, ValueError):
            logger.warning("ID inválido omitido del índice visual: %r", raw_id)
    return matches


def _estado(score: float) -> Literal["encontrada", "dudosa", "no_encontrada"]:
    if score >= config.UMBRAL_ENCONTRADA:
        return "encontrada"
    if score >= config.UMBRAL_DUDOSA:
        return "dudosa"
    return "no_encontrada"


def identificar_imagen(session: Session, content: bytes) -> IdentificarImagenResponse:
    """Clasifica el resultado vectorial según los umbrales configurados."""
    embedding = embedding_imagen(abrir_imagen(content))
    matches = buscar_similares(embedding)
    pinturas = obtener_pinturas_por_ids(session, [match.pintura_id for match in matches])
    valid_matches = [match for match in matches if match.pintura_id in pinturas]
    if not valid_matches:
        return IdentificarImagenResponse(
            estado="no_encontrada",
            score=0.0,
            pintura=None,
            candidatos=[],
        )

    best = valid_matches[0]
    estado = _estado(best.score)
    pintura = pinturas[best.pintura_id] if estado != "no_encontrada" else None
    candidatos: list[CandidatoPintura] = []
    if estado == "dudosa":
        candidatos = [
            CandidatoPintura(
                **pinturas[match.pintura_id].model_dump(),
                score=match.score,
            )
            for match in valid_matches[:3]
        ]
    return IdentificarImagenResponse(
        estado=estado,
        score=best.score,
        pintura=pintura,
        candidatos=candidatos,
    )
