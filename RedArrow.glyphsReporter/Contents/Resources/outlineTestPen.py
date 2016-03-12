from __future__ import division
from math import atan2, degrees, cos, pi, sin, sqrt
from types import TupleType
from miniFontTools.misc.arrayTools import pointInRect, normRect
from miniFontTools.misc.bezierTools import calcCubicParameters, solveQuadratic, splitCubicAtT
from miniFontTools.pens.pointPen import BasePointToSegmentPen

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


class OutlineTestPen(BasePointToSegmentPen):
	
	'''Reimplementation of FontLab's FontAudit.'''
	
	def __init__(self, glyphSet, options={}, run_tests=[]):
		self.glyphSet = glyphSet
		try:
			self.upm = self.glyphSet.info.unitsPerEm
		except:
			self.upm = 1000
		
		self.__currentPoint = None
		
		self.options = options
		self.run_tests = run_tests
		self.errors = []
		
		self.all_tests = [
			"test_extrema",
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
		
		# Keep track of the final point of the previous segment,
		# needed for bbox calculation
		self._prev = None
		self._prev_type = None
		
		# Reference point for smooth connections
		# The previous bcp or pt depending on segment type
		self._prev_ref = None
		
		# Reference point for smooth connection check on last segment of contour
		self._contour_start_ref = None
		
		# Start point of previous and current contours
		self._prev_cstart = None
		self._cstart = None
		
		self._should_test_collinear = False
		
		# From BasePointToSegmentPen.__init__()
		self.currentPath = None
		
		self.current_smooth = False
		
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
		self.zero_handles_max_distance = self._normalize_upm(self.options.get("zero_handles_max_distance", 0))
		
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
	
	def addComponent(self, baseGlyph, transformation):
		self._runComponentTests(baseGlyph, transformation)
	
	# Tests for different segment types
	
	def _runMoveTests(self, pt):
		if self.test_fractional_coords:
			self._checkFractionalCoordinates(pt)
		if self.test_smooth and self._contour_start_ref is not None:
			self._checkIncorrectSmoothConnection(self._prev, self._contour_start_ref)
		#if self.test_empty_segments:
		#	self._checkEmptyLinesAndCurves(pt)
	
	def _runLineTests(self, pt):
		if self.test_fractional_coords:
			self._checkFractionalCoordinates(pt)
		if self.test_smooth:
			self._checkIncorrectSmoothConnection(self._prev, pt)
		if self.test_empty_segments:
			self._checkEmptyLinesAndCurves(pt)
		if self.test_collinear and self._should_test_collinear:
			self._checkCollinearVectors(self._prev, pt)
		if self.test_semi_hv:
			self._checkSemiHorizontalVectors(self._prev, pt)
			self._checkSemiVerticalVectors(self._prev, pt)
	
	def _runCurveTests(self, bcp1, bcp2, pt):
		#for bcp in [bcp1, bcp2]:
		#	self._checkBbox(bcp, pt)
		if self.test_extrema:
			self._checkBboxSegment(bcp1, bcp2, pt)
		if self.test_fractional_coords:
			for p in [bcp1, bcp2, pt]:
				self._checkFractionalCoordinates(p)
		if not self.curveTypeDetected:
			self._countCurveSegment()
		if self.test_smooth:
			self._checkIncorrectSmoothConnection(self._prev, bcp1)
		if self.test_empty_segments:
			self._checkEmptyLinesAndCurves(pt)
		if self.test_zero_handles:
			self._checkZeroHandles(self._prev, bcp1)
			self._checkZeroHandles(pt, bcp2)

	def _runQCurveTests(self, bcp, pt):
		if self.test_extrema:
			self._checkBbox(bcp, pt)
		if self.test_fractional_coords:
			for p in [bcp, pt]:
				self._checkFractionalCoordinates(p)
		if not self.curveTypeDetected:
			self._countQCurveSegment()
		if self.test_smooth:
			self._checkIncorrectSmoothConnection(self._prev, bcp)
		if self.test_empty_segments:
			self._checkEmptyLinesAndCurves(pt)
	
	def _runClosePathTests(self):
		if self.test_closepath and self._prev_type == "line":
			self._checkVectorsOnClosepath(self._prev)
		if self.test_collinear and self._should_test_collinear:
			self._checkCollinearVectors(self._prev, self._cstart)
		if self.test_semi_hv:
			self._checkSemiHorizontalVectors(self._prev, self._cstart)
			self._checkSemiVerticalVectors(self._prev, self._cstart)
	
	def _runComponentTests(self, baseGlyph, transformation):
		if self.test_fractional_transform:
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
			"Fractional Coordinates", # (%0.2f, %0.2f)" % (pt[0], pt[1]),
		))
	
	def _checkFractionalTransformation(self, baseGlyph, transformation):
		if self.fractional_ignore_point_zero:
			for p in transformation:
				if round(p) != p:
					self.errors.append(OutlineError(
						None,
						"Fractional transformation", # (%0.2f, %0.2f, %0.2f, %0.2f, %0.2f, %0.2f)" % transformation
					))
					break
		else:
			for p in transformation:
				if type(p) == float:
					self.errors.append(OutlineError(
						None,
						"Fractional transformation", # (%0.2f, %0.2f, %0.2f, %0.2f, %0.2f, %0.2f)" % transformation
					))
					break
	
	def _checkIncorrectSmoothConnection(self, pt, next_ref):
		'''Test for incorrect smooth connections.'''
		if self._prev_ref is not None:
			# angle of previous reference point to current point
			phi1 = angle_between_points(self._prev_ref, pt)
			phi2 = angle_between_points(pt, next_ref)
			
			# distance of pt to next reference point
			dist1 = distance_between_points(self._prev_ref, pt)
			dist2 = distance_between_points(pt, next_ref)
			
			#print "Checking:"
			#print "  ", self._prev_ref, pt, degrees(phi1), dist1
			#print "  ", pt, next_ref, degrees(phi2), dist2
			
			if dist1 >= dist2:
				# distance 1 is longer, check dist2 for correct angle
				dist = dist2
				phi = phi1
				ref = next_ref
			else:
				# distance 2 is longer, check dist1 for correct angle
				dist = dist1
				phi = phi2 - pi
				ref = self._prev_ref
			
			#print "  Chose: %s -> %s, angle %0.2f, dist %0.2f" % (ref, next_ref, degrees(phi), dist)
			
			if dist > 2 * self.smooth_connection_max_distance: # Ignore short segments
				# TODO: Add sanity check to save calculating the projected point for each segment?
				# This fails for connections around 180 degrees which may be reported as 180 or -180
				#if 0 < abs(phi1 - phi2) < 0.1: # 0.1 (radians) = 5.7 degrees
				# Calculate where the second reference point should be
				# TODO: Decide which angle is more important?
				# E.g. line to curve: line is fixed, curve / tangent point is flexible?
				# or always consider the longer segment more important?
				projected_pt = (pt[0] + dist * cos(phi), pt[1] + dist * sin(phi))
				# Compare projected position with actual position
				badness = distance_between_points(round_point(projected_pt), ref)
				#print "  Projected: %s, actual: %s, diff: %0.2f" % (projected_pt, ref, badness)
				if 0 < badness:
					if self.current_smooth or badness < self.smooth_connection_max_distance:
						self.errors.append(OutlineError(pt, "Incorrect smooth connection", badness))
	
	def _checkEmptyLinesAndCurves(self, pt):
		if self._prev == pt:
			self.errors.append(OutlineError(pt, "Empty segment"))
	
	def _checkVectorsOnClosepath(self, pt):
		if self._cstart == pt:
			self.errors.append(OutlineError(pt, "Vector on closepath"))
	
	def _checkCollinearVectors(self, pt, next_ref):
		'''Test for consecutive lines that have nearly the same angle.'''
		if self._prev_ref is not None:
			if next_ref != pt:
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
			if 0 < abs(phi) < 0.032 or 0 < abs(phi - pi) < 0.032 or 0 < abs(abs(phi) - pi) < 0.032:
				if abs(p1[1] - p0[1]) < 2:
					self.errors.append(OutlineError(half_point(p0, p1), "Semi-horizontal vector", degrees(phi)))
	
	def _checkSemiVerticalVectors(self, p0, p1):
		'''Test for semi-vertical lines.'''
		# TODO: Option to respect Italic angle?
		if distance_between_points(p0, p1) > self.semi_hv_vectors_min_distance:
			phi = angle_between_points(p0, p1)
			#                            atan2(31, 1)                       atan2(31, -1)
			if 0 < abs(phi - 0.5 * pi) < 0.032 or 0 < abs(phi + 0.5 * pi) < 0.032:
				self.errors.append(OutlineError(half_point(p0, p1), "Semi-vertical vector", degrees(phi)))
	
	def _checkZeroHandles(self, p0, p1):
		badness = distance_between_points(p0, p1)
		if badness <= self.zero_handles_max_distance:
			self.errors.append(OutlineError(p1, "Zero handle", badness))
	
	def _flushContour(self, segments):
			first_segment = True
			pt = segments[0][1][0][0]
			self._prev = None
			self._prev_ref = None
			self.current_smooth = False
			self._prev_cstart = self._cstart
			self._cstart = pt
			self._runMoveTests(pt)
			self._prev_ref = None
			self._prev = pt
			self._prev_type = None
			self._is_contour_start = True
			self._should_test_collinear = False
			for segment_type, points in segments:
		
				if first_segment:
					prev_segment_type, prev_points = segments[-1]
					self._prev = prev_points[-1][0]
					if prev_segment_type == 'curve':
						self._prev_ref = prev_points[-2][0]
						self.current_smooth = prev_points[-1][1]
					else:
						self._prev_ref = prev_points[0][0]
						self.current_smooth = prev_points[0][1]
					first_segment = False
			
				if segment_type == 'curve':
					bcp1, bcp2, pt = points[0][0], points[1][0], points[2][0]
					self._runCurveTests(bcp1, bcp2, pt)
					self._prev_ref = bcp2
					self._prev = pt
					self._prev_type = "curve"
					if self._is_contour_start:
						self._contour_start_ref = bcp1
						self._is_contour_start = False
					self._should_test_collinear = False
					self.current_smooth = points[2][1]
				elif segment_type == 'line':
					pt = points[0][0]
					self._runLineTests(pt)
					self._prev_ref = self._prev
					#?
					#self._prev_ref = pt
					self._prev = pt
					self._prev_type = "line"
					if self._is_contour_start:
						self._contour_start_ref = pt
					self._should_test_collinear = True
					self.current_smooth = points[0][1]
				elif segment_type == 'qcurve':
					bcp, pt = points[0][0], points[1][0]
					self._runCurveTests(bcp, pt)
					self._prev_ref = bcp
					self._prev = pt
					self._prev_type = "curve"
					if self._is_contour_start:
						self._contour_start_ref = bcp
						self._is_contour_start = False
					self._should_test_collinear = False
					self.current_smooth = points[1][1]
				else:
					pass
		
			self._runClosePathTests()
			self._prev_type = None
			self._should_test_collinear = False




if __name__ == "__main__":
	g = CurrentGlyph()
	p = OutlineTestPen(CurrentFont())
	g.drawPoints(p)
	for e in p.errors:
		print e