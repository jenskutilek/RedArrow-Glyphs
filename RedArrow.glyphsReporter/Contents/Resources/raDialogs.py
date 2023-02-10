# encoding: utf-8
from __future__ import division

import vanilla
from dialogs_mac_vanilla import _RAModalWindow, _RAbaseWindowController


class SelectGlyphsWindowController(_RAbaseWindowController):

    test_names = {
        "test_extrema": "Missing Extremum Points",
        "test_inflections": "Missing Inflection Points",
        "test_fractional_coords": "Fractional Coordinates",
        "test_fractional_transform": "Fractional Transformation",
        "test_smooth": "Nearly Smooth Connections",
        "test_empty_segments": "Zero-length Segments",
        "test_collinear": "Collinear Vectors",
        "test_semi_hv": "Semi-horizontal/-vertical Segments",
    }

    option_names = {
        "ignore_warnings": "Ignore Warnings",
        "extremum_calculate_badness": "Calculate Extremum Badness",
        "extremum_ignore_badness_below": "Ignore Extremum Badness Below",
        "smooth_connection_max_distance": "Smooth Connection Tolerance",
        "fractional_ignore_point_zero": "Ignore .0 Fractional Values",
        "collinear_vectors_max_distance": "Collinear Vectors Tolerance",
        "grid_length": "Grid Length",
        "inflection_max": "Maximum Allowed Inflection t",
        "inflection_min": "Minimum Allowed Inflection t",
    }

    def __init__(self, options={}, run_tests=[], title="Select Glyphs With Errors"):

        self.run_tests = {o: True for o in run_tests}
        self.options = options

        x = 10
        y = 8
        col = 240
        entry_line_height = 22
        title_line_height = 24
        title_skip = 8
        buttons_height = 44

        height = (
            y
            + title_line_height
            + entry_line_height * (len(self.options) + len(self.run_tests))
            + title_line_height
            + title_skip
            + buttons_height
        )
        self.w = _RAModalWindow((300, height), title)

        self.w.tests_title = vanilla.TextBox((x, y, -10, 23), "Select Glyphs With:")
        y += title_line_height

        for k in sorted(self.run_tests.keys()):
            setattr(
                self.w,
                k,
                vanilla.CheckBox(
                    (x + 3, y, -10, 20),
                    self.test_names.get(k, k),
                    value=self.run_tests[k],
                    sizeStyle="small",
                ),
            )
            y += entry_line_height

        vanilla.HorizontalLine((x, y, -10, 1))

        y += 8
        self.w.options_title = vanilla.TextBox((x, y, -10, 23), "Options (For Advanced Users):")
        y += title_line_height

        for k in sorted(self.options.keys()):
            v = self.options[k]
            if type(v) in (int, float):
                setattr(
                    self.w,
                    "%s_label" % k,
                    vanilla.TextBox(
                        (x + 18, y + 3, -10, 20),
                        self.option_names.get(k, k),
                        sizeStyle="small",
                    ),
                )
                setattr(
                    self.w,
                    k,
                    vanilla.EditText(
                        (col, y + 1, -14, 18),
                        text=v,
                        sizeStyle="small",
                    ),
                )
            elif type(v) == bool:
                setattr(
                    self.w,
                    k,
                    vanilla.CheckBox(
                        (x + 3, y, -10, 20),
                        self.option_names.get(k, k),
                        value=v,
                        sizeStyle="small",
                    ),
                )
            y += entry_line_height

        self.setUpBaseWindowBehavior()
        self.w.open()

    def get(self):
        if self.cancelled:
            return None, None
        else:
            options = {option_name: int(getattr(self.w, option_name).get()) for option_name in self.options.keys()}
            run_tests = [test_name for test_name in self.run_tests if getattr(self.w, test_name).get()]
            return options, run_tests
