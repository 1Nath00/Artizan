# Guía de Configuración PostgreSQL con SQLModel

Esta guía te ayudará a configurar PostgreSQL para tu proyecto Artizan que ahora usa SQLModel.

## ¿Qué es SQLModel?

SQLModel es una biblioteca que combina **SQLAlchemy** (para el ORM) con **Pydantic** (para validación). Es perfect para FastAPI porque:
- Los modelos funcionan tanto para la base de datos como para validación de datos
- Sintaxis más simple y legible que SQLAlchemy puro
- Integración nativa con FastAPI
- Type hints completos

## 📋 Requisitos Previos

- Python 3.10 o superior
- PostgreSQL 12 o superior instalado

## 🚀 Instalación de PostgreSQL

### Windows

1. **Descargar PostgreSQL**
   - Visita: https://www.postgresql.org/download/windows/
   - Descarga el instalador para Windows
   - Ejecuta el instalador y sigue las instrucciones

2. **Durante la instalación**
   - Establece una contraseña para el usuario `postgres` (¡guárdala!)
   - Puerto por defecto: `5432`
   - Instala pgAdmin 4 (herramienta gráfica útil)

3. **Verificar instalación**
   ```bash
   psql --version
   ```

### Linux (Ubuntu/Debian)

```bash
# Actualizar repositorios
sudo apt update

# Instalar PostgreSQL
sudo apt install postgresql postgresql-contrib

# Verificar que el servicio esté corriendo
sudo systemctl status postgresql

# Iniciar PostgreSQL si no está corriendo
sudo systemctl start postgresql
```

### macOS

```bash
# Usando Homebrew
brew install postgresql@15

# Iniciar el servicio
brew services start postgresql@15
```

## 🗄️ Configuración de la Base de Datos

### 1. Acceder a PostgreSQL

**Windows:**
```bash
# Abrir PowerShell o CMD como administrador
psql -U postgres
```

**Linux:**
```bash
sudo -u postgres psql
```

### 2. Crear la Base de Datos

```sql
-- Crear la base de datos
CREATE DATABASE artizan_db;

-- Crear un usuario específico (opcional pero recomendado)
CREATE USER artizan_user WITH PASSWORD 'tu_contraseña_segura';

-- Dar permisos al usuario
GRANT ALL PRIVILEGES ON DATABASE artizan_db TO artizan_user;

-- En PostgreSQL 15+, también necesitas:
\c artizan_db
GRANT ALL ON SCHEMA public TO artizan_user;

-- Salir
\q
```

## ⚙️ Configuración del Proyecto

### 1. Instalar Dependencias

```bash
pip install -r requirements.txt
```

Esto instalará:
- `sqlmodel>=0.0.16` - ORM con Pydantic
- `psycopg2-binary>=2.9.9` - Driver de PostgreSQL
- `alembic>=1.13.0` - Migraciones de base de datos

### 2. Configurar Variables de Entorno

Edita el archivo `.env`:

```env
SECRET_KEY=tu-clave-secreta-super-segura-cambiala
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Comentar SQLite
# DATABASE_URL=sqlite:///./artizan.db

# Descomentar y configurar PostgreSQL
DATABASE_URL=postgresql://artizan_user:tu_contraseña_segura@localhost:5432/artizan_db

UPLOAD_DIR=uploads
MAX_IMAGE_SIZE_MB=10
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080
```

**Formato de URL:**
```
postgresql://usuario:contraseña@host:puerto/nombre_base_datos
```

**Ejemplos:**
- Local: `postgresql://artizan_user:password123@localhost:5432/artizan_db`
- Docker: `postgresql://artizan_user:password123@db:5432/artizan_db`
- Remoto: `postgresql://user:pass@servidor.com:5432/artizan_db`

### 3. Ejecutar Migraciones

```bash
# Ver el estado actual
alembic current

# Aplicar todas las migraciones
alembic upgrade head

# Verificar que se aplicaron
alembic current
```

### 4. Verificar la Instalación

```bash
# Conectar a PostgreSQL
psql -U artizan_user -d artizan_db

# Ver las tablas creadas
\dt

# Ver la estructura de la tabla users
\d users

# Salir
\q
```

Deberías ver la tabla `users` con las columnas:
- `id` (integer, primary key)
- `username` (varchar, unique)
- `email` (varchar, unique)
- `hashed_password` (varchar)
- `is_active` (boolean)
- `created_at` (timestamp)

## 🧪 Probar la Aplicación

### 1. Iniciar el Servidor

```bash
uvicorn app.main:app --reload
```

### 2. Acceder a la Documentación

Abre tu navegador en: http://localhost:8000/docs

### 3. Registrar un Usuario

En Swagger UI (http://localhost:8000/docs):
1. Ve a `POST /auth/register`
2. Click en "Try it out"
3. Ingresa los datos:
   ```json
   {
     "username": "testuser",
     "email": "test@example.com",
     "password": "securepassword123"
   }
   ```
4. Click en "Execute"

### 4. Verificar en la Base de Datos

```bash
psql -U artizan_user -d artizan_db
SELECT * FROM users;
```

## 🔄 Crear Nuevas Migraciones

Cuando modifiques los modelos de SQLModel:

```bash
# Generar una nueva migración automáticamente
alembic revision --autogenerate -m "Descripción del cambio"

# Revisar el archivo generado en alembic/versions/

# Aplicar la migración
alembic upgrade head
```

## 📖 Ejemplo: Agregar un Nuevo Modelo

### 1. Crear el Modelo (app/posts/models.py)

```python
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship

class Post(SQLModel, table=True):
    """Modelo de publicación."""
    __tablename__ = "posts"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=200, nullable=False)
    content: str = Field(nullable=False)
    user_id: int = Field(foreign_key="users.id", nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relación (opcional)
    # user: Optional["User"] = Relationship(back_populates="posts")
```

### 2. Importar en alembic/env.py

```python
# Agregar la importación
from app.posts.models import Post  # noqa
```

### 3. Generar y Aplicar Migración

```bash
alembic revision --autogenerate -m "Add posts table"
alembic upgrade head
```

## 🛠️ Comandos Útiles de Alembic

```bash
# Ver historial de migraciones
alembic history

# Ver migración actual
alembic current

# Revertir una migración
alembic downgrade -1

# Revertir a una versión específica
alembic downgrade <revision_id>

# Volver a la migración inicial
alembic downgrade base

# Ver SQL sin ejecutarlo
alembic upgrade head --sql
```

## 🐳 Usar PostgreSQL con Docker

Si prefieres usar Docker:

### docker-compose.yml

```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: artizan_user
      POSTGRES_PASSWORD: artizan_pass
      POSTGRES_DB: artizan_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Comandos

```bash
# Iniciar PostgreSQL
docker-compose up -d

# Ver logs
docker-compose logs -f db

# Detener
docker-compose down

# Detener y eliminar datos
docker-compose down -v
```

### .env para Docker

```env
DATABASE_URL=postgresql://artizan_user:artizan_pass@localhost:5432/artizan_db
```

## 🔧 Troubleshooting

### Error: "Connection refused"

**Problema:** No se puede conectar a PostgreSQL.

**Soluciones:**
1. Verificar que PostgreSQL esté corriendo:
   ```bash
   # Linux
   sudo systemctl status postgresql

   # Windows (en Services o Task Manager)
   # Buscar "postgresql-x64-15"
   ```

2. Verificar el puerto:
   ```bash
   # Linux/Mac
   sudo netstat -plnt | grep 5432

   # Windows
   netstat -an | findstr 5432
   ```

3. Verificar archivo de configuración PostgreSQL:
   - Linux: `/etc/postgresql/15/main/postgresql.conf`
   - Asegurarse de que `listen_addresses = 'localhost'` o `'*'`

### Error: "password authentication failed"

**Solución:**
1. Verificar credenciales en `.env`
2. Resetear contraseña:
   ```sql
   ALTER USER artizan_user WITH PASSWORD 'nueva_contraseña';
   ```

### Error: "FATAL: database does not exist"

**Solución:**
```bash
psql -U postgres
CREATE DATABASE artizan_db;
\q
```

### Error: "ModuleNotFoundError: No module named 'sqlmodel'"

**Solución:**
```bash
pip install sqlmodel
```

## 📚 Recursos Adicionales

- [Documentación de SQLModel](https://sqlmodel.tiangolo.com/)
- [Documentación de PostgreSQL](https://www.postgresql.org/docs/)
- [Documentación de Alembic](https://alembic.sqlalchemy.org/)
- [Tutorial de FastAPI con SQLModel](https://sqlmodel.tiangolo.com/tutorial/fastapi/)

## 🎯 Diferencias Clave entre SQLAlchemy y SQLModel

### SQLAlchemy (Antiguo)
```python
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    is_active = Column(Boolean, default=True)
```

### SQLModel (Actual)
```python
from sqlmodel import SQLModel, Field
from typing import Optional

class User(SQLModel, table=True):
    __tablename__ = "users"
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    is_active: bool = Field(default=True)
```

**Ventajas de SQLModel:**
- Type hints nativos de Python
- Validación automática con Pydantic
- Menos código boilerplate
- Mejor experiencia con IDEs
- Un solo modelo para DB y API

## ✅ Checklist de Migración Completada

- [x] SQLModel agregado a requirements.txt
- [x] database.py actualizado para usar SQLModel
- [x] Modelos migrados a SQLModel (User)
- [x] Schemas actualizados (herencia de SQLModel)
- [x] Servicios actualizados (Session y select)
- [x] Routers actualizados (get_session)
- [x] Dependencies actualizados
- [x] Alembic configurado para SQLModel
- [x] Migración inicial creada y probada

¡Tu proyecto ahora está usando SQLModel y está listo para PostgreSQL! 🎉
