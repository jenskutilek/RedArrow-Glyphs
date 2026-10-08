import unittest

from redArrow.geometry import round_value


class GeometryTests(unittest.TestCase):
    def test_round_half_up(self) -> None:
        assert round_value(0.5) == 1
        assert round_value(1.5) == 2
        assert round_value(-0.5) == -1
        assert round_value(-1.5) == -2
