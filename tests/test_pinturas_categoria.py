from sqlmodel import Session, SQLModel, create_engine, select

from app.categorias.models import Categoria
from app.pinturas.models import Pintura
from app.pinturas.router import list_pinturas


def test_pinturas_reference_and_filter_categories_by_id():
    assert "categoria_id" in Pintura.__table__.columns
    assert "categoria" not in Pintura.__table__.columns
    assert Pintura.__table__.c.categoria_id.foreign_keys

    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        barroco = Categoria(nombre="Barroco", slug="barroco")
        cubismo = Categoria(nombre="Cubismo", slug="cubismo")
        session.add_all([barroco, cubismo])
        session.flush()

        barroco_painting = Pintura(
            autor="Rembrandt",
            nombre="Autorretrato",
            categoria_id=barroco.id,
            url_imagen="https://example.test/barroco.jpg",
            filename_original="barroco.jpg",
        )
        cubismo_painting = Pintura(
            autor="Picasso",
            nombre="Bodegón",
            categoria_id=cubismo.id,
            url_imagen="https://example.test/cubismo.jpg",
            filename_original="cubismo.jpg",
        )
        session.add_all([barroco_painting, cubismo_painting])
        session.commit()

        results = list_pinturas(
            categoria_id=barroco.id,
            autor=None,
            skip=0,
            limit=50,
            session=session,
        )
        stored_painting = session.exec(
            select(Pintura).where(Pintura.id == barroco_painting.id)
        ).one()

        assert [painting.categoria_id for painting in results] == [barroco.id]
        assert stored_painting.categoria.nombre == "Barroco"


def test_list_pinturas_by_categoria_slug(client, db_session):
    barroco = db_session.exec(
        select(Categoria).where(Categoria.slug == "barroco")
    ).one()
    cubismo = db_session.exec(
        select(Categoria).where(Categoria.slug == "cubismo")
    ).one()
    db_session.add_all(
        [
            Pintura(
                autor="Rembrandt",
                nombre="Autorretrato",
                categoria_id=barroco.id,
                url_imagen="https://example.test/barroco.jpg",
                filename_original="endpoint-barroco.jpg",
                descripcion="Un autorretrato del período barroco.",
            ),
            Pintura(
                autor="Picasso",
                nombre="Bodegón",
                categoria_id=cubismo.id,
                url_imagen="https://example.test/cubismo.jpg",
                filename_original="endpoint-cubismo.jpg",
            ),
        ]
    )
    db_session.commit()

    response = client.get("/pinturas/categoria/barroco")

    assert response.status_code == 200
    assert [painting["categoria_id"] for painting in response.json()] == [barroco.id]
    assert response.json()[0]["url_imagen"] == "https://example.test/barroco.jpg"
    assert response.json()[0]["descripcion"] == "Un autorretrato del período barroco."


def test_list_pinturas_by_categoria_slug_returns_404_for_unknown_slug(client):
    response = client.get("/pinturas/categoria/no-existe")

    assert response.status_code == 404
    assert response.json() == {"detail": "Categoría no encontrada"}


def test_search_pinturas_by_name_author_and_category(client, db_session):
    barroco = db_session.exec(
        select(Categoria).where(Categoria.slug == "barroco")
    ).one()
    db_session.add_all(
        [
            Pintura(
                autor="Leonardo da Vinci",
                nombre="La Gioconda",
                categoria_id=barroco.id,
                url_imagen="https://example.test/gioconda.jpg",
                filename_original="search-gioconda.jpg",
            ),
            Pintura(
                autor="Rembrandt",
                nombre="Autorretrato",
                categoria_id=barroco.id,
                url_imagen="https://example.test/autorretrato.jpg",
                filename_original="search-autorretrato.jpg",
            ),
        ]
    )
    db_session.commit()

    by_name = client.get("/pinturas/search", params={"q": "gioc"})
    by_author = client.get("/pinturas/search", params={"q": "rembrandt"})
    by_category = client.get("/pinturas/search", params={"q": "barroco"})

    assert by_name.status_code == 200
    assert [painting["nombre"] for painting in by_name.json()] == ["La Gioconda"]
    assert [painting["autor"] for painting in by_author.json()] == ["Rembrandt"]
    assert len(by_category.json()) == 2


def test_search_pinturas_requires_query(client):
    response = client.get("/pinturas/search")

    assert response.status_code == 422
