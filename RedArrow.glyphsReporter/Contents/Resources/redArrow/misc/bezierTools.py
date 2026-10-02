"""Partly based on fontTools.misc.bezierTools.py -- tools for working with bezier path
segments.
"""

from math import acos, cos, pi, sqrt
from typing import TYPE_CHECKING

from AppKit import NSMakePoint

from redArrow.misc.arrayTools import calc_bounds
from redArrow.misc.transform import Transform

if TYPE_CHECKING:
    from collections.abc import Sequence

    from AppKit import NSAffineTransformStruct, NSPoint, NSRect
    from GlyphsApp import GSNode

    from redArrow.typing import PointTuple, RectTuple, Vector2D

__all__ = [
    "calc_cubic_bounds",
    "calc_quadratic_bounds",
    "solve_cubic",
    "solve_quadratic",
    "split_cubic",
    "split_cubic_at_t",
    "split_line",
    "split_quadratic",
    "split_quadratic_at_t",
]


epsilon = 1e-12


def calc_quadratic_bounds(
    pt1: "PointTuple", pt2: "PointTuple", pt3: "PointTuple"
) -> "RectTuple":
    """Return the bounding rectangle for a qudratic bezier segment.
    pt1 and pt3 are the "anchor" points, pt2 is the "handle".

        >>> calc_quadratic_bounds((0, 0), (50, 100), (100, 0))
        (0, 0, 100, 50.0)
        >>> calc_quadratic_bounds((0, 0), (100, 0), (100, 100))
        (0.0, 0.0, 100, 100)
    """
    (ax, ay), (bx, by), (cx, cy) = calc_quadratic_parameters(pt1, pt2, pt3)
    ax2 = ax * 2.0
    ay2 = ay * 2.0
    roots = []
    if ax2 != 0:
        roots.append(-bx / ax2)
    if ay2 != 0:
        roots.append(-by / ay2)
    points = [
        (ax * t * t + bx * t + cx, ay * t * t + by * t + cy)
        for t in roots
        if 0 <= t < 1
    ] + [pt1, pt3]
    return calc_bounds(points)


def calc_cubic_bounds(
    pt1: "PointTuple", pt2: "PointTuple", pt3: "PointTuple", pt4: "PointTuple"
) -> "RectTuple":
    """Return the bounding rectangle for a cubic bezier segment.
    pt1 and pt4 are the "anchor" points, pt2 and pt3 are the "handles".

        >>> calc_cubic_bounds((0, 0), (25, 100), (75, 100), (100, 0))
        (0, 0, 100, 75.0)
        >>> calc_cubic_bounds((0, 0), (50, 0), (100, 50), (100, 100))
        (0.0, 0.0, 100, 100)
        >>> print "%f %f %f %f" % calc_cubic_bounds((50, 0), (0, 100), (100, 100), (50, 0))
        35.566243 0.000000 64.433757 75.000000
    """
    (ax, ay), (bx, by), (cx, cy), (dx, dy) = calc_cubic_parameters(pt1, pt2, pt3, pt4)
    # calc first derivative
    ax3 = ax * 3.0
    ay3 = ay * 3.0
    bx2 = bx * 2.0
    by2 = by * 2.0
    xRoots = [t for t in solve_quadratic(ax3, bx2, cx) if 0 <= t < 1]
    yRoots = [t for t in solve_quadratic(ay3, by2, cy) if 0 <= t < 1]
    roots = xRoots + yRoots

    points = [
        (
            ax * t * t * t + bx * t * t + cx * t + dx,
            ay * t * t * t + by * t * t + cy * t + dy,
        )
        for t in roots
    ] + [pt1, pt4]
    return calc_bounds(points)


def split_line(
    pt1: "PointTuple", pt2: "PointTuple", where: float, isHorizontal: bool
) -> "list[tuple[PointTuple, PointTuple]]":
    """Split the line between pt1 and pt2 at position 'where', which
    is an x coordinate if isHorizontal is False, a y coordinate if
    isHorizontal is True. Return a list of two line segments if the
    line was successfully split, or a list containing the original
    line.

        >>> print_segments(split_line((0, 0), (100, 100), 50, True))
        ((0, 0), (50.0, 50.0))
        ((50.0, 50.0), (100, 100))
        >>> print_segments(split_line((0, 0), (100, 100), 100, True))
        ((0, 0), (100, 100))
        >>> print_segments(split_line((0, 0), (100, 100), 0, True))
        ((0, 0), (0.0, 0.0))
        ((0.0, 0.0), (100, 100))
        >>> print_segments(split_line((0, 0), (100, 100), 0, False))
        ((0, 0), (0.0, 0.0))
        ((0.0, 0.0), (100, 100))
    """
    pt1x, pt1y = pt1
    pt2x, pt2y = pt2

    ax = pt2x - pt1x
    ay = pt2y - pt1y

    bx = pt1x
    by = pt1y

    if ax == 0:
        return [(pt1, pt2)]

    t = (where - (bx, by)[isHorizontal]) / ax
    if 0 <= t < 1:
        midPt = ax * t + bx, ay * t + by
        return [(pt1, midPt), (midPt, pt2)]
    else:
        return [(pt1, pt2)]


def split_quadratic(
    pt1: "PointTuple",
    pt2: "PointTuple",
    pt3: "PointTuple",
    where: float,
    isHorizontal: bool,
) -> "list[tuple[PointTuple, PointTuple, PointTuple]]":
    """Split the quadratic curve between pt1, pt2 and pt3 at position 'where',
    which is an x coordinate if isHorizontal is False, a y coordinate if
    isHorizontal is True. Return a list of curve segments.

        >>> print_segments(split_quadratic((0, 0), (50, 100), (100, 0), 150, False))
        ((0, 0), (50, 100), (100, 0))
        >>> print_segments(split_quadratic((0, 0), (50, 100), (100, 0), 50, False))
        ((0.0, 0.0), (25.0, 50.0), (50.0, 50.0))
        ((50.0, 50.0), (75.0, 50.0), (100.0, 0.0))
        >>> print_segments(split_quadratic((0, 0), (50, 100), (100, 0), 25, False))
        ((0.0, 0.0), (12.5, 25.0), (25.0, 37.5))
        ((25.0, 37.5), (62.5, 75.0), (100.0, 0.0))
        >>> print_segments(split_quadratic((0, 0), (50, 100), (100, 0), 25, True))
        ((0.0, 0.0), (7.32233047034, 14.6446609407), (14.6446609407, 25.0))
        ((14.6446609407, 25.0), (50.0, 75.0), (85.3553390593, 25.0))
        ((85.3553390593, 25.0), (92.6776695297, 14.6446609407), (100.0, -7.1054273576e-15))
        >>> # XXX I'm not at all sure if the following behavior is desirable:
        >>> print_segments(split_quadratic((0, 0), (50, 100), (100, 0), 50, True))
        ((0.0, 0.0), (25.0, 50.0), (50.0, 50.0))
        ((50.0, 50.0), (50.0, 50.0), (50.0, 50.0))
        ((50.0, 50.0), (75.0, 50.0), (100.0, 0.0))
    """
    a, b, c = calc_quadratic_parameters(pt1, pt2, pt3)
    solutions = solve_quadratic(
        a[isHorizontal], b[isHorizontal], c[isHorizontal] - where
    )
    solutions = sorted([t for t in solutions if 0 <= t < 1])
    if not solutions:
        return [(pt1, pt2, pt3)]
    return _split_quadratic_at_t(a, b, c, *solutions)


def split_cubic(
    pt1: "PointTuple",
    pt2: "PointTuple",
    pt3: "PointTuple",
    pt4: "PointTuple",
    where: float,
    isHorizontal: bool,
) -> "list[tuple[PointTuple, PointTuple, PointTuple, PointTuple]]":
    """Split the cubic curve between pt1, pt2, pt3 and pt4 at position 'where',
    which is an x coordinate if isHorizontal is False, a y coordinate if
    isHorizontal is True. Return a list of curve segments.

        >>> print_segments(split_cubic((0, 0), (25, 100), (75, 100), (100, 0), 150, False))
        ((0, 0), (25, 100), (75, 100), (100, 0))
        >>> print_segments(split_cubic((0, 0), (25, 100), (75, 100), (100, 0), 50, False))
        ((0.0, 0.0), (12.5, 50.0), (31.25, 75.0), (50.0, 75.0))
        ((50.0, 75.0), (68.75, 75.0), (87.5, 50.0), (100.0, 0.0))
        >>> print_segments(split_cubic((0, 0), (25, 100), (75, 100), (100, 0), 25, True))
        ((0.0, 0.0), (2.2937927384, 9.17517095361), (4.79804488188, 17.5085042869), (7.47413641001, 25.0))
        ((7.47413641001, 25.0), (31.2886200204, 91.6666666667), (68.7113799796, 91.6666666667), (92.52586359, 25.0))
        ((92.52586359, 25.0), (95.2019551181, 17.5085042869), (97.7062072616, 9.17517095361), (100.0, 1.7763568394e-15))
    """
    a, b, c, d = calc_cubic_parameters(pt1, pt2, pt3, pt4)
    solutions = solve_cubic(
        a[isHorizontal],
        b[isHorizontal],
        c[isHorizontal],
        d[isHorizontal] - where,
    )
    solutions = sorted([t for t in solutions if 0 <= t < 1])
    if not solutions:
        return [(pt1, pt2, pt3, pt4)]
    return _split_cubic_at_t(a, b, c, d, *solutions)


def split_quadratic_at_t(
    pt1: "PointTuple", pt2: "PointTuple", pt3: "PointTuple", *ts
) -> "list[tuple[PointTuple, PointTuple, PointTuple]]":
    """Split the quadratic curve between pt1, pt2 and pt3 at one or more
    values of t. Return a list of curve segments.

        >>> print_segments(split_quadratic_at_t((0, 0), (50, 100), (100, 0), 0.5))
        ((0.0, 0.0), (25.0, 50.0), (50.0, 50.0))
        ((50.0, 50.0), (75.0, 50.0), (100.0, 0.0))
        >>> print_segments(split_quadratic_at_t((0, 0), (50, 100), (100, 0), 0.5, 0.75))
        ((0.0, 0.0), (25.0, 50.0), (50.0, 50.0))
        ((50.0, 50.0), (62.5, 50.0), (75.0, 37.5))
        ((75.0, 37.5), (87.5, 25.0), (100.0, 0.0))
    """
    a, b, c = calc_quadratic_parameters(pt1, pt2, pt3)
    return _split_quadratic_at_t(a, b, c, *ts)


def split_cubic_at_t(
    pt1: "PointTuple", pt2: "PointTuple", pt3: "PointTuple", pt4: "PointTuple", *ts
) -> "list[tuple[PointTuple, PointTuple, PointTuple, PointTuple]]":
    """Split the cubic curve between pt1, pt2, pt3 and pt4 at one or more
    values of t. Return a list of curve segments.

        >>> print_segments(split_cubic_at_t((0, 0), (25, 100), (75, 100), (100, 0), 0.5))
        ((0.0, 0.0), (12.5, 50.0), (31.25, 75.0), (50.0, 75.0))
        ((50.0, 75.0), (68.75, 75.0), (87.5, 50.0), (100.0, 0.0))
        >>> print_segments(split_cubic_at_t((0, 0), (25, 100), (75, 100), (100, 0), 0.5, 0.75))
        ((0.0, 0.0), (12.5, 50.0), (31.25, 75.0), (50.0, 75.0))
        ((50.0, 75.0), (59.375, 75.0), (68.75, 68.75), (77.34375, 56.25))
        ((77.34375, 56.25), (85.9375, 43.75), (93.75, 25.0), (100.0, 0.0))
    """
    a, b, c, d = calc_cubic_parameters(pt1, pt2, pt3, pt4)
    return _split_cubic_at_t(a, b, c, d, *ts)


def _split_quadratic_at_t(
    a: "PointTuple", b: "PointTuple", c: "PointTuple", *ts
) -> "list[tuple[PointTuple, PointTuple, PointTuple]]":
    tsl = list(ts)
    segments = []
    tsl.insert(0, 0.0)
    tsl.append(1.0)
    ax, ay = a
    bx, by = b
    cx, cy = c
    for i in range(len(tsl) - 1):
        t1 = tsl[i]
        t2 = tsl[i + 1]
        delta = t2 - t1
        # calc new a, b and c
        a1x = ax * delta**2
        a1y = ay * delta**2
        b1x = (2 * ax * t1 + bx) * delta
        b1y = (2 * ay * t1 + by) * delta
        c1x = ax * t1**2 + bx * t1 + cx
        c1y = ay * t1**2 + by * t1 + cy

        pt1, pt2, pt3 = calcQuadraticPoints((a1x, a1y), (b1x, b1y), (c1x, c1y))
        segments.append((pt1, pt2, pt3))
    return segments


def _split_cubic_at_t(
    a: "PointTuple", b: "PointTuple", c: "PointTuple", d: "PointTuple", *ts
) -> "list[tuple[PointTuple, PointTuple, PointTuple, PointTuple]]":
    tsl = list(ts)
    tsl.insert(0, 0.0)
    tsl.append(1.0)
    segments = []
    ax, ay = a
    bx, by = b
    cx, cy = c
    dx, dy = d
    for i in range(len(tsl) - 1):
        t1 = tsl[i]
        t2 = tsl[i + 1]
        delta = t2 - t1
        # calc new a, b, c and d
        a1x = ax * delta**3
        a1y = ay * delta**3
        b1x = (3 * ax * t1 + bx) * delta**2
        b1y = (3 * ay * t1 + by) * delta**2
        c1x = (2 * bx * t1 + cx + 3 * ax * t1**2) * delta
        c1y = (2 * by * t1 + cy + 3 * ay * t1**2) * delta
        d1x = ax * t1**3 + bx * t1**2 + cx * t1 + dx
        d1y = ay * t1**3 + by * t1**2 + cy * t1 + dy
        pt1, pt2, pt3, pt4 = calcCubicPoints(
            (a1x, a1y), (b1x, b1y), (c1x, c1y), (d1x, d1y)
        )
        segments.append((pt1, pt2, pt3, pt4))
    return segments


#
# Equation solvers.
#


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


def solve_quadratic(a: float, b: float, c: float, sqrt=sqrt) -> list[float]:
    """Solve a quadratic equation where a, b and c are real.
        a*x*x + b*x + c = 0
    This function returns a list of roots. Note that the returned list
    is neither guaranteed to be sorted nor to contain unique values!
    """
    if abs(a) < epsilon:
        if abs(b) < epsilon:
            # We have a non-equation; therefore, we have no valid solution
            roots = []
        else:
            # We have a linear equation with 1 root.
            roots = [-c / b]
    else:
        # We have a true quadratic equation.  Apply the quadratic formula to find two roots.
        DD = b * b - 4.0 * a * c
        if DD >= 0.0:
            rDD = sqrt(DD)
            roots = [(-b + rDD) / 2.0 / a, (-b - rDD) / 2.0 / a]
        else:
            # complex roots, ignore
            roots = []
    return roots


def solve_cubic(a: float, b: float, c: float, d: float) -> list[float]:
    """Solve a cubic equation where a, b, c and d are real.
        a*x*x*x + b*x*x + c*x + d = 0
    This function returns a list of roots. Note that the returned list
    is neither guaranteed to be sorted nor to contain unique values!
    """
    #
    # adapted from:
    #   CUBIC.C - Solve a cubic polynomial
    #   public domain by Ross Cottrell
    # found at: http://www.strangecreations.com/library/snippets/Cubic.C
    #
    if abs(a) < epsilon:
        # don't just test for zero; for very small values of 'a' solve_cubic()
        # returns unreliable results, so we fall back to quad.
        return solve_quadratic(b, c, d)
    a = float(a)
    a1 = b / a
    a2 = c / a
    a3 = d / a

    Q = (a1 * a1 - 3.0 * a2) / 9.0
    R = (2.0 * a1 * a1 * a1 - 9.0 * a1 * a2 + 27.0 * a3) / 54.0
    R2_Q3 = R * R - Q * Q * Q

    if R2_Q3 < 0:
        theta = acos(R / sqrt(Q * Q * Q))
        rQ2 = -2.0 * sqrt(Q)
        x0 = rQ2 * cos(theta / 3.0) - a1 / 3.0
        x1 = rQ2 * cos((theta + 2.0 * pi) / 3.0) - a1 / 3.0
        x2 = rQ2 * cos((theta + 4.0 * pi) / 3.0) - a1 / 3.0
        return [x0, x1, x2]
    else:
        if Q == 0 and R == 0:
            x: float | int = 0
        else:
            x = pow(sqrt(R2_Q3) + abs(R), 1 / 3.0)
            x = x + Q / x
        if R >= 0.0:
            x = -x
        x = x - a1 / 3.0
        return [x]


#
# Conversion routines for points to parameters and vice versa
#


def calc_quadratic_parameters(
    pt1: "PointTuple", pt2: "PointTuple", pt3: "PointTuple"
) -> "tuple[PointTuple, PointTuple, PointTuple]":
    x2, y2 = pt2
    x3, y3 = pt3
    cx, cy = pt1
    bx = (x2 - cx) * 2.0
    by = (y2 - cy) * 2.0
    ax = x3 - cx - bx
    ay = y3 - cy - by
    return (ax, ay), (bx, by), (cx, cy)


def calc_cubic_parameters(
    pt1: "PointTuple", pt2: "PointTuple", pt3: "PointTuple", pt4: "PointTuple"
) -> "tuple[PointTuple, PointTuple, PointTuple, PointTuple]":
    x2, y2 = pt2
    x3, y3 = pt3
    x4, y4 = pt4
    dx, dy = pt1
    cx = (x2 - dx) * 3.0
    cy = (y2 - dy) * 3.0
    bx = (x3 - x2) * 3.0 - cx
    by = (y3 - y2) * 3.0 - cy
    ax = x4 - dx - cx - bx
    ay = y4 - dy - cy - by
    return (ax, ay), (bx, by), (cx, cy), (dx, dy)


def calcQuadraticPoints(
    a: "PointTuple", b: "PointTuple", c: "PointTuple"
) -> "tuple[PointTuple, PointTuple, PointTuple]":
    ax, ay = a
    bx, by = b
    cx, cy = c
    x1 = cx
    y1 = cy
    x2 = (bx * 0.5) + cx
    y2 = (by * 0.5) + cy
    x3 = ax + bx + cx
    y3 = ay + by + cy
    return (x1, y1), (x2, y2), (x3, y3)


def calcCubicPoints(
    a: "PointTuple", b: "PointTuple", c: "PointTuple", d: "PointTuple"
) -> "tuple[PointTuple, PointTuple, PointTuple, PointTuple]":
    ax, ay = a
    bx, by = b
    cx, cy = c
    dx, dy = d
    x1 = dx
    y1 = dy
    x2 = (cx / 3.0) + dx
    y2 = (cy / 3.0) + dy
    x3 = (bx + cx) / 3.0 + x2
    y3 = (by + cy) / 3.0 + y2
    x4 = ax + dx + cx + bx
    y4 = ay + dy + cy + by
    return (x1, y1), (x2, y2), (x3, y3), (x4, y4)


def _segmentrepr(obj: "Sequence"):
    """
    >>> _segmentrepr([1, [2, 3], [], [[2, [3, 4], [0.1, 2.2]]]])
    '(1, (2, 3), (), ((2, (3, 4), (0.1, 2.2))))'
    """
    try:
        it = iter(obj)
    except TypeError:
        return str(obj)
    else:
        return "({})".format(", ".join([_segmentrepr(x) for x in it]))


def print_segments(segments: "Sequence") -> None:
    """Helper for the doctests, displaying each segment in a list of
    segments on a single line as a tuple.
    """
    for segment in segments:
        print(_segmentrepr(segment))


def quad_with_explicit_oncurve_points(
    quad: "Sequence[GSNode|NSPoint]",
) -> "list[PointTuple]":
    """
    Take a quadratic segment of GSNodes and add implied oncurve points

    Args:
        quad (Sequence[GSNode]): The quadratic segment with implicit oncurve points

    Returns:
        list[PointTuple]: The quadratic segment as tuple points with explicit oncurve points
    """
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


def round_point(pt: "GSNode | NSPoint", grid_length: int = 1) -> "NSPoint":
    """
    Return a copy of point or node pt with its coordinates rounded depending on
        grid_length.

    Args:
        pt (GSNode | NSPoint): The node or point
        grid_length (int, optional): The grid length. Defaults to 1.

    Returns:
        NSPoint: The rounded point
    """
    x = round_value(pt.x, grid_length)
    y = round_value(pt.y, grid_length)
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
        vr: int = round(v)
    else:
        vr = round(v / grid_length) * grid_length
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
