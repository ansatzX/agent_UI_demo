from backend.src.gradio_app.app import create_app


def _is_load_target(targets):
    return targets in ([(0, "load")], [[0, "load"]]) or str(targets) in ("[(0, 'load')]", "[[0, 'load']]")


def test_gradio_load_does_not_call_blocking_mcp_connect():
    app = create_app()
    deps = app.config.get("dependencies", [])
    load_deps = [d for d in deps if _is_load_target(d.get("targets"))]

    assert all("connect_mcp_servers" not in str(d.get("api_name")) for d in load_deps)


def test_hotspot_scan_uses_single_click_event_for_progress_and_history():
    app = create_app()
    deps = app.config.get("dependencies", [])
    scan_deps = [d for d in deps if d.get("api_name") == "scan_hotspots_progress"]

    assert len(scan_deps) == 1
    assert len(scan_deps[0].get("outputs", [])) == 2
