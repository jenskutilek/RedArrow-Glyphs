from __future__ import absolute_import, division, print_function, unicode_literals

import objc
from AppKit import NSDecimalNumber

default_tests = [
    "test_extrema",
    "test_inflections",
    "test_fractional_coords",
    "test_fractional_transform",
    "test_smooth",
    "test_empty_segments",
    "test_collinear",
    "test_semi_hv",
    # "test_closepath",
    "test_zero_handles",
    "test_bbox_handles",
    "test_short_segments",
]

default_options = {
    "ignore_warnings": False,
    "extremum_calculate_badness": False,
    "extremum_ignore_badness_below": 0,
    "smooth_connection_max_distance": 4,
    "fractional_ignore_point_zero": True,
    "collinear_vectors_max_distance": 2,
    "grid_length": 1,
    "inflection_min": 0.3,
}

option_types = {
    "ignore_warnings": "bool",
    "extremum_calculate_badness": "bool",
    "extremum_ignore_badness_below": "float",
    "smooth_connection_max_distance": "float",
    "fractional_ignore_point_zero": "bool",
    "collinear_vectors_max_distance": "float",
    "grid_length": "float",
    "inflection_min": "float",
}


def typechecked_options(options):
    out = {}
    for k, v in default_options.items():
        t = option_types.get(k, "float")
        if t == "bool":
            out[k] = bool(options.get(k, v))
        elif t == "float":
            v = options.get(k, v)
            if isinstance(v, NSDecimalNumber):
                out[k] = v.floatValue()
            elif isinstance(v, objc._pythonify.OC_PythonFloat) or isinstance(
                v, objc._pythonify.OC_PythonLong
            ):
                out[k] = float(v)
            elif isinstance(v, float) or isinstance(v, int):
                out[k] = v
            else:
                print(
                    "Unknown type for %s: '%s', using default value: %s"
                    % (k, type(v), default_options[k])
                )
        else:
            print(
                "Unknown type for %s: '%s', using default value: %s"
                % (k, type(v), default_options[k])
            )

    return out
