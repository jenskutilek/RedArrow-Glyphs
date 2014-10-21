from __future__ import division
from math import atan2, degrees, cos, pi, sin, sqrt
from types import TupleType
from miniFontTools.misc.arrayTools import pointInRect, normRect
from miniFontTools.misc.bezierTools import calcCubicParameters, solveQuadratic, splitCubicAtT
from miniFontTools.pens.basePen import BasePen

# Helper functions

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
	return [p[3] for p in splitCubicAtT(pt1, pt2, pt3, pt4, *roots)[:-1]]

def round_point(pt):
	return (int(round(pt[0])), int(round(pt[1])))

def angle_between_points(p0, p1):
	return atan2(p1[1] - p0[1], p1[0] - p0[0])

def distance_between_points(p0, p1):
	return sqrt((p1[1] - p0[1])**2 + (p1[0] - p0[0])**2)

def half_point(p0, p1):
	if type(p0) == TupleType:
		p01 = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
	else:
		# NSPoint (Glyphs)
		p01 = p0.copy()
		p01[0] = (p0[0] + p1[0]) / 2
		p01[1] = (p0[1] + p1[1]) / 2
	return p01


class OutlineError(object):
	def __init__(self, position=None, kind="Unknown error", badness=None):
		self.position = position
		self.kind = kind
		self.badness = badness
	
	def __repr__(self):
		r = "%s" % self.kind
		if self.position is not None:
			r += " at (%i, %i)" % (self.position[0], self.position[1])
		if self.badness is not None:
			r += " (badness %i)" % self.badness
		return r


class OutlineTestPen(BasePen):
	
	'''Reimplementation of FontLab's FontAudit.'''
	
	def __init__(self, glyphSet, options={}):
		self.glyphSet = glyphSet
		try:
			self.upm = self.glyphSet.info.unitsPerEm
		except:
			self.upm = 1000
		
		self.__currentPoint = None
		
		self.options = options
		self.errors = []
		
		# Curve type detection
		self.apparentlyCubic = False
		self.apparentlyQuadratic = False
		self.curveTypeDetected = False
		
		# Mixed composites
		self.glyphHasComponents = False
		self.glyphHasOutlines = False
		
		# Keep track of the final point of the previous segment,
		# needed for bbox calculation
		self._prev = None
		
		# Reference point for smooth connections
		# The previous bcp or pt depending on segment type
		self._prev_ref = None
		
		# Reference point for smooth connection check on last segment of contour
		self._contour_start_ref = None
		
		# Start point of previous and current contours
		self._prev_cstart = None
		self._cstart = None
		
		self._should_test_collinear = False
		
		self._cache_options()
	
	def _normalize_upm(self, value):
		'''Return a value that is normalized from 1000 upm to the current font's upm'''
		return value * self.upm / 1000
	
	def _cache_options(self):
		# store options dict into instance variables
		# in the hope that it's faster than asking the dict every time
		
		# boolean values
		self.extremum_calculate_badness = self.options.get("extremum_calculate_badness", True)
		self.fractional_ignore_point_zero = self.options.get("fractional_ignore_point_zero", True)
		
		# absolute values that are converted to current upm
		self.extremum_ignore_badness_below = self._normalize_upm(self.options.get("extremum_ignore_badness_below", 1))
		self.smooth_connection_max_distance = self._normalize_upm(self.options.get("smooth_connection_max_distance", 4))
		self.collinear_vectors_max_distance = self._normalize_upm(self.options.get("collinear_vectors_max_distance", 2))
		self.semi_hv_vectors_min_distance = self._normalize_upm(self.options.get("semi_hv_vectors_min_distance", 30))
	
	def _moveTo(self, pt):
		self._prev_cstart = self._cstart
		self._cstart = pt
		self._runMoveTests(pt)
		self._prev_ref = None
		self._prev = pt
		self._is_contour_start = True
		self._should_test_collinear = False
		
	def _lineTo(self, pt):
		self._runLineTests(pt)
		self._prev_ref = self._prev
		self._prev = pt
		if self._is_contour_start:
			self._contour_start_ref = pt
		self._should_test_collinear = True
	
	def _curveToOne(self, bcp1, bcp2, pt):
		self._runCurveTests(bcp1, bcp2, pt)
		self._prev_ref = bcp2
		self._prev = pt
		if self._is_contour_start:
			self._contour_start_ref = bcp1
			self._is_contour_start = False
		self._should_test_collinear = False
	
	def _qCurveToOne(self, bcp, pt):
		self._runQCurveTests(bcp, pt)
		self._prev_ref = bcp
		self._prev = pt
		if self._is_contour_start:
			self._contour_start_ref = bcp
			self._is_contour_start = False
		self._should_test_collinear = False
	
	def _closePath(self):
		self._runClosePathTests()
		self._should_test_collinear = False
	
	def addComponent(self, baseGlyph, transformation):
		self._runComponentTests(baseGlyph, transformation)
	
	# Tests for different segment types
	
	def _runMoveTests(self, pt):
		self._checkFractionalCoordinates(pt)
		if self._contour_start_ref is not None:
			self._checkIncorrectSmoothConnection(self._prev, self._contour_start_ref)
		self._checkEmptyLinesAndCurves(pt)
	
	def _runLineTests(self, pt):
		self._checkFractionalCoordinates(pt)
		self._checkIncorrectSmoothConnection(self._prev, pt)
		self._checkEmptyLinesAndCurves(pt)
		if self._should_test_collinear:
			self._checkCollinearVectors(self._prev, pt)
		self._checkSemiHorizontalVectors(self._prev, pt)
		self._checkSemiVerticalVectors(self._prev, pt)
	
	def _runCurveTests(self, bcp1, bcp2, pt):
		#for bcp in [bcp1, bcp2]:
		#	self._checkBbox(bcp, pt)
		self._checkBboxSegment(bcp1, bcp2, pt)
		for p in [bcp1, bcp2, pt]:
			self._checkFractionalCoordinates(p)
		if not self.curveTypeDetected:
			self._countCurveSegment()
		self._checkIncorrectSmoothConnection(self._prev, bcp1)
		self._checkEmptyLinesAndCurves(pt)
	
	def _runQCurveTests(self, bcp, pt):
		self._checkBbox(bcp, pt)
		for p in [bcp, pt]:
			self._checkFractionalCoordinates(p)
		if not self.curveTypeDetected:
			self._countQCurveSegment()
		self._checkIncorrectSmoothConnection(self._prev, bcp)
		self._checkEmptyLinesAndCurves(pt)
	
	def _runClosePathTests(self):
		self._checkVectorsOnClosepath(self._prev)
		if self._should_test_collinear:
			self._checkCollinearVectors(self._prev, self._cstart)
		self._checkSemiHorizontalVectors(self._prev, self._cstart)
		self._checkSemiVerticalVectors(self._prev, self._cstart)
	
	def _runComponentTests(self, baseGlyph, transformation):
		self._checkFractionalTransformation(baseGlyph, transformation)
	
	# Implementations for all the different tests
	
	def _checkBbox(self, pointToCheck, boxPoint):
		# boxPoint is the final point of the current node,
		# the other bbox point is the previous final point
		myRect = normRect((self._prev[0], self._prev[1], boxPoint[0], boxPoint[1]))
		if not pointInRect(pointToCheck, myRect):
			if self.extremum_calculate_badness:
				badness = self._getBadness(pointToCheck, myRect)
				if badness >= self.extremum_ignore_badness_below:
					self.errors.append(OutlineError(pointToCheck, "Extremum", badness))
			else:
				self.errors.append(OutlineError(pointToCheck, "Extremum"))
	
	def _checkBboxSegment(self, bcp1, bcp2, pt):
		# Like _checkBbox, but checks the whole segment and calculates extrema
		myRect = normRect((self._prev[0], self._prev[1], pt[0], pt[1]))
		if not pointInRect(bcp1, myRect) or not pointInRect(bcp2, myRect):
			extrema = getExtremaForCubic(self._prev, bcp1, bcp2, pt, h=True, v=True)
			for p in extrema:
				if self.extremum_calculate_badness:
					badness = self._getBadness(p, myRect)
					if badness >= self.extremum_ignore_badness_below:
						self.errors.append(OutlineError(p, "Extremum", badness))
				else:
					self.errors.append(OutlineError(p, "Extremum"))
	
	def _getBadness(self, pointToCheck, myRect):
			# calculate distance of point to rect
			badness = 0
			if pointToCheck[0] < myRect[0]:
				# point is left from rect
				if pointToCheck[1] < myRect[1]:
					# point is lower left from rect
					badness = int(round(sqrt((myRect[0] - pointToCheck[0])**2 + (myRect[1] - pointToCheck[1])**2)))
				elif pointToCheck[1] > myRect[3]:
					# point is upper left from rect
					badness = int(round(sqrt((myRect[0] - pointToCheck[0])**2 + (myRect[3] - pointToCheck[1])**2)))
				else:
					badness = myRect[0] - pointToCheck[0]
			elif pointToCheck[0] > myRect[2]:
				# point is right from rect
				if pointToCheck[1] < myRect[1]:
					# point is lower right from rect
					badness = int(round(sqrt((myRect[2] - pointToCheck[0])**2 + (myRect[1] - pointToCheck[1])**2)))
				elif pointToCheck[1] > myRect[3]:
					# point is upper right from rect
					badness = int(round(sqrt((myRect[2] - pointToCheck[0])**2 + (myRect[3] - pointToCheck[1])**2)))
				else:
					badness = pointToCheck[0] - myRect[2]
			else:
				# point is centered from rect, check for upper/lower
				if pointToCheck[1] < myRect[1]:
					# point is lower center from rect
					badness = myRect[1] - pointToCheck[1]
				elif pointToCheck[1] > myRect[3]:
					# point is upper center from rect
					badness = pointToCheck[1] - myRect[3]
				else:
					badness = 0
			return badness
	
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
			if round(pt[0]) == pt[0] and round(pt[1]) == pt[1]:
				return False
		else:
			if type(pt[0]) == int and type(pt[1] == int):
				return False
		self.errors.append(OutlineError(
			(int(round(pt[0])), int(round(pt[1]))),
			"Fractional Coordinates (%s, %s)" % pt,
		))
	
	def _checkFractionalTransformation(self, baseGlyph, transformation):
		if self.fractional_ignore_point_zero:
			for p in transformation:
				if round(p) != p:
					self.errors.append(OutlineError(
						None,
						"Fractional transformation (%s, %s, %s, %s, %s, %s)" % transformation
					))
					break
		else:
			for p in transformation:
				if type(p) == float:
					self.errors.append(OutlineError(
						None,
						"Fractional transformation (%s, %s, %s, %s, %s, %s)" % transformation
					))
					break
	
	def _checkIncorrectSmoothConnection(self, pt, next_ref):
		'''Test for incorrect smooth connections.'''
		if self._prev_ref is not None:
			# angle of previous reference point to current point
			phi1 = angle_between_points(self._prev_ref, pt)

			# distance of pt to next reference point
			dist = distance_between_points(pt, next_ref)
			
			if dist > 2 * self.smooth_connection_max_distance: # Ignore short segments
				# TODO: Add sanity check to save calculating the projected point for each segment?
				# This fails for connections around 180 degrees which may be reported as 180 or -180
				#if 0 < abs(phi1 - phi2) < 0.1: # 0.1 (radians) = 5.7 degrees
				# Calculate where the second reference point should be
				projected_pt = (pt[0] + dist * cos(phi1), pt[1] + dist * sin(phi1))
				# Compare projected position with actual position
				badness = distance_between_points(round_point(projected_pt), next_ref)
				if 0 < badness < self.smooth_connection_max_distance:
					self.errors.append(OutlineError(pt, "Incorrect smooth connection", badness))
	
	def _checkEmptyLinesAndCurves(self, pt):
		if self._prev == pt:
			self.errors.append(OutlineError(pt, "Empty segment"))
	
	def _checkVectorsOnClosepath(self, pt):
		if self._cstart == pt:
			self.errors.append(OutlineError(pt, "Vector on closepath"))
	
	def _checkCollinearVectors(self, pt, next_ref):
		'''Test for consecutive lines that have nearly the same angle.'''
		# Currently this is pretty much the same as the IncorrectSmoothConnection test.
		if self._prev_ref is not None:
			# angle of previous reference point to current point
			phi1 = angle_between_points(self._prev_ref, pt)
			# angle of current point to next reference point
			# could be used for angle check without distance check
			#phi2 = angle_between_points(pt, next_ref)
			# distance of pt to next reference point
			dist = distance_between_points(pt, next_ref)
			
			projected_pt = (pt[0] + dist * cos(phi1), pt[1] + dist * sin(phi1))
			badness = distance_between_points(round_point(projected_pt), next_ref)
			if badness < self.collinear_vectors_max_distance:
				self.errors.append(OutlineError(pt, "Collinear vectors", badness))
	
	def _checkSemiHorizontalVectors(self, p0, p1):
		'''Test for semi-horizontal lines.'''
		if distance_between_points(p0, p1) > self.semi_hv_vectors_min_distance:
			phi = angle_between_points(p0, p1)
			#                 atan2(1, 31)
			if 0 < abs(phi) < 0.032 or 0 < abs(phi - pi) < 0.032:
				if abs(p1[1] - p0[1]) < 2:
					self.errors.append(OutlineError(half_point(p0, p1), "Semi-horizontal vector", degrees(phi)))
	
	def _checkSemiVerticalVectors(self, p0, p1):
		'''Test for semi-vertical lines.'''
		if distance_between_points(p0, p1) > self.semi_hv_vectors_min_distance:
			phi = angle_between_points(p0, p1)
			#                            atan2(31, 1)                       atan2(31, -1)
			if 0 < abs(phi - 0.5 * pi) < 0.032 or 0 < abs(phi + 0.5 * pi) < 0.032:
				self.errors.append(OutlineError(half_point(p0, p1), "Semi-vertical vector", degrees(phi)))

	
	def _checkSemiVerticalVectors(self, p0, p1):
		'''Test for semi-vertical lines.'''
		if distance_between_points(p0, p1) > self.semi_hv_vectors_min_distance:
			phi = angle_between_points(p0, p1)
			#                            atan2(31, 1)                       atan2(31, -1)
			if 0 < abs(phi - 0.5 * pi) < 0.032 or 0 < abs(phi + 0.5 * pi) < 0.032:
				self.errors.append(OutlineError(half_point(p0, p1), "Semi-vertical vector", degrees(phi)))
