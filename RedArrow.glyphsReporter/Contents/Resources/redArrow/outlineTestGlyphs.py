from math import atan2, cos, degrees, pi, sin, sqrt
from typing import TYPE_CHECKING

from AppKit import NSMakePoint
from GlyphsApp import GSCURVE, GSLINE, GSOFFCURVE, GSQCURVE

from redArrow.misc.arrayTools import is_node_inside_rect, norm_rect
from redArrow.misc.bezierTools import (
    get_extrema_for_cubic,
    get_extrema_for_quadratic,
    get_inflections_for_cubic,
    get_inflections_for_quadratic,
    nodes_angle,
    nodes_distance,
    nodes_half_point,
    nodes_normal_vector,
    quad_with_explicit_oncurve_points,
    round_point,
    round_value,
    transform_rect,
)
from redArrow.typing import RedArrowOptionsDict

if TYPE_CHECKING:
    from collections.abc import Sequence

    from AppKit import NSPoint
    from GlyphsApp import GSComponent, GSLayer, GSNode

    from redArrow.typing import PointTuple, QuadraticCurveTuple, RectTuple


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
        run_checks: "Sequence[str] | None" = None,
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
        self.options = options or RedArrowOptionsDict()
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
        if self.layer is None:
            self.upm = 1000
        else:
            # We used .upm before, but in G4, parent may be a GSInterpolationFontProxy.
            # GSFont and GSInterpolationFontProxy both have .unitsPerEm(), so use that.
            self.upm = self.layer.parent.parent.unitsPerEm()  # type: ignore
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

    def _run_line_checks(self, node: "GSNode") -> None:
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
        rect = norm_rect((node0.x, node0.y, node3.x, node3.y))
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
                badness = round(sqrt((myRect[0] - x) ** 2 + (myRect[1] - y) ** 2))
            elif y > myRect[3]:
                # point is upper left from rect
                badness = round(sqrt((myRect[0] - x) ** 2 + (myRect[3] - y) ** 2))
            else:
                badness = myRect[0] - x
        elif x > myRect[2]:
            # point is right from rect
            if y < myRect[1]:
                # point is lower right from rect
                badness = round(sqrt((myRect[2] - x) ** 2 + (myRect[1] - y) ** 2))
            elif y > myRect[3]:
                # point is upper right from rect
                badness = round(sqrt((myRect[2] - x) ** 2 + (myRect[3] - y) ** 2))
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
                            f"on ‘{component.componentName}’"
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
                            f"Semi-horizontal {segment}",
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
                            f"Semi-vertical {segment}",
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
