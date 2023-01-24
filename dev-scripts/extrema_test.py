from __future__ import division
from math import atan2, degrees, cos, pi, sin, sqrt
# from types import TupleType
from fontTools.misc.arrayTools import pointInRect, normRect
from fontTools.misc.bezierTools import calcCubicParameters, solveQuadratic, splitCubicAtT
from fontTools.misc.transform import Transform
#from fontTools.pens.pointPen import BasePointToSegmentPen

def get_extrema_points_vectors(roots, pt1, pt2, pt3, pt4):
    split_segments = [p for p in splitCubicAtT(pt1, pt2, pt3, pt4, *roots)[:-1]]
    points = [p[3] for p in split_segments]
    vectors = [get_vector(p[2], p[3]) for p in split_segments]
    for s in split_segments:
        print("    Split:", s)
        save()
        stroke(None)
        fill(1, 0.6, 0, 0.8)
        for p in s:
            oval(p[0] - 1, p[1] - 1, 2, 2)
            fontSize(4)
            text("%i|%i" % p, p)
        #oval(s[-1][0] - 2, s[-1][1] - 2, 4, 4)
        fill(None)
        strokeWidth(0.5)
        stroke(1, 0.6, 0, 0.8)
        line(s[0], s[1])
        line(s[2], s[3])
        restore()
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

def get_vector(p0, p1):
    return (
        int(round(p1[0] - p0[0])),
        int(round(p1[1] - p0[1]))
    )

def angle_between_points(p0, p1):
    return atan2(
        int(round(p1[1])) - int(round(p0[1])),
        int(round(p1[0])) - int(round(p0[0]))
    )

cubics = [
    ((329,40), (287,22), (266,53), (235,40)),
    ((200, 280), (160, 250), (230, 200), (200, 100)),
    ((300, 100), (340, 140), (360, 180), (280, 160)),
]

size(400, 300)

fill(None)
strokeWidth(1)
stroke(0)

for j, cubic in enumerate(cubics):
    save()
    stroke(None)
    fill(0, 0, 0, 0.3)
    text("%i" % (j + 1), cubic[0])
    for p in cubic:
        oval(p[0] - 1, p[1] - 1, 2, 2)
    fill(None)
    strokeWidth(0.25)
    stroke(0, 0, 0, 0.15)
    line(cubic[0], cubic[1])
    line(cubic[2], cubic[3])
    restore()
    
    newPath()
    moveTo(cubic[0])
    curveTo(*cubic[1:])
    #endPath()
    drawPath()
    
    print("\nCubic %i:" % (j + 1))
    print(cubic)

    points, vectors = getExtremaForCubic(*cubic, h=True, v=True)
    print("    Points: ", points)
    print("    Vectors:", vectors)

    for i, p in enumerate(points):
        phi = atan2(vectors[i][1], vectors[i][0])
        save()
        stroke(1, 0, 0)
        translate(*p)
        rotate(degrees(phi))
        line((0, 0), (0, -20))
        restore()
