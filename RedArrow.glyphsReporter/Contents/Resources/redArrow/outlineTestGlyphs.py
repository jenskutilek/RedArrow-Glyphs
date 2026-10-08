from math import atan2, cos, degrees, pi, sin, sqrt
from typing import TYPE_CHECKING

from AppKit import NSMakePoint
from GlyphsApp import GSCURVE, GSLINE, GSOFFCURVE, GSQCURVE

from redArrow.geometry import (
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
from redArrow.misc.arrayTools import is_node_inside_rect, norm_rect
from redArrow.typing import RedArrowOptionsDict

if TYPE_CHECKING:
    from collections.abc import Sequence

    from AppKit import NSPoint
    from GlyphsApp import GSComponent, GSLayer, GSNode

    from redArrow.typing import PointTuple, QuadraticCurveTuple, RectTuple


def fmt_node(node: "GSNode | None") -> str:
    if node is None:
        return "(none)"
    return f"({node.position.x:g}, {node.position.y:g})[{node.index}]"


def fmt_nodes(nodes):
    node_strings = [fmt_node(n) for n in nodes]
    return ", ".join(node_strings)


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
        self.run_checks = run_checks or []
        self.reset()
        self.layer = layer

        # Cached test run settings
        self.RedArrowCheckFractionalCoords = True
        self.RedArrowCheckSmooth = True
        self.RedArrowCheckEmptySegments = True
        self.RedArrowCheckCollinear = True
        self.RedArrowCheckSpikes = True
        self.RedArrowCheckSemiHV = True
        self.RedArrowCheckShortSegments = True
        self.RedArrowCheckExtrema = True
        self.RedArrowCheckInflections = True
        self.RedArrowCheckZeroHandles = True
        self.RedArrowCheckBboxHandles = True
        self.RedArrowCheckFractionalTransform = True

        self.RedArrowSemiHMaxAngle = atan2(1, 31)
        self.RedArrowSemiVMaxAngle = atan2(31, 1)

    def reset(self) -> None:
        """
        Reset the outline check to its initial state.
        """
        self.errors: list[OutlineError | OutlineWarning] = []

        self.all_checks = [
            "RedArrowCheckExtrema",
            "RedArrowCheckInflections",
            "RedArrowCheckFractionalCoords",
            "RedArrowCheckFractionalTransform",
            "RedArrowCheckSmooth",
            "RedArrowCheckEmptySegments",
            "RedArrowCheckCollinear",
            "RedArrowCheckSemiHV",
            # "RedArrowCheckClosepath",
            "RedArrowCheckZeroHandles",
            "RedArrowCheckBboxHandles",
            "RedArrowCheckShortSegments",
            "RedArrowCheckSpikes",
        ]

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
        self.RedArrowExtremaCalculateBadness = self.options.get(
            "RedArrowExtremaCalculateBadness", True
        )
        self.RedArrowCheckFractionalIgnorePointZero = self.options.get(
            "RedArrowCheckFractionalIgnorePointZero", True
        )

        # absolute values that are converted to current upm
        self.RedArrowExtremaIgnoreBadnessBelow = self._normalize_upm(
            self.options.get("RedArrowExtremaIgnoreBadnessBelow", 1)
        )
        self.RedArrowSmoothMaxDistance = self._normalize_upm(
            self.options.get("RedArrowSmoothMaxDistance", 4)
        )
        # We need this value * 2 often, so precompute it
        self.RedArrowSmoothMaxDistance2 = self.RedArrowSmoothMaxDistance * 2
        self.RedArrowCollinearMaxDistance = self._normalize_upm(
            self.options.get("RedArrowCollinearMaxDistance", 2)
        )
        self.RedArrowCheckSemiHVMinDistance = self._normalize_upm(
            self.options.get("RedArrowCheckSemiHVMinDistance", 30)
        )
        self.RedArrowCheckSemiHVMaxDistance = self._normalize_upm(
            self.options.get("RedArrowCheckSemiHVMaxDistance", 2)
        )
        self.RedArrowZeroHandlesMaxDistance = self._normalize_upm(
            self.options.get("RedArrowZeroHandlesMaxDistance", 0)
        )
        self.RedArrowInflectionMin = self.options.get("RedArrowInflectionMin", 0.3)
        self.RedArrowSpikeAngle = self.options.get("RedArrowSpikeAngle", 0.49)

        self.RedArrowGridLengthH = self.options.get("RedArrowGridLengthH", 1)
        self.RedArrowGridLengthV = self.options.get("RedArrowGridLengthV", 1)
        self.RedArrowIgnoreWarnings = self.options.get("RedArrowIgnoreWarnings", False)

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
            offcurves: list[GSNode] = []
            oncurves: list[GSNode] = []
            prev_node = None
            next_node = None
            num_nodes = len(path.nodes)
            if num_nodes > 150:
                print(f"Red Arrow: Not checking path with {num_nodes} nodes")
                continue

            first_oncurve_index = path.firstOncurveNodeIndex()
            for i in range(first_oncurve_index, first_oncurve_index + num_nodes):
                node = path.nodes[i]
                node_type = node.type
                if node_type == GSOFFCURVE:
                    offcurves.append(node)
                elif node_type in (GSLINE, GSQCURVE, GSCURVE):
                    prev_node_index = i - 1
                    if path.closed or prev_node_index >= 0:
                        prev_node = path.nodes[prev_node_index]
                    else:
                        prev_node = None
                    next_node_index = i + 1
                    if path.closed or next_node_index < num_nodes:
                        next_node = path.nodes[next_node_index % num_nodes]
                    else:
                        next_node = None
                    oncurves.append(node)

                if node_type == GSLINE:
                    self._run_line_checks(node, prev_node, next_node)
                    continue

                if node_type == GSOFFCURVE:
                    self._run_offcurve_checks(node)
                    continue

                if len(oncurves) < 2:
                    # FIXME: Quadratic contour without oncurves
                    continue

                on = oncurves[-2]

                if node_type == GSCURVE:
                    self._run_curve_checks(node, prev_node, next_node, on, offcurves)
                    offcurves = []
                    continue

                if node_type == GSQCURVE:
                    self._run_qcurve_checks(node, prev_node, next_node, on, offcurves)
                    offcurves = []

        for component in self.layer.components:
            self._run_component_checks(component)

    # Checks for different node types

    def _run_line_checks(
        self,
        node: "GSNode",
        prev_node: "GSNode | None",
        next_node: "GSNode | None",
    ) -> None:
        # Checks that use the current node

        if self.RedArrowCheckFractionalCoords:
            self._check_fractional_coordinates(node)

        if prev_node is None:
            return

        # Checks that use the previous node

        if self.RedArrowCheckEmptySegments:
            self._check_empty_lines_and_curves(prev_node, node)
        if self.RedArrowCheckSemiHV:
            self._check_semi_horizontal(prev_node, node)
            self._check_semi_vertical(prev_node, node)
        if self.RedArrowCheckShortSegments:
            self._check_short_lines_and_curves(prev_node, node)

        if next_node is None:
            return

        # Checks that use the previous and next node

        if next_node.type == GSLINE and self.RedArrowCheckCollinear:
            self._check_collinear_vectors(node, prev_node, next_node)
        if self.RedArrowCheckSmooth:
            self._check_incorrect_smooth_connection(node, prev_node, next_node)
        if self.RedArrowCheckSpikes:
            self._check_spike(node, prev_node, next_node)

    def _run_curve_checks(
        self,
        node: "GSNode",
        prev_node: "GSNode | None",
        next_node: "GSNode | None",
        prev_oncurve: "GSNode",
        offcurves: "list[GSNode]",
    ) -> None:
        if len(offcurves) < 2:
            print(
                f"Red Arrow: Skipping curve without offcurves: on={fmt_node(prev_oncurve)} off={fmt_nodes(offcurves)} on={fmt_node(node)}"
            )
            return
        node4 = node
        node3 = offcurves[-1]  # control point 2
        node2 = offcurves[-2]  # control point 1
        node1 = prev_oncurve
        if self.RedArrowCheckExtrema:
            self._check_bbox_curve(node1, node2, node3, node4)
        if self.RedArrowCheckInflections:
            self._check_inflections_curve(node1, node2, node3, node4)
        if self.RedArrowCheckFractionalCoords:
            self._check_fractional_coordinates(node)
        if self.RedArrowCheckEmptySegments:
            self._check_empty_lines_and_curves(prev_oncurve, node)
        if self.RedArrowCheckZeroHandles:
            self._check_zero_handles(node3, node4)
            self._check_zero_handles(node2, node1)
        if self.RedArrowCheckSemiHV:
            # Start of curve
            self._check_semi_horizontal(node1, node2, "handle")
            self._check_semi_vertical(node1, node2, "handle")
            # End of curve
            self._check_semi_horizontal(node3, node4, "handle")
            self._check_semi_vertical(node3, node4, "handle")
        if self.RedArrowCheckShortSegments:
            self._check_short_lines_and_curves(prev_oncurve, node)

        if prev_node is None or next_node is None:
            return

        if self.RedArrowCheckSmooth:
            self._check_incorrect_smooth_connection(node, prev_node, next_node)
        if self.RedArrowCheckSpikes:
            self._check_spike(node, prev_node, next_node)

    def _run_offcurve_checks(self, node: "GSNode") -> None:
        if self.RedArrowCheckFractionalCoords:
            self._check_fractional_coordinates(node)
        if self.RedArrowCheckBboxHandles:
            self._check_layer_bbox_handle(node)

    def _run_qcurve_checks(
        self,
        node: "GSNode",
        prev_node: "GSNode | None",
        next_node: "GSNode | None",
        prev_oncurve: "GSNode",
        offcurves: "list[GSNode]",
    ) -> None:
        if not offcurves:
            return

        if self.RedArrowCheckExtrema:
            self._check_extrema_quad(prev_oncurve, offcurves, node)
        # FIXME: Not implemented yet
        # if self.RedArrowCheckInflections:
        #     self._check_inflections_quad(node)
        if self.RedArrowCheckFractionalCoords:
            self._check_fractional_coordinates(node)
        if self.RedArrowCheckEmptySegments:
            self._check_empty_lines_and_curves(prev_oncurve, node)
        if self.RedArrowCheckSemiHV:
            # Start of curve
            self._check_semi_horizontal(prev_oncurve, offcurves[0], "handle")
            self._check_semi_vertical(prev_oncurve, offcurves[0], "handle")

            # End of curve
            self._check_semi_horizontal(offcurves[-1], node, "handle")
            self._check_semi_vertical(offcurves[-1], node, "handle")
        if self.RedArrowCheckShortSegments:
            self._check_short_lines_and_curves(prev_oncurve, node)

        if prev_node is None or next_node is None:
            return

        if self.RedArrowCheckSmooth:
            self._check_incorrect_smooth_connection(node, prev_node, next_node)
        if self.RedArrowCheckSpikes:
            self._check_spike(node, prev_node, next_node)

    def _run_component_checks(self, component: "GSComponent") -> None:
        if self.RedArrowCheckFractionalCoords:
            self._check_fractional_component_offset(component)
        if self.RedArrowCheckFractionalTransform:
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
                if self.RedArrowExtremaCalculateBadness:
                    badness = self._get_badness(pt, rect)
                    if badness >= self.RedArrowExtremaIgnoreBadnessBelow:
                        self.errors.append(
                            error_class(NSMakePoint(*pt), desc, badness, vector=vector)
                        )
                else:
                    self.errors.append(
                        error_class(NSMakePoint(*pt), desc, vector=vector)
                    )

    def _check_layer_bbox_handle(self, node: "GSNode") -> None:
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

    def _check_extrema_quad(
        self, on0: "GSNode", offcurves: "Sequence[GSNode]", on1: "GSNode"
    ) -> None:
        quad = quad_with_explicit_oncurve_points(on0, offcurves, on1)
        for i in range(0, len(quad) - 1, 2):
            extrema, vectors = get_extrema_for_quadratic(
                quad[i], quad[i + 1], quad[i + 2], h=True, v=True
            )
            for i, p in enumerate(extrema):
                # if self.RedArrowExtremaCalculateBadness:
                # 	badness = self._get_badness(p, myRect)
                # 	if badness >= self.RedArrowExtremaIgnoreBadnessBelow:
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
            self.RedArrowInflectionMin,
            1 - self.RedArrowInflectionMin,
        )
        ok_inflections, ok_vectors = ok
        err_inflections, err_vectors = err
        for i, p in enumerate(err_inflections):
            self.errors.append(
                OutlineError(NSMakePoint(*p), "Inflection", vector=err_vectors[i])
            )

        if self.RedArrowIgnoreWarnings:
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

    def _check_fractional_coordinates(self, n: "GSNode") -> bool | None:
        if self.RedArrowCheckFractionalIgnorePointZero:
            n_prev = round_point(n, self.RedArrowGridLengthH, self.RedArrowGridLengthV)
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
            if abs(round_value(value, self.RedArrowGridLength) - value) > 0.001:
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

    def _check_incorrect_smooth_connection(
        self, node: "GSNode", prev_node: "GSNode", next_node: "GSNode"
    ) -> None:
        """
        Check for nearly smooth connections.
        """
        # distance of the current node to next reference node
        dist1 = nodes_distance(prev_node, node)
        dist2 = nodes_distance(node, next_node)

        if dist1 >= dist2:
            if dist2 <= self.RedArrowSmoothMaxDistance2:  # Ignore short segments
                return

            # distance 1 is longer, check dist2 for correct angle
            dist = dist2
            phi = nodes_angle(prev_node, node)  # phi1
            ref = next_node
        else:
            if dist1 <= self.RedArrowSmoothMaxDistance2:  # Ignore short segments
                return

            # distance 2 is longer, check dist1 for correct angle
            dist = dist1
            phi = nodes_angle(node, next_node) - pi  # phi2 - pi
            ref = prev_node

        # TODO: Add sanity check to save calculating the projected point for each
        # segment? This fails for connections around 180 degrees which may be reported
        # as 180 or -180
        # if 0 < abs(phi1 - phi2) < 0.1: # 0.1 (radians) = 5.7 degrees
        # Calculate where the second reference point should be
        # TODO: Decide which angle is more important?
        # E.g. line to curve: line is fixed, curve / tangent point is flexible?
        # or always consider the longer segment more important?
        projected_pt = NSMakePoint(
            node.x + dist * cos(phi),
            node.y + dist * sin(phi),
        )
        # Compare projected position with actual position
        badness = nodes_distance(
            round_point(projected_pt, self.RedArrowGridLength), ref
        )
        if self.RedArrowGridLength == 0:
            d = 0.49
        else:
            d = self.RedArrowGridLength * 0.49
        if d < badness and (node.smooth or badness < self.RedArrowSmoothMaxDistance):
            self.errors.append(
                OutlineError(
                    node,
                    "Not quite smooth connection",
                    badness,
                    vector=nodes_normal_vector(prev_node, node),
                )
            )

    def _check_empty_lines_and_curves(self, node0: "GSNode", node1: "GSNode") -> None:
        if node0.x == node1.x and node0.y == node1.y:
            self.errors.append(
                OutlineError(
                    node1,
                    "Zero-length distance",
                    vector=nodes_normal_vector(node0, node1),
                )
            )

    def _check_short_lines_and_curves(self, node0: "GSNode", node1: "GSNode") -> None:
        # TODO: Normalize 1/1000 to upm?
        if abs(node0.x - node1.x) <= 1 and abs(node0.y - node1.y) <= 1:
            self.errors.append(
                OutlineWarning(
                    node0,
                    "Short segment",
                    vector=nodes_normal_vector(node0, node1),
                )
            )

    def _check_collinear_vectors(
        self, node: "GSNode", prev_node: "GSNode", next_node: "GSNode"
    ) -> None:
        """
        Check for consecutive lines that have nearly the same angle.
        """
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
        badness = nodes_distance(
            round_point(projected_pt, self.RedArrowGridLength), next_node
        )
        if badness < self.RedArrowCollinearMaxDistance:
            self.errors.append(
                OutlineError(
                    node,
                    "Collinear vectors",
                    badness,
                    nodes_normal_vector(prev_node, next_node),
                )
            )

    def _check_spike(
        self, node: "GSNode", prev_node: "GSNode", next_node: "GSNode"
    ) -> None:
        """
        Check for consecutive segments that have a very narrow angle.
        """
        phi1 = nodes_angle(prev_node, node)
        phi2 = nodes_angle(next_node, node)
        if abs(phi2 - phi1) < self.RedArrowSpikeAngle:
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
        if (
            nodes_distance(node0, node1) > self.RedArrowCheckSemiHVMinDistance
            and abs(node1.y - node0.y) <= self.RedArrowCheckSemiHVMaxDistance
        ):
            phi = nodes_angle(node0, node1)
            rho = self.RedArrowSemiHMaxAngle
            if (
                0 < abs(phi) < rho
                or 0 < abs(phi - pi) < rho
                or 0 < abs(abs(phi) - pi) < rho
            ):
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
        if (
            nodes_distance(node0, node1) > self.RedArrowCheckSemiHVMinDistance
            and abs(node1.x - node0.x) <= self.RedArrowCheckSemiHVMaxDistance
        ):
            phi = nodes_angle(node0, node1)
            rho = self.RedArrowSemiVMaxAngle
            if 0 < abs(phi - 0.5 * pi) < rho or 0 < abs(phi + 0.5 * pi) < rho:
                self.errors.append(
                    OutlineError(
                        nodes_half_point(node0, node1),
                        f"Semi-vertical {segment}",
                        degrees(phi),
                        nodes_normal_vector(node0, node1),
                    )
                )

    def _check_zero_handles(self, node0: "GSNode", node1: "GSNode") -> None:
        badness = nodes_distance(node0, node1)
        if badness <= self.RedArrowZeroHandlesMaxDistance:
            self.errors.append(
                OutlineError(
                    node1, "Zero handle", badness, nodes_normal_vector(node0, node1)
                )
            )
