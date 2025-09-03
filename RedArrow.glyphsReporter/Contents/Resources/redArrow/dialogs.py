# encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from AppKit import NSNumber, NSNumberFormatter
from vanilla import CheckBox, EditText, HorizontalLine, TextBox

from redArrow.defaults import default_tests, typechecked_options
from redArrow.dialogs_mac_vanilla import _RAbaseWindowController, _RAModalWindow

float_formatter = NSNumberFormatter.alloc().init()
float_formatter.setAllowsFloats_(True)
float_formatter.setFormat_("#.###;0;-#.###")
float_formatter.setGeneratesDecimalNumbers_(True)
float_formatter.setMinimum_(NSNumber.numberWithFloat_(0.0))


inflection_formatter = NSNumberFormatter.alloc().init()
inflection_formatter.setAllowsFloats_(True)
inflection_formatter.setFormat_("#.###;0;-#.###")
inflection_formatter.setGeneratesDecimalNumbers_(True)
inflection_formatter.setMinimum_(NSNumber.numberWithFloat_(0.0))
inflection_formatter.setMaximum_(NSNumber.numberWithFloat_(0.49))


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
        # "test_closepath": "Closepaths",
        "test_zero_handles": "Zero-length Handles",
        "test_bbox_handles": "Handles Outside Bounding Box",
        "test_short_segments": "Short Segments",
    }

    option_names = {
        "ignore_warnings": ("Ignore Warnings", "b"),
        "extremum_calculate_badness": ("Calculate Extremum Badness", "b"),
        "extremum_ignore_badness_below": ("Ignore Extremum Badness Below", "f"),
        "smooth_connection_max_distance": ("Smooth Connection Tolerance", "f"),
        "fractional_ignore_point_zero": ("Ignore .0 Fractional Values", "b"),
        "collinear_vectors_max_distance": ("Collinear Vectors Tolerance", "f"),
        "grid_length": ("Grid Length", "f"),
        "inflection_min": ("Minimum Allowed Inflection t (0–0.5)", "i"),
    }

    def __init__(self, options={}, run_tests=[], title="Select Glyphs With Errors"):
        self.run_tests = {o: o in run_tests for o in default_tests}
        self.options = typechecked_options(options)
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

        for k, val_type in self.option_names.items():
            name, tp = val_type
            v = self.options.get(k)
            if v is None:
                continue

            if tp == "b":
                setattr(
                    self.w,
                    k,
                    CheckBox(
                        (x + 3, y, -10, 20),
                        name,
                        value=v,
                        sizeStyle="small",
                    ),
                )
            else:
                if tp == "f":
                    formatter = float_formatter
                elif tp == "i":
                    formatter = inflection_formatter
                else:
                    print("Unknown value type for option key '%s': '%s'" % (k, tp))
                    continue

                setattr(
                    self.w,
                    "%s_label" % k,
                    TextBox(
                        (x + 18, y + 3, -10, 20),
                        name,
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
                        formatter=formatter,
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
            options = {
                option_name: getattr(self.w, option_name).get()
                for option_name in self.options.keys()
            }
            # print("Set options from dialog:")
            # for k, v in options.items():
            #     print("   ", k, v, type(v))
            run_tests = [
                test_name
                for test_name in self.run_tests
                if getattr(self.w, test_name).get()
            ]
            return self.save_global, options, run_tests
