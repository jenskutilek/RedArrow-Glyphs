from typing import NotRequired, TypeAlias, TypedDict

PointTuple: TypeAlias = tuple[float, float]
CubicCurveTuple: TypeAlias = tuple[PointTuple, PointTuple, PointTuple, PointTuple]
QuadraticCurveTuple: TypeAlias = tuple[PointTuple, PointTuple, PointTuple]
RectTuple: TypeAlias = tuple[float, float, float, float]
Vector2D: TypeAlias = tuple[float, float]


class RedArrowOptionsDict(TypedDict):
    # Checks
    RedArrowCheckExtrema: NotRequired[bool]
    RedArrowCheckInflections: NotRequired[bool]
    RedArrowCheckFractionalCoords: NotRequired[bool]
    RedArrowCheckFractionalTransform: NotRequired[bool]
    RedArrowCheckSmooth: NotRequired[bool]
    RedArrowCheckEmptySegments: NotRequired[bool]
    RedArrowCheckCollinear: NotRequired[bool]
    RedArrowCheckSemiHV: NotRequired[bool]
    RedArrowCheckClosepath: NotRequired[bool]
    RedArrowCheckZeroHandles: NotRequired[bool]
    RedArrowCheckBboxHandles: NotRequired[bool]
    RedArrowCheckShortSegments: NotRequired[bool]
    RedArrowCheckSpikes: NotRequired[bool]
    # Options
    RedArrowIgnoreWarnings: NotRequired[bool]
    RedArrowExtremaCalculateBadness: NotRequired[bool]
    RedArrowExtremaIgnoreBadnessBelow: NotRequired[int]
    RedArrowSmoothMaxDistance: NotRequired[int]
    RedArrowCheckSemiHVMinDistance: NotRequired[int]
    RedArrowCheckSemiHVMaxDistance: NotRequired[int]
    RedArrowCheckFractionalIgnorePointZero: NotRequired[bool]
    RedArrowCollinearMaxDistance: NotRequired[int]
    RedArrowGridLengthH: NotRequired[int]
    RedArrowGridLengthV: NotRequired[int]
    RedArrowZeroHandlesMaxDistance: NotRequired[int]
    RedArrowInflectionMin: NotRequired[float]
    RedArrowSpikeAngle: NotRequired[float]
