from math import atan2, cos, degrees, pi, sin, sqrt
from typing import TYPE_CHECKING, Sequence

from AppKit import NSMakePoint
from GlyphsApp import GSCURVE, GSLINE, GSOFFCURVE, GSQCURVE

from redArrow.misc.arrayTools import normRect
from redArrow.misc.bezierTools import (
    calcCubicParameters,
    calcQuadraticParameters,
    epsilon,
    solveQuadratic,
    splitCubicAtT,
    splitQuadraticAtT,
)
from redArrow.misc.transform import Transform
from redArrow.typing import RedArrowOptionsDict

if TYPE_CHECKING:
    from AppKit import NSAffineTransformStruct, NSPoint, NSRect
    from GlyphsApp import GSComponent, GSLayer, GSNode

    from redArrow.typing import PointTuple, QuadraticCurveTuple, RectTuple, Vector2D


# Helper functions


# from fontTools.misc.arrayTools
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
    roots: Sequence[float],
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
    split_segments = [seg for seg in splitCubicAtT(pt1, pt2, pt3, pt4, *roots)[:-1]]
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
    (ax, ay), (bx, by), c, _ = calcCubicParameters(pt1, pt2, pt3, pt4)
    ax *= 3.0
    ay *= 3.0
    bx *= 2.0
    by *= 2.0
    points: "list[PointTuple]" = []
    vectors: "list[Vector2D]" = []
    if h:
        roots = [t for t in solveQuadratic(ay, by, c[1]) if 0 < t < 1]
        points, vectors = get_extrema_points_vectors(roots, pt1, pt2, pt3, pt4)
    if v:
        roots = [t for t in solveQuadratic(ax, bx, c[0]) if 0 < t < 1]
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
    roots: Sequence[float], pt1: "PointTuple", pt2: "PointTuple", pt3: "PointTuple"
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
    split_segments = [seg for seg in splitQuadraticAtT(pt1, pt2, pt3, *roots)[:-1]]
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
    (ax, ay), (bx, by), _ = calcQuadraticParameters(pt1, pt2, pt3)
    ax *= 2.0
    ay *= 2.0
    points: "list[PointTuple]" = []
    vectors: "list[Vector2D]" = []
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
    ll_x, ll_y, tr_x, tr_y = normRect((ll_x, ll_y, tr_x, tr_y))
    return NSMakePoint(ll_x, ll_y), NSMakePoint(tr_x, tr_y)


class OutlineError:
    level: str = "e"

    def __init__(
        self,
        position: "GSNode | NSPoint | None" = None,
        kind: str = "Unknown error",
        badness: float | None = None,
        vector: "PointTuple | None" = None,
    ) -> None:
        """
        An outline error.

        Args:
            position (NSPoint | None, optional): The position of the error. Defaults to
                None.
            kind (str, optional): The description. Defaults to "Unknown error".
            badness (float | None, optional): The "badness" level. Defaults to None.
            vector (PointTuple | None, optional): The vector at the error position.
                Defaults to None. It is used to determine the angle of the arrow
                pointing at the error.
        """
        self.position = position
        self.kind = kind
        self.badness = badness
        self.vector = vector

    def __repr__(self) -> str:
        """
        Return a string representation of the outline error.

        Returns:
            str: The description
        """
        r = self.kind
        if self.position is not None:
            r += f" at ({self.position.x}, {self.position.y})"
        if self.badness is not None:
            r += f" (badness {self.badness})"
        return r


class OutlineWarning(OutlineError):
    level: str = "w"


class OutlineCheck:
    """
    Reimplementation of FontLab's FontAudit.
    """

    def __init__(
        self,
        layer: "GSLayer | None",
        options: RedArrowOptionsDict | None = None,
        run_checks: Sequence[str] | None = None,
    ) -> None:
        """
        The outline check.

        Args:
            layer (GSLayer | None): The layer that should be checked.
            options (RedArrowOptionsDict | None, optional): The options for each check.
                Defaults to None.
            run_checks (Sequence[str] | None, optional): The names of the checks to be
                run. Defaults to None.
        """
        self.options = RedArrowOptionsDict() if options is None else options
        self.run_checks = [] if run_checks is None else run_checks
        self.reset()
        self.layer = layer

        # Cached test run settings
        self.test_fractional_coords = True
        self.test_smooth = True
        self.test_empty_segments = True
        self.test_collinear = True
        self.test_spikes = True
        self.test_semi_hv = True
        self.test_short_segments = True
        self.test_extrema = True
        self.test_inflections = True
        self.test_zero_handles = True
        self.test_bbox_handles = True
        self.test_fractional_transform = True

    def reset(self) -> None:
        """
        Reset the outline check to its initial state.
        """
        self.errors: list[OutlineError | OutlineWarning] = []

        self.all_checks = [
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
            "test_spikes",
        ]

        # Curve type detection
        self.apparently_cubic = False
        self.apparently_quadratic = False
        self.curve_type_detected = False

        # Mixed composites
        self.glyph_has_components = False
        self.glyph_has_outlines = False

        # Cached bounding box
        self.bb_bottom = 0.0
        self.bb_left = 0.0
        self.bb_top = 0.0

    @property
    def layer(self) -> "GSLayer | None":
        return self._layer

    @layer.setter
    def layer(self, value: "GSLayer | None") -> None:
        self._layer = value
        self.upm = 1000 if self.layer is None else self.layer.parent.parent.upm
        if self._layer is not None:
            try:
                bounds = self._layer.bounds
                self.bb_bottom = bounds.origin.y
                self.bb_left = bounds.origin.x
                self.bb_top = self.bb_bottom + bounds.size.height
            except AttributeError:
                self.bb_bottom = 0
                self.bb_left = 0
                self.bb_top = 0
        self._cache_options()

    def _normalize_upm(self, value: float) -> float:
        """
        Return a value that is normalized from 1000 upm to the current font's upm.

        Args:
            value (float): The value

        Returns:
            float: The normalized value
        """
        return value * self.upm / 1000

    def _cache_options(self) -> None:
        # store options dict into instance variables
        # in the hope that it's faster than asking the dict every time

        # boolean values
        self.extremum_calculate_badness = self.options.get(
            "extremum_calculate_badness", True
        )
        self.fractional_ignore_point_zero = self.options.get(
            "fractional_ignore_point_zero", True
        )

        # absolute values that are converted to current upm
        self.extremum_ignore_badness_below = self._normalize_upm(
            self.options.get("extremum_ignore_badness_below", 1)
        )
        self.smooth_connection_max_distance = self._normalize_upm(
            self.options.get("smooth_connection_max_distance", 4)
        )
        self.collinear_vectors_max_distance = self._normalize_upm(
            self.options.get("collinear_vectors_max_distance", 2)
        )
        self.semi_hv_vectors_min_distance = self._normalize_upm(
            self.options.get("semi_hv_vectors_min_distance", 30)
        )
        self.semi_hv_vectors_max_distance = self._normalize_upm(
            self.options.get("semi_hv_vectors_max_distance", 2)
        )
        self.zero_handles_max_distance = self._normalize_upm(
            self.options.get("zero_handles_max_distance", 0)
        )
        self.inflection_min = self.options.get("inflection_min", 0.3)
        self.spike_angle = self.options.get("spike_angle", 0.49)

        self.grid_length = self.options.get("grid_length", 1)
        self.ignore_warnings = self.options.get("ignore_warnings", False)

        # which checks should be run
        if self.run_checks == []:
            # run all checks
            for t in self.all_checks:
                setattr(self, t, True)
        else:
            # only run supplied checks
            for t in self.all_checks:
                if t in self.run_checks:
                    setattr(self, t, True)
                else:
                    setattr(self, t, False)

    def check_layer(self) -> None:
        self.errors = []
        if self.layer is None:
            return

        for path in self.layer.paths:
            for node in path.nodes:
                node_type = node.type
                if node_type == GSCURVE:
                    self._run_curve_checks(node)
                elif node_type == GSQCURVE:
                    self._run_qcurve_checks(node)
                elif node_type == GSLINE:
                    self._run_line_checks(node)
                else:
                    self._run_offcurve_checks(node)

        for component in self.layer.components:
            self._run_component_checks(component)

    # Checks for different node types

    def _run_line_checks(self, node) -> None:
        prev_node = node.prevNode
        if self.test_fractional_coords:
            self._check_fractional_coordinates(node)
        if self.test_smooth:
            self._check_incorrect_smooth_connection(node)
        if self.test_empty_segments:
            self._check_empty_lines_and_curves(prev_node, node)
        if node.nextNode is not None and node.nextNode.type == GSLINE:
            if self.test_collinear:
                self._check_collinear_vectors(node)
        if self.test_spikes:
            self._check_spike(node)
        if self.test_semi_hv:
            if prev_node is not None:
                self._check_semi_horizontal(prev_node, node)
                self._check_semi_vertical(prev_node, node)
        if self.test_short_segments:
            self._check_short_lines_and_curves(prev_node, node)

    def _run_curve_checks(self, node: "GSNode") -> None:
        node4 = node
        node3 = node4.prevNode  # control point 2
        node2 = node3.prevNode  # control point 1
        node1 = node2.prevNode
        if self.test_extrema:
            self._check_bbox_curve(node1, node2, node3, node4)
        if self.test_inflections:
            self._check_inflections_curve(node1, node2, node3, node4)
        if self.test_fractional_coords:
            self._check_fractional_coordinates(node)
        if not self.curve_type_detected:
            self._count_curve_segment()
        if self.test_smooth:
            self._check_incorrect_smooth_connection(node)
        if self.test_spikes:
            self._check_spike(node)
        if self.test_empty_segments:
            self._check_empty_lines_and_curves(node1, node4)
        if self.test_zero_handles:
            if node3 is not None:
                self._check_zero_handles(node3, node4)
            if not (node2 is None or node1 is None):
                self._check_zero_handles(node2, node1)
        if self.test_semi_hv:
            if not (node2 is None or node1 is None):
                # Start of curve
                self._check_semi_horizontal(node1, node2, "handle")
                self._check_semi_vertical(node1, node2, "handle")
            if node3 is not None:
                # End of curve
                self._check_semi_horizontal(node3, node4, "handle")
                self._check_semi_vertical(node3, node4, "handle")
        if self.test_short_segments:
            if not (node4 is None or node1 is None):
                self._check_short_lines_and_curves(node1, node4)

    def _run_offcurve_checks(self, node: "GSNode") -> None:
        if self.test_fractional_coords:
            self._check_fractional_coordinates(node)
        if self.test_bbox_handles:
            self._check_layer_bbox_handle(node)

    def _run_qcurve_checks(self, node: "GSNode") -> None:
        # Find the previous oncurve node
        start_node = node.prevNode
        start_node_index = node.index
        offcurves = []
        while start_node.type == GSOFFCURVE:
            offcurves.append(start_node)
            start_node = start_node.prevNode
            if start_node.index == start_node_index:
                # There seems to be no other oncurve node
                break
        offcurves.reverse()
        segment = [start_node] + offcurves + [node]

        if self.test_extrema:
            self._check_extrema_quad(segment)
        # FIXME: Not implemented yet
        # if self.test_inflections:
        #     self._check_inflections_quad(node)
        if self.test_fractional_coords:
            self._check_fractional_coordinates(node)
        if not self.curve_type_detected:
            self._count_qcurve_segment()
        if self.test_smooth:
            self._check_incorrect_smooth_connection(node)
        pv = node.prevNode
        nx = start_node.nextNode
        if self.test_empty_segments:
            self._check_empty_lines_and_curves(pv, node)
        if self.test_semi_hv:
            if nx is not None:
                # Start of curve
                self._check_semi_horizontal(start_node, nx, "handle")
                self._check_semi_vertical(start_node, nx, "handle")

            if pv is not None:
                # End of curve
                self._check_semi_horizontal(pv, node, "handle")
                self._check_semi_vertical(pv, node, "handle")
        if self.test_short_segments:
            self._check_short_lines_and_curves(pv, node)
        if self.test_spikes:
            self._check_spike(node)

    def _run_component_checks(self, component: "GSComponent") -> None:
        if self.test_fractional_coords:
            self._check_fractional_component_offset(component)
        if self.test_fractional_transform:
            self._check_fractional_transformation(component)

    # Implementations for all the different checks

    def _check_bbox_curve(
        self, node0: "GSNode", node1: "GSNode", node2: "GSNode", node3: "GSNode"
    ) -> None:
        rect = normRect((node0.x, node0.y, node3.x, node3.y))
        if not is_node_inside_rect(node1, rect) or not is_node_inside_rect(node2, rect):
            extrema, vectors = get_extrema_for_cubic(
                node0, node1, node2, node3, h=True, v=True
            )
            for i, pt in enumerate(extrema):
                vector = vectors[i]
                if abs(vector[1]) < 0.1:
                    error_class = OutlineError
                    desc = "Extremum relevant for hinting"
                else:
                    error_class = OutlineWarning
                    desc = "Extremum"
                if self.extremum_calculate_badness:
                    badness = self._get_badness(pt, rect)
                    if badness >= self.extremum_ignore_badness_below:
                        self.errors.append(
                            error_class(NSMakePoint(*pt), desc, badness, vector=vector)
                        )
                else:
                    self.errors.append(
                        error_class(NSMakePoint(*pt), desc, vector=vector)
                    )

    def _check_layer_bbox_handle(self, node: "GSNode") -> None:
        if self.layer is None:
            return

        if node.x < self.bb_left:
            self.errors.append(
                OutlineError(node, "Handle outside bounding box", vector=(0, -1))
            )
            return

        if node.y > self.bb_top:
            self.errors.append(
                OutlineError(node, "Handle outside bounding box", vector=(-1, 0))
            )
            return

        if node.y < self.bb_bottom:
            self.errors.append(
                OutlineError(node, "Handle outside bounding box", vector=(1, 0))
            )
            return

    def _check_extrema_quad(self, segment: "Sequence[GSNode]") -> None:
        quad = quad_with_explicit_oncurve_points(segment)
        for i in range(0, len(quad) - 1, 2):
            extrema, vectors = get_extrema_for_quadratic(
                quad[i], quad[i + 1], quad[i + 2], h=True, v=True
            )
            for i, p in enumerate(extrema):
                # if self.extremum_calculate_badness:
                # 	badness = self._get_badness(p, myRect)
                # 	if badness >= self.extremum_ignore_badness_below:
                # 		self.errors.append(OutlineError(NSMakePoint(*p), "Extremum", badness, vectors[i]))
                # else:
                self.errors.append(
                    OutlineError(NSMakePoint(*p), "Extremum", vector=vectors[i])
                )

    def _get_badness(self, pointToCheck: "PointTuple", myRect: "RectTuple") -> float:
        # calculate distance of point to rect
        badness = 0.0
        x, y = pointToCheck
        if x < myRect[0]:
            # point is left from rect
            if y < myRect[1]:
                # point is lower left from rect
                badness = int(round(sqrt((myRect[0] - x) ** 2 + (myRect[1] - y) ** 2)))
            elif y > myRect[3]:
                # point is upper left from rect
                badness = int(round(sqrt((myRect[0] - x) ** 2 + (myRect[3] - y) ** 2)))
            else:
                badness = myRect[0] - x
        elif x > myRect[2]:
            # point is right from rect
            if y < myRect[1]:
                # point is lower right from rect
                badness = int(round(sqrt((myRect[2] - x) ** 2 + (myRect[1] - y) ** 2)))
            elif y > myRect[3]:
                # point is upper right from rect
                badness = int(round(sqrt((myRect[2] - x) ** 2 + (myRect[3] - y) ** 2)))
            else:
                badness = x - myRect[2]
        else:
            # point is centered from rect, check for upper/lower
            if y < myRect[1]:
                # point is lower center from rect
                badness = myRect[1] - y
            elif pointToCheck[1] > myRect[3]:
                # point is upper center from rect
                badness = y - myRect[3]
            else:
                badness = 0
        return badness

    def _check_inflections_curve(
        self,
        node0: "GSNode | None",
        node1: "GSNode | None",
        node2: "GSNode | None",
        node3: "GSNode",
    ) -> None:
        if node2 is None or node1 is None or node0 is None:
            return

        ok, err = get_inflections_for_cubic(
            (node0.x, node0.y),
            (node1.x, node1.y),
            (node2.x, node2.y),
            (node3.x, node3.y),
            self.inflection_min,
            1 - self.inflection_min,
        )
        ok_inflections, ok_vectors = ok
        err_inflections, err_vectors = err
        for i, p in enumerate(err_inflections):
            self.errors.append(
                OutlineError(NSMakePoint(*p), "Inflection", vector=err_vectors[i])
            )

        if self.ignore_warnings:
            return

        for i, p in enumerate(ok_inflections):
            self.errors.append(
                OutlineWarning(NSMakePoint(*p), "Inflection", vector=ok_vectors[i])
            )

    def _check_inflections_quad(self, segment: "QuadraticCurveTuple") -> None:
        # FIXME: Not implemented
        inflections, vectors = get_inflections_for_quadratic(segment)
        for i, pt in enumerate(inflections):
            x, y = pt
            self.errors.append(
                OutlineError(NSMakePoint(x, y), "Inflection", vector=vectors[i])
            )

    def _count_curve_segment(self) -> None:
        if self.apparently_quadratic:
            self.errors.append(OutlineError(None, "Mixed cubic and quadratic segments"))
            self.curve_type_detected = True
        self.apparently_cubic = True

    def _count_qcurve_segment(self) -> None:
        if self.apparently_cubic:
            self.errors.append(OutlineError(None, "Mixed cubic and quadratic segments"))
            self.curve_type_detected = True
        self.apparently_quadratic = True

    def _check_fractional_coordinates(self, n: "GSNode") -> bool | None:
        if self.fractional_ignore_point_zero:
            n_prev = round_point(n, self.grid_length)
            if abs(n_prev.x - n.x) < 0.001 and abs(n_prev.y - n.y) < 0.001:
                return False
        else:
            if isinstance(n.x, int) and isinstance(n.y, int):
                return False

        self.errors.append(
            OutlineError(
                n,
                "Fractional Coordinates",  # (%0.2f, %0.2f)" % (pt[0], pt[1]),
                vector=None,
            )
        )
        return None

    def _get_component_error_position(self, component: "GSComponent") -> "NSPoint":
        if component.component is None or self.layer is None:
            return NSMakePoint(0, 0)

        bbox = component.component.layers[self.layer.layerId].bounds
        tbox = transform_rect(bbox, component.transform)
        return nodes_half_point(*tbox)

    def _check_fractional_component_offset(self, component: "GSComponent"):
        for value in component.transform[-2:]:
            if abs(round_value(value, self.grid_length) - value) > 0.001:
                self.errors.append(
                    OutlineError(
                        self._get_component_error_position(component),
                        f"Fractional component offset on ‘{component.componentName}’",
                        vector=None,
                    )
                )
                break

    def _check_fractional_transformation(self, component: "GSComponent") -> None:
        for value in component.transform[:-2]:
            if abs(round(value) - value) > 0.001:
                self.errors.append(
                    OutlineWarning(
                        self._get_component_error_position(component),
                        (
                            "Fractional component transformation "
                            "on ‘%s’" % component.componentName
                        ),
                        vector=None,
                    )
                )
                break

    def _check_incorrect_smooth_connection(self, node: "GSNode") -> None:
        """
        Check for nearly smooth connections.
        """
        prev_node = node.prevNode
        next_node = node.nextNode

        if prev_node is None or next_node is None:
            return

        # angle of previous reference node to current node
        phi1 = nodes_angle(prev_node, node)
        phi2 = nodes_angle(node, next_node)

        # distance of the current node to next reference node
        dist1 = nodes_distance(prev_node, node)
        dist2 = nodes_distance(node, next_node)

        if dist1 >= dist2:
            # distance 1 is longer, check dist2 for correct angle
            dist = dist2
            phi = phi1
            ref = next_node
        else:
            # distance 2 is longer, check dist1 for correct angle
            dist = dist1
            phi = phi2 - pi
            ref = prev_node

        # Ignore short segments
        if dist > 2 * self.smooth_connection_max_distance:
            # TODO: Add sanity check to save calculating the projected
            # point for each segment?
            # This fails for connections around 180 degrees which may be
            # reported as 180 or -180
            # if 0 < abs(phi1 - phi2) < 0.1: # 0.1 (radians) = 5.7 degrees
            # Calculate where the second reference point should be
            # TODO: Decide which angle is more important?
            # E.g. line to curve: line is fixed, curve / tangent point is
            # flexible?
            # or always consider the longer segment more important?
            projected_pt = NSMakePoint(
                node.x + dist * cos(phi),
                node.y + dist * sin(phi),
            )
            # Compare projected position with actual position
            badness = nodes_distance(round_point(projected_pt, self.grid_length), ref)
            if self.grid_length == 0:
                d = 0.49
            else:
                d = self.grid_length * 0.49
            if d < badness:
                if node.smooth or badness < self.smooth_connection_max_distance:
                    self.errors.append(
                        OutlineError(
                            node,
                            "Not quite smooth connection",
                            badness,
                            vector=nodes_normal_vector(prev_node, node),
                        )
                    )

    def _check_empty_lines_and_curves(self, node0: "GSNode", node1: "GSNode") -> None:
        if node0 is None or node1 is None:
            return

        if node0.x == node1.x and node0.y == node1.y:
            self.errors.append(
                OutlineError(
                    node1,
                    "Zero-length distance",
                    vector=nodes_normal_vector(node0, node1),
                )
            )

    def _check_short_lines_and_curves(self, node0: "GSNode", node1: "GSNode") -> None:
        if node0 is None or node1 is None:
            return

        if abs(node0.x - node1.x) <= 1 and abs(node0.y - node1.y) <= 1:
            self.errors.append(
                OutlineWarning(
                    node0,
                    "Short segment",
                    vector=nodes_normal_vector(node0, node1),
                )
            )

    def _check_collinear_vectors(self, node: "GSNode") -> None:
        """
        Check for consecutive lines that have nearly the same angle.
        """
        prev_node = node.prevNode
        next_node = node.nextNode

        if prev_node is None or next_node is None:
            return

        # angle of previous reference point to current point
        phi1 = nodes_angle(prev_node, node)
        # angle of current point to next reference point
        # could be used for angle check without distance check
        # phi2 = nodes_angle(pt, next_ref)
        # distance of pt to next reference point
        dist = nodes_distance(node, next_node)
        projected_pt = NSMakePoint(
            node.x + dist * cos(phi1),
            node.y + dist * sin(phi1),
        )
        badness = nodes_distance(round_point(projected_pt, self.grid_length), next_node)
        if badness < self.collinear_vectors_max_distance:
            self.errors.append(
                OutlineError(
                    node,
                    "Collinear vectors",
                    badness,
                    nodes_normal_vector(prev_node, next_node),
                )
            )

    def _check_spike(self, node: "GSNode") -> None:
        """
        Check for consecutive segments that have a very narrow angle.
        """
        prev_node = node.prevNode
        next_node = node.nextNode

        if prev_node is None or next_node is None:
            return

        phi1 = nodes_angle(prev_node, node)
        phi2 = nodes_angle(next_node, node)
        if abs(phi2 - phi1) < self.spike_angle:
            self.errors.append(
                OutlineWarning(
                    node, "Spike", vector=nodes_normal_vector(prev_node, next_node)
                )
            )

    def _check_semi_horizontal(
        self, node0: "GSNode", node1: "GSNode", segment: str = "line"
    ) -> None:
        """
        Check for semi-horizontal lines and handles.
        """
        if nodes_distance(node0, node1) > self.semi_hv_vectors_min_distance:
            phi = nodes_angle(node0, node1)
            rho = atan2(1, 31)
            if (
                0 < abs(phi) < rho
                or 0 < abs(phi - pi) < rho
                or 0 < abs(abs(phi) - pi) < rho
            ):
                if abs(node1.y - node0.y) <= self.semi_hv_vectors_max_distance:
                    self.errors.append(
                        OutlineError(
                            nodes_half_point(node0, node1),
                            "Semi-horizontal %s" % segment,
                            degrees(phi),
                            nodes_normal_vector(node0, node1),
                        )
                    )

    def _check_semi_vertical(
        self, node0: "GSNode", node1: "GSNode", segment: str = "line"
    ) -> None:
        """
        Check for semi-vertical lines and handles.
        """
        # TODO: Option to respect Italic angle?
        if nodes_distance(node0, node1) > self.semi_hv_vectors_min_distance:
            phi = nodes_angle(node0, node1)
            rho = atan2(31, 1)
            if 0 < abs(phi - 0.5 * pi) < rho or 0 < abs(phi + 0.5 * pi) < rho:
                if abs(node1.x - node0.x) <= self.semi_hv_vectors_max_distance:
                    self.errors.append(
                        OutlineError(
                            nodes_half_point(node0, node1),
                            "Semi-vertical %s" % segment,
                            degrees(phi),
                            nodes_normal_vector(node0, node1),
                        )
                    )

    def _check_zero_handles(self, node0, node1) -> None:
        badness = nodes_distance(node0, node1)
        if badness <= self.zero_handles_max_distance:
            self.errors.append(
                OutlineError(
                    node1, "Zero handle", badness, nodes_normal_vector(node0, node1)
                )
            )
