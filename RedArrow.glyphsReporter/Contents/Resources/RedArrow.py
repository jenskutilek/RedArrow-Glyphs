# encoding: utf-8


from GlyphsApp.plugins import *

from outlineTestPenGlyphs import OutlineTestPenGlyphs
from string import strip

try:
	#from defconAppKit.windows.baseWindow import BaseWindowController
	from robofab.interface.all.dialogs_mac_vanilla import _ModalWindow, _baseWindowController
	import vanilla
	can_display_ui = True
except:
	can_display_ui = False

plugin_id = "de.kutilek.RedArrow"


class SelectGlyphsWindowController(_baseWindowController):
	
	test_names = {
		"test_extrema": "Missing Extremum Points",
		"test_fractional_coords": "Fractional Coordinates",
		"test_fractional_transform": "Fractional Transformation",
		"test_smooth": "Incorrect Smooth Connections",
		"test_empty_segments": "Empty Segments",
		"test_collinear": "Collinear Vectors",
		"test_semi_hv": "Semi-horizontal/-vertical Vectors",
		#"test_closepath": "",
		"test_zero_handles": "Zero Handles",
	}
	
	option_names = {
		"extremum_calculate_badness": "Calculate Extremum Badness",
		"extremum_ignore_badness_below": "Ignore Extremum Badness Below",
		"smooth_connection_max_distance": "Smooth Connection Tolerance",
		"fractional_ignore_point_zero": "Ignore .0 Fractional Values",
		"collinear_vectors_max_distance": "Collinear Vectors Tolerance",
		"grid_length": "Grid Length",
	}
	
	def __init__(self, options, run_tests):
		
		self.run_tests = {o: True for o in run_tests}
		self.options = options
		
		x = 10
		y = 8
		col = 240
		entry_line_height = 22
		title_line_height = 24
		title_skip = 8
		buttons_height = 44

		height = y + title_line_height + entry_line_height * (len(self.options) + len(self.run_tests)) + title_line_height + title_skip + buttons_height
		self.w = _ModalWindow((300, height), "Select Glyphs With Errors")
		
		self.w.tests_title = vanilla.TextBox((x, y, -10, 23), "Run Tests:")
		y += title_line_height

		for k in sorted(self.run_tests.keys()):
			setattr(self.w, k,
				vanilla.CheckBox((x + 3, y, -10, 20),
					self.test_names.get(k, k),
					value=self.run_tests[k],
					sizeStyle="small",
				)
			)
			y += entry_line_height
		
		vanilla.HorizontalLine((x, y, -10, 1))
		
		y += 8
		self.w.options_title = vanilla.TextBox((x, y, -10, 23), "Test Options (For Advanced Users):")
		y += title_line_height
		
		for k in sorted(self.options.keys()):
			v = self.options[k]
			if type(v) in (int, float):
				setattr(self.w, "%s_label" % k,
					vanilla.TextBox((x + 18, y+3, -10, 20),
						self.option_names.get(k, k),
						sizeStyle="small",
					)
				)
				setattr(self.w, k,
					vanilla.EditText((col, y+1, -14, 18),
						text=v,
						sizeStyle="small",
					)
				)
			elif type(v) == bool:
				setattr(self.w, k,
					vanilla.CheckBox((x + 3, y, -10, 20),
						self.option_names.get(k, k),
						value=v,
						sizeStyle="small",
					)
				)
			y += entry_line_height
		
		self.setUpBaseWindowBehavior()
		self.w.open()

	def get(self):
		if self.cancelled:
			return None, None
		else:
			options   = {option_name: int(getattr(self.w, option_name).get()) for option_name in self.options.keys()}
			run_tests = [test_name for test_name in self.run_tests if getattr(self.w, test_name).get()]
			return options, run_tests




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
				if not (
					tool.isKindOfClass_(NSClassFromString("GlyphsToolText")) 
					or tool.isKindOfClass_(NSClassFromString("GlyphsToolHand"))
					or tool.isKindOfClass_(NSClassFromString("GlyphsToolTrueTypeInstructor"))
				):
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


	def selectGlyphsOptions(self):
		ui = SelectGlyphsWindowController(self.options, self.run_tests)
		options, run_tests = ui.get()
		return options, run_tests
	

	def selectGlyphsWithErrors(self):
		"""
		Selects all glyphs with errors in the active layer
		"""
		font = NSApplication.sharedApplication().font
		if font is None:
			return None

		if can_display_ui:
			options, run_tests = self.selectGlyphsOptions()
		else:
			options = self.options
			run_tests = self.run_tests

		font.disableUpdateInterface()
		mid = font.selectedFontMaster.id
		self.options["grid_length"] = font.gridLength
		selection = []
		# pre-filter glyph list
		#glyphlist = [glyph.name for glyph in font.glyphs if len(glyph.layers[mid].paths) > 0]
		glyphlist = font.glyphs.keys()
		for glyph_name in glyphlist:
			glyph = font.glyphs[glyph_name]
			layer = glyph.layers[mid]
			if layer is not None:
				outline_test_pen = OutlineTestPenGlyphs(font, options, run_tests)
				try:
					layer.drawPoints(outline_test_pen)
					if len(outline_test_pen.errors) > 0:
						glyph.selected = True
						selection.append(glyph_name)
					else:
						glyph.selected = False
				except Exception as e:
					self.logToConsole( "selectGlyphsWithErrors: Layer '%s': %s" % (glyph_name, str(e)) )
		font.enableUpdateInterface()
		
	
	def _updateOutlineCheck(self, layer):
		self.current_layer = layer
		self.errors = []
		if layer is not None:
			self.options["grid_length"] = layer.parent.parent.gridLength
			outline_test_pen = OutlineTestPenGlyphs(layer.parent.parent, self.options, self.run_tests)
			layer.drawPoints(outline_test_pen)
			self.errors = outline_test_pen.errors
			if self.errors:
				self._drawArrows()
	
	
	def _drawArrow(self, position, kind, size, angle=0):
		size *= 2
		x, y = position
		head_ratio = 0.7
		w = size * 0.5
		tail_width = 0.3
		
		hor = 0.5 * (w - w * tail_width) # horizontal part under the head

		NSColor.colorWithCalibratedRed_green_blue_alpha_( 0.9, 0.1, 0.0, 0.85 ).set()
		t = NSAffineTransform.transform()
		t.translateXBy_yBy_(x, y)
		t.rotateByRadians_(angle)
		myPath = NSBezierPath.alloc().init()

		myPath.moveToPoint_( (0, 0) )
		myPath.relativeLineToPoint_( (- w * 0.5,      - size * head_ratio) )
		myPath.relativeLineToPoint_( (hor,            0) )
		myPath.relativeLineToPoint_( (0,              - size * (1 - head_ratio)) )
		myPath.relativeLineToPoint_( (w * tail_width, 0) )
		myPath.relativeLineToPoint_( (0,              size * (1 - head_ratio)) )
		myPath.relativeLineToPoint_( (hor,            0) )
		myPath.closePath()
		myPath.transformUsingAffineTransform_(t)
		myPath.fill()
		
		#mx, my = NSWindow.mouseLocationOutsideOfEventStream()
		#NSLog("Mouse %f %f" % (mx, my))
		#if NSMouseInRect((mx, my), NSMakeRect(x-size, y-size, size, size), False):
		if self.show_labels:
			myString = NSString.string().stringByAppendingString_(kind)
			myString.drawAtPoint_withAttributes_(
				(position[0] + 1.8 * size, position[1] - 1.8 * size),
				{
					NSFontAttributeName: NSFont.systemFontOfSize_(int(round(size/2))),
					NSForegroundColorAttributeName: NSColor.colorWithCalibratedRed_green_blue_alpha_( 0.4, 0.4, 0.6, 0.7 ),
				}
			)
	
	def _drawUnspecified(self, position, kind, size, angle=0):
		circle_size = size * 1.3
		x, y = position
		NSColor.colorWithCalibratedRed_green_blue_alpha_( 0.9, 0.1, 0.0, 0.85 ).set()
		myPath = NSBezierPath.alloc().init()
		myPath.setLineWidth_( 0 )
		myPath.appendBezierPathWithOvalInRect_( NSMakeRect( x - 0.5 * circle_size, y - 0.5 * circle_size, circle_size, circle_size ) )
		myPath.stroke()
		# FIXME
		#mx, my = NSWindow.mouseLocationOutsideOfEventStream()
		#NSLog("Mouse %f %f" % (mx, my))
		#if NSMouseInRect((mx, my), NSMakeRect(x-size, y-size, size, size), False):
		if self.show_labels: # show labels
			myString = NSString.string().stringByAppendingString_(kind)
			myString.drawAtPoint_withAttributes_(
				(position[0] + 1.8 * size, position[1] - 1.8 * size),
				{
					NSFontAttributeName: NSFont.systemFontOfSize_(size),
					NSForegroundColorAttributeName: NSColor.colorWithCalibratedRed_green_blue_alpha_( 0.4, 0.4, 0.6, 0.7 ),
				}
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
		for pos, errors in errors_by_position.iteritems():
			message = ""
			for e in errors:
				if e.badness is None or not debug:
					message += "%s, " % e.kind
				else:
					message += "%s (Severity %0.1f), " % (e.kind, e.badness)
			if pos is None:
				#bb = self.current_layer.bounds
				#pos = (bb.origin.x + 0.5 * bb.size.width, bb.origin.y + 0.5 * bb.size.height)
				pos = (self.current_layer.width + 20, -10)
				self._drawUnspecified(pos, message.strip(", "), size, e.angle)
			else:
				self._drawArrow(pos, message.strip(", "), size, e.angle)
