from app.models.rag import service


class FakeCollection:
    def __init__(self):
        self.ids = ["semantic", "related", "exact"]
        self.documents = [
            "Una descripción general de un movimiento artístico.",
            "El arte se transforma con el paso del tiempo.",
            "El cubismo representa objetos con formas geométricas.",
        ]
        self.metadatas = [{"filename": name, "chunk": 0} for name in self.ids]

    def count(self):
        return len(self.ids)

    def query(self, query_embeddings, n_results):
        assert n_results == len(self.ids)
        return {
            "documents": [self.documents],
            "metadatas": [self.metadatas],
            "distances": [[0.1, 0.2, 0.3]],
        }


def test_retrieve_uses_lexical_match_to_rerank_semantic_candidates(monkeypatch):
    collection = FakeCollection()
    monkeypatch.setattr(service, "_get_collection", lambda: collection)
    monkeypatch.setattr(service, "_embed_query", lambda question: [[0.0]])

    results = service.retrieve("¿Qué es el cubismo?", k=1)

    assert results[0]["filename"] == "exact"
    assert results[0]["distance"] == 0.3


def test_retrieve_keeps_semantic_order_when_no_query_terms_match(monkeypatch):
    collection = FakeCollection()
    monkeypatch.setattr(service, "_get_collection", lambda: collection)
    monkeypatch.setattr(service, "_embed_query", lambda question: [[0.0]])

    results = service.retrieve("¿Dónde y cuándo?", k=2)

    assert [result["filename"] for result in results] == ["semantic", "related"]
