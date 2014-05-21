def pointInRect((x, y), rect):
    """Return True when point (x, y) is inside rect."""
    xMin, yMin, xMax, yMax = rect
    return (xMin <= x <= xMax) and (yMin <= y <= yMax)

def normRect((xMin, yMin, xMax, yMax)):
    """Normalize the rectangle so that the following holds:
        xMin <= xMax and yMin <= yMax
    """
    return min(xMin, xMax), min(yMin, yMax), max(xMin, xMax), max(yMin, yMax)
