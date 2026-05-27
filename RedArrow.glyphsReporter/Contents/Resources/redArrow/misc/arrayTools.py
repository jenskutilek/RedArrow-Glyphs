#
# Various array and rectangle tools, but mostly rectangles, hence the
# name of this module (not).
#
import math
from typing import Callable, Sequence

from redArrow.typing import PointTuple, RectTuple


def calcBounds(array: Sequence[PointTuple]) -> RectTuple:
    """Return the bounding rectangle of a 2D points array as a tuple:
    (xMin, yMin, xMax, yMax)
    """
    if len(array) == 0:
        return 0, 0, 0, 0
    xs = [x for x, _ in array]
    ys = [y for _, y in array]
    return min(xs), min(ys), max(xs), max(ys)


def calcIntBounds(array: Sequence[PointTuple]) -> tuple[int, int, int, int]:
    """Return the integer bounding rectangle of a 2D points array as a
    tuple: (xMin, yMin, xMax, yMax)
    """
    xMin, yMin, xMax, yMax = calcBounds(array)
    xMin = int(math.floor(xMin))
    xMax = int(math.ceil(xMax))
    yMin = int(math.floor(yMin))
    yMax = int(math.ceil(yMax))
    return xMin, yMin, xMax, yMax


def updateBounds(
    bounds, p: PointTuple, min: Callable = min, max: Callable = max
) -> RectTuple:
    """Return the bounding recangle of rectangle bounds and point (x, y)."""
    (x, y) = p
    xMin, yMin, xMax, yMax = bounds
    return min(xMin, x), min(yMin, y), max(xMax, x), max(yMax, y)


def pointInRect(p: PointTuple, rect: RectTuple) -> bool:
    """Return True when point (x, y) is inside rect."""
    (x, y) = p
    xMin, yMin, xMax, yMax = rect
    return (xMin <= x <= xMax) and (yMin <= y <= yMax)


def pointsInRect(array: Sequence[PointTuple], rect: RectTuple):
    """Find out which points or array are inside rect.
    Returns an array with a boolean for each point.
    """
    if len(array) < 1:
        return []
    xMin, yMin, xMax, yMax = rect
    return [(xMin <= x <= xMax) and (yMin <= y <= yMax) for x, y in array]


def vectorLength(vector: PointTuple) -> float:
    """Return the length of the given vector."""
    x, y = vector
    return math.sqrt(x**2 + y**2)


def asInt16(array: Sequence[float]) -> list[int]:
    """Round and cast to 16 bit integer."""
    return [int(math.floor(i + 0.5)) for i in array]


def normRect(rect: RectTuple) -> RectTuple:
    """Normalize the rectangle so that the following holds:
    xMin <= xMax and yMin <= yMax
    """
    (xMin, yMin, xMax, yMax) = rect
    return min(xMin, xMax), min(yMin, yMax), max(xMin, xMax), max(yMin, yMax)


def scaleRect(rect: RectTuple, x: float, y: float) -> RectTuple:
    """Scale the rectangle by x, y."""
    (xMin, yMin, xMax, yMax) = rect
    return xMin * x, yMin * y, xMax * x, yMax * y


def offsetRect(rect: RectTuple, dx: float, dy: float) -> RectTuple:
    """Offset the rectangle by dx, dy."""
    (xMin, yMin, xMax, yMax) = rect
    return xMin + dx, yMin + dy, xMax + dx, yMax + dy


def insetRect(rect: RectTuple, dx: float, dy: float) -> RectTuple:
    """Inset the rectangle by dx, dy on all sides."""
    (xMin, yMin, xMax, yMax) = rect
    return xMin + dx, yMin + dy, xMax - dx, yMax - dy


def sectRect(rect1: RectTuple, rect2: RectTuple) -> tuple[bool, RectTuple]:
    """Return a boolean and a rectangle. If the input rectangles intersect,
    return True and the intersecting rectangle. Return False and (0, 0, 0, 0)
    if the input rectangles don't intersect.
    """
    (xMin1, yMin1, xMax1, yMax1) = rect1
    (xMin2, yMin2, xMax2, yMax2) = rect2
    xMin, yMin, xMax, yMax = (
        max(xMin1, xMin2),
        max(yMin1, yMin2),
        min(xMax1, xMax2),
        min(yMax1, yMax2),
    )
    if xMin >= xMax or yMin >= yMax:
        return False, (0, 0, 0, 0)
    return True, (xMin, yMin, xMax, yMax)


def unionRect(rect1: RectTuple, rect2: RectTuple) -> RectTuple:
    """Return the smallest rectangle in which both input rectangles are fully
    enclosed. In other words, return the total bounding rectangle of both input
    rectangles.
    """
    (xMin1, yMin1, xMax1, yMax1) = rect1
    (xMin2, yMin2, xMax2, yMax2) = rect2
    xMin, yMin, xMax, yMax = (
        min(xMin1, xMin2),
        min(yMin1, yMin2),
        max(xMax1, xMax2),
        max(yMax1, yMax2),
    )
    return (xMin, yMin, xMax, yMax)


def rectCenter(rect0: RectTuple) -> PointTuple:
    """Return the center of the rectangle as an (x, y) coordinate."""
    (xMin, yMin, xMax, yMax) = rect0
    return (xMin + xMax) / 2, (yMin + yMax) / 2


def intRect(rect1: RectTuple) -> tuple[int, int, int, int]:
    """Return the rectangle, rounded off to integer values, but guaranteeing
    that the resulting rectangle is NOT smaller than the original.
    """
    (xMin, yMin, xMax, yMax) = rect1
    xMin = int(math.floor(xMin))
    yMin = int(math.floor(yMin))
    xMax = int(math.ceil(xMax))
    yMax = int(math.ceil(yMax))
    return (xMin, yMin, xMax, yMax)
