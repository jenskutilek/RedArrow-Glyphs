import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest
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


@pytest.fixture
def plugin(monkeypatch):
    # The Glyphs host is unavailable when running the tests outside the app.
    glyphs_module = ModuleType("GlyphsApp")
    for name in (
        "GSCURVE",
        "GSLINE",
        "GSOFFCURVE",
        "GSQCURVE",
        "MOUSEMOVED",
        "WINDOW_MENU",
    ):
        setattr(glyphs_module, name, name)
    glyphs = SimpleNamespace(defaults={}, versionNumber=4.0, redraw=Mock())
    glyphs.registerDefaults = lambda values: [
        glyphs.defaults.setdefault(key, value) for key, value in values.items()
    ]
    glyphs_module.Glyphs = glyphs
    plugins = ModuleType("GlyphsApp.plugins")
    plugins.ReporterPlugin = type("ReporterPlugin", (), {})
    drawing = ModuleType("GlyphsApp.drawingTools")
    drawing.save = drawing.restore = Mock()
    for module in (glyphs_module, plugins, drawing):
        monkeypatch.setitem(sys.modules, module.__name__, module)
    path = (
        Path(__file__).parents[1]
        / "RedArrow.glyphsReporter/Contents/Resources/plugin.py"
    )
    spec = importlib.util.spec_from_file_location("red_arrow_plugin_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_live_preferences_invalidate_current_layer(plugin):
    reporter = plugin.RedArrow()
    reporter.load_defaults()
    old_checker = reporter.outline_check
    reporter.current_layer = object()
    plugin.Glyphs.defaults["RedArrowSmoothMaxDistance"] = 1.5
    plugin.Glyphs.defaults["RedArrowCheckSmooth"] = False
    reporter.defaultsDidChange_(None)
    assert reporter.current_layer is None
    assert reporter.outline_check is not old_checker
    assert reporter.outline_check.RedArrowSmoothMaxDistance == 1.5
    # Layer assignment refreshes the cached options before checking an outline.
    reporter.outline_check.layer = None
    assert reporter.outline_check.RedArrowCheckSmooth is False
    plugin.Glyphs.redraw.assert_called()


def test_all_checks_can_be_disabled(plugin):
    reporter = plugin.RedArrow()
    reporter.load_defaults()
    for key in plugin.default_checks:
        plugin.Glyphs.defaults[key] = False
    reporter.defaultsDidChange_(None)
    reporter.outline_check.layer = None
    assert all(
        not getattr(reporter.outline_check, key) for key in plugin.default_checks
    )


def test_glyphs4_uses_switches_instead_of_legacy_check_list(plugin):
    plugin.Glyphs.defaults["RedArrowRunChecks"] = ["RedArrowCheckSmooth"]
    reporter = plugin.RedArrow()
    reporter.load_defaults()
    assert reporter.run_checks == plugin.default_checks


def test_glyphs3_preserves_legacy_check_list(plugin):
    plugin.Glyphs.versionNumber = 3.0
    plugin.Glyphs.defaults["RedArrowRunChecks"] = ["RedArrowCheckSmooth"]
    reporter = plugin.RedArrow()
    reporter.load_defaults()
    assert reporter.run_checks == ["RedArrowCheckSmooth"]


def test_stopping_mouse_observer_keeps_defaults_observer(plugin, monkeypatch):
    center = Mock()
    monkeypatch.setattr(
        plugin, "NSNotificationCenter", SimpleNamespace(defaultCenter=lambda: center)
    )
    reporter = plugin.RedArrow()
    reporter.stopMouseMoved()
    center.removeObserver_name_object_.assert_called_once_with(
        reporter, "MOUSEMOVED", None
    )
    center.removeObserver_.assert_not_called()
