"""NFR-08 Browser and device compatibility, tested in real browsers.

These tests are skipped automatically unless Playwright is installed, so the
normal test run and GitHub Actions are not affected. To run them:

    pip install playwright
    python -m playwright install          # downloads Chromium, Firefox, WebKit
    python -m pytest tests/browser -v

Chromium covers Chrome and Edge, Firefox covers Firefox, WebKit covers Safari.
An engine that is not installed is skipped, not failed.
"""
import os
import sqlite3
import sys
import threading
import urllib.request

import pytest

sync_api = pytest.importorskip("playwright.sync_api")
from werkzeug.serving import make_server  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import app as tms  # noqa: E402

ENGINES = ["chromium", "firefox", "webkit"]
SCREENS = {                      # name: (width, height)
    "desktop-1920": (1920, 1080),
    "laptop-1366": (1366, 768),
    "small-laptop-1024": (1024, 600),
    "tablet-768": (768, 1024),
    "phone-390": (390, 844),
    "small-phone-360": (360, 640),
}
LEAFLET_URL = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"

# A tiny stand-in for Leaflet so most tests do not need the internet.
LEAFLET_STUB = """
window.L = (function () {
  const chain = () => new Proxy(function () {}, {
    get: (t, k) => k === 'getBounds' ? () => ({}) : chain,
    apply: () => chain() });
  return { map: chain, tileLayer: chain,
    layerGroup: () => ({ addTo: () => ({ clearLayers() {} }), clearLayers() {} }),
    circleMarker: () => ({ bindPopup: () => ({ addTo() {} }) }),
    polyline: () => ({ addTo: () => ({ getBounds: () => ({}) }) }) };
})();
"""


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    path = str(tmp_path_factory.mktemp("browser") / "site.db")
    tms.DB = path
    tms.init_db()
    client = tms.app.test_client()
    for name in ("driver1", "admin1"):
        client.post("/api/register", json={
            "username": name, "email": name + "@x.com",
            "password": "Valid@123"})
    conn = sqlite3.connect(path)
    conn.execute("UPDATE users SET role = 'admin' WHERE username = 'admin1'")
    conn.commit()
    conn.close()
    server = make_server("127.0.0.1", 0, tms.app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield "http://127.0.0.1:%d/" % server.server_port
    server.shutdown()


@pytest.fixture(scope="module")
def pw():
    with sync_api.sync_playwright() as p:
        yield p


@pytest.fixture
def launch(pw):
    opened = []

    def _launch(engine):
        try:
            browser = getattr(pw, engine).launch()
        except Exception:
            pytest.skip("%s is not installed here" % engine)
        opened.append(browser)
        return browser
    yield _launch
    for browser in opened:
        browser.close()


def stub_map(page):
    page.route("**/leaflet*", lambda r: r.fulfill(
        body=LEAFLET_STUB if r.request.url.endswith(".js") else "",
        content_type="text/javascript" if r.request.url.endswith(".js")
        else "text/css"))
    page.route("**/tile.openstreetmap.org/**", lambda r: r.abort())


def block_map(page):
    page.route("**/leaflet*", lambda r: r.abort())
    page.route("**/tile.openstreetmap.org/**", lambda r: r.abort())


def log_in(page, url, name):
    page.goto(url)
    page.fill("#username", name)
    page.fill("#password", "Valid@123")
    page.click('button:text-is("Login")')
    page.wait_for_selector("#app", state="visible", timeout=10000)
    page.wait_for_selector("#parkList tr", timeout=10000)


def sideways_scroll(page):
    return page.evaluate("document.documentElement.scrollWidth - "
                         "window.innerWidth")


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize("screen", sorted(SCREENS))
def test_pages_fit_the_screen_and_the_user_journey_works(
        site, launch, engine, screen):
    width, height = SCREENS[screen]
    page = launch(engine).new_page(viewport={"width": width,
                                             "height": height})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    stub_map(page)

    page.goto(site)
    assert sideways_scroll(page) <= 0, "login page scrolls sideways"

    log_in(page, site, "driver1")
    assert sideways_scroll(page) <= 0, "main page scrolls sideways"
    assert page.locator("#parkList tr").count() == 7        # header + 6 areas
    assert page.locator("#alertList").is_visible()

    page.click('button:text-is("Find route")')
    page.wait_for_function(
        "document.getElementById('rmsg').textContent.includes('km')")
    page.fill("#iloc", "MG Road")
    page.fill("#idesc", "Two vehicles blocking lane")
    page.click('button:text-is("Submit report")')
    page.wait_for_function(
        "document.getElementById('imsg').textContent.includes('Thank you')")
    page.click('button:text-is("Download my data")')  # must not crash
    assert errors == []


@pytest.mark.parametrize("engine", ENGINES)
def test_buttons_are_big_enough_to_tap(site, launch, engine):
    page = launch(engine).new_page(viewport={"width": 390, "height": 844})
    stub_map(page)
    log_in(page, site, "driver1")
    heights = page.evaluate(
        "[...document.querySelectorAll('button')].filter(b => b.offsetParent)"
        ".map(b => b.getBoundingClientRect().height)")
    assert heights and min(heights) >= 24     # WCAG 2.2 minimum target size


@pytest.mark.parametrize("engine", ENGINES)
def test_everything_but_the_map_works_if_the_map_cannot_load(
        site, launch, engine):
    page = launch(engine).new_page(viewport={"width": 390, "height": 844})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    block_map(page)
    log_in(page, site, "driver1")
    assert "could not load" in page.inner_text("#map")
    assert page.locator("#parkList tr").count() == 7
    page.click('button:text-is("Find route")')
    page.wait_for_function(
        "document.getElementById('rmsg').textContent.includes('km')")
    assert errors == []


@pytest.mark.parametrize("engine", ENGINES)
def test_admin_tools_work_and_a_report_downloads(site, launch, engine):
    page = launch(engine).new_page(accept_downloads=True,
                                   viewport={"width": 1366, "height": 768})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    stub_map(page)
    log_in(page, site, "admin1")
    assert page.is_visible("#adminPanel")
    page.click('button:text-is("Show analytics")')
    page.wait_for_selector("#analyticsBox .card", timeout=10000)
    assert page.locator("#analyticsBox .card").count() == 4
    page.fill("#rtitle", "Browser test report")
    page.click('button:text-is("Generate report")')
    page.wait_for_selector("#reportList button", timeout=10000)
    with page.expect_download() as download:
        page.click('#reportList button:text-is("Download")')
    assert download.value.suggested_filename.startswith("report-")
    page.click('button:text-is("Check data consistency")')
    page.wait_for_function(
        "document.getElementById('statusBox').textContent.includes('agree')")
    assert errors == []


@pytest.mark.parametrize("device, engine", [("Pixel 7", "chromium"),
                                            ("iPhone 13", "webkit"),
                                            ("iPad (gen 7)", "webkit")])
def test_phone_and_tablet_emulation(site, pw, device, engine):
    try:
        browser = getattr(pw, engine).launch()
    except Exception:
        pytest.skip("%s is not installed here" % engine)
    try:
        context = browser.new_context(**pw.devices[device])
        page = context.new_page()
        stub_map(page)
        log_in(page, site, "driver1")
        assert sideways_scroll(page) <= 0
        assert page.locator("#parkList tr").count() == 7
    finally:
        browser.close()


def _cdn_reachable():
    try:
        urllib.request.urlopen(LEAFLET_URL, timeout=5)
        return True
    except Exception:
        return False


@pytest.mark.parametrize("engine", ENGINES)
def test_the_real_interactive_map_loads(site, launch, engine):
    if not _cdn_reachable():
        pytest.skip("the Leaflet CDN is not reachable from here")
    page = launch(engine).new_page(viewport={"width": 1366, "height": 768})
    page.route("**/tile.openstreetmap.org/**", lambda r: r.abort())
    log_in(page, site, "driver1")
    page.wait_for_selector("#map .leaflet-container, #map.leaflet-container",
                           timeout=10000)
    assert page.evaluate(
        "document.getElementById('map').getBoundingClientRect().height") > 100
