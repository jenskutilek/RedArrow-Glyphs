from typing import NotRequired, TypeAlias, TypedDict

PointTuple: TypeAlias = tuple[float, float]
CubicCurveTuple: TypeAlias = tuple[PointTuple, PointTuple, PointTuple, PointTuple]
QuadraticCurveTuple: TypeAlias = tuple[PointTuple, PointTuple, PointTuple]
RectTuple: TypeAlias = tuple[float, float, float, float]
Vector2D: TypeAlias = tuple[float, float]


class RedArrowOptionsDict(TypedDict):
    RedArrowIgnoreWarnings: NotRequired[bool]
    RedArrowExtremaCalculateBadness: NotRequired[bool]
    RedArrowExtremaIgnoreBadnessBelow: NotRequired[int]
    RedArrowSmoothMaxDistance: NotRequired[int]
    RedArrowCheckSemiHVMinDistance: NotRequired[int]
    RedArrowCheckSemiHVMaxDistance: NotRequired[int]
    RedArrowCheckFractionalIgnorePointZero: NotRequired[bool]
    RedArrowCollinearMaxDistance: NotRequired[int]
    RedArrowGridLength: NotRequired[int]
    RedArrowZeroHandlesMaxDistance: NotRequired[int]
    RedArrowInflectionMin: NotRequired[float]
    RedArrowSpikeAngle: NotRequired[float]
