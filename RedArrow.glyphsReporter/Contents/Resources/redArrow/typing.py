from typing import NotRequired, TypeAlias, TypedDict

PointTuple: TypeAlias = tuple[float, float]
CubicCurveTuple: TypeAlias = tuple[PointTuple, PointTuple, PointTuple, PointTuple]
QuadraticCurveTuple: TypeAlias = tuple[PointTuple, PointTuple, PointTuple]
RectTuple: TypeAlias = tuple[float, float, float, float]
Vector2D: TypeAlias = tuple[float, float]


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
