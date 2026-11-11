import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY: str = os.getenv("SECRET_KEY", "change-this-secret-key-in-production")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./artizan.db")

UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
MAX_IMAGE_SIZE_MB: int = int(os.getenv("MAX_IMAGE_SIZE_MB", "10"))
ALLOWED_EXTENSIONS: set = {"jpg", "jpeg", "png", "gif", "webp"}
ALLOWED_ORIGINS: list = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# RAG (art knowledge base)
RAG_DATA_DIR: str = os.getenv("RAG_DATA_DIR", "rag_data")
RAG_DB_DIR: str = os.getenv("RAG_DB_DIR", "rag_db")
RAG_EMBEDDING_MODEL: str = os.getenv("RAG_EMBEDDING_MODEL", "intfloat/multilingual-e5-small")
RAG_LLM_MODEL: str = os.getenv("RAG_LLM_MODEL", "llama3.2")
RAG_CHUNK_SIZE: int = int(os.getenv("RAG_CHUNK_SIZE", "900"))
RAG_CHUNK_OVERLAP: int = int(os.getenv("RAG_CHUNK_OVERLAP", "150"))
RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "5"))
RAG_TEMPERATURE: float = float(os.getenv("RAG_TEMPERATURE", "0.2"))
RAG_NUM_CTX: int = int(os.getenv("RAG_NUM_CTX", "4096"))
RAG_JUDGE_MODEL: str = os.getenv("RAG_JUDGE_MODEL", "llama3.2")
RAG_MIN_MENTIONS: int = int(os.getenv("RAG_MIN_MENTIONS", "20"))
OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Cloudinary
CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET", "")
