# encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from AppKit import NSNumber, NSNumberFormatter
from vanilla import CheckBox, EditText, HorizontalLine, TextBox
from redArrow.defaults import default_tests
from redArrow.dialogs_mac_vanilla import _RAModalWindow, _RAbaseWindowController


float_formatter = NSNumberFormatter.alloc().init()
float_formatter.setAllowsFloats_(True)
float_formatter.setFormat_("#.###;0;-#.###")
float_formatter.setGeneratesDecimalNumbers_(True)
float_formatter.setMinimum_(NSNumber.numberWithFloat_(0.0))


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
        "inflection_min": "Minimum Allowed Inflection t (0–0.5)",
    }

    def __init__(self, options={}, run_tests=[], title="Select Glyphs With Errors"):

        self.run_tests = {o: o in run_tests for o in default_tests}
        self.options = options
        self.save_global = False

        x = 10
        y = 8
        col = 240
        entry_line_height = 22
        title_line_height = 24
        title_skip = 8
        buttons_height = 44 + 24

        height = (
            y
            + title_line_height
            + entry_line_height * (len(self.options) + len(self.run_tests))
            + title_line_height
            + title_skip
            + buttons_height
        )
        self.w = _RAModalWindow((300, height), title)

        self.w.tests_title = TextBox((x, y, -10, 23), "Select Errors To Flag:")
        y += title_line_height

        for k in sorted(self.run_tests.keys()):
            setattr(
                self.w,
                k,
                CheckBox(
                    (x + 3, y, -10, 20),
                    self.test_names.get(k, k),
                    value=self.run_tests[k],
                    sizeStyle="small",
                ),
            )
            y += entry_line_height

        HorizontalLine((x, y, -10, 1))

        y += 8
        self.w.options_title = TextBox((x, y, -10, 23), "Options (For Advanced Users):")
        y += title_line_height

        for k in sorted(self.options.keys()):
            v = self.options[k]
            if type(v) == bool:
                setattr(
                    self.w,
                    k,
                    CheckBox(
                        (x + 3, y, -10, 20),
                        self.option_names.get(k, k),
                        value=v,
                        sizeStyle="small",
                    ),
                )
            else:
                setattr(
                    self.w,
                    "%s_label" % k,
                    TextBox(
                        (x + 18, y + 3, -10, 20),
                        self.option_names.get(k, k),
                        sizeStyle="small",
                    ),
                )
                setattr(
                    self.w,
                    k,
                    EditText(
                        (col, y + 1, -14, 18),
                        text=v,
                        sizeStyle="small",
                        formatter=float_formatter,
                    ),
                )
            y += entry_line_height

        y += title_skip
        self.w.saveGlobal = CheckBox(
            (-148, -54, -15, 20),
            "Save Permanently",
            callback=self.saveCallback,
            value=False,
            sizeStyle="small",
        )

        self.setUpBaseWindowBehavior()
        self.w.open()

    def saveCallback(self, sender):
        self.save_global = sender.get()

    def get(self):
        if self.cancelled:
            return False, None, None
        else:
            options = {option_name: getattr(self.w, option_name).get() for option_name in self.options.keys()}
            # print("Set options from dialog:")
            # for k, v in options.items():
            #     print("   ", k, v, type(v))
            run_tests = [test_name for test_name in self.run_tests if getattr(self.w, test_name).get()]
            return self.save_global, options, run_tests
