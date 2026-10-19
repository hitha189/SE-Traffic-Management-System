import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import app as tms


def test_home_page_loads():
    client = tms.app.test_client()
    r = client.get("/")
    assert r.status_code == 200
    assert b"Traffic Management System" in r.data