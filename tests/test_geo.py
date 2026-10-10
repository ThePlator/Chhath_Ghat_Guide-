import pytest

from ghat_guide.geo import bearing_deg, compass_point, haversine_m, round_distance_m

# Patna-ish reference point
LAT, LON = 25.6100, 85.1400

# Shared with tests/test_meeting_widget.py so the JS and Python stay in sync.
GEO_CASES = [
    # (lat1, lon1, lat2, lon2, distance_m, bearing_deg)
    (LAT, LON, LAT, LON, 0.0, None),
    (LAT, LON, LAT + 0.001, LON, 111.19, 0.0),          # due north
    (LAT, LON, LAT - 0.001, LON, 111.19, 180.0),        # due south
    (LAT, LON, LAT, LON + 0.001, 100.31, 90.0),         # due east (shorter: cos(lat))
    (LAT, LON, LAT, LON - 0.001, 100.31, 270.0),        # due west
    (LAT, LON, LAT + 0.0005, LON + 0.0005, 74.9, 42.0),  # roughly north-east
    (0.0, 179.9995, 0.0, -179.9995, 111.19, 90.0),      # across the date line
]


@pytest.mark.parametrize("lat1,lon1,lat2,lon2,dist,brg", GEO_CASES)
def test_haversine_and_bearing(lat1, lon1, lat2, lon2, dist, brg):
    assert haversine_m(lat1, lon1, lat2, lon2) == pytest.approx(dist, abs=0.5)
    if brg is not None:
        b = bearing_deg(lat1, lon1, lat2, lon2)
        assert min(abs(b - brg), 360 - abs(b - brg)) < 1.0


def test_bearing_always_in_range():
    for dlat, dlon in [(0.001, -0.0001), (-0.001, -0.0001), (0.0, -0.001)]:
        b = bearing_deg(LAT, LON, LAT + dlat, LON + dlon)
        assert 0 <= b < 360


@pytest.mark.parametrize(
    "deg,name",
    [(0, "उत्तर"), (359, "उत्तर"), (22, "उत्तर"), (23, "उत्तर-पूर्व"), (90, "पूर्व"), (180, "दक्षिण"), (270, "पश्चिम"), (315, "उत्तर-पश्चिम"), (-90, "पश्चिम"), (720, "उत्तर")],
)
def test_compass_point(deg, name):
    assert compass_point(deg) == name


def test_compass_point_english_and_fallback():
    assert compass_point(45, "en") == "NE"
    assert compass_point(45, "bho") == "उत्तर-पूर्व"


@pytest.mark.parametrize("d,r", [(0, 0), (12, 10), (13, 15), (98, 100), (101, 100), (106, 110), (1234, 1230)])
def test_round_distance(d, r):
    assert round_distance_m(d) == r
