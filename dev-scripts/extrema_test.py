#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from math import atan2, degrees, cos, pi, sin, sqrt
from types import TupleType
from fontTools.misc.arrayTools import pointInRect, normRect
from fontTools.misc.bezierTools import calcCubicParameters, solveQuadratic, splitCubicAtT
from fontTools.misc.transform import Transform
#from fontTools.pens.pointPen import BasePointToSegmentPen

def getExtremaForCubic(pt1, pt2, pt3, pt4, h=True, v=False):
	(ax, ay), (bx, by), c, d = calcCubicParameters(pt1, pt2, pt3, pt4)
	ax *= 3.0
	ay *= 3.0
	bx *= 2.0
	by *= 2.0
	h_roots = []
	v_roots = []
	if h:
		h_roots = [t for t in solveQuadratic(ay, by, c[1]) if 0 < t < 1]
	if v:
		v_roots  = [t for t in solveQuadratic(ax, bx, c[0]) if 0 < t < 1]
	roots = h_roots + v_roots
	split_segments = [p for p in splitCubicAtT(pt1, pt2, pt3, pt4, *roots)[:-1]]
	points = [p[3] for p in split_segments]
	# Calculate the orthogonal angle to the outline at the extrema
	angles = [degrees(angle_between_points(p[2], p[3]) - 0.5 * pi) for p in split_segments]
	return points, angles

def angle_between_points(p0, p1):
	return atan2(p1[1] - p0[1], p1[0] - p0[0])

print getExtremaForCubic((329,40), (287,22), (266,53), (235,40))