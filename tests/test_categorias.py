from sqlmodel import Session, SQLModel, create_engine, select

from app.categorias.models import Categoria
from app.categorias.service import seed_missing_categories


def test_seed_missing_categories_is_idempotent_and_preserves_existing_rows():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        barroco = Categoria(id=41, nombre="Barroco", slug="barroco")
        cubismo = Categoria(id=42, nombre="Cubismo", slug="cubismo")
        session.add_all([barroco, cubismo])
        session.commit()

        seed_missing_categories(session)
        first_result = session.exec(select(Categoria).order_by(Categoria.id)).all()
        first_ids = {category.slug: category.id for category in first_result}

        seed_missing_categories(session)
        second_result = session.exec(select(Categoria).order_by(Categoria.id)).all()
        assert session.get(Categoria, 41).nombre == "Barroco"
        assert session.get(Categoria, 42).nombre == "Cubismo"
        assert session.get(Categoria, first_ids["impresionismo"]) is not None
        assert session.get(Categoria, first_ids["expresionismo"]) is not None
        assert session.get(Categoria, first_ids["pop-art"]) is not None

    assert {category.nombre for category in second_result} == {
        "Barroco",
        "Cubismo",
        "Impresionismo",
        "Expresionismo",
        "Pop Art",
    }
    assert len({category.id for category in second_result}) == 5
    assert len(second_result) == 5
    assert first_ids["barroco"] == 41
    assert first_ids["cubismo"] == 42
    assert {category.slug: category.id for category in second_result} == first_ids


def test_seed_missing_categories_creates_all_categories_once():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        seed_missing_categories(session)
        seed_missing_categories(session)
        categories = session.exec(select(Categoria)).all()

    assert {category.nombre for category in categories} == {
        "Barroco",
        "Cubismo",
        "Impresionismo",
        "Expresionismo",
        "Pop Art",
    }
    assert len(categories) == 5
    assert len({category.id for category in categories}) == 5
