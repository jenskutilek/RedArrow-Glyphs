from miniFontTools.misc.bezierTools import calcCubicParameters, solveQuadratic, splitCubicAtT

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
