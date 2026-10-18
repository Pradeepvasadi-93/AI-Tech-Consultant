from app.agents import build_scope_graph, compare_requirements

def test_graph_compiles():
    graph = build_scope_graph()
    assert graph is not None

def test_change_report_detects_add_remove_modify():
    old = [
        {"id": "REQ-001", "title": "Search", "description": "Name search", "status": "confirmed"},
        {"id": "REQ-002", "title": "CSV export", "description": "Export reports", "status": "confirmed"},
    ]
    new = [
        {"id": "REQ-001", "title": "Search", "description": "Name and category search", "status": "confirmed"},
        {"id": "REQ-003", "title": "Spanish search", "description": "Search Spanish catalog", "status": "confirmed"},
    ]
    result = compare_requirements(old, new)
    assert result["counts"] == {"added": 1, "modified": 1, "removed": 1}
