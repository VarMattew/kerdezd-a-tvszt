import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "eval"))

from metrics import citation_metrics, para_key, retrieval_metrics  # noqa: E402


def test_para_key():
    assert para_key("tvsz:54:4") == "tvsz:54"
    assert para_key("tvsz:231#7") == "tvsz:231"
    assert para_key("tjsz:m3:2:1") == "tjsz:m3:2"
    assert para_key("vik_bsc_zv:tvsz138:1") == "vik_bsc_zv:tvsz138"
    assert para_key("kp_bsc_info:targy:VIAUAC15") == "kp_bsc_info:targy:VIAUAC15"
    assert para_key("vik_kepzesi_tajekoztato:s13") == "vik_kepzesi_tajekoztato:s13"


def test_retrieval_metrics_basic():
    m = retrieval_metrics(["a", "x", "b"], ["b", "a"])
    assert m["hit@1"] == 1 and m["recall@1"] == 0.5 and m["recall@3"] == 1.0 and m["mrr"] == 1.0
    m = retrieval_metrics(["x", "y", "tvsz:54:2"], ["tvsz:54:4"], level="para")
    assert m["hit@3"] == 1 and abs(m["mrr"] - 1 / 3) < 1e-9
    assert retrieval_metrics(["x"], ["a"])["ndcg@10"] == 0.0


def test_retrieval_counts_each_gold_once():
    m = retrieval_metrics(["tvsz:5:1", "tvsz:5:2"], ["tvsz:5:1"], level="para")
    assert m["recall@10"] == 1.0 and m["ndcg@10"] == 1.0


def test_citation_metrics():
    m = citation_metrics(["a", "x"], ["a", "b"])
    assert m == {"cit_precision": 0.5, "cit_recall": 0.5}


def test_equivalence_groups_count_once():
    gold = ["tvsz:149:3", "vik_msc_zv:tvsz149:3", "tvsz:150:1"]
    groups = [["tvsz:149:3", "vik_msc_zv:tvsz149:3"], ["tvsz:150:1"]]
    m = retrieval_metrics(["vik_msc_zv:tvsz149:3", "tvsz:149:3", "x"], gold, groups=groups)
    assert m["recall@3"] == 0.5 and m["mrr"] == 1.0
    assert citation_metrics(["tvsz:149:3"], gold, groups=groups)["cit_recall"] == 0.5
