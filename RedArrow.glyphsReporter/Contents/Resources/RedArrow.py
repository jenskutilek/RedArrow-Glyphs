#!/usr/bin/env python
# encoding: utf-8

import objc
from Foundation import *
from AppKit import *
import sys, os, re
from string import strip

from outlineTestPen import OutlineTestPen

MainBundle = NSBundle.mainBundle()
path = MainBundle.bundlePath() + "/Contents/Scripts"
if not path in sys.path:
	sys.path.append( path )

import GlyphsApp

GlyphsReporterProtocol = objc.protocolNamed( "GlyphsReporter" )

class RedArrow ( NSObject, GlyphsReporterProtocol ):
	
	def init( self ):
		"""
		Put any initializations you want to make here.
		"""
		try:
			#Bundle = NSBundle.bundleForClass_( NSClassFromString( self.className() ));
			return self
		except Exception as e:
			self.logToConsole( "init: %s" % str(e) )
	
	def interfaceVersion( self ):
		"""
		Distinguishes the API version the plugin was built for. 
		Return 1.
		"""
		try:
			return 1
		except Exception as e:
			self.logToConsole( "interfaceVersion: %s" % str(e) )
	
	def title( self ):
		"""
		This is the name as it appears in the menu in combination with 'Show'.
		E.g. 'return "Nodes"' will make the menu item read "Show Nodes".
		"""
		try:
			return "Red Arrows"
		except Exception as e:
			self.logToConsole( "title: %s" % str(e) )
	
	def keyEquivalent( self ):
		"""
		The key for the keyboard shortcut. Set modifier keys in modifierMask() further below.
		Pretty tricky to find a shortcut that is not taken yet, so be careful.
		If you are not sure, use 'return None'. Users can set their own shortcuts in System Prefs.
		"""
		try:
			return "a"
		except Exception as e:
			self.logToConsole( "keyEquivalent: %s" % str(e) )
	
	def modifierMask( self ):
		"""
		Use any combination of these to determine the modifier keys for your default shortcut:
			return NSShiftKeyMask | NSControlKeyMask | NSCommandKeyMask | NSAlternateKeyMask
		Or:
			return 0
		... if you do not want to set a shortcut.
		"""
		try:
			return NSCommandKeyMask | NSShiftKeyMask | NSAlternateKeyMask
		except Exception as e:
			self.logToConsole( "modifierMask: %s" % str(e) )
	
	def drawForegroundForLayer_( self, Layer ):
		try:
			self._updateOutlineCheck(Layer)
		except Exception as e:
			self.logToConsole( "drawForegroundForLayer_: %s" % str(e) )
	
	def drawBackgroundForLayer_( self, Layer ):
		"""
		Whatever you draw here will be displayed BEHIND the paths.
		"""
		pass
	
	def drawBackgroundForInactiveLayer_( self, Layer ):
		"""
		Whatever you draw here will be displayed behind the paths, but for inactive masters.
		"""
		pass
	
	def needsExtraMainOutlineDrawingForInactiveLayer_( self, Layer ):
		"""
		Return False to disable the black outline. Otherwise remove the method.
		"""
		return True
	
	def getScale( self ):
		"""
		self.getScale() returns the current scale factor of the Edit View UI.
		Divide any scalable size by this value in order to keep the same apparent pixel size.
		"""
		try:
			return self.controller.graphicView().scale()
		except:
			self.logToConsole( "Scale defaulting to 1.0" )
			return 1.0
	
	def setController_( self, Controller ):
		"""
		Use self.controller as object for the current view controller.
		"""
		try:
			self.controller = Controller
		except Exception as e:
			self.logToConsole( "Could not set controller" )
	
	def logToConsole( self, message ):
		"""
		The variable 'message' will be passed to Console.app.
		Use self.logToConsole( "bla bla" ) for debugging.
		"""
		myLog = "Show %s plugin:\n%s" % ( self.title(), message )
		NSLog( myLog )
	
	
	def _updateOutlineCheck(self, layer):
		self.current_layer = layer
		if layer is not None:
			outline_test_pen = OutlineTestPen(layer.parent.parent)
			layer.draw(outline_test_pen)
			self.errors = outline_test_pen.errors
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
			if not e.kind == "Vector on closepath":
				if (e.position[0], e.position[1]) in errors_by_position:
					errors_by_position[(e.position[0], e.position[1])].extend([e])
				else:
					errors_by_position[(e.position[0], e.position[1])] = [e]
		for pos, errors in errors_by_position.iteritems():
			message = ""
			for e in errors:
				if e.badness is None or not debug:
					message += "%s, " % (e.kind)
				else:
					message += "%s (Severity %0.1f), " % (e.kind, e.badness)
			self._drawArrow(pos, message.strip(", "), size, width)
