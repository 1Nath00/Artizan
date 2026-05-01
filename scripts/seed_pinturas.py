"""
Script para subir las pinturas del dataset a Cloudinary y poblar la tabla `pinturas`.

Uso:
    python scripts/seed_pinturas.py

Es idempotente: omite imágenes cuyo filename_original ya existe en la BD.
"""

import re
import sys
from pathlib import Path

import cloudinary
import cloudinary.uploader
from sqlmodel import Session, SQLModel, create_engine, select

# Añadir la raíz del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import (
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
    CLOUDINARY_CLOUD_NAME,
    DATABASE_URL,
)
from app.pinturas.models import Pintura  # noqa: F401

DATASET_DIR = Path(__file__).parent.parent / "dataset"
CATEGORIAS = ["Baroque", "Cubism"]

# ── Cloudinary config ────────────────────────────────────────────────────────

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True,
)

# ── Filename parsing ─────────────────────────────────────────────────────────

# Matches trailing year: -YEAR, -YEAR-N, -YEAR(N), etc.
_YEAR_RE = re.compile(r"-(\d{4})(?:\(\d+\)|(?:-\d+))*$")


def parse_filename(filename: str, categoria: str) -> dict:
    """
    Extrae autor, nombre, año del nombre de archivo del dataset.
    Formato: <autor>_<nombre-pintura>[-<año>][sufijo].jpg
    """
    base = filename.rsplit(".", 1)[0]

    if "_" not in base:
        nombre = base.replace("-", " ").title()
        return {"autor": nombre, "nombre": nombre, "año": None, "categoria": categoria}

    autor_raw, painting_raw = base.split("_", 1)
    autor = autor_raw.replace("-", " ").title()

    year_match = _YEAR_RE.search(painting_raw)
    if year_match:
        año = int(year_match.group(1))
        nombre_raw = painting_raw[: year_match.start()]
    else:
        año = None
        nombre_raw = painting_raw

    nombre = nombre_raw.replace("-", " ").replace("_", " ").title()
    return {"autor": autor, "nombre": nombre, "año": año, "categoria": categoria}


# ── Cloudinary upload ────────────────────────────────────────────────────────


def upload_image(filepath: Path, categoria: str) -> str:
    """Sube una imagen a Cloudinary y devuelve la URL segura."""
    stem = filepath.stem
    autor_raw = stem.split("_")[0] if "_" in stem else stem
    public_id = f"artizan/pinturas/{categoria}/{autor_raw}/{stem}"

    result = cloudinary.uploader.upload(
        str(filepath),
        public_id=public_id,
        overwrite=False,
        resource_type="image",
    )
    return result["secure_url"]


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    if not CLOUDINARY_CLOUD_NAME or not CLOUDINARY_API_KEY or not CLOUDINARY_API_SECRET:
        print(
            "ERROR: Falta configuración de Cloudinary.\n"
            "Agrega las variables al archivo .env:\n"
            "  CLOUDINARY_CLOUD_NAME=...\n"
            "  CLOUDINARY_API_KEY=...\n"
            "  CLOUDINARY_API_SECRET=...\n"
        )
        sys.exit(1)

    engine = create_engine(DATABASE_URL)
    SQLModel.metadata.create_all(engine)

    total_ok = 0
    total_skip = 0
    total_error = 0

    with Session(engine) as session:
        for categoria in CATEGORIAS:
            folder = DATASET_DIR / categoria
            if not folder.exists():
                print(f"[WARN] Carpeta no encontrada: {folder}")
                continue

            files = sorted(folder.glob("*.jpg"))
            print(f"\n── {categoria} ({len(files)} archivos) ──────────────────────────")

            for filepath in files:
                filename = filepath.name

                # Chequeo de idempotencia
                existing = session.exec(
                    select(Pintura).where(Pintura.filename_original == filename)
                ).first()
                if existing:
                    print(f"  SKIP  {filename}")
                    total_skip += 1
                    continue

                parsed = parse_filename(filename, categoria)
                try:
                    url = upload_image(filepath, categoria)
                    pintura = Pintura(
                        autor=parsed["autor"],
                        nombre=parsed["nombre"],
                        año=parsed["año"],
                        categoria=parsed["categoria"],
                        url_imagen=url,
                        filename_original=filename,
                    )
                    session.add(pintura)
                    session.commit()
                    print(f"  OK    {filename}")
                    total_ok += 1
                except Exception as exc:
                    session.rollback()
                    print(f"  ERROR {filename}: {exc}")
                    total_error += 1

    print(
        f"\n{'═'*50}\n"
        f"Listo. Subidas: {total_ok} | Omitidas: {total_skip} | Errores: {total_error}\n"
    )


if __name__ == "__main__":
    main()
