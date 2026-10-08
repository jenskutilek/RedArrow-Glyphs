import unittest

from AppKit import NSMakePoint

from redArrow.geometry import is_point_on_grid, round_value


class GeometryTests(unittest.TestCase):
    def test_round_half_up(self) -> None:
        assert round_value(0.5) == 1
        assert round_value(1.5) == 2
        assert round_value(-0.5) == -1
        assert round_value(-1.5) == -2

    def test_is_point_on_grid(self) -> None:
        p = NSMakePoint(1.0, 1.0)
        assert is_point_on_grid(p)
        p = NSMakePoint(2.0, 1.0)
        assert is_point_on_grid(p, 2, 1)
        p = NSMakePoint(2.00001, 1.0)
        assert not is_point_on_grid(p, 2, 1)
        p = NSMakePoint(0.5, 0.5)
        assert is_point_on_grid(p, 0)
        p = NSMakePoint(1.0, 0.5)
        assert is_point_on_grid(p, 1, 0)
        p = NSMakePoint(0.5, 1.0)
        assert is_point_on_grid(p, 0, 1)
