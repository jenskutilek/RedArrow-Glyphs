from decimal import ROUND_HALF_UP, Decimal, DefaultContext, setcontext
from math import atan2, sqrt
from typing import TYPE_CHECKING

from AppKit import NSMakePoint

from redArrow.misc.arrayTools import norm_rect
from redArrow.misc.bezierTools import (
    calc_cubic_parameters,
    calc_quadratic_parameters,
    epsilon,
    solve_quadratic,
    split_cubic_at_t,
    split_quadratic_at_t,
)
from redArrow.misc.transform import Transform

if TYPE_CHECKING:
    from collections.abc import Sequence

    from AppKit import NSAffineTransformStruct, NSPoint, NSRect
    from GlyphsApp import GSNode

    from redArrow.typing import PointTuple, QuadraticCurveTuple, Vector2D


DefaultContext.rounding = ROUND_HALF_UP
setcontext(DefaultContext)


def solve_linear(a: float, b: float) -> list[float]:
    if abs(a) < epsilon:
        if abs(b) < epsilon:
            roots = []
        else:
            roots = [0.0]
    else:
        DD = b * b
        if DD >= 0.0:
            rDD = sqrt(DD)
            roots = [(-b + rDD) / 2.0 / a, (-b - rDD) / 2.0 / a]
        else:
            roots = []
    return roots


def quad_with_explicit_oncurve_points(
    on0: "GSNode",
    offcurves: "Sequence[GSNode|NSPoint]",
    on1: "GSNode",
) -> "list[PointTuple]":
    """
    Take a quadratic segment of GSNodes and add implied oncurve points

    Args:
        quad (Sequence[GSNode]): The quadratic segment with implicit oncurve points

    Returns:
        list[PointTuple]: The quadratic segment as tuple points with explicit oncurve points
    """
    # FIXME: Use the args directly
    quad: list[GSNode | NSPoint] = []
    quad.append(on0)
    quad.extend(offcurves)
    quad.append(on1)
    # end of fixme
    new_quad = [quad[0]]
    for i in range(1, len(quad) - 2):
        new_quad.append(quad[i])
        new_quad.append(nodes_half_point(quad[i], quad[i + 1]))
    new_quad.extend(quad[-2:])
    # Convert to tuples
    return [(p.x, p.y) for p in new_quad]


def get_extrema_points_vectors(
    roots: "Sequence[float]",
    pt1: "PointTuple",
    pt2: "PointTuple",
    pt3: "PointTuple",
    pt4: "PointTuple",
) -> "tuple[list[PointTuple], list[Vector2D]]":
    """
    Calculate extremum points and the normal vectors for those points for a cubic
    segment represented by four control points and the roots of the extrema.

    Args:
        roots (Sequence[float]): The extrema roots
        pt1 (PointTuple): The first control point
        pt2 (PointTuple): The second control point
        pt3 (PointTuple): The third control point
        pt4 (PointTuple): The fourth control point

    Returns:
        tuple[list[PointTuple], list[Vector2D]]: The extremum points and normal vectors
    """
    split_segments = [seg for seg in split_cubic_at_t(pt1, pt2, pt3, pt4, *roots)[:-1]]
    points = [pt[3] for pt in split_segments]
    vectors = [pts_normal_vector(pt[2], pt[3]) for pt in split_segments]
    return points, vectors


def get_extrema_for_cubic(
    node1: "GSNode",
    node2: "GSNode",
    node3: "GSNode",
    node4: "GSNode",
    h: bool = True,
    v: bool = False,
) -> "tuple[list[PointTuple], list[Vector2D]]":
    """
    Calculate extremum points and the normal vectors for those points for a cubic
    segment represented by four control points as GSNodes.

    Args:
        node1 (GSNode): The first control point as GSNode
        node2 (GSNode): The second control point as GSNode
        node3 (GSNode): The third control point as GSNode
        node4 (GSNode): The fourth control point as GSNode
        h (bool, optional): Whether to find horizontal extrema. Defaults to True.
        v (bool, optional): Whether to find vertical extrema. Defaults to False.

    Returns:
        tuple[list[PointTuple], list[Vector2D]]: The extremum points and normal vectors
    """
    pt1 = (node1.x, node1.y)
    pt2 = (node2.x, node2.y)
    pt3 = (node3.x, node3.y)
    pt4 = (node4.x, node4.y)
    (ax, ay), (bx, by), c, _ = calc_cubic_parameters(pt1, pt2, pt3, pt4)
    ax *= 3.0
    ay *= 3.0
    bx *= 2.0
    by *= 2.0
    points: list[PointTuple] = []
    vectors: list[Vector2D] = []
    if h:
        roots = [t for t in solve_quadratic(ay, by, c[1]) if 0 < t < 1]
        points, vectors = get_extrema_points_vectors(roots, pt1, pt2, pt3, pt4)
    if v:
        roots = [t for t in solve_quadratic(ax, bx, c[0]) if 0 < t < 1]
        v_points, v_vectors = get_extrema_points_vectors(roots, pt1, pt2, pt3, pt4)
        points += v_points
        vectors += v_vectors
    return points, vectors


def get_inflections_for_cubic(
    pt1: "PointTuple",
    pt2: "PointTuple",
    pt3: "PointTuple",
    pt4: "PointTuple",
    err_min: float = 0.3,
    err_max: float = 0.7,
) -> "tuple[tuple[list[PointTuple], list[Vector2D]], tuple[list[PointTuple], list[Vector2D]]]":
    """
    Calculate inflection points and the normal vectors for those points for a cubic
    segment represented by four control points.

    Args:
        pt1 (PointTuple): The first control point
        pt2 (PointTuple): The second control point
        pt3 (PointTuple): The third control point
        pt4 (PointTuple): The fourth control point
        err_min (float, optional): The minimum allowed t of an inflection point. Defaults to 0.3.
        err_max (float, optional): The maximum allowed t of an inflection point. Defaults to 0.7.

    Returns:
        tuple[tuple[list[PointTuple], list[Vector2D]], tuple[list[PointTuple], list[Vector2D]]]:
            The inflection points and normal vectors. The first part of the tuple are the
            inflection points that are allowed per minimum and maximum t, the second part
            are the inflection points that are considered errors.
    """
    # After https://github.com/mekkablue/InsertInflections
    roots: list[float] = []

    x1, y1 = pt1
    x2, y2 = pt2
    x3, y3 = pt3
    x4, y4 = pt4

    ax = x2 - x1
    ay = y2 - y1
    bx = x3 - x2 - ax
    by = y3 - y2 - ay
    cx = x4 - x3 - ax - bx - bx
    cy = y4 - y3 - ay - by - by

    c0 = (ax * by) - (ay * bx)
    c1 = (ax * cy) - (ay * cx)
    c2 = (bx * cy) - (by * cx)

    if abs(c2) > 0.00001:
        discr = (c1**2) - (4 * c0 * c2)
        c2 *= 2
        if abs(discr) < 0.000001:
            root = -c1 / c2
            if 0.001 < root < 0.999:
                roots.append(root)
        elif discr > 0:
            discr = discr**0.5
            root = (-c1 - discr) / c2
            if 0.001 < root < 0.999:
                roots.append(root)

            root = (-c1 + discr) / c2
            if 0.001 < root < 0.999:
                roots.append(root)
    elif c1 != 0.0:
        root = -c0 / c1
        if 0.001 < root < 0.999:
            roots.append(root)

    ok_inflections = []
    err_inflections = []
    for r in roots:
        if err_min < r < err_max:
            ok_inflections.append(r)
        else:
            err_inflections.append(r)
    return (
        get_extrema_points_vectors(ok_inflections, pt1, pt2, pt3, pt4),
        get_extrema_points_vectors(err_inflections, pt1, pt2, pt3, pt4),
    )


def get_extrema_points_vectors_quad(
    roots: "Sequence[float]", pt1: "PointTuple", pt2: "PointTuple", pt3: "PointTuple"
) -> "tuple[list[PointTuple], list[Vector2D]]":
    """
    Calculate extremum points and the normal vectors for those points for a quadratic
    segment represented by four control points and the roots of the extrema.

    Args:
        roots (Sequence[float]): The extrema roots
        pt1 (PointTuple): The first control point
        pt2 (PointTuple): The second control point
        pt3 (PointTuple): The third control point

    Returns:
        tuple[list[PointTuple], list[Vector2D]]: The extremum points and normal vectors
    """
    split_segments = [seg for seg in split_quadratic_at_t(pt1, pt2, pt3, *roots)[:-1]]
    points = [pt[2] for pt in split_segments]
    vectors = [pts_normal_vector(pt[1], pt[2]) for pt in split_segments]
    return points, vectors


def get_extrema_for_quadratic(
    pt1: "PointTuple",
    pt2: "PointTuple",
    pt3: "PointTuple",
    h: bool = True,
    v: bool = False,
) -> "tuple[list[PointTuple], list[Vector2D]]":
    """
    Calculate extremum points and the normal vectors for those points for a quadratic
    segment represented by four control points.

    Args:
        pt1 (PointTuple): The first control point
        pt2 (PointTuple): The second control point
        pt3 (PointTuple): The third control point
        h (bool, optional): Whether to find horizontal extrema. Defaults to True.
        v (bool, optional): Whether to find vertical extrema. Defaults to False.

    Returns:
        tuple[list[PointTuple], list[Vector2D]]: The extremum points and normal vectors
    """
    (ax, ay), (bx, by), _ = calc_quadratic_parameters(pt1, pt2, pt3)
    ax *= 2.0
    ay *= 2.0
    points: list[PointTuple] = []
    vectors: list[Vector2D] = []
    if h:
        roots = [t for t in solve_linear(ay, by) if 0 < t < 1]
        points, vectors = get_extrema_points_vectors_quad(roots, pt1, pt2, pt3)
    if v:
        roots = [t for t in solve_linear(ax, bx) if 0 < t < 1]
        v_points, v_vectors = get_extrema_points_vectors_quad(roots, pt1, pt2, pt3)
        points += v_points
        vectors += v_vectors
    return points, vectors


def get_inflections_for_quadratic(
    segment: "QuadraticCurveTuple",
) -> "tuple[list[PointTuple], list[Vector2D]]":
    """
    Calculate inflection points and the normal vectors for those points for a quadratic
    segment represented by a number of control points.

    This method is not implemented yet and will return empty lists.

    Args:
        segment (QuadraticCurveTuple): The quadratic segment as a sequence of point
            tuples with explicit oncurve points

    Returns:
        tuple[list[PointTuple], list[Vector2D]]: The inflection points and normal
            vectors
    """
    if len(segment) < 2:
        return [], []
    else:
        # TODO: Implement the actual check
        return [], []


def round_point(
    pt: "GSNode | NSPoint", grid_length_h: int = 1, grid_length_v: int | None = None
) -> "NSPoint":
    """
    Return a copy of point or node pt with its coordinates rounded depending on
        grid_length.

    Args:
        pt (GSNode | NSPoint): The node or point
        grid_length_h (int, optional): The horizontal grid length. Defaults to 1.
        grid_length_v (int | None, optional): The vertical grid length. Defaults to
            None. If None, the horizontal grid length is used for both dimensions.

    Returns:
        NSPoint: The rounded point
    """
    x = round_value(pt.x, grid_length_h)
    y = round_value(pt.y, grid_length_v or grid_length_h)
    return NSMakePoint(x, y)


def round_value(v: float, grid_length: int = 1) -> float | int:
    """
    Return a value rounded depending on grid_length.

    Args:
        v (float): The value
        grid_length (int, optional): The grid length. Defaults to 1.

    Returns:
        float | int: The rounded value. If the grid lenth is 0, the value is not
            rounded.
    """
    if grid_length == 0:
        return v
    elif grid_length == 1:
        vr: int = int(round(Decimal(str(v)), 0))
    else:
        vr = int(round(Decimal(str(v / grid_length)), 0)) * grid_length
    return vr


def nodes_normal_vector(node1: "GSNode", node2: "GSNode") -> "PointTuple":
    """
    Return the normal vector of the line connecting two nodes.

    Args:
        node1 (GSNode): The first node
        node2 (GSNode): The second node

    Returns:
        Vector2D: The normal vector
    """
    return (node2.x - node1.x, node2.y - node1.y)


def pts_normal_vector(pt1: "PointTuple", pt2: "PointTuple") -> "Vector2D":
    """
    Return the normal vector of the line connecting two tuple points.

    Args:
        pt1 (PointTuple): The first point
        pt2 (PointTuple): The second point

    Returns:
        Vector2D: The normal vector
    """
    pt1x, pt1y = pt1
    pt2x, pt2y = pt2
    return (pt2x - pt1x, pt2y - pt1y)


def nodes_angle(node1: "GSNode", node2: "GSNode") -> float:
    """
    Return the angle between two nodes as radians.

    Args:
        node1 (GSNode): The first node
        node2 (GSNode): The second node

    Returns:
        float: The angle in radians
    """
    return atan2(node2.y - node1.y, node2.x - node1.x)


def nodes_distance(node1: "GSNode | NSPoint", node2: "GSNode | NSPoint") -> float:
    """
    Return the distance between two nodes.

    Args:
        node1 (GSNode | NSPoint): The first node
        node2 (GSNode | NSPoint): The second node

    Returns:
        float: The distance
    """
    return sqrt((node2.y - node1.y) ** 2 + (node2.x - node1.x) ** 2)


def nodes_half_point(node1: "GSNode | NSPoint", node2: "GSNode | NSPoint") -> "NSPoint":
    """
    Return the halfway point between two nodes.

    Args:
        node1 (GSNode | NSPoint): The first node
        node1 (GSNode | NSPoint): The second node

    Returns:
        NSPoint: The halfway point
    """
    x = (node1.x + node2.x) / 2
    y = (node1.y + node2.y) / 2
    return NSMakePoint(x, y)


def transform_rect(
    rect: "NSRect",
    matrix: "NSAffineTransformStruct | tuple[float, float, float, float, float, float]",
) -> "tuple[NSPoint, NSPoint]":
    """
    Transform a rectangle with a matrix.

    Args:
        rect (NSRect): The rectangle
        matrix (NSAffineTransformStruct | tuple[float, float, float, float, float, float]):
            The transformation matrix

    Returns:
        tuple[NSPoint, NSPoint]: The transformed rectangle described by its lower left
            and top right points
    """
    t = Transform(*matrix)
    ll_x, ll_y = t.transformPoint((rect.origin.x, rect.origin.y))
    tr_x, tr_y = t.transformPoint(
        (rect.origin.x + rect.size.width, rect.origin.y + rect.size.height)
    )
    ll_x, ll_y, tr_x, tr_y = norm_rect((ll_x, ll_y, tr_x, tr_y))
    return NSMakePoint(ll_x, ll_y), NSMakePoint(tr_x, tr_y)
