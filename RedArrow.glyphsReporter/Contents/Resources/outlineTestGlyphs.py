from AppKit import NSMakePoint
from fontTools.misc.arrayTools import normRect
from fontTools.misc.bezierTools import (
    calcQuadraticParameters,
    calcCubicParameters,
    solveQuadratic,
    splitCubicAtT,
    splitQuadraticAtT,
    epsilon,
)
from fontTools.misc.transform import Transform
from GlyphsApp import CURVE, LINE, QCURVE
from math import atan2, degrees, cos, pi, sin, sqrt


# Helper functions


def get_bounds(font, glyphname):
    return (0, 0, 0, 0)
    # FIXME: We need to find the layer.bounds() in Glyphs
    # return font.glyphs[glyphname].bounds()


# from fontTools.misc.arrayTools
def pointInRect(p, rect):
    """Test if a point is inside a bounding rectangle."""
    xMin, yMin, xMax, yMax = rect
    return (xMin <= p.x <= xMax) and (yMin <= p.y <= yMax)


def solveLinear(a, b):
    if abs(a) < epsilon:
        if abs(b) < epsilon:
            roots = []
        else:
            roots = [0]
    else:
        DD = b * b
        if DD >= 0.0:
            rDD = sqrt(DD)
            roots = [(-b + rDD) / 2.0 / a, (-b - rDD) / 2.0 / a]
        else:
            roots = []
    return roots


def add_implied_oncurve_points_quad(quad):
    new_quad = [quad[0]]
    for i in range(1, len(quad) - 2):
        new_quad.append(quad[i])
        new_quad.append(half_point(quad[i], quad[i + 1]))
    new_quad.extend(quad[-2:])
    return new_quad


def get_extrema_points_vectors(roots, pt1, pt2, pt3, pt4):
    split_segments = [p for p in splitCubicAtT(pt1, pt2, pt3, pt4, *roots)[:-1]]
    points = [p[3] for p in split_segments]
    vectors = [get_vector_tuple(p[2], p[3]) for p in split_segments]
    return points, vectors


def getExtremaForCubic(pt1, pt2, pt3, pt4, h=True, v=False):
    pt1 = (pt1.x, pt1.y)
    pt2 = (pt2.x, pt2.y)
    pt3 = (pt3.x, pt3.y)
    pt4 = (pt4.x, pt4.y)
    (ax, ay), (bx, by), c, d = calcCubicParameters(pt1, pt2, pt3, pt4)
    ax *= 3.0
    ay *= 3.0
    bx *= 2.0
    by *= 2.0
    points = []
    vectors = []
    if h:
        roots = [t for t in solveQuadratic(ay, by, c[1]) if 0 < t < 1]
        points, vectors = get_extrema_points_vectors(roots, pt1, pt2, pt3, pt4)
    if v:
        roots = [t for t in solveQuadratic(ax, bx, c[0]) if 0 < t < 1]
        v_points, v_vectors = get_extrema_points_vectors(roots, pt1, pt2, pt3, pt4)
        points += v_points
        vectors += v_vectors
    return points, vectors


def getInflectionsForCubic(pt1, pt2, pt3, pt4, err_min=0.3, err_max=0.7):
    # After https://github.com/mekkablue/InsertInflections
    roots = []

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


def get_extrema_points_vectors_quad(roots, pt1, pt2, pt3):
    split_segments = [p for p in splitQuadraticAtT(pt1, pt2, pt3, *roots)[:-1]]
    points = [p[2] for p in split_segments]
    vectors = [get_vector_tuple(p[1], p[2]) for p in split_segments]
    return points, vectors


def getExtremaForQuadratic(pt1, pt2, pt3, h=True, v=False):
    (ax, ay), (bx, by), c = calcQuadraticParameters(pt1, pt2, pt3)
    ax *= 2.0
    ay *= 2.0
    points = []
    vectors = []
    if h:
        roots = [t for t in solveLinear(ay, by) if 0 < t < 1]
        points, vectors = get_extrema_points_vectors_quad(roots, pt1, pt2, pt3)
    if v:
        roots = [t for t in solveLinear(ax, bx) if 0 < t < 1]
        v_points, v_vectors = get_extrema_points_vectors_quad(roots, pt1, pt2, pt3)
        points += v_points
        vectors += v_vectors
    return points, vectors


def getInflectionsForQuadratic(pt1, bcps, pt2):
    if len(bcps) < 2:
        return [], []
    else:
        # TODO: Implement the actual check
        return [], []


def round_point(pt, gridLength=1):
    # Return a rounded copy of point pt, depending on gridLength
    pr = NSMakePoint(pt.x, pt.y)
    if gridLength == 1:
        pr.x = int(round(pt.x))
        pr.y = int(round(pt.y))
        return pr
    elif gridLength == 0:
        return pr
    else:
        pr.x = round(pt.x / gridLength) * gridLength
        pr.y = round(pt.y / gridLength) * gridLength
        return pr


def get_vector(p0, p1):
    return (p1.x - p0.x, p1.y - p0.y)


def get_vector_tuple(p0, p1):
    p0x, p0y = p0
    p1x, p1y = p1
    return (p1x - p0x, p1y - p0y)


def angle_between_points(p0, p1):
    return atan2(p1.y - p0.y, p1.x - p0.x)


def distance_between_points(p0, p1):
    return sqrt((p1.y - p0.y) ** 2 + (p1.x - p0.x) ** 2)


def half_point(p0, p1):
    p01 = NSMakePoint(p0.x, p0.y)
    p01.x = (p0.x + p1.x) / 2
    p01.y = (p0.y + p1.y) / 2
    return p01


def transform_bbox(bbox, matrix):
    t = Transform(*matrix)
    ll_x, ll_y = t.transformPoint((bbox[0], bbox[1]))
    tr_x, tr_y = t.transformPoint((bbox[2], bbox[3]))
    return normRect((ll_x, ll_y, tr_x, tr_y))


class OutlineError(object):
    level = "e"

    def __init__(self, position=None, kind="Unknown error", badness=None, vector=None):
        self.position = position
        self.kind = kind
        self.badness = badness
        self.vector = vector

    def __repr__(self):
        r = "%s" % self.kind
        if self.position is not None:
            r += " at (%i, %i)" % (self.position.x, self.position.y)
        if self.badness is not None:
            r += " (badness %i)" % self.badness
        return r


class OutlineWarning(OutlineError):
    level = "w"


class OutlineTest:
    """
    Reimplementation of FontLab's FontAudit.
    """

    def __init__(self, layer, options={}, run_tests=[]):
        self.layer = layer

        self.current_vector = None

        self.options = options
        self.run_tests = run_tests
        self.errors = []

        self.all_tests = [
            "test_extrema",
            "test_inflections",
            "test_fractional_coords",
            "test_fractional_transform",
            "test_smooth",
            "test_empty_segments",
            "test_collinear",
            "test_semi_hv",
            "test_closepath",
            "test_zero_handles",
            "test_bbox_handles",
        ]

        # Curve type detection
        self.apparentlyCubic = False
        self.apparentlyQuadratic = False
        self.curveTypeDetected = False

        # Mixed composites
        self.glyphHasComponents = False
        self.glyphHasOutlines = False

        self._cache_options()

    @property
    def layer(self):
        return self._layer

    @layer.setter
    def layer(self, value):
        self._layer = value
        self.upm = self.layer.parent.parent.upm

    def _normalize_upm(self, value):
        """
        Return a value that is normalized from 1000 upm to the current font's
        upm
        """
        return value * self.upm / 1000

    def _cache_options(self):
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
        self.zero_handles_max_distance = self._normalize_upm(
            self.options.get("zero_handles_max_distance", 0)
        )

        self.grid_length = self.options.get("grid_length", 1)

        # which tests should be run
        if self.run_tests == []:
            # run all tests
            for t in self.all_tests:
                setattr(self, t, True)
        else:
            # only run supplied tests
            for t in self.all_tests:
                if t in self.run_tests:
                    setattr(self, t, True)
                else:
                    setattr(self, t, False)

    def checkLayer(self):
        self.errors = []
        for path in self.layer.paths:
            print("Path start")
            for node in path.nodes:
                print(f"    {node}")
                node_type = node.type
                if node_type == CURVE:
                    self._runCurveTests(node)
                elif node_type == QCURVE:
                    self._runQCurveTests(node)
                elif node_type == LINE:
                    self._runLineTests(node)
                else:
                    self._runOffcurveTests(node)
            print("Path end")

        for component in self.layer.components:
            self._runComponentTests(component)

    # Tests for different node types

    def _runLineTests(self, node):
        if self.test_fractional_coords:
            self._checkFractionalCoordinates(node)
        if self.test_smooth:
            self._checkIncorrectSmoothConnection(node)
        if self.test_empty_segments:
            self._checkEmptyLinesAndCurves(node)
        if self.test_collinear and node.nextNode.type == LINE:
            self._checkCollinearVectors(node)
        if self.test_semi_hv:
            self._checkSemiHorizontalLine(node.prevNode, node)
            self._checkSemiVerticalLine(node.prevNode, node)

    def _runCurveTests(self, node):
        if self.test_extrema:
            self._checkBboxCurve(node)
        if self.test_inflections:
            self._checkInflectionsSegment(node)
        if self.test_fractional_coords:
            self._checkFractionalCoordinates(node)
        if not self.curveTypeDetected:
            self._countCurveSegment()
        if self.test_smooth:
            self._checkIncorrectSmoothConnection(node)
        if self.test_empty_segments:
            self._checkEmptyLinesAndCurves(node)
        # if self.test_zero_handles:
        #     self._checkZeroHandles(node.prevNode, node)
        #     self._checkZeroHandles(node, node.nextNode)
        if self.test_semi_hv:
            self._checkSemiHorizontalHandle(node.prevNode, node)
            self._checkSemiVerticalHandle(node.prevNode, node)

    def _runOffcurveTests(self, node):
        if self.test_fractional_coords:
            self._checkFractionalCoordinates(node)

    def _runQCurveTests(self, node):
        # if self.test_extrema:
        #     self._checkExtremaQuad(node)
        # if self.test_inflections:
        #     self._checkInflectionsQuad(node)
        if self.test_fractional_coords:
            self._checkFractionalCoordinates(node)
        if not self.curveTypeDetected:
            self._countQCurveSegment()
        if self.test_smooth:
            self._checkIncorrectSmoothConnection(node)
        if self.test_empty_segments:
            self._checkEmptyLinesAndCurves(node)
        # if self.test_semi_hv:
        #     self._checkSemiHorizontalHandles(node)
        #     self._checkSemiVerticalHandles(node)

    def _runComponentTests(self, component):
        if self.test_fractional_transform:
            self._checkFractionalTransformation(
                component.component, component.transform
            )

    # Implementations for all the different tests

    def _checkBboxCurve(self, node):
        pt3 = node
        bcp2 = node.prevNode
        bcp1 = bcp2.prevNode
        pt0 = bcp1.prevNode
        myRect = normRect((pt0.x, pt0.y, pt3.x, pt3.y))
        if not pointInRect(bcp1, myRect) or not pointInRect(bcp2, myRect):
            extrema, vectors = getExtremaForCubic(pt0, bcp1, bcp2, pt3, h=True, v=True)
            for i, p in enumerate(extrema):
                if self.extremum_calculate_badness:
                    badness = self._getBadness(p, myRect)
                    if badness >= self.extremum_ignore_badness_below:
                        self.errors.append(
                            OutlineError(
                                NSMakePoint(*p), "Extremum", badness, vectors[i]
                            )
                        )
                else:
                    self.errors.append(
                        OutlineError(NSMakePoint(*p), "Extremum", vector=vectors[i])
                    )

    def _checkExtremaQuad(self, bcps, pt):
        quad = add_implied_oncurve_points_quad([self._prev] + bcps + [pt])
        for i in range(0, len(quad) - 1, 2):
            extrema, vectors = getExtremaForQuadratic(
                quad[i], quad[i + 1], quad[i + 2], h=True, v=True
            )
            for i, p in enumerate(extrema):
                # if self.extremum_calculate_badness:
                # 	badness = self._getBadness(p, myRect)
                # 	if badness >= self.extremum_ignore_badness_below:
                # 		self.errors.append(OutlineError(NSMakePoint(*p), "Extremum", badness, vectors[i]))
                # else:
                self.errors.append(
                    OutlineError(NSMakePoint(*p), "Extremum", vector=vectors[i])
                )

    def _getBadness(self, pointToCheck, myRect):
        # calculate distance of point to rect
        badness = 0
        if pointToCheck.x < myRect[0]:
            # point is left from rect
            if pointToCheck.y < myRect[1]:
                # point is lower left from rect
                badness = int(
                    round(
                        sqrt(
                            (myRect[0] - pointToCheck.x) ** 2
                            + (myRect[1] - pointToCheck.y) ** 2
                        )
                    )
                )
            elif pointToCheck.y > myRect[3]:
                # point is upper left from rect
                badness = int(
                    round(
                        sqrt(
                            (myRect[0] - pointToCheck.x) ** 2
                            + (myRect[3] - pointToCheck.y) ** 2
                        )
                    )
                )
            else:
                badness = myRect[0] - pointToCheck.x
        elif pointToCheck.x > myRect[2]:
            # point is right from rect
            if pointToCheck.y < myRect[1]:
                # point is lower right from rect
                badness = int(
                    round(
                        sqrt(
                            (myRect[2] - pointToCheck.x) ** 2
                            + (myRect[1] - pointToCheck.y) ** 2
                        )
                    )
                )
            elif pointToCheck.y > myRect[3]:
                # point is upper right from rect
                badness = int(
                    round(
                        sqrt(
                            (myRect[2] - pointToCheck.x) ** 2
                            + (myRect[3] - pointToCheck.y) ** 2
                        )
                    )
                )
            else:
                badness = pointToCheck.x - myRect[2]
        else:
            # point is centered from rect, check for upper/lower
            if pointToCheck.y < myRect[1]:
                # point is lower center from rect
                badness = myRect[1] - pointToCheck.y
            elif pointToCheck[1] > myRect[3]:
                # point is upper center from rect
                badness = pointToCheck.y - myRect[3]
            else:
                badness = 0
        return badness

    def _checkInflectionsSegment(self, node):
        pt3 = node
        bcp2 = node.prevNode
        bcp1 = bcp2.prevNode
        pt0 = bcp1.prevNode
        ok, err = getInflectionsForCubic(
            (pt0.x, pt0.y),
            (bcp1.x, bcp1.y),
            (bcp2.x, bcp2.y),
            (pt3.x, pt3.y),
            self.options["inflection_min"],
            self.options["inflection_max"],
        )
        ok_inflections, ok_vectors = ok
        err_inflections, err_vectors = err
        for i, p in enumerate(err_inflections):
            self.errors.append(
                OutlineError(NSMakePoint(*p), "Inflection", vector=err_vectors[i])
            )
        for i, p in enumerate(ok_inflections):
            self.errors.append(
                OutlineWarning(NSMakePoint(*p), "Inflection", vector=ok_vectors[i])
            )

    def _checkInflectionsQuad(self, bcps, pt):
        inflections, vectors = getInflectionsForQuadratic(self._prev, bcps, pt)
        for i, p in enumerate(inflections):
            self.errors.append(
                OutlineError(NSMakePoint(*p), "Inflection", vector=vectors[i])
            )

    def _countCurveSegment(self):
        if self.apparentlyQuadratic:
            self.errors.append(OutlineError(None, "Mixed cubic and quadratic segments"))
            self.curveTypeDetected = True
        self.apparentlyCubic = True

    def _countQCurveSegment(self):
        if self.apparentlyCubic:
            self.errors.append(OutlineError(None, "Mixed cubic and quadratic segments"))
            self.curveTypeDetected = True
        self.apparentlyQuadratic = True

    def _checkFractionalCoordinates(self, pt):
        if self.fractional_ignore_point_zero:
            pr = round_point(pt, self.grid_length)
            if abs(pr.x - pt.x) < 0.001 and abs(pr.y - pt.y) < 0.001:
                return False
        else:
            if type(pt.x) == int and type(pt.y == int):
                return False

        self.errors.append(
            OutlineError(
                pt,
                "Fractional Coordinates",  # (%0.2f, %0.2f)" % (pt[0], pt[1]),
                vector=None,
            )
        )

    def _checkFractionalTransformation(self, baseGlyph, transformation):
        bbox = get_bounds(self.glyphSet, baseGlyph)
        tbox = transform_bbox(bbox, transformation)
        if self.fractional_ignore_point_zero:
            for p in transformation[-2:]:
                if round(p) != p:
                    self.errors.append(
                        OutlineError(
                            half_point((tbox[0], tbox[1]), (tbox[2], tbox[3])),
                            "Fractional transformation",
                            # (%0.2f, %0.2f, %0.2f, %0.2f, %0.2f, %0.2f)" % transformation
                            vector=None,
                        )
                    )
                    break
        else:
            for p in transformation[-2:]:
                if type(p) == float:
                    self.errors.append(
                        OutlineError(
                            half_point((tbox[0], tbox[1]), (tbox[2], tbox[3])),
                            "Fractional transformation",
                            # (%0.2f, %0.2f, %0.2f, %0.2f, %0.2f, %0.2f)" % transformation
                            vector=None,
                        )
                    )
                    break

    def _checkIncorrectSmoothConnection(self, node):
        """
        Test for nearly smooth connections.
        """
        prev_node = node.prevNode
        next_node = node.nextNode

        # angle of previous reference point to current point
        phi1 = angle_between_points(prev_node, node)
        phi2 = angle_between_points(node, next_node)

        # distance of pt to next reference point
        dist1 = distance_between_points(prev_node, node)
        dist2 = distance_between_points(node, next_node)

        # print("Checking:")
        # print("  ", prev_node, node, degrees(phi1), dist1)
        # print("  ", node, next_node, degrees(phi2), dist2)

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

        # print(
        # 	"  Chose: %s -> %s, angle %0.2f, dist %0.2f" % (
        # 		ref, next_ref, degrees(phi), dist
        # 	)
        # )

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
            badness = distance_between_points(
                round_point(projected_pt, self.grid_length), ref
            )
            # print(
            # 	"  Projected: %s, actual: %s, diff: %0.2f" % (
            # 		projected_pt, ref, badness
            # 	)
            # )
            if self.grid_length == 0:
                d = 0.49
            else:
                d = self.grid_length * 0.49
            if d < badness:
                if node.smooth or badness < self.smooth_connection_max_distance:
                    self.errors.append(
                        OutlineError(
                            node,
                            "Incorrect smooth connection",
                            badness,
                            vector=get_vector(prev_node, node),
                        )
                    )

    def _checkEmptyLinesAndCurves(self, node):
        if node.prevNode.x == node.x and node.prevNode.y == node.y:
            self.errors.append(
                OutlineError(
                    node,
                    "Zero-length distance",
                    vector=get_vector(node.prevNode, node.nextNode),
                )
            )

    def _checkCollinearVectors(self, node):
        """
        Test for consecutive lines that have nearly the same angle.
        """
        prev_node = node.prevNode
        next_node = node.nextNode
        # if next_ref != pt:
        # angle of previous reference point to current point
        phi1 = angle_between_points(prev_node, node)
        # angle of current point to next reference point
        # could be used for angle check without distance check
        # phi2 = angle_between_points(pt, next_ref)
        # distance of pt to next reference point
        dist = distance_between_points(node, next_node)
        projected_pt = NSMakePoint(
            node.x + dist * cos(phi1),
            node.y + dist * sin(phi1),
        )
        badness = distance_between_points(
            round_point(projected_pt, self.grid_length), next_node
        )
        if badness < self.collinear_vectors_max_distance:
            self.errors.append(
                OutlineError(
                    node,
                    "Collinear vectors",
                    badness,
                    get_vector(prev_node, next_node),
                )
            )

    def _checkSemiHorizontalLine(self, n0, n1):
        """
        Test for semi-horizontal lines.
        """
        if distance_between_points(n0, n1) > self.semi_hv_vectors_min_distance:
            phi = angle_between_points(n0, n1)
            rho = atan2(1, 31)
            if (
                0 < abs(phi) < rho
                or 0 < abs(phi - pi) < rho
                or 0 < abs(abs(phi) - pi) < rho
            ):
                if abs(n1.y - n0.y) < 2:
                    self.errors.append(
                        OutlineError(
                            half_point(n0, n1),
                            "Semi-horizontal line",
                            degrees(phi),
                            get_vector(n0, n1),
                        )
                    )

    def _checkSemiVerticalLine(self, n0, n1):
        """
        Test for semi-vertical lines.
        """
        # TODO: Option to respect Italic angle?
        if distance_between_points(n0, n1) > self.semi_hv_vectors_min_distance:
            phi = angle_between_points(n0, n1)
            rho = atan2(31, 1)
            if (
                0 < abs(phi - 0.5 * pi) < rho
                or 0 < abs(phi + 0.5 * pi) < rho
            ):
                self.errors.append(
                    OutlineError(
                        half_point(n0, n1),
                        "Semi-vertical line",
                        degrees(phi),
                        get_vector(n0, n1),
                    )
                )

    def _checkSemiHorizontalHandle(self, p0, p1):
        """
        Test for semi-horizontal handles.
        """
        phi = angle_between_points(p0, p1)
        rho = atan2(1, 31)
        if (
            0 < abs(phi) < rho
            or 0 < abs(phi - pi) < rho
            or 0 < abs(abs(phi) - pi) < rho
        ):
            if abs(p1.y - p0.y) < 2:
                self.errors.append(
                    OutlineError(
                        half_point(p0, p1),
                        "Semi-horizontal handle",
                        degrees(phi),
                        get_vector(p0, p1),
                    )
                )

    def _checkSemiVerticalHandle(self, p0, p1):
        """
        Test for semi-vertical handles.
        """
        # TODO: Option to respect Italic angle?
        phi = angle_between_points(p0, p1)
        rho = atan2(31, 1)
        if (
            0 < abs(phi - 0.5 * pi) < rho
            or 0 < abs(phi + 0.5 * pi) < rho
        ):
            self.errors.append(
                OutlineError(
                    half_point(p0, p1),
                    "Semi-vertical handle",
                    degrees(phi),
                    get_vector(p0, p1),
                )
            )

    def _checkZeroHandles(self, p0, p1):
        badness = distance_between_points(p0, p1)
        if badness <= self.zero_handles_max_distance:
            self.errors.append(
                OutlineError(p1, "Zero handle", badness, get_vector(p0, p1))
            )
