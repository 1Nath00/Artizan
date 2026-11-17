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
