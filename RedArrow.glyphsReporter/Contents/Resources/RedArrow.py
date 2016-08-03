# encoding: utf-8


from GlyphsApp.plugins import *

from outlineTestPenGlyphs import OutlineTestPenGlyphs
from string import strip

plugin_id = "de.kutilek.RedArrow"


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
			"test_closepath": False,
		}
		self.run_tests = [
			"test_extrema",
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
		self.toggleLabels()
	
	def addMenuItem(self):
		mainMenu = NSApplication.sharedApplication().mainMenu()
		s = objc.selector(self.selectGlyphsWithErrors,signature='v@:')
		newMenuItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
			Glyphs.localize({
				'en': u"Select Glyphs With Outline Errors",
				'de': u'Glyphen mit Outlinefehlern auswählen'
			}),
			s,
			""
		)
		newMenuItem.setTarget_(self)
		mainMenu.itemAtIndex_(2).submenu().insertItem_atIndex_(newMenuItem, 11)
	
	def foreground(self, Layer):
		try:
			currentController = self.controller.view().window().windowController()
			if currentController:
			    tool = currentController.toolDrawDelegate()
			    # don't activate if on cursor tool, or pan tool
			    if not tool.isKindOfClass_( NSClassFromString("GlyphsToolText") ) and not tool.isKindOfClass_( NSClassFromString("GlyphsToolHand") ):
					self._updateOutlineCheck(Layer)
		except Exception as e:
			self.logToConsole( "drawForegroundForLayer_: %s" % str(e) )
	
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
	
	def selectGlyphsWithErrors(self):
		"""
		Selects all glyphs with errors in the active layer
		"""
		font = NSApplication.sharedApplication().font
		if font is None:
			return None
		font.disableUpdateInterface()
		mid = font.selectedFontMaster.id
		selection = []
		# pre-filter glyph list
		#glyphlist = [glyph.name for glyph in font.glyphs if len(glyph.layers[mid].paths) > 0]
		glyphlist = font.glyphs.keys()
		for glyph_name in glyphlist:
			glyph = font.glyphs[glyph_name]
			layer = glyph.layers[mid]
			if layer is not None:
				#try:
				outline_test_pen = OutlineTestPenGlyphs(layer.parent.parent, self.options, self.run_tests)
				layer.drawPoints(outline_test_pen)
				if len(outline_test_pen.errors) > 0:
					glyph.selected = True
					selection.append(glyph_name)
				else:
					glyph.selected = False
				#except Exception as e:
				#	self.logToConsole( "selectGlyphsWithErrors: Layer '%s': %s" % (glyph_name, str(e)) )
		font.enableUpdateInterface()
		
	
	def _updateOutlineCheck(self, layer):
		self.current_layer = layer
		self.errors = []
		if layer is not None:
			outline_test_pen = OutlineTestPenGlyphs(layer.parent.parent, self.options, self.run_tests)
			layer.drawPoints(outline_test_pen)
			self.errors = outline_test_pen.errors
			if self.errors:
				self._drawArrows()
	
	def _drawArrow(self, position, kind, size, width):
		x, y = position
		NSColor.colorWithCalibratedRed_green_blue_alpha_( 0.9, 0.1, 0.0, 0.85 ).set()
		myPath = NSBezierPath.alloc().init()
		myPath.setLineWidth_( width )
		myPath.moveToPoint_( (x, y-size) )
		myPath.lineToPoint_( (x, y) )
		myPath.lineToPoint_( (x+size, y) )
		myPath.moveToPoint_( (x, y) )
		myPath.lineToPoint_( (x+size, y-size) )
		myPath.stroke()
		#mx, my = NSWindow.mouseLocationOutsideOfEventStream()
		#NSLog("Mouse %f %f" % (mx, my))
		#if NSMouseInRect((mx, my), NSMakeRect(x-size, y-size, size, size), False):
		if self.show_labels:
			myString = NSString.string().stringByAppendingString_(kind)
			myString.drawAtPoint_withAttributes_(
				(position[0] + 1.8 * size, position[1] - 1.8 * size),
				{
					NSFontAttributeName: NSFont.systemFontOfSize_(size),
					NSForegroundColorAttributeName: NSColor.colorWithCalibratedRed_green_blue_alpha_( 0.4, 0.4, 0.6, 0.7 ),
				}
			)
	
	def _drawUnspecified(self, position, kind, size, width):
		circle_size = size * 1.3
		width *= 0.8
		x, y = position
		NSColor.colorWithCalibratedRed_green_blue_alpha_( 0.9, 0.1, 0.0, 0.85 ).set()
		myPath = NSBezierPath.alloc().init()
		myPath.setLineWidth_( width )
		myPath.appendBezierPathWithOvalInRect_( NSMakeRect( x - 0.5 * circle_size, y - 0.5 * circle_size, circle_size, circle_size ) )
		myPath.stroke()
		# FIXME
		#mx, my = NSWindow.mouseLocationOutsideOfEventStream()
		#NSLog("Mouse %f %f" % (mx, my))
		#if NSMouseInRect((mx, my), NSMakeRect(x-size, y-size, size, size), False):
		if True: # show labels
			myString = NSString.string().stringByAppendingString_(kind)
			myString.drawAtPoint_withAttributes_(
				(position[0] + 1.8 * size, position[1] - 1.8 * size),
				{
					NSFontAttributeName: NSFont.systemFontOfSize_(size),
					NSForegroundColorAttributeName: NSColor.colorWithCalibratedRed_green_blue_alpha_( 0.4, 0.4, 0.6, 0.7 ),
				}
			)
	
	def _drawArrows(self, debug=False):
		scale = self.getScale()
		size = 10.0 / scale
		width = 3.0 / scale
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
		for pos, errors in errors_by_position.iteritems():
			message = ""
			for e in errors:
				if e.badness is None or not debug:
					message += "%s, " % (e.kind)
				else:
					message += "%s (Severity %0.1f), " % (e.kind, e.badness)
			if pos is None:
				#bb = self.current_layer.bounds
				#pos = (bb.origin.x + 0.5 * bb.size.width, bb.origin.y + 0.5 * bb.size.height)
				pos = (self.current_layer.width + 20, -10)
				self._drawUnspecified(pos, message.strip(", "), size, width)
			else:
				self._drawArrow(pos, message.strip(", "), size, width)
