from __future__ import absolute_import, division, print_function, unicode_literals

default_tests = [
    "test_extrema",
    "test_inflections",
    "test_fractional_coords",
    "test_fractional_transform",
    "test_smooth",
    "test_empty_segments",
    "test_collinear",
    "test_semi_hv",
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
    "inflection_max": 0.7,
}

option_types = {
    "ignore_warnings": bool,
    "extremum_calculate_badness": bool,
    "extremum_ignore_badness_below": int,
    "smooth_connection_max_distance": int,
    "fractional_ignore_point_zero": bool,
    "collinear_vectors_max_distance": int,
    "grid_length": int,
    "inflection_min": float,
    "inflection_max": float,
}

# FIXME: float(0,7) -> Traceback

def typechecked_options(options):
    out = {}
    for k, v in default_options.items():
        cast = option_types.get(k, int)
        out[k] = cast(options.get(k, v))
    return out
