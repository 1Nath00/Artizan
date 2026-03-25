from sqlmodel import create_engine, Session, SQLModel

from app.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=True  # Para debug, puedes poner False en producción
)


def get_session():
    """Obtiene una sesión de base de datos."""
    with Session(engine) as session:
        yield session


def init_db():
    """Crea todas las tablas en la base de datos."""
    SQLModel.metadata.create_all(engine)
