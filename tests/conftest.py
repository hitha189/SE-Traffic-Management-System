import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import app as tms


@pytest.fixture(autouse=True)
def reset_login_attempts():
    tms.FAILED_LOGINS.clear()
    yield
    tms.FAILED_LOGINS.clear()