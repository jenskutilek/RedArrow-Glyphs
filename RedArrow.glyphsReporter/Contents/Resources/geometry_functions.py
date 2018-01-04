from math import sqrt

def distance_between_points(p0, p1, do_round=False):
	d = sqrt((p1[1] - p0[1])**2 + (p1[0] - p0[0])**2)
	if do_round:
		return int(round(d))
	else:
		return d
