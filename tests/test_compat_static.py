"""NFR-08 Browser and device compatibility: checks on the page itself that
run everywhere. Real browsers are tested in tests/browser/."""
import os
import re

import pytest

import app as tms  # noqa: F401  (puts app/ on the path)
from helpers import make_client

HTML_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "static",
                         "index.html")
HTML = open(HTML_PATH, encoding="utf-8").read()


def test_page_declares_standard_html_and_encoding():
    assert HTML.lstrip().lower().startswith("<!doctype html>")
    assert re.search(r'<html[^>]+lang="en"', HTML)
    assert '<meta charset="UTF-8">' in HTML


def test_page_scales_to_phones_and_tablets():
    assert re.search(r'<meta name="viewport" content="width=device-width, '
                     r'initial-scale=1"', HTML)
    assert "@media (max-width: 600px)" in HTML


def test_layout_has_no_fixed_wide_elements():
    # every width is a maximum or a percentage, so nothing forces sideways
    # scrolling on a 320px phone
    for width in re.findall(r"(?<![-\w])width:\s*([^;]+);", HTML):
        assert width.strip() in ("100%", "auto", "14px") or \
            width.strip().endswith("%"), width
    assert "overflow-x: auto" in HTML


def test_form_fields_have_labels():
    labelled = set(re.findall(r'<label[^>]+for="([^"]+)"', HTML))
    for tag in re.findall(r"<(?:input|select)\b[^>]*>", HTML):
        field_id = re.search(r'id="([^"]+)"', tag)
        if field_id and 'type="hidden"' not in tag:
            assert (field_id.group(1) in labelled
                    or "aria-label" in tag), tag


def test_text_and_buttons_are_big_enough_to_tap():
    assert re.search(r"body \{[^}]*font-size: 16px", HTML)
    assert re.search(r"button \{[^}]*font-size: 16px", HTML)
    assert re.search(r"button \{[^}]*padding: 10px 16px", HTML)


def test_only_secure_external_resources_are_used():
    assert "http://" not in HTML.replace("http://www.w3.org", "")
    for url in re.findall(r'(?:src|href)="(https://[^"]+)"', HTML):
        assert "unpkg.com/leaflet@1.9.4" in url, url


def test_page_works_without_modern_only_tricks():
    for risky in ("document.write(", "XMLHttpRequest", "ActiveXObject",
                  "-ms-", "<blink", "<marquee"):
        assert risky not in HTML


def test_a_broken_map_library_does_not_stop_the_app():
    """If the map script cannot load (blocked network, old device) the rest
    of the app must still work, so the page guards every use of it."""
    assert 'typeof L === "undefined"' in HTML or \
        "typeof L === 'undefined'" in HTML
    assert "mapReady()" in HTML


def test_server_sends_the_page_as_html_utf8(tmp_path):
    client = make_client(tmp_path)
    r = client.get("/")
    assert r.status_code == 200
    assert r.content_type.lower() == "text/html; charset=utf-8"
    assert r.headers["X-Content-Type-Options"] == "nosniff"


def test_supported_browsers_are_documented():
    doc = open(os.path.join(os.path.dirname(__file__), "..", "docs",
                            "NFR_EVIDENCE.md"), encoding="utf-8").read()
    for browser in ("Chrome", "Edge", "Firefox", "Safari"):
        assert browser in doc
