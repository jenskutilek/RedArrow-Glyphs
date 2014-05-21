from math import sqrt
from miniFontTools.bezierTools import calcCubicParameters, solveQuadratic, splitCubicAtT
from miniFontTools.basePen import BasePen
from miniFontTools.arrayTools import pointInRect, normRect


# Helper functions

def getExtremaForCubic(pt1, pt2, pt3, pt4):
    (ax, ay), (bx, by), c, d = calcCubicParameters(pt1, pt2, pt3, pt4)
    ax *= 3.0
    ay *= 3.0
    bx *= 2.0
    by *= 2.0
    roots  = [t for t in solveQuadratic(ax, bx, c[0]) if 0 < t < 1]
    roots += [t for t in solveQuadratic(ay, by, c[1]) if 0 < t < 1]
    return [p[3] for p in splitCubicAtT(pt1, pt2, pt3, pt4, *roots)[:-1]]


def getTriangleArea(a, b, c):
    return (b[0] -a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])


# Classes

class RedArrowError(object):
    def __init__(self, position, kind, badness=1):
        self.position = position
        self.kind = kind
        self.badness = badness
    
    def __repr__(self):
        return "%s at (%i, %i)" % (self.kind, self.position[0], self.position[1])


class RedArrowPen(BasePen):
    def __init__(self, glyphSet, calculateBadness=True, ignoreBelow=0):
        self.glyphSet = glyphSet
        self.__currentPoint = None
        self.calculateBadness = calculateBadness
        self.ignoreBelow = ignoreBelow
        self.errors = []
        self.numErrors = 0
        # final point of the previous segment, needed for bbox calculation
        self._prev = None
        self._prev_ref = None
    
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
    
    def _checkBbox(self, pointToCheck, boxPoint):
        # boxPoint is the final point of the current node,
        # the other bbox point is the previous final point
        myRect = normRect((self._prev[0], self._prev[1], boxPoint[0], boxPoint[1]))
        if not pointInRect(pointToCheck, myRect):
            if self.calculateBadness:
                badness = self._getBadness(pointToCheck, myRect)
                if badness >= self.ignoreBelow:
                    self.errors.append(RedArrowError(pointToCheck, "Extremum (badness %i units)" % badness, badness))
                    self.numErrors += 1
            else:
                self.errors.append(RedArrowError(pointToCheck, "Extremum"))
                self.numErrors += 1
    
    def _checkExtremumCubic(self, bcp1, bcp2, pt):
        myRect = normRect((self._prev[0], self._prev[1], pt[0], pt[1]))
        if not (pointInRect(bcp1, myRect) and pointInRect(bcp2, myRect)):
            for p in getExtremaForCubic(self._prev, bcp1, bcp2, pt):
                self.errors.append(RedArrowError((round(p[0]), round(p[1])), "Missing extremum"))
                self.numErrors += 1
    
    def _checkSmooth(self, pointToCheck, refPoint):
        if self._prev_ref is not None:
            a = abs(getTriangleArea(self._prev_ref, refPoint, pointToCheck))
            if 4000 > a > 200:
                #print a, self._prev_ref, refPoint, pointToCheck
                self.errors.append(RedArrowError(pointToCheck, "Smooth Connection (badness %i)" % a, a))
                self.numErrors += 1
    
    def _moveTo(self, pt):
        self._prev_ref = None
        self._prev = pt
    
    def _lineTo(self, pt):
        self._checkSmooth(self._prev, pt)
        self._prev_ref = self._prev
        self._prev = pt
    
    def _curveToOne(self, bcp1, bcp2, pt):
        # self._checkBbox doesn't display the actual extremum point,
        # but the offending handles. Superseded by self._checkExtremumCubic.
        #for bcp in [bcp1, bcp2]:
        #    self._checkBbox(bcp, pt)
        self._checkExtremumCubic(bcp1, bcp2, pt)
        self._checkSmooth(self._prev, bcp1)
        self._prev_ref = bcp2
        self._prev = pt
    
    def _qCurveToOne(self, bcp, pt):
        self._checkBbox(bcp, pt)
        # TODO extrema check on quadratic curves
        #self._checkExtremumQuad(bcp1, bcp2, pt)
        self._checkSmooth(self._prev, pt)
        self._prev_ref = bcp
        self._prev = pt
    
    def addComponent(self, baseGlyph, transformation):
        pass
