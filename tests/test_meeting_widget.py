"""Browser tests for static/meeting_spot.html with emulated GPS and compass.

Needs Playwright and a Chromium build; skipped otherwise:
    pip install playwright   # browser: `playwright install chromium`, or set CHROMIUM_PATH
"""

import base64
import os
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from ghat_guide.geo import bearing_deg, haversine_m
from tests.test_geo import GEO_CASES

sync_api = pytest.importorskip("playwright.sync_api")

PAGE = (Path(__file__).resolve().parent.parent / "static" / "meeting_spot.html").as_uri()
SPOT = {"latitude": 25.6100, "longitude": 85.1400, "accuracy": 8}
KNOWN_CHROMIUM = [os.environ.get("CHROMIUM_PATH"), "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"]


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        last_error = None
        for path in [None, *[c for c in KNOWN_CHROMIUM if c]]:
            try:
                b = p.chromium.launch(executable_path=path, args=["--no-sandbox"])
                break
            except Exception as e:  # noqa: BLE001
                last_error = e
        else:
            pytest.skip(f"no Chromium available: {last_error}")
        yield b
        b.close()


@pytest.fixture
def ctx(browser):
    c = browser.new_context(permissions=["geolocation"], geolocation=SPOT, viewport={"width": 412, "height": 900})
    yield c
    c.close()


def open_page(ctx, query=""):
    page = ctx.new_page()
    page.goto(PAGE + query)
    page.wait_for_selector("#title:not(:empty)")
    return page


def heading(page, deg):
    """Emulate the Android compass pointing `deg` clockwise from north."""
    page.evaluate(
        "d => window.dispatchEvent(new DeviceOrientationEvent('deviceorientationabsolute', {alpha: (360 - d) % 360, absolute: true}))",
        deg,
    )


def save_spot(page, note="नीला टेंट, घाट 5"):
    page.fill("#note", note)
    page.click("#btn-save")
    page.wait_for_selector("#v-saved:not(.hidden)")


def arrow_deg(page) -> float:
    style = page.get_attribute("#g-arrow", "style") or ""
    return float(style.split("rotate(")[1].split("deg")[0])


# --------------------------------------------------------------------- tests

@pytest.mark.parametrize("lat1,lon1,lat2,lon2,dist,brg", GEO_CASES)
def test_js_maths_matches_python(ctx, lat1, lon1, lat2, lon2, dist, brg):
    page = open_page(ctx)
    js_d = page.evaluate("a => GhatGeo.haversine(...a)", [lat1, lon1, lat2, lon2])
    assert js_d == pytest.approx(haversine_m(lat1, lon1, lat2, lon2), abs=1e-6)
    if brg is not None:
        js_b = page.evaluate("a => GhatGeo.bearing(...a)", [lat1, lon1, lat2, lon2])
        assert js_b == pytest.approx(bearing_deg(lat1, lon1, lat2, lon2), abs=1e-6)


def test_circular_mean_wraps_north(ctx):
    page = open_page(ctx)
    m = page.evaluate("GhatGeo.circularMean([350, 10, 0])")
    assert min(m, 360 - m) < 1e-6


def test_save_survives_reload_and_expires_at_midnight(ctx):
    page = open_page(ctx)
    assert page.is_visible("#v-save")
    save_spot(page)
    assert page.inner_text("#saved-note") == "नीला टेंट, घाट 5"
    assert "±8" in page.inner_text("#saved-meta")

    page.reload()
    page.wait_for_selector("#v-saved:not(.hidden)")
    stored = page.evaluate("JSON.parse(localStorage.getItem('ghat_guide.meeting_spot.v1'))")
    assert stored["lat"] == SPOT["latitude"] and stored["lon"] == SPOT["longitude"]
    midnight = page.evaluate("(() => { const d = new Date(); d.setHours(24,0,0,0); return d.getTime(); })()")
    assert stored["expires_at"] == midnight


def test_expired_spot_is_removed(ctx):
    page = open_page(ctx)
    save_spot(page)
    page.evaluate(
        "() => { const k='ghat_guide.meeting_spot.v1'; const s=JSON.parse(localStorage.getItem(k));"
        " s.expires_at = Date.now() - 1; localStorage.setItem(k, JSON.stringify(s)); }"
    )
    page.reload()
    page.wait_for_selector("#v-save:not(.hidden)")
    assert page.evaluate("localStorage.getItem('ghat_guide.meeting_spot.v1')") is None


def test_clear_button(ctx):
    page = open_page(ctx)
    save_spot(page)
    page.once("dialog", lambda d: d.accept())
    page.click("#btn-clear")
    page.wait_for_selector("#v-save:not(.hidden)")
    assert page.evaluate("localStorage.getItem('ghat_guide.meeting_spot.v1')") is None


def test_guide_arrow_distance_and_direction(ctx):
    page = open_page(ctx)
    save_spot(page)
    # Walk ~111 m south of the spot: the spot is due north.
    ctx.set_geolocation({"latitude": SPOT["latitude"] - 0.001, "longitude": SPOT["longitude"], "accuracy": 6})
    page.click("#btn-guide")
    page.wait_for_function("document.querySelector('#g-distance').textContent.length > 0")
    assert page.inner_text("#g-distance") == "लगभग 110 मीटर"
    assert page.inner_text("#g-direction") == "उत्तर की ओर"

    heading(page, 0)  # facing north → arrow straight up
    page.wait_for_selector("#g-compass:not(.hidden)")
    assert arrow_deg(page) == pytest.approx(0, abs=0.5)

    for _ in range(5):  # facing east (replace the smoothing window) → arrow points left
        heading(page, 90)
    assert arrow_deg(page) == pytest.approx(270, abs=0.5)
    assert "सीधा" in page.inner_text("#g-hint")


def test_arrived_when_within_gps_error(ctx):
    page = open_page(ctx)
    save_spot(page)
    ctx.set_geolocation({"latitude": SPOT["latitude"] + 0.00005, "longitude": SPOT["longitude"], "accuracy": 12})  # ~6 m
    page.click("#btn-guide")
    page.wait_for_function("document.querySelector('#g-status').textContent.includes('बहुत पास')")
    assert page.is_hidden("#g-compass")


def test_no_compass_falls_back_to_text_directions(ctx):
    page = open_page(ctx)
    save_spot(page)
    ctx.set_geolocation({"latitude": SPOT["latitude"], "longitude": SPOT["longitude"] + 0.001, "accuracy": 6})
    page.click("#btn-guide")
    page.wait_for_function("document.querySelector('#g-hint').textContent.includes('कम्पास नहीं मिला')", timeout=6000)
    assert page.inner_text("#g-direction") == "पश्चिम की ओर"
    assert page.is_hidden("#g-compass")


def test_rough_fix_asks_before_saving(ctx):
    ctx.set_geolocation({**SPOT, "accuracy": 55})
    page = open_page(ctx)
    page.click("#btn-save")
    page.wait_for_selector("text=फिर भी सहेजें")
    assert page.is_visible("#v-save")
    page.click("text=फिर भी सहेजें")
    page.wait_for_selector("#v-saved:not(.hidden)")
    assert "±55" in page.inner_text("#saved-meta")


def test_photo_downscaled_and_metadata_free(ctx, tmp_path):
    big = tmp_path / "landmark.jpg"
    exif = Image.Exif()
    exif[0x8825] = {1: "N", 2: (25.0, 36.0, 33.0)}  # GPS block
    Image.new("RGB", (3000, 2000), (30, 90, 200)).save(big, format="JPEG", exif=exif.tobytes())

    page = open_page(ctx)
    page.set_input_files("#photo", str(big))
    page.wait_for_selector("#photo-preview:not(.hidden)")
    save_spot(page)
    data_url = page.evaluate("JSON.parse(localStorage.getItem('ghat_guide.meeting_spot.v1')).photo")
    assert data_url.startswith("data:image/jpeg;base64,")
    im = Image.open(BytesIO(base64.b64decode(data_url.split(",", 1)[1])))
    assert max(im.size) == 640
    assert 0x8825 not in im.getexif()
    assert page.is_visible("#saved-photo")


def test_language_from_query(ctx):
    page = open_page(ctx, "?lang=mai")
    assert page.inner_text("#title") == "भेंट होबाक जगह"
    assert page.inner_text("#btn-save") == "📍 यह जगह सहेजें"  # falls back to Hindi


def test_note_is_text_not_html(ctx):
    page = open_page(ctx)
    save_spot(page, note="<img src=x onerror=alert(1)>")
    assert page.inner_text("#saved-note") == "<img src=x onerror=alert(1)>"
    assert page.query_selector("#saved-note img") is None
