from outlineTestPen import OutlineTestPen

class OutlineTestPenGlyphs(OutlineTestPen):
	
	def _flushContour(self, segments):
		
		reordered_segments = []
		remaining = []
		
		first_segment = True
		segment_points = []
		
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
			elif segment_type == "line":
				first_segment = False
				reordered_segments.append((segment_type, point))
				segment_points = []
			elif segment_type == "move":
				reordered_segments.append((segment_type, point))
			else:
				pass
		if segment_points:
			remaining.insert(0, segment_points[0])
		if len(remaining) == 3:
			reordered_segments.insert(0, ("curve", remaining))
		
		super(OutlineTestPenGlyphs, self)._flushContour(reordered_segments)




if __name__ == "__main__":
	g = Font.selectedLayers[0]
	p = OutlineTestPenGlyphs(Font)
	g.drawPoints(p)
	for e in p.errors:
		print e