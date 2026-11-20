import asyncio
import logging
import math
import uuid
from pathlib import Path

import cloudinary
import cloudinary.uploader
import httpx
from PIL import Image as PILImage
import io
from fastapi import HTTPException, UploadFile, status
from sqlmodel import Session, select

from app.config import (
    ALLOWED_EXTENSIONS,
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
    CLOUDINARY_CLOUD_NAME,
    MAX_IMAGE_SIZE_MB,
)
from app.categorias.models import Categoria
from app.categorias.service import resolve_categoria_id_for_label
from app.images.models import Image
from app.images.yolo_loader import get_yolo_model
from app.models.cnn.model import classify_image

MAX_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024
UPLOADS_DIR = Path("uploads")
DETECTION_CONFIDENCE_THRESHOLD = 0.5

COCO_LABELS_ES = {
    "person": "persona",
    "bicycle": "bicicleta",
    "car": "automóvil",
    "motorcycle": "motocicleta",
    "airplane": "avión",
    "bus": "autobús",
    "train": "tren",
    "truck": "camión",
    "boat": "barco",
    "traffic light": "semáforo",
    "fire hydrant": "hidrante",
    "stop sign": "señal de alto",
    "parking meter": "parquímetro",
    "bench": "banco",
    "bird": "pájaro",
    "cat": "gato",
    "dog": "perro",
    "horse": "caballo",
    "sheep": "oveja",
    "cow": "vaca",
    "elephant": "elefante",
    "bear": "oso",
    "zebra": "cebra",
    "giraffe": "jirafa",
    "backpack": "mochila",
    "umbrella": "paraguas",
    "handbag": "bolso",
    "tie": "corbata",
    "suitcase": "maleta",
    "frisbee": "disco volador",
    "skis": "esquís",
    "snowboard": "tabla de snowboard",
    "sports ball": "balón",
    "kite": "cometa",
    "baseball bat": "bate de béisbol",
    "baseball glove": "guante de béisbol",
    "skateboard": "monopatín",
    "surfboard": "tabla de surf",
    "tennis racket": "raqueta de tenis",
    "bottle": "botella",
    "wine glass": "copa",
    "cup": "taza",
    "fork": "tenedor",
    "knife": "cuchillo",
    "spoon": "cuchara",
    "bowl": "tazón",
    "banana": "plátano",
    "apple": "manzana",
    "sandwich": "sándwich",
    "orange": "naranja",
    "broccoli": "brócoli",
    "carrot": "zanahoria",
    "hot dog": "perro caliente",
    "pizza": "pizza",
    "donut": "dona",
    "cake": "pastel",
    "chair": "silla",
    "couch": "sofá",
    "potted plant": "planta en maceta",
    "bed": "cama",
    "dining table": "mesa de comedor",
    "toilet": "inodoro",
    "tv": "televisor",
    "laptop": "computadora portátil",
    "mouse": "ratón",
    "remote": "control remoto",
    "keyboard": "teclado",
    "cell phone": "teléfono celular",
    "microwave": "microondas",
    "oven": "horno",
    "toaster": "tostadora",
    "sink": "fregadero",
    "refrigerator": "refrigerador",
    "book": "libro",
    "clock": "reloj",
    "vase": "jarrón",
    "scissors": "tijeras",
    "teddy bear": "oso de peluche",
    "hair drier": "secador de pelo",
    "toothbrush": "cepillo de dientes",
}

logger = logging.getLogger(__name__)

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True,
)


def _get_extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _validate_content(filename: str, content: bytes) -> str:
    ext = _get_extension(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}",
        )
    if len(content) > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_IMAGE_SIZE_MB} MB",
        )
    return ext


def _persist_image(
    content: bytes,
    ext: str,
    session: Session,
    usuario_id: int,
    categoria_id: int | None = None,
    titulo: str | None = None,
    descripcion: str | None = None,
    confianza: float | None = None,
    estado: str = "pendiente",
    detecciones: list[dict] | None = None,
) -> Image:
    if categoria_id is not None and session.get(Categoria, categoria_id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"categoria_id {categoria_id} does not exist",
        )

    UPLOADS_DIR.mkdir(exist_ok=True)
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    file_path = UPLOADS_DIR / unique_name
    file_path.write_bytes(content)

    # Subir a Cloudinary
    cloudinary_url = str(file_path)
    if CLOUDINARY_CLOUD_NAME:
        try:
            result = cloudinary.uploader.upload(
                str(file_path),
                public_id=f"artizan/images/{unique_name.rsplit('.', 1)[0]}",
                overwrite=False,
                resource_type="image",
            )
            cloudinary_url = result["secure_url"]
            file_path.unlink(missing_ok=True)  # ya no se necesita la copia local
        except Exception:
            logger.exception("Cloudinary upload failed, falling back to local path")
    else:
        logger.warning("CLOUDINARY_CLOUD_NAME is not set, skipping Cloudinary upload")

    image = Image(
        usuario_id=usuario_id,
        imagen_url=cloudinary_url,
        categoria_id=categoria_id,
        titulo=titulo,
        descripcion=descripcion,
        confianza=confianza,
        detecciones=detecciones,
        estado=estado,
    )
    session.add(image)
    session.commit()
    session.refresh(image)
    return image


async def save_image(
    session: Session,
    file: UploadFile,
    usuario_id: int,
    categoria_id: int | None = None,
    titulo: str | None = None,
    descripcion: str | None = None,
) -> Image:
    content = await file.read()
    ext = _validate_content(file.filename or "", content)
    return _persist_image(
        content,
        ext,
        session,
        usuario_id=usuario_id,
        categoria_id=categoria_id,
        titulo=titulo,
        descripcion=descripcion,
    )


async def analyze_image(
    session: Session,
    file: UploadFile,
    usuario_id: int,
    top_k: int = 5,
    conf: float = 0.25,
) -> tuple[Image, list[dict], list[dict]]:
    """Sube la imagen una sola vez y ejecuta clasificación y detección en paralelo."""
    content = await file.read()
    ext = _validate_content(file.filename or "", content)

    predictions, detections = await asyncio.gather(
        asyncio.to_thread(classify_image, content, top_k),
        asyncio.to_thread(detect_objects_from_bytes, content, conf),
    )

    # Categoría y confianza del MISMO resultado top-1; si la etiqueta no
    # mapea a una categoría existente, ambos quedan en None.
    top_prediction = predictions[0] if predictions else None
    categoria_id = (
        resolve_categoria_id_for_label(session, top_prediction["label"]) if top_prediction else None
    )
    confianza = top_prediction["confidence"] if top_prediction and categoria_id is not None else None
    stored_detections = normalize_detections(detections)
    image = _persist_image(
        content,
        ext,
        session,
        usuario_id=usuario_id,
        categoria_id=categoria_id,
        titulo=top_prediction["label"] if top_prediction else None,
        confianza=confianza,
        estado="clasificada",
        detecciones=stored_detections,
    )
    return image, predictions, detections


def list_images(session: Session, usuario_id: int | None = None) -> list[Image]:
    statement = select(Image)
    if usuario_id is not None:
        statement = statement.where(Image.usuario_id == usuario_id)
    return list(session.exec(statement).all())


def get_image(session: Session, image_id: int) -> Image | None:
    return session.get(Image, image_id)


def normalize_detections(detections: list[dict]) -> list[dict]:
    """Translate COCO labels, filter low-confidence objects and keep each class once."""
    best_by_class: dict[str, dict] = {}
    for detection in detections:
        original_label = detection.get("clase")
        if not isinstance(original_label, str) or not original_label.strip():
            raise ValueError("A detection must contain a non-empty class label.")

        try:
            confidence = float(detection["confianza"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("A detection must contain a numeric confidence.") from exc
        if not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError("Detection confidence must be between 0 and 1.")
        if confidence < DETECTION_CONFIDENCE_THRESHOLD:
            continue

        bbox = detection.get("bbox")
        if not isinstance(bbox, list) or any(
            not isinstance(coordinate, (int, float)) or not math.isfinite(coordinate)
            for coordinate in bbox
        ):
            raise ValueError("A detection must contain a numeric bounding box.")

        normalized_label = " ".join(original_label.casefold().split())
        candidate = {
            "clase_original": original_label.strip(),
            "clase_es": COCO_LABELS_ES.get(normalized_label),
            "confianza": confidence,
            "bbox": bbox,
        }
        current = best_by_class.get(normalized_label)
        if current is None or confidence > current["confianza"]:
            best_by_class[normalized_label] = candidate

    return sorted(best_by_class.values(), key=lambda item: -item["confianza"])


def persist_detections(session: Session, image: Image, detections: list[dict]) -> list[dict]:
    """Replace the stored detections for one image after a successful YOLO run."""
    normalized = normalize_detections(detections)
    image.detecciones = normalized
    session.add(image)
    session.commit()
    session.refresh(image)
    return normalized


def delete_image(session: Session, image_id: int, usuario_id: int) -> bool:
    image = session.get(Image, image_id)
    if not image:
        return False
    if image.usuario_id != usuario_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this image",
        )
    # Remove file from disk if it exists
    file_path = Path(image.imagen_url)
    if file_path.exists():
        file_path.unlink()

    session.delete(image)
    session.commit()
    return True

def detect_objects_from_bytes(image_bytes: bytes, conf: float = 0.25) -> list[dict]:
    img = PILImage.open(io.BytesIO(image_bytes)).convert("RGB")
    model = get_yolo_model()
    results = model(img, conf=conf)
    detections = []
    for r in results:
        for box in r.boxes:
            detections.append({
                "clase": model.names[int(box.cls)],
                "confianza": round(float(box.conf), 4),
                "bbox": [round(x, 2) for x in box.xyxy.tolist()[0]],
            })
    return detections


def detect_objects(image_url: str, conf: float = 0.25) -> list[dict]:
    if image_url.startswith(("http://", "https://")):
        response = httpx.get(image_url, timeout=10.0, follow_redirects=True)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("image/"):
            raise ValueError(f"La URL no devolvió una imagen válida (content-type={content_type})")
        image_bytes = response.content
    else:
        file_path = Path(image_url)
        if not file_path.is_file():
            raise FileNotFoundError(f"Stored image file not found: {image_url}")
        image_bytes = file_path.read_bytes()

    return detect_objects_from_bytes(image_bytes, conf=conf)