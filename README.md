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
| POST | `/images/analyze` | Subir imagen y ejecutar clasificación y detección |
| GET | `/images/` | Listar imágenes propias |
| GET | `/images/{id}` | Obtener metadata de una imagen |
| POST | `/images/{id}/description` | Generar y guardar la descripción RAG de una imagen |
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

## Importar las pinturas pendientes

El importador procesa exclusivamente `dataset/Impressionism`, `dataset/Expressionism`
y `dataset/Pop_Art`. Requiere el esquema migrado (`alembic upgrade head`), las
categorías `impresionismo`, `expresionismo` y `pop-art`, y las variables
`DATABASE_URL`, `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY` y
`CLOUDINARY_API_SECRET`. No crea tablas ni categorías.

Desde la raíz, en PowerShell:

```powershell
# Solo lectura: valida carpetas, categorías, nombres y conflictos.
.\.venv\Scripts\python.exe scripts\seed_pinturas.py --dry-run

# Carga real: consume cuota de Cloudinary.
.\.venv\Scripts\python.exe scripts\seed_pinturas.py

# QA: comprueba registros, metadatos y acceso HTTP a cada imagen, sin escribir.
.\.venv\Scripts\python.exe scripts\seed_pinturas.py --verify-only
```

El dataset real usa `autor_nombre-pintura[-año].jpg`; se reconocen sufijos de
duplicado como `-1900(2)-1`. Los archivos sin año se reportan como `SIN_ANIO`
y se guardan con año `NULL`, sin inventar fechas. También se admite
`nombrePintura-autor-año` cuando tiene exactamente tres partes; sin separador
entre autor y título, nombres con más partes son ambiguos y se rechazan.

`filename_original` sigue siendo único globalmente. Se conservan todos los
registros existentes, incluidos Barroco y Cubismo. Una coincidencia con otra
categoría se reporta sin modificarla. Si un nombre nuevo aparece en varias
carpetas pendientes, se omiten **todas** sus copias como ambiguas. Por esta
decisión, las copias conflictivas no se consideran cargables automáticamente.

Cada carga usa un identificador estable en Cloudinary y `overwrite=False`.
Antes de guardar se comprueba que la URL HTTPS responda correctamente con una
imagen no vacía y cuyo SHA-256 coincida con el archivo local; tras guardar se
relee el registro. Esta verificación descarga la imagen y consume transferencia.
Las reejecuciones verifican
los registros existentes sin duplicarlos ni cambiar metadatos. Ejecutar una sola
instancia del importador a la vez.

Ante un error individual, se informa el archivo y se continúa. Si falla el
guardado, se intenta retirar únicamente una imagen cuya creación por ese intento
se confirme mediante su contexto de Cloudinary; nunca se elimina una imagen
preexistente. Si la escritura pudo haberse confirmado, se consulta antes de
eliminar. Fallos de recuperación o respuestas de red perdidas requieren revisión:
Cloudinary y la base de datos no comparten una transacción atómica. Los recursos
conservados pueden recuperarse al reejecutar gracias al identificador estable.

El resumen informa creadas, existentes, pendientes válidas (simulación),
verificadas, sin año y errores. El código de salida es `1` si hubo errores,
incluidos nombres inválidos, conflictos o registros faltantes en verificación.
Las URLs deben ser accesibles con los permisos de entrega configurados; no se
cambian permisos para sortear errores.

---

## Notas sobre los modelos de IA

- **CNN (ResNet-50)**: Los pesos se descargan automáticamente de PyTorch Hub la primera vez que se llama al endpoint `/models/cnn/classify`. Requiere `torch` y `torchvision`.
- **NLP (GPT-2)**: El modelo se descarga de Hugging Face la primera vez que se llama a `/models/nlp/generate`. Requiere `transformers`.

Ambos modelos se cargan de forma *lazy* (solo cuando se usan) y se cachean en memoria para las peticiones siguientes.
