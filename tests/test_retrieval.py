"""F3: RRF-fúzió, BM25-tokenizálás, idézet-ellenőrzés, JSON-kinyerés."""
from vikrag.generate.answer import verify_quote
from vikrag.index.bm25 import tokenize
from vikrag.llm.client import parse_json
from vikrag.retrieve.hybrid import rrf


def test_rrf_matches_slide_example():
    # órai dia (Cormack et al.): A (1., 50.), B (3., 3.), C (10., 1.) -> RRF, k=60: B > C > A
    bm25 = [("A", 0)] + [(f"x{i}", 0) for i in range(1)] + [("B", 0)] + [(f"y{i}", 0) for i in range(6)] + [("C", 0)]
    dense = [("C", 0), ("z", 0), ("B", 0)] + [(f"w{i}", 0) for i in range(46)] + [("A", 0)]
    assert [d for d, *_ in rrf({"bm25": bm25, "dense": dense}, k=60)[:3]] == ["B", "C", "A"]


def test_rrf_records_ranks():
    fused = rrf({"bm25": [(1, 9.0), (2, 5.0)], "dense": [(2, 0.9)]}, k=60)
    top_id, _, ranks, raw = fused[0]
    assert top_id == 2 and ranks == {"bm25": 2, "dense": 1} and raw["dense"] == 0.9


def test_tokenize_keeps_subject_codes_and_stems():
    toks = tokenize("A VIAUAC15 tárgyból vizsgázhatok az 55/A. § szerint")
    assert "viauac15" in toks and "55/a" in toks and "tárgy" in toks
    assert "az" not in toks  # stopszó


def test_verify_quote_exact_fuzzy_and_wrong():
    text = "A kérelmező – a képzési és létszámkapacitásokra is figyelemmel – alapképzési szakra legalább egy lezárt aktív félévet követően vehető át."
    assert verify_quote("legalább egy lezárt aktív félévet követően", text) == 100
    assert verify_quote("legalább egy lezárt aktiv félevet követően", text) >= 85  # OCR-szerű eltérés
    assert verify_quote("legalább három lezárt passzív félév után bárki", text) < 85


def test_parse_json_with_fence():
    assert parse_json('```json\n{"answerable": true, "answer": "x"}\n```') == {"answerable": True, "answer": "x"}


def test_weighted_rrf_and_zero_weight():
    from vikrag.retrieve.hybrid import rrf

    r = {"bm25:orig": [(1, 9.0), (2, 8.0)], "dense:orig": [(2, 0.9), (3, 0.8)]}
    assert [x[0] for x in rrf(r, 60, {"bm25": 0.0})] == [2, 3]
    assert rrf(r, 60, {"bm25": 0.5})[0][0] == 2


def test_sandwich_order():
    from vikrag.pipeline import sandwich

    assert sandwich([1, 2, 3, 4, 5]) == [1, 3, 5, 4, 2]


def test_glossary_expansion():
    from vikrag.retrieve.query import expand_glossary, glossary_terms

    assert "záróvizsga" in " ".join(glossary_terms("Mikor lesz a zv?"))
    assert "zárthelyi dolgozat" in expand_glossary("Bebuktam a zh-t")
    assert expand_glossary("Mennyi a kreditek száma?") == "Mennyi a kreditek száma?"
    assert not glossary_terms("hiteles másolat kérése")


def test_context_filter_crossref_sandwich():
    from types import SimpleNamespace

    from vikrag.pipeline import RAG, RAGConfig
    from vikrag.retrieve.hybrid import Hit

    chunks = [{"chunk_id": f"c{i}", "crossrefs": ["c9"] if i == 0 else []} for i in range(10)]
    fake = SimpleNamespace(chunks=chunks)
    hits = [Hit(i, chunks[i], s, {}, {"rerank": s}) for i, s in enumerate([0.9, 0.5, 0.04, 0.01])]
    rag = RAG(RAGConfig(min_score=0.05), retriever=fake)
    assert [h.chunk["chunk_id"] for h in rag.context(hits)] == ["c0", "c1"]
    rag = RAG(RAGConfig(min_score=0.95, min_keep=1), retriever=fake)
    assert [h.chunk["chunk_id"] for h in rag.context(hits)] == ["c0"]
    rag = RAG(RAGConfig(crossref=2, order="sandwich", min_score=0.0), retriever=fake)
    assert [h.chunk["chunk_id"] for h in rag.context(hits)] == ["c0", "c2", "c9", "c3", "c1"]
