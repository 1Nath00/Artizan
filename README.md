# Artizan

API REST construida con **FastAPI** para el proyecto de trabajo de grado *Artizan*.

## Características

| Módulo | Descripción |
|---|---|
| **Auth** | Registro, login y protección de rutas con JWT (Bearer Token) |
| **Imágenes** | Subir, listar, obtener y eliminar imágenes |
| **CNN** | Clasificación de imágenes con ResNet-50 pre-entrenado en ImageNet |
| **NLP** | Generación de texto con GPT-2 (Hugging Face Transformers) |

---

## Estructura del proyecto

```
Artizan/
├── app/
│   ├── main.py            # Punto de entrada de FastAPI
│   ├── config.py          # Configuración / variables de entorno
│   ├── database.py        # Motor SQLAlchemy y sesión de BD
│   ├── auth/
│   │   ├── models.py      # Modelo ORM de Usuario
│   │   ├── schemas.py     # Schemas Pydantic (request/response)
│   │   ├── service.py     # Lógica de negocio y JWT
│   │   ├── dependencies.py# Dependencias FastAPI (usuario actual)
│   │   └── router.py      # Rutas /auth
│   ├── images/
│   │   ├── schemas.py     # Schemas de imagen
│   │   ├── service.py     # Guardado / gestión de archivos
│   │   └── router.py      # Rutas /images
│   └── models/
│       ├── cnn/
│       │   ├── model.py   # Clasificador ResNet-50
│       │   └── router.py  # Ruta /models/cnn/classify
│       └── nlp/
│           ├── model.py   # Generador GPT-2
│           └── router.py  # Ruta /models/nlp/generate
├── tests/
│   ├── conftest.py        # Fixtures compartidos (BD en memoria, cliente)
│   ├── test_auth.py
│   ├── test_images.py
│   ├── test_cnn.py
│   └── test_nlp.py
├── requirements.txt
└── .gitignore
```

---

## Instalación

### Requisitos previos
- Python 3.10+
- (Opcional) GPU con CUDA para acelerar CNN y NLP

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/1Nath00/Artizan.git
cd Artizan

# 2. Crear entorno virtual
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env        # editar con tus valores

# 5. Ejecutar el servidor
uvicorn app.main:app --reload
```

La API quedará disponible en `http://localhost:8000`.  
Documentación interactiva: `http://localhost:8000/docs`

---

## Variables de entorno

Crear un archivo `.env` en la raíz del proyecto:

```env
SECRET_KEY=your-super-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30
DATABASE_URL=sqlite:///./artizan.db
UPLOAD_DIR=uploads
MAX_IMAGE_SIZE_MB=10
```

---

## Endpoints principales

### Auth
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/auth/register` | Registrar un nuevo usuario |
| POST | `/auth/login` | Obtener token JWT |
| GET | `/auth/me` | Datos del usuario autenticado |

### Imágenes
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/images/upload` | Subir una imagen |
| GET | `/images/` | Listar imágenes propias |
| GET | `/images/{id}` | Obtener metadata de una imagen |
| GET | `/images/{id}/file` | Descargar el archivo de imagen |
| DELETE | `/images/{id}` | Eliminar una imagen |

### CNN – Clasificación de imágenes
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/models/cnn/classify` | Clasificar imagen (ResNet-50 / ImageNet) |

Parámetros: `top_k` (entero, 1-100) — número de predicciones a devolver.

### NLP – Generación de texto
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/models/nlp/generate` | Generar texto con GPT-2 |

Cuerpo JSON:
```json
{
  "prompt": "Había una vez",
  "max_new_tokens": 100,
  "num_return_sequences": 1,
  "temperature": 0.9,
  "top_p": 0.95,
  "do_sample": true
}
```

---

## Pruebas

```bash
pytest tests/ -v
```

---

## Notas sobre los modelos de IA

- **CNN (ResNet-50)**: Los pesos se descargan automáticamente de PyTorch Hub la primera vez que se llama al endpoint `/models/cnn/classify`. Requiere `torch` y `torchvision`.
- **NLP (GPT-2)**: El modelo se descarga de Hugging Face la primera vez que se llama a `/models/nlp/generate`. Requiere `transformers`.

Ambos modelos se cargan de forma *lazy* (solo cuando se usan) y se cachean en memoria para las peticiones siguientes.
