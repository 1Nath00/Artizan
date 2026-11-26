import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY: str = os.getenv("SECRET_KEY", "change-this-secret-key-in-production")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./artizan.db")

UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
MAX_IMAGE_SIZE_MB: int = int(os.getenv("MAX_IMAGE_SIZE_MB", "10"))
ALLOWED_EXTENSIONS: set = {"jpg", "jpeg", "png", "gif", "webp"}
ALLOWED_ORIGINS: list = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# RAG (art knowledge base)
RAG_DATA_DIR: str = os.getenv("RAG_DATA_DIR", "rag_data")
RAG_DB_DIR: str = os.getenv("CHROMA_PATH", "rag_db")
RAG_EMBEDDING_MODEL: str = os.getenv("RAG_EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
RAG_LLM_MODEL: str = os.getenv("RAG_LLM_MODEL", "llama3.2")
RAG_CHUNK_SIZE: int = int(os.getenv("RAG_CHUNK_SIZE", "1000"))
RAG_CHUNK_OVERLAP: int = int(os.getenv("RAG_CHUNK_OVERLAP", "200"))
RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "10"))
RAG_TEMPERATURE: float = float(os.getenv("RAG_TEMPERATURE", "0.2"))
RAG_NUM_CTX: int = int(os.getenv("RAG_NUM_CTX", "4096"))
RAG_JUDGE_MODEL: str = os.getenv("RAG_JUDGE_MODEL", "llama3.2")
RAG_MIN_MENTIONS: int = int(os.getenv("RAG_MIN_MENTIONS", "20"))
OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Cloudinary
CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET", "")

# GROQ API Key
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

GROQ_IMAGE_DESCRIPTION_MODEL: str = os.getenv(
    "GROQ_IMAGE_DESCRIPTION_MODEL",
    "qwen/qwen3.8-27b",
)

# Búsqueda de pinturas por similitud visual.
# TODO: sustituir [] por los categoria_id reales de Barroco y Cubismo.
CATEGORIA_IDS_INDEXAR: list[int] = [
    int(value)
    for value in os.getenv("CATEGORIA_IDS_INDEXAR", "").split(",")
    if value.strip()
]
NOMBRE_COLECCION_IMAGENES: str = os.getenv(
    "NOMBRE_COLECCION_IMAGENES", "pinturas_imagenes_dino"
)
MODELO_EMBEDDINGS_IMAGEN: str = os.getenv(
    "MODELO_EMBEDDINGS_IMAGEN", "facebook/dinov2-small"
)
MODELO_SOLO_LOCAL: bool = os.getenv("MODELO_SOLO_LOCAL", "true").lower() in {
    "1",
    "true",
    "yes",
    "si",
    "sí",
}
TORCH_NUM_THREADS: int | None = (
    int(os.environ["TORCH_NUM_THREADS"])
    if os.getenv("TORCH_NUM_THREADS", "").strip()
    else None
)
UMBRAL_ENCONTRADA: float = float(os.getenv("UMBRAL_ENCONTRADA", "0.80"))
UMBRAL_DUDOSA: float = float(os.getenv("UMBRAL_DUDOSA", "0.60"))

# Nombres de columnas físicos: modificar únicamente aquí si el esquema difiere.
PINTURAS_TABLA: str = "pinturas"
PINTURA_ID_COLUMNA: str = "id"
PINTURA_URL_COLUMNA: str = "url_imagen"
PINTURA_AUTOR_COLUMNA: str = "autor"
PINTURA_ANIO_COLUMNA: str = "año"
PINTURA_DESCRIPCION_COLUMNA: str = "descripcion"
PINTURA_CATEGORIA_ID_COLUMNA: str = "categoria_id"