from backend.src.hotspots.history import HotspotHistoryStore


def test_hotspot_history_store_appends_and_lists_runs(tmp_path):
    store = HotspotHistoryStore(tmp_path / "history.jsonl")

    run = store.append_run(keywords="科技", sources=["知乎 MCP"], markdown="结果", cards_count=2)
    rows = store.list_runs()

    assert run["run_id"]
    assert rows[0]["keywords"] == "科技"
    assert rows[0]["cards_count"] == 2
    assert store.get_run(run["run_id"])["markdown"] == "结果"
