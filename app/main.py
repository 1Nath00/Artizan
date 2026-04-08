from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_api_router
from app.config import ALLOWED_ORIGINS
from app.database import init_db
from app.images.router import router as images_router
from app.middleware import LoggingMiddleware
from app.models.cnn.router import router as cnn_router
from app.models.nlp.router import router as nlp_router

# Create database tables
init_db()

app = FastAPI(
    title="Artizan API",
    description=(
        "API for Artizan — features user authentication, image management, "
        "CNN image classification (ResNet-50), and NLP text generation (GPT-2)."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(LoggingMiddleware)

app.include_router(auth_api_router)
app.include_router(images_router)
app.include_router(cnn_router)
app.include_router(nlp_router)


@app.get("/", tags=["root"])
def root():
    return {"message": "Welcome to Artizan API", "docs": "/docs"}


@app.get("/health", tags=["root"])
def health():
    return {"status": "ok"}
