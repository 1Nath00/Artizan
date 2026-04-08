import logging
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Crear directorio de logs si no existe
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Configurar logger con múltiples handlers
logger = logging.getLogger("artizan.requests")
logger.setLevel(logging.INFO)

# Evitar duplicación de handlers si se recarga el módulo
if not logger.handlers:
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    
    # Handler para archivo con rotación (5 MB por archivo, hasta 10 archivos)
    file_handler = RotatingFileHandler(
        LOGS_DIR / "requests.log",
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=10,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    
    # Agregar ambos handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware para loggear todas las peticiones HTTP."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Capturar información de la petición
        method = request.method
        path = request.url.path
        query_params = str(request.query_params) if request.query_params else ""
        client_host = request.client.host if request.client else "unknown"
        
        # Iniciar temporizador
        start_time = time.time()
        
        # Log de la petición entrante
        logger.info(
            f"→ {method} {path}{f'?{query_params}' if query_params else ''} "
            f"from {client_host}"
        )
        
        # Procesar la petición
        try:
            response = await call_next(request)
            
            # Calcular tiempo de procesamiento
            process_time = time.time() - start_time
            
            # Log de la respuesta
            logger.info(
                f"← {method} {path} "
                f"Status: {response.status_code} "
                f"Duration: {process_time:.3f}s"
            )
            
            # Agregar header con tiempo de procesamiento
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            # Log de errores
            process_time = time.time() - start_time
            logger.error(
                f"✗ {method} {path} "
                f"Error: {str(e)} "
                f"Duration: {process_time:.3f}s"
            )
            raise
