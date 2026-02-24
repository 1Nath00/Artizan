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
