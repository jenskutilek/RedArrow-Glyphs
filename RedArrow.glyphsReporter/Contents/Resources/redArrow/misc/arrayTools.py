from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from GlyphsApp import GSNode

    from redArrow.typing import PointTuple, RectTuple


def calc_bounds(array: "Sequence[PointTuple]") -> "RectTuple":
    """Return the bounding rectangle of a 2D points array as a tuple:
    (xMin, yMin, xMax, yMax)
    """
    if len(array) == 0:
        return 0, 0, 0, 0
    xs = [x for x, _ in array]
    ys = [y for _, y in array]
    return min(xs), min(ys), max(xs), max(ys)


def is_node_inside_rect(n: "GSNode", rect: "RectTuple") -> bool:
    """
    Test if a point lies inside a rectangle.

    Args:
        n (GSNode): The node
        rect (RectTuple): The rectangle

    Returns:
        bool: Whether the node is inside the triangle
    """

    xMin, yMin, xMax, yMax = rect
    return (xMin <= n.x <= xMax) and (yMin <= n.y <= yMax)


def norm_rect(rect: "RectTuple") -> "RectTuple":
    """Normalize the rectangle so that the following holds:
    xMin <= xMax and yMin <= yMax
    """
    (xMin, yMin, xMax, yMax) = rect
    return min(xMin, xMax), min(yMin, yMax), max(xMin, xMax), max(yMin, yMax)
