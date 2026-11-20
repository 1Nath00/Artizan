from unittest.mock import Mock

import httpx
import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, SQLModel, create_engine, select

from app.categorias.models import Categoria
from app.pinturas.models import Pintura
from scripts import seed_pinturas as seed


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("claude-monet_water-lilies-1916.jpg", ("Claude Monet", "Water Lilies", 1916)),
        ("andy-warhol_flowers-1964(2)-1.JPG", ("Andy Warhol", "Flowers", 1964)),
        ("abraham-manievich_autumn-day.jpg", ("Abraham Manievich", "Autumn Day", None)),
        ("guido-reni_not_detected_232244-1635.jpg", ("Guido Reni", "Not Detected 232244", 1635)),
        ("Guernica-Picasso-1937.png", ("Picasso", "Guernica", 1937)),
    ],
)
def test_parse_dataset_and_declared_format(filename, expected):
    parsed = seed.parse_filename(filename)
    assert (parsed["autor"], parsed["nombre"], parsed["año"]) == expected


@pytest.mark.parametrize(
    "filename", ["invalid.jpg", "_painting-1910.jpg", "author_-1910.jpg", "title-author-year.jpg",
                 "ambiguous-title-author-name-1900.jpg", "author_title-0000.jpg"]
)
def test_reject_invalid_or_ambiguous_names(filename):
    with pytest.raises(ValueError):
        seed.parse_filename(filename)


@pytest.fixture
def import_environment(tmp_path, monkeypatch):
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    for folder in seed.CATEGORIAS:
        (tmp_path / folder).mkdir()
        (tmp_path / folder / f"artist_{folder.lower()}-1900.jpg").write_bytes(b"image")
    upload = Mock(side_effect=lambda path, folder: seed.UploadedImage(
        f"https://example.test/{folder}/{path.name}", f"{folder}/{path.stem}", True
    ))
    verify = Mock()
    destroy = Mock(return_value={"result": "ok"})
    monkeypatch.setattr(seed, "upload_image", upload)
    monkeypatch.setattr(seed, "verify_image", verify)
    monkeypatch.setattr(seed.cloudinary.uploader, "destroy", destroy)
    with Session(engine) as session:
        session.add_all(
            Categoria(nombre=slug, slug=slug)
            for slug in ["barroco", "cubismo", *seed.CATEGORIAS.values()]
        )
        session.commit()
        yield session, tmp_path, upload, verify, destroy
    engine.dispose()


def test_import_preserves_existing_styles_and_retries_without_duplicates(import_environment):
    session, dataset, upload, verify, _ = import_environment
    protected = []
    for slug in ("barroco", "cubismo"):
        category = session.exec(select(Categoria).where(Categoria.slug == slug)).one()
        painting = Pintura(
            autor="Original", nombre=slug, año=1600, categoria_id=category.id,
            filename_original=f"{slug}.jpg", url_imagen=f"https://example.test/{slug}.jpg",
        )
        session.add(painting)
        protected.append(painting)
    session.commit()
    before = [painting.model_dump() for painting in protected]

    first = seed.run_import(session, dataset)
    second = seed.run_import(session, dataset)
    assert (first.created, first.errors, second.created, second.skipped) == (3, 0, 0, 3)
    assert upload.call_count == 3
    assert verify.call_count == 6
    assert [painting.model_dump() for painting in protected] == before
    for folder, slug in seed.CATEGORIAS.items():
        painting = session.exec(select(Pintura).where(
            Pintura.filename_original == f"artist_{folder.lower()}-1900.jpg"
        )).one()
        assert painting.categoria.slug == slug
        assert painting.url_imagen == f"https://example.test/{folder}/artist_{folder.lower()}-1900.jpg"
        assert (painting.autor, painting.nombre, painting.año) == (
            "Artist", folder.lower().replace("_", " ").title(), 1900
        )


def test_dry_run_and_verification_only_never_upload(import_environment):
    session, dataset, upload, _, _ = import_environment
    planned = seed.run_import(session, dataset, dry_run=True)
    missing = seed.run_import(session, dataset, verify_only=True)
    assert (planned.planned, planned.errors, missing.errors) == (3, 0, 3)
    assert session.exec(select(Pintura)).all() == []
    upload.assert_not_called()


def test_conflicts_and_invalid_files_are_reported_but_valid_undated_file_imports(import_environment):
    session, dataset, upload, _, _ = import_environment
    folders = list(seed.CATEGORIAS)
    for folder in folders[:2]:
        (dataset / folder / "same_painting-1900.jpg").write_bytes(b"image")
    (dataset / folders[0] / "invalid.jpg").write_bytes(b"image")
    (dataset / folders[0] / "artist_undated.jpg").write_bytes(b"image")
    old_category = session.exec(select(Categoria).where(Categoria.slug == "cubismo")).one()
    existing = Pintura(
        autor="Artist", nombre="Old", categoria_id=old_category.id,
        filename_original="artist_old.jpg", url_imagen="https://example.test/old.jpg",
    )
    session.add(existing)
    session.commit()
    (dataset / folders[0] / existing.filename_original).write_bytes(b"image")

    result = seed.run_import(session, dataset)
    assert (result.created, result.errors, result.undated) == (4, 4, 2)
    assert upload.call_count == 4
    assert session.exec(select(Pintura).where(
        Pintura.filename_original == "artist_undated.jpg"
    )).one().año is None
    assert session.exec(select(Pintura).where(
        Pintura.filename_original == "same_painting-1900.jpg"
    )).all() == []
    session.refresh(existing)
    assert existing.categoria_id == old_category.id


def test_database_failure_compensates_owned_upload_and_continues(import_environment, monkeypatch):
    session, dataset, upload, _, destroy = import_environment
    original_commit = session.commit
    commits = 0

    def fail_once():
        nonlocal commits
        commits += 1
        if commits == 1:
            raise SQLAlchemyError("write failed")
        original_commit()

    monkeypatch.setattr(session, "commit", fail_once)
    result = seed.run_import(session, dataset)
    assert (result.created, result.errors) == (2, 1)
    assert len(session.exec(select(Pintura)).all()) == 2
    assert upload.call_count == 3
    destroy.assert_called_once()


def test_upload_failure_does_not_create_row_and_continues(import_environment):
    session, dataset, upload, _, destroy = import_environment
    upload.side_effect = [
        RuntimeError("upload failed"),
        seed.UploadedImage("https://example.test/b.jpg", "b", True),
        seed.UploadedImage("https://example.test/c.jpg", "c", True),
    ]
    result = seed.run_import(session, dataset)
    assert (result.created, result.errors) == (2, 1)
    assert len(session.exec(select(Pintura)).all()) == 2
    destroy.assert_not_called()


def test_unreachable_url_does_not_create_row_or_delete_preexisting_asset(import_environment):
    session, dataset, upload, verify, destroy = import_environment
    upload.side_effect = None
    upload.return_value = seed.UploadedImage("https://example.test/old.jpg", "old", False)
    verify.side_effect = RuntimeError("image not accessible")
    result = seed.run_import(session, dataset)
    assert (result.created, result.errors) == (0, 3)
    assert session.exec(select(Pintura)).all() == []
    destroy.assert_not_called()


def test_missing_category_fails_before_upload(import_environment):
    session, dataset, upload, _, _ = import_environment
    category = session.exec(select(Categoria).where(Categoria.slug == "pop-art")).one()
    session.delete(category)
    session.commit()
    with pytest.raises(RuntimeError, match="pop-art"):
        seed.run_import(session, dataset)
    upload.assert_not_called()


def test_upload_uses_stable_id_and_proves_ownership_from_context(monkeypatch, tmp_path):
    def response(path, **options):
        return {
            "public_id": options["public_id"],
            "secure_url": "https://example.test/image.jpg",
            "context": {"custom": options["context"]},
        }

    upload = Mock(side_effect=response)
    monkeypatch.setattr(seed.cloudinary.uploader, "upload", upload)
    path = tmp_path / "artist_title-1900.jpg"
    first = seed.upload_image(path, "Impressionism")
    second = seed.upload_image(path, "Impressionism")
    assert first.public_id == second.public_id == "artizan/pinturas/Impressionism/artist/artist_title-1900"
    assert first.owned and second.owned
    assert upload.call_args.kwargs["overwrite"] is False
    upload.side_effect = None
    upload.return_value = {"public_id": first.public_id, "secure_url": first.url}
    assert not seed.upload_image(path, "Impressionism").owned


@pytest.mark.parametrize(
    ("status", "content_type", "content", "error"),
    [(200, "image/jpeg", b"image", None), (404, "image/jpeg", b"x", httpx.HTTPStatusError),
     (200, "text/html", b"html", ValueError), (200, "image/jpeg", b"", ValueError),
     (200, "image/jpeg", b"different image", ValueError)],
)
def test_url_verification_checks_status_image_type_and_content(
    monkeypatch, tmp_path, status, content_type, content, error
):
    path = tmp_path / "image.jpg"
    path.write_bytes(b"image")
    transport = httpx.MockTransport(lambda request: httpx.Response(
        status, headers={"content-type": content_type}, content=content
    ))
    with httpx.Client(transport=transport) as client:
        monkeypatch.setattr(seed.httpx, "stream", lambda method, url, **kwargs: client.stream(method, url))
        if error:
            with pytest.raises(error):
                seed.verify_image("https://example.test/image.jpg", path)
        else:
            seed.verify_image("https://example.test/image.jpg", path)


def test_lost_commit_response_keeps_persisted_image(import_environment, monkeypatch):
    session, dataset, _, _, destroy = import_environment
    original_commit = session.commit

    def commit_then_fail():
        original_commit()
        raise SQLAlchemyError("commit response lost")

    monkeypatch.setattr(session, "commit", commit_then_fail)
    result = seed.run_import(session, dataset)
    assert result.errors == 3
    assert len(session.exec(select(Pintura)).all()) == 3
    destroy.assert_not_called()
    resumed = seed.run_import(session, dataset)
    assert (resumed.skipped, resumed.errors) == (3, 0)
