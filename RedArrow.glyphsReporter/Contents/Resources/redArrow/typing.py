from typing import NotRequired, TypedDict

type CubicCurveTuple = tuple[PointTuple, PointTuple, PointTuple, PointTuple]
type PointTuple = tuple[float, float]
type QuadraticCurveTuple = tuple[PointTuple, PointTuple, PointTuple]
type RectTuple = tuple[float, float, float, float]


class RedArrowOptionsDict(TypedDict):
    ignore_warnings: NotRequired[bool]
    extremum_calculate_badness: NotRequired[bool]
    extremum_ignore_badness_below: NotRequired[int]
    smooth_connection_max_distance: NotRequired[int]
    semi_hv_vectors_min_distance: NotRequired[int]
    semi_hv_vectors_max_distance: NotRequired[int]
    fractional_ignore_point_zero: NotRequired[bool]
    collinear_vectors_max_distance: NotRequired[int]
    grid_length: NotRequired[int]
    zero_handles_max_distance: NotRequired[int]
    inflection_min: NotRequired[float]
    spike_angle: NotRequired[float]
