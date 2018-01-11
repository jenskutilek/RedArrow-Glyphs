from __future__ import division, print_function
from outlineTestPen import OutlineTestPen

class OutlineTestPenGlyphs(OutlineTestPen):
	
	def _glyphs_workaround(self, segments):
		# FIXME workaround for Glyphs iterating the wrong direction for quadratic outlines
		
		segment_types = list(set([segment_type for segment_type, point in segments]))
		
		if "offcurve" in segment_types and "curve" not in segment_types:
			segments.reverse()
			segments = self._fix_qcurves(segments)
		
		return segments
	
	def _fix_qcurves(self, segments):
		# FIXME workaround for Glyphs giving "line" instead of "qcurve" segment type
		prev_segment_type = None
		fixed_segments = []
		for segment_type, point in segments:
			if segment_type == "line":
				if prev_segment_type == "offcurve":
					segment_type = "qcurve"
			fixed_segments.append((segment_type, point))
			prev_segment_type = segment_type		
		return fixed_segments
	
	def _flushContour(self, segments):
		
		reordered_segments = []
		remaining = []
		
		first_segment = True
		segment_points = []
		
		curve_order = 0
		
		# For Glyphs < 2.3b 860
		# This seems to be broken again in the current version (873)
		#segments = self._glyphs_workaround(segments)
		
		#print("Raw segments:")
		#print(segments)
		
		
		for segment_type, point in segments:
			point = point[0]
			if segment_type == "offcurve":
				if first_segment:
					remaining.append(point)
				else:
					segment_points.append(point)
			elif segment_type in ["curve", "qcurve"]:
				if first_segment:
					remaining.append(point)
				else:
					segment_points.append(point)
					reordered_segments.append((segment_type, segment_points))
					segment_points = []
				first_segment = False
				if segment_type == "curve":
					curve_order = 3
				elif segment_type == "qcurve":
					curve_order = 2
			elif segment_type == "line":
				first_segment = False
				reordered_segments.append((segment_type, [point]))
				segment_points = []
			elif segment_type == "move":
				reordered_segments.append((segment_type, [point]))
			else:
				pass
		
		if segment_points:
			first = segment_points + remaining
		else:
			first = remaining
		
		if len(first) > 0:
			if curve_order == 3:
				reordered_segments.insert(0, ("curve", first))
			elif curve_order == 2:
				reordered_segments.insert(0, ("qcurve", first))
			else:
				print("Warning: Undetermined curve order.")
		
		super(OutlineTestPenGlyphs, self)._flushContour(reordered_segments)




if __name__ == "__main__":
	g = Font.selectedLayers[0]
	p = OutlineTestPenGlyphs(Font)
	g.drawPoints(p)
	for e in p.errors:
		print(e)
