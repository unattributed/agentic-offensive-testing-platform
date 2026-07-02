from aotp.integrations.osmap_route_map import build_osmap_route_auth_map
from aotp.integrations.osmap_source_review import review_osmap_source


SOURCE = '''
@app.route("/login", methods=["GET", "POST"])
def login():
    return "login"

@app.route("/account/settings", methods=["GET"])
def settings():
    require_auth()
    csrf_token = "redacted"
    return "settings"

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return "logout"
'''


def test_route_auth_map_is_deterministic_and_redacted(tmp_path):
    root = tmp_path / "osmap"
    root.mkdir()
    (root / "app.py").write_text(SOURCE, encoding="utf-8")

    first = build_osmap_route_auth_map(review_osmap_source(root, workspace=tmp_path))
    second = build_osmap_route_auth_map(review_osmap_source(root, workspace=tmp_path))

    assert first.as_dict() == second.as_dict()
    assert first.auth_map.login_route_candidates
    assert first.auth_map.logout_route_candidates
    assert first.auth_map.session_validation_candidates
    assert first.auth_map.csrf_related_route_hints
    assert all(route.limitations for route in first.routes)


def test_route_auth_map_deduplicates_routes(tmp_path):
    root = tmp_path / "osmap"
    root.mkdir()
    (root / "app.py").write_text(SOURCE + SOURCE, encoding="utf-8")

    route_map = build_osmap_route_auth_map(review_osmap_source(root, workspace=tmp_path))
    unique = {(route.method, route.path_pattern) for route in route_map.routes}

    assert len(route_map.routes) == len(unique)
