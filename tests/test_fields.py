"""Harita katman ızgaraları: kara poligonu ve ızgara (internet gerektirmez)."""
from shapely.geometry import Point

from hibrit_enerji.core import fields


def test_land_polygon_matches_kktc():
    poly = fields.land()
    assert 0.28 < poly.area < 0.36  # ~3.300 km² (derece² cinsinden)
    assert poly.contains(Point(34.381, 35.598))      # Dipkarpaz
    assert poly.contains(Point(33.940, 35.125))      # Gazimağusa
    assert not poly.contains(Point(33.0, 35.0))      # güney


def test_land_points_inside_grid():
    pts = fields.land_points()
    lats, lons = fields.grid()
    assert 30 < len(pts) < len(lats) * len(lons)
    assert all(fields.LAT0 <= la <= fields.LAT1 and fields.LON0 <= lo <= fields.LON1 for la, lo in pts)
