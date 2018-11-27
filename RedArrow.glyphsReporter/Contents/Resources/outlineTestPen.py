from __future__ import absolute_import, division, print_function
from math import atan2, degrees, cos, pi, sin, sqrt

try:
	from fontTools.misc.arrayTools import pointInRect, normRect
	from fontTools.misc.bezierTools import calcQuadraticParameters, calcCubicParameters, solveQuadratic, splitCubicAtT, splitQuadraticAtT, epsilon
	from fontTools.misc.transform import Transform
except ImportError:
	from miniFontTools.misc.arrayTools import pointInRect, normRect
	from miniFontTools.misc.bezierTools import calcQuadraticParameters, calcCubicParameters, solveQuadratic, splitCubicAtT, splitQuadraticAtT, epsilon
	from miniFontTools.misc.transform import Transform

try:
	from mojo.roboFont import version as roboFontVersion
	if roboFontVersion >= "3.0":
		v = "rf3"
		from ufoLib.pointPen import BasePointToSegmentPen
	else:
		v = "rf1"
		from robofab.pens import BasePointToSegmentPen
except ImportError:
	v = "g"
	from miniFontTools.pens.pointPen import BasePointToSegmentPen



# Helper functions

if v == "g":
	def get_bounds(font, glyphname):
		return (0, 0, 0, 0)
		# FIXME: We need to find the layer.bounds() in Glyphs
		# return font.glyphs[glyphname].bounds()
elif v == "rf3":
	def get_bounds(font, glyphname):
		return font[glyphname].bounds
else:
	def get_bounds(font, glyphname):
		return font[glyphname].box


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
			roots = [(-b+rDD)/2.0/a, (-b-rDD)/2.0/a]
		else:
			roots = []
	return roots


def add_implied_oncurve_points_quad(quad):
	new_quad = [quad[0]]
	for i in range(1, len(quad)-2):
		new_quad.append(quad[i])
		new_quad.append(half_point(quad[i], quad[i+1]))
	new_quad.extend(quad[-2:])
	return new_quad


def get_extrema_points_vectors(roots, pt1, pt2, pt3, pt4):
	split_segments = [p for p in splitCubicAtT(pt1, pt2, pt3, pt4, *roots)[:-1]]
	points = [p[3] for p in split_segments]
	vectors = [get_vector(p[2], p[3]) for p in split_segments]
	return points, vectors

def getExtremaForCubic(pt1, pt2, pt3, pt4, h=True, v=False):
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

def getInflectionsForCubic(pt1, pt2, pt3, pt4):
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
	
	c0 = ( ax * by ) - ( ay * bx )
	c1 = ( ax * cy ) - ( ay * cx )
	c2 = ( bx * cy ) - ( by * cx )

	if abs(c2) > 0.00001:
		discr = ( c1 ** 2 ) - ( 4 * c0 * c2)
		c2 *= 2
		if abs(discr) < 0.000001:
			root = -c1 / c2
			if (root > 0.001) and (root < 0.99):
				roots.append(root)
		elif discr > 0:
			discr = discr ** 0.5
			root = ( -c1 - discr ) / c2
			if (root > 0.001) and (root < 0.99):
				roots.append(root)
	
			root = ( -c1 + discr ) / c2
			if (root > 0.001) and (root < 0.99):
				roots.append(root)
	elif c1 != 0.0:
		root = - c0 / c1
		if (root > 0.001) and (root < 0.99):
			roots.append(root)

	return get_extrema_points_vectors(roots, pt1, pt2, pt3, pt4)

def get_extrema_points_vectors_quad(roots, pt1, pt2, pt3):
	split_segments = [p for p in splitQuadraticAtT(pt1, pt2, pt3, *roots)[:-1]]
	points = [p[2] for p in split_segments]
	vectors = [get_vector(p[1], p[2]) for p in split_segments]
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
	if gridLength == 1:
		return (int(round(pt[0])), int(round(pt[1])))
	elif gridLength == 0:
		return pt
	else:
		x = round(pt[0] / gridLength) * gridLength
		y = round(pt[1] / gridLength) * gridLength
		return (x, y)

def get_vector(p0, p1):
	return (p1[0] - p0[0], p1[1] - p0[1])

def angle_between_points(p0, p1):
	return atan2(p1[1] - p0[1], p1[0] - p0[0])

def distance_between_points(p0, p1):
	return sqrt((p1[1] - p0[1])**2 + (p1[0] - p0[0])**2)

def half_point(p0, p1):
	if type(p0) == tuple:
		p01 = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
	else:
		# NSPoint (Glyphs)
		p01 = p0.copy()
		p01[0] = (p0[0] + p1[0]) / 2
		p01[1] = (p0[1] + p1[1]) / 2
	return p01

def transform_bbox(bbox, matrix):
	t = Transform(*matrix)
	ll_x, ll_y = t.transformPoint((bbox[0], bbox[1]))
	tr_x, tr_y = t.transformPoint((bbox[2], bbox[3]))
	return normRect((ll_x, ll_y, tr_x, tr_y))


class OutlineError(object):
	def __init__(self, position=None, kind="Unknown error", badness=None, vector=None):
		self.position = position
		self.kind = kind
		self.badness = badness
		self.vector = vector
	
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
		if self.test_inflections:
			self._checkInflectionsSegment(bcp1, bcp2, pt)
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
		if self.test_semi_hv:
			self._checkSemiHorizontalHandle(self._prev, bcp1)
			self._checkSemiHorizontalHandle(bcp2, pt)
			self._checkSemiVerticalHandle(self._prev, bcp1)
			self._checkSemiVerticalHandle(bcp2, pt)

	def _runQCurveTests(self, bcps, pt):
		if self.test_extrema:
			self._checkExtremaQuad(bcps, pt)
		if self.test_inflections:
				self._checkInflectionsQuad(bcps, pt)
		if self.test_fractional_coords:
			for p in bcps + [pt]:
				self._checkFractionalCoordinates(p)
		if not self.curveTypeDetected:
			self._countQCurveSegment()
		if self.test_smooth:
			self._checkIncorrectSmoothConnection(self._prev, bcps[0])
		if self.test_empty_segments:
			self._checkEmptyLinesAndCurves(pt)
		if self.test_semi_hv:
			pp = self._prev
			for p in bcps + [pt]:
				self._checkSemiHorizontalHandle(pp, p)
				self._checkSemiVerticalHandle(pp, p)
				pp = p
	
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
					self.errors.append(OutlineError(pointToCheck, "Extremum", badness, None))
			else:
				self.errors.append(OutlineError(pointToCheck, "Extremum", vector = None))
	
	def _checkBboxSegment(self, bcp1, bcp2, pt):
		# Like _checkBbox, but checks the whole segment and calculates extrema
		myRect = normRect((self._prev[0], self._prev[1], pt[0], pt[1]))
		if not pointInRect(bcp1, myRect) or not pointInRect(bcp2, myRect):
			extrema, vectors = getExtremaForCubic(self._prev, bcp1, bcp2, pt, h=True, v=True)
			for i, p in enumerate(extrema):
				if self.extremum_calculate_badness:
					badness = self._getBadness(p, myRect)
					if badness >= self.extremum_ignore_badness_below:
						self.errors.append(OutlineError(p, "Extremum", badness, vectors[i]))
				else:
					self.errors.append(OutlineError(p, "Extremum", vector = vectors[i]))

	def _checkExtremaQuad(self, bcps, pt):
		quad = add_implied_oncurve_points_quad([self._prev] + bcps + [pt])
		for i in range(0, len(quad)-1, 2):
			extrema, vectors = getExtremaForQuadratic(quad[i], quad[i + 1], quad[i + 2], h=True, v=True)
			for i, p in enumerate(extrema):
				#if self.extremum_calculate_badness:
				#	badness = self._getBadness(p, myRect)
				#	if badness >= self.extremum_ignore_badness_below:
				#		self.errors.append(OutlineError(p, "Extremum", badness, vectors[i]))
				#else:
				self.errors.append(OutlineError(p, "Extremum", vector = vectors[i]))
	
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

	def _checkInflectionsSegment(self, bcp1, bcp2, pt):
		inflections, vectors = getInflectionsForCubic(self._prev, bcp1, bcp2, pt)
		for i, p in enumerate(inflections):
			self.errors.append(OutlineError(p, "Inflection", vector = vectors[i]))
	
	def _checkInflectionsQuad(self, bcps, pt):
		inflections, vectors = getInflectionsForQuadratic(self._prev, bcps, pt)
		for i, p in enumerate(inflections):
			self.errors.append(OutlineError(p, "Inflection", vector = vectors[i]))

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
			if abs(pr[0] - pt[0]) < 0.001 and abs(pr[1] - pt[1]) < 0.001:
				return False
		else:
			if type(pt[0]) == int and type(pt[1] == int):
				return False
		self.errors.append(OutlineError(
			(int(round(pt[0])), int(round(pt[1]))),
			"Fractional Coordinates", # (%0.2f, %0.2f)" % (pt[0], pt[1]),
			vector = None,
		))
	
	def _checkFractionalTransformation(self, baseGlyph, transformation):
		bbox = get_bounds(self.glyphSet, baseGlyph)
		tbox = transform_bbox(bbox, transformation)
		if self.fractional_ignore_point_zero:
			for p in transformation:
				if round(p) != p:
					self.errors.append(OutlineError(
						half_point((tbox[0], tbox[1]), (tbox[2], tbox[3])),
						"Fractional transformation", # (%0.2f, %0.2f, %0.2f, %0.2f, %0.2f, %0.2f)" % transformation
						vector = None,
					))
					break
		else:
			for p in transformation:
				if type(p) == float:
					self.errors.append(OutlineError(
						half_point((tbox[0], tbox[1]), (tbox[2], tbox[3])),
						"Fractional transformation", # (%0.2f, %0.2f, %0.2f, %0.2f, %0.2f, %0.2f)" % transformation
						vector = None,
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
			
			#print("Checking:")
			#print("  ", self._prev_ref, pt, degrees(phi1), dist1)
			#print("  ", pt, next_ref, degrees(phi2), dist2)
			
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
			
			#print("  Chose: %s -> %s, angle %0.2f, dist %0.2f" % (ref, next_ref, degrees(phi), dist))
			
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
				badness = distance_between_points(round_point(projected_pt, self.grid_length), ref)
				#print("  Projected: %s, actual: %s, diff: %0.2f" % (projected_pt, ref, badness))
				if self.grid_length == 0:
					d = 0.49
				else:
					d = self.grid_length * 0.49
				if d < badness:
					if self.current_smooth or badness < self.smooth_connection_max_distance:
						self.errors.append(OutlineError(pt, "Incorrect smooth connection", badness, vector = get_vector(self._prev_ref, pt)))
	
	def _checkEmptyLinesAndCurves(self, pt):
		if self._prev == pt:
			self.errors.append(OutlineError(pt, "Empty segment", vector = self.current_vector))
	
	def _checkVectorsOnClosepath(self, pt):
		if self._cstart == pt:
			self.errors.append(OutlineError(pt, "Vector on closepath", vector = self.current_vector))
	
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
				badness = distance_between_points(round_point(projected_pt, self.grid_length), next_ref)
				if badness < self.collinear_vectors_max_distance:
					self.errors.append(OutlineError(pt, "Collinear vectors", badness, self.current_vector))
	
	def _checkSemiHorizontalVectors(self, p0, p1):
		'''Test for semi-horizontal lines.'''
		if distance_between_points(p0, p1) > self.semi_hv_vectors_min_distance:
			phi = angle_between_points(p0, p1)
			#                 atan2(1, 31)
			if 0 < abs(phi) < 0.032 or 0 < abs(phi - pi) < 0.032 or 0 < abs(abs(phi) - pi) < 0.032:
				if abs(p1[1] - p0[1]) < 2:
					self.errors.append(OutlineError(half_point(p0, p1), "Semi-horizontal line", degrees(phi), get_vector(p0, p1)))
	
	def _checkSemiVerticalVectors(self, p0, p1):
		'''Test for semi-vertical lines.'''
		# TODO: Option to respect Italic angle?
		if distance_between_points(p0, p1) > self.semi_hv_vectors_min_distance:
			phi = angle_between_points(p0, p1)
			#                            atan2(31, 1)                       atan2(31, -1)
			if 0 < abs(phi - 0.5 * pi) < 0.032 or 0 < abs(phi + 0.5 * pi) < 0.032:
				self.errors.append(OutlineError(half_point(p0, p1), "Semi-vertical line", degrees(phi), get_vector(p0, p1)))

	def _checkSemiHorizontalHandle(self, p0, p1):
		'''Test for semi-horizontal handles.'''
		phi = angle_between_points(p0, p1)
		#                 atan2(1, 31)
		if 0 < abs(phi) < 0.032 or 0 < abs(phi - pi) < 0.032 or 0 < abs(abs(phi) - pi) < 0.032:
			if abs(p1[1] - p0[1]) < 2:
				self.errors.append(OutlineError(half_point(p0, p1), "Semi-horizontal handle", degrees(phi), get_vector(p0, p1)))
	
	def _checkSemiVerticalHandle(self, p0, p1):
		'''Test for semi-vertical handles.'''
		# TODO: Option to respect Italic angle?
		phi = angle_between_points(p0, p1)
		#                            atan2(31, 1)                       atan2(31, -1)
		if 0 < abs(phi - 0.5 * pi) < 0.032 or 0 < abs(phi + 0.5 * pi) < 0.032:
			self.errors.append(OutlineError(half_point(p0, p1), "Semi-vertical handle", degrees(phi), get_vector(p0, p1)))
	
	def _checkZeroHandles(self, p0, p1):
		badness = distance_between_points(p0, p1)
		if badness <= self.zero_handles_max_distance:
			self.errors.append(OutlineError(p1, "Zero handle", badness, self.current_vector))
	
	def _flushContour(self, segments):
		first_segment = True
		self.current_vector = None
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
				self._prev_type, prev_points = segments[-1]
				self._prev = prev_points[-1][0]
				if self._prev_type in ['curve', 'qcurve']:
					self._prev_ref = prev_points[-2][0]
					self.current_smooth = prev_points[-1][1]
				else:
					self._prev_ref = prev_points[0][0]
					self.current_smooth = prev_points[0][1]
				first_segment = False
		
			if segment_type == 'curve':
				bcp1, bcp2, pt = points[0][0], points[1][0], points[2][0]
				self.current_vector = get_vector(bcp2, pt)
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
				self.current_vector = get_vector(self._prev, pt)
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
				bcp = points[0][0]
				pt = points[-1][0]
				bcps = [p[0] for p in points[:-1]]
				self.current_vector = get_vector(bcps[-1], pt)
				self._runQCurveTests(bcps, pt)
				self._prev_ref = points[-2][0]
				self._prev = pt
				self._prev_type = "qcurve"
				if self._is_contour_start:
					self._contour_start_ref = bcp
					self._is_contour_start = False
				self._should_test_collinear = False
				self.current_smooth = points[1][1]
			else:
				pass
		
		#self._runClosePathTests()




if __name__ == "__main__":
	g = CurrentGlyph()
	p = OutlineTestPen(CurrentFont())
	g.drawPoints(p)
	for e in p.errors:
		print(e)
