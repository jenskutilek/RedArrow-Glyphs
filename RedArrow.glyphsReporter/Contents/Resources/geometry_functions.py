from math import sqrt


def distance_between_points(p0, p1, do_round=False):
    d = sqrt((p1.y - p0.y) ** 2 + (p1.x - p0.x) ** 2)
    if do_round:
        return int(round(d))
    else:
        return d
