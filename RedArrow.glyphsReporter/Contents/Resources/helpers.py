from miniFontTools.bezierTools import calcCubicParameters, solveQuadratic, splitCubicAtT

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


# Classes

class RedArrowError(object):
    def __init__(self, position, kind, badness=1):
        self.position = position
        self.kind = kind
        self.badness = badness
    
    def __repr__(self):
        return "%s at (%i, %i)" % (self.kind, self.position[0], self.position[1])
