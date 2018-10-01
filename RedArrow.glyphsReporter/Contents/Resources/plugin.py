# encoding: utf-8
from __future__ import division, print_function

import objc
from GlyphsApp import Glyphs, MOUSEMOVED #, UPDATEINTERFACE
from GlyphsApp.plugins import *
from AppKit import NSAffineTransform, NSApplication, NSAlternateKeyMask, NSBezierPath, NSClassFromString, NSColor, NSCommandKeyMask, NSFont, NSFontAttributeName, NSForegroundColorAttributeName, NSMakeRect, NSMenuItem, NSMutableParagraphStyle, NSPoint, NSRect, NSShiftKeyMask, NSString

if hasattr(Glyphs, 'buildNumber') and Glyphs.buildNumber >= 1147:
	from outlineTestPen import OutlineTestPen
else:
	from outlineTestPenGlyphs import OutlineTestPenGlyphs as OutlineTestPen
from geometry_functions import distance_between_points
from math import atan2, cos, pi, sin, degrees

plugin_id = "de.kutilek.RedArrow"
DEBUG = False




class RedArrow(ReporterPlugin):
	
	def settings(self):
		self.menuName = "Red Arrows"
		self.keyboardShortcut = 'a'
		self.keyboardShortcutModifier = NSCommandKeyMask | NSShiftKeyMask | NSAlternateKeyMask
		self.generalContextMenus = [
			{"name": Glyphs.localize({'en': u'Show Error Labels', 'de': u'Fehlerbeschriftung anzeigen'}), "action": self.toggleLabels},
		]
	
	def start(self):
		self.addMenuItem()
		self.options = {
			"extremum_calculate_badness": False,
			"extremum_ignore_badness_below": 0,
			"smooth_connection_max_distance": 4,
			"fractional_ignore_point_zero": True,
			"collinear_vectors_max_distance": 2,
			#"test_closepath": False,
			"grid_length": 1,
		}
		self.run_tests = [
			"test_extrema",
			"test_inflections",
			"test_fractional_coords",
			"test_fractional_transform",
			"test_smooth",
			"test_empty_segments",
			"test_collinear",
			"test_semi_hv",
			#"test_closepath",
			"test_zero_handles",
		]
		self.errors = []
		self.show_labels = Glyphs.defaults["%s.showLabels" % plugin_id]
		self.show_labels = not(self.show_labels)
		self.mouse_position = (0, 0)
		self.should_update_report = True
		self.vanilla_alerted = False
		self.toggleLabels()
	

	def addMenuItem(self):
		mainMenu = NSApplication.sharedApplication().mainMenu()
		s = objc.selector(self.selectGlyphsWithErrors,signature='v@:')
		newMenuItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
			Glyphs.localize({
				'en': u"Select Glyphs With Outline Errors",
				'de': u'Glyphen mit Outlinefehlern auswählen',
				'ko': u"윤곽선 오류가 있는 글리프 선택"
			}),
			s,
			""
		)
		newMenuItem.setTarget_(self)
		mainMenu.itemAtIndex_(2).submenu().insertItem_atIndex_(newMenuItem, 11)


	def updateReport(self, notification):
		if DEBUG: self.logToConsole( "updateReport")
		self.should_update_report = True
		Glyphs.redraw()


	def mouseDidMove(self, notification):
		Glyphs.redraw()
	

	def willActivate(self):
		#Glyphs.addCallback(self.updateReport, UPDATEINTERFACE)
		Glyphs.addCallback(self.mouseDidMove, MOUSEMOVED)


	def willDeactivate(self):
		try:
			Glyphs.removeCallback(self.mouseDidMove)
			#Glyphs.removeCallback(self.updateReport)
		except Exception as e:
			self.logToConsole( "willDeactivate: %s" % str(e) )
	

	def foreground(self, layer):
		if self.should_update_report:
			#self.logToConsole( "_updateOutlineCheck: %s" % layer)
			self._updateOutlineCheck(layer)
			#self.logToConsole( "foreground: Errors: %s" % self.errors )
			#self.should_update_report = False
		try:
			try:
				self.mouse_position = self.controller.graphicView().getActiveLocation_(Glyphs.currentEvent())
			except Exception as e:
				self.logToConsole( "foreground: mouse_position: %s" % str(e) )
				self.mouse_position = (0, 0)
			currentController = self.controller.view().window().windowController()
			if currentController:
				tool = currentController.toolDrawDelegate()
				# don't activate if on cursor tool, or pan tool
				if not (
					tool.isKindOfClass_(NSClassFromString("GlyphsToolText")) 
					or tool.isKindOfClass_(NSClassFromString("GlyphsToolHand"))
					or tool.isKindOfClass_(NSClassFromString("GlyphsToolTrueTypeInstructor"))
				):
					if len(self.errors) > 0:
						self._drawArrows()
		except Exception as e:
			self.logToConsole( "foreground: %s" % str(e) )


	
	def toggleLabels(self):
		if self.show_labels:
			self.show_labels = False
			self.generalContextMenus = [
				{
					"name": Glyphs.localize(
						{
							'en': u'Show Error Labels',
							'de': u'Fehlerbeschriftung anzeigen'
						}
					),
					"action": self.toggleLabels
				},
			]
		else:
			self.show_labels = True
			self.generalContextMenus = [
				{
					"name": Glyphs.localize(
						{
							'en': u'Hide Error Labels',
							'de': u'Fehlerbeschriftung ausblenden'
						}
					),
					"action": self.toggleLabels
				},
			]
		Glyphs.defaults["%s.showLabels" % plugin_id] = self.show_labels


	def selectGlyphsOptions(self):
		try:
			from raDialogs import SelectGlyphsWindowController
		except ImportError:
			if not self.vanilla_alerted:
				print("Please install vanilla to enable UI dialogs for RedArrow. You can install vanilla through Glyphs > Preferences > Addons > Modules.")
				self.vanilla_alerted = True

		if self.vanilla_alerted:
			return self.options, self.run_tests
		else:
			ui = SelectGlyphsWindowController(self.options, self.run_tests)
			return ui.get()
	

	def selectGlyphsWithErrors(self):
		"""
		Selects all glyphs with errors in the active layer
		"""
		font = NSApplication.sharedApplication().font
		if font is None:
			return None

		options, run_tests = self.selectGlyphsOptions()
		if run_tests is None:
			return
		if options is None:
			return
		
		font.disableUpdateInterface()
		mid = font.selectedFontMaster.id
		self.options["grid_length"] = font.gridLength
		glyphlist = font.glyphs.keys()
		outline_test_pen = OutlineTestPen(font, options, run_tests)
		for glyph_name in glyphlist:
			glyph = font.glyphs[glyph_name]
			layer = glyph.layers[mid]
			outline_test_pen.errors = []
			if layer is not None:
				try:
					layer.drawPoints(outline_test_pen)
					if len(outline_test_pen.errors) > 0:
						glyph.selected = True
					else:
						glyph.selected = False
				except Exception as e:
					self.logToConsole( "selectGlyphsWithErrors: Layer '%s': %s" % (glyph_name, str(e)) )
		font.enableUpdateInterface()
		
	
	def _updateOutlineCheck(self, layer):
		if DEBUG and hasattr(layer, "parent"): self.logToConsole( "_updateOutlineCheck: '%s' from %s" % (layer.parent.name, layer.parent.parent) )
		self.current_layer = layer
		self.errors = []
		if layer is not None and hasattr(layer, "parent"):
			self.options["grid_length"] = layer.parent.parent.gridLength
			outline_test_pen = OutlineTestPen(layer.parent.parent, self.options, self.run_tests)
			layer.drawPoints(outline_test_pen)
			self.errors = outline_test_pen.errors
	
	
	def _drawArrow(self, position, kind, size, vector = (-1, 1)):
		if vector is None:
			vector = (-1, 1)
		angle = atan2(vector[0], -vector[1])
		size *= 2
		x, y = position
		head_ratio = 0.7
		w = size * 0.5
		tail_width = 0.3
		
		chin = 0.5 * (w - w * tail_width) # part under the head

		NSColor.colorWithCalibratedRed_green_blue_alpha_( 0.9, 0.1, 0.0, 0.85 ).set()
		t = NSAffineTransform.transform()
		t.translateXBy_yBy_(x, y)
		t.rotateByRadians_(angle)
		myPath = NSBezierPath.alloc().init()

		myPath.moveToPoint_(         (0, 0)                                       )
		myPath.relativeLineToPoint_( (-size * head_ratio,        w * 0.5)         )
		myPath.relativeLineToPoint_( (0,                         -chin)           )
		myPath.relativeLineToPoint_( (-size * (1 - head_ratio),  0)               )
		myPath.relativeLineToPoint_( (0,                         -w * tail_width) )
		myPath.relativeLineToPoint_( (size * (1 - head_ratio),   0)               )
		myPath.relativeLineToPoint_( (0,                         -chin)           )
		myPath.closePath()
		myPath.transformUsingAffineTransform_(t)
		myPath.fill()
		
		if self.show_labels or distance_between_points(self.mouse_position, position) < size:
			self._drawTextLabel(
				transform = t,
				text = kind,
				size = size,
				vector = vector,
			)


	def _drawTextLabel(self, transform, text, size, vector):
		if vector is None:
			vector = (-1, 1)
		angle = atan2(vector[0], -vector[1])
		text_size = 0.5 * size
		
		#para_style = NSMutableParagraphStyle.alloc().init()
		#para_style.setAlignment_(NSCenterTextAlignment)

		attrs = {
			NSFontAttributeName:            NSFont.systemFontOfSize_(text_size),
			NSForegroundColorAttributeName: NSColor.colorWithCalibratedRed_green_blue_alpha_( 0.4, 0.4, 0.6, 0.7 ),
			#NSParagraphStyleAttributeName:  para_style,
		}
		myString = NSString.string().stringByAppendingString_(text)
		bbox = myString.sizeWithAttributes_(attrs)
		bw = bbox.width
		bh = bbox.height

		text_pt = NSPoint()
		text_pt.y = 0

		if -0.5 * pi < angle <= 0.5 * pi:
			text_pt.x = -1.3 * size - bw / 2 * cos(angle) - bh / 2 * sin(angle)
		else:
			text_pt.x = -1.3 * size + bw / 2 * cos(angle) + bh / 2 * sin(angle)
		
		text_pt = transform.transformPoint_(text_pt)
		
		rr = NSRect(
			origin = (text_pt.x - bw / 2, text_pt.y - bh / 2),
			size = (bw, bh)
		)
		
		if DEBUG:
			NSColor.colorWithCalibratedRed_green_blue_alpha_( 0, 0, 0, 0.15 ).set()
			myRect = NSBezierPath.bezierPathWithRect_(rr)
			myRect.setLineWidth_(0.05 * size)
			myRect.stroke()
		
		myString.drawInRect_withAttributes_(
			rr,
			attrs
		)

		#myString.drawAtPoint_withAttributes_(
		#	text_pt,
		#	attrs
		#)
	
	def _drawUnspecified(self, position, kind, size, vector = (-1, 1)):
		if vector is None:
			vector = (-1, 1)
		angle = atan2(vector[1], vector[0])
		circle_size = size * 1.3
		x, y = position
		NSColor.colorWithCalibratedRed_green_blue_alpha_( 0.9, 0.1, 0.0, 0.85 ).set()
		
		t = NSAffineTransform.transform()
		t.translateXBy_yBy_(x, y)
		t.rotateByRadians_(angle)

		myPath = NSBezierPath.alloc().init()
		myPath.setLineWidth_( 0 )
		myPath.appendBezierPathWithOvalInRect_( NSMakeRect( x - 0.5 * circle_size, y - 0.5 * circle_size, circle_size, circle_size ) )
		myPath.stroke()
		if self.show_labels or distance_between_points(self.mouse_position, position) < size:
			self._drawTextLabel(
				transform = t,
				text = kind,
				size = size,
				angle = angle,
			)
	
	def _drawArrows(self, debug=False):
		size = 10.0 / self.getScale()
		errors_by_position = {}
		for e in self.errors:
			if e.position is not None:
				if (e.position[0], e.position[1]) in errors_by_position:
					errors_by_position[(e.position[0], e.position[1])].extend([e])
				else:
					errors_by_position[(e.position[0], e.position[1])] = [e]
			else:
				if None in errors_by_position:
					errors_by_position[None].extend([e])
				else:
					errors_by_position[None] = [e]
		for pos, errors in errors_by_position.items():
			message = u""
			for e in errors:
				if e.badness is None or not debug:
					if DEBUG:
						message += u"%s (%0.2f|%0.2f = %0.2f π), " % (e.kind, e.vector[0], e.vector[1], atan2(*e.vector) / pi)
					else:
						message += u"%s, " % e.kind
				else:
					message += "%s (Severity %0.1f), " % (e.kind, e.badness)
			if pos is None:
				pos = (self.current_layer.width + 20, -10)
				self._drawUnspecified(pos, message.strip(", "), size, e.vector)
			else:
				self._drawArrow(pos, message.strip(", "), size, e.vector)
