"""NFR-07 Modularity: features are separate modules that can change with
minimal impact on the others. These tests act as architecture rules: they
fail if someone adds a dependency that would tie features together."""
import ast
import os
import subprocess
import sqlite3
import sys
from types import SimpleNamespace

import pytest
from flask import Flask

APP_DIR = os.path.join(os.path.dirname(__file__), "..", "app")
sys.path.insert(0, APP_DIR)

MODULES = sorted(f[:-3] for f in os.listdir(APP_DIR) if f.endswith(".py"))
BLUEPRINTS = [m for m in MODULES if m.endswith("_api")]
SCRIPTS = {"app", "seed_demo"}
LOGIC = [m for m in MODULES if m not in SCRIPTS and m not in BLUEPRINTS]


def imports_of(module):
    tree = ast.parse(open(os.path.join(APP_DIR, module + ".py")).read())
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module.split(".")[0])
    return found


def siblings(module):
    return imports_of(module) & set(MODULES)


def test_no_feature_module_imports_the_main_app_file():
    for module in MODULES:
        if module in SCRIPTS:
            continue
        assert "app" not in imports_of(module), module


def test_no_circular_dependencies():
    graph = {m: siblings(m) for m in MODULES}
    state = {}

    def visit(node, path):
        if state.get(node) == "done":
            return
        assert state.get(node) != "active", "cycle: " + " -> ".join(
            path + [node])
        state[node] = "active"
        for nxt in graph[node]:
            visit(nxt, path + [node])
        state[node] = "done"
    for module in MODULES:
        visit(module, [])


def test_business_logic_does_not_depend_on_the_web_framework():
    for module in LOGIC:
        assert not imports_of(module) & {"flask", "werkzeug"}, module


def test_blueprints_do_not_depend_on_each_other():
    for module in BLUEPRINTS:
        assert not siblings(module) & set(BLUEPRINTS), module


def test_there_is_one_blueprint_per_feature_group():
    assert BLUEPRINTS == ["health_api", "integrations_api", "network_api",
                          "parking_api", "privacy_api", "reporting_api"]


@pytest.mark.parametrize("module", BLUEPRINTS)
def test_each_blueprint_is_built_from_injected_dependencies(module):
    mod = __import__(module)
    assert callable(mod.create_blueprint)
    bp = mod.create_blueprint(stub_deps(None))
    assert bp.name and bp.name != "app"


def test_blueprint_names_are_unique():
    names = [__import__(m).create_blueprint(stub_deps(None)).name
             for m in BLUEPRINTS]
    assert len(names) == len(set(names))


# What each new module is allowed to depend on. If a change adds a dependency,
# this test fails and the team decides whether the coupling is acceptable.
ALLOWED = {
    "parking": set(),
    "health": set(),
    "validation": set(),
    "privacy": {"storage"},
    "network": {"routing", "signals"},
    "analytics": {"traffic"},
    "datasources": {"parking", "traffic"},
    "consistency": {"alerts", "incidents", "signals", "traffic"},
    "reports": {"alerts", "analytics", "emergency", "parking", "signals"},
}


@pytest.mark.parametrize("module", sorted(ALLOWED))
def test_dependencies_stay_within_the_agreed_limits(module):
    assert siblings(module) <= ALLOWED[module], siblings(module)


def test_importing_a_feature_does_not_load_the_rest_of_the_system():
    code = ("import sys; sys.path.insert(0, %r); import parking_api; "
            "loaded = {m for m in sys.modules if m in %r}; "
            "print(sorted(loaded))" % (APP_DIR, MODULES))
    out = subprocess.run([sys.executable, "-c", code], capture_output=True,
                         text=True, check=True).stdout.strip()
    loaded = set(eval(out))
    assert "app" not in loaded
    assert loaded <= {"parking_api", "audit", "datasources", "parking",
                      "traffic", "validation"}


def stub_deps(db_path):
    def get_db():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    class Session:
        def __enter__(self):
            self.conn = get_db()
            return self.conn

        def __exit__(self, exc_type, *_):
            (self.conn.rollback if exc_type else self.conn.commit)()
            self.conn.close()
    return SimpleNamespace(
        get_db=get_db, db_session=Session,
        require_role=lambda *roles: (lambda fn: fn),   # no login needed
        current_user=lambda: "tester",
        json_body=lambda: {},
        check_password_hash=lambda *_: True)


def test_a_feature_runs_on_its_own_with_stand_in_dependencies(tmp_path):
    """The parking feature works in a brand-new app that has no login, no
    other features and no app.py: it is genuinely independent."""
    import parking
    import parking_api
    db = str(tmp_path / "solo.db")
    conn = sqlite3.connect(db)
    parking.init_parking(conn)
    conn.close()
    solo = Flask("solo")
    solo.register_blueprint(parking_api.create_blueprint(stub_deps(db)))
    r = solo.test_client().get("/api/parking")
    assert r.status_code == 200
    assert len(r.get_json()["parking"]) == 6
