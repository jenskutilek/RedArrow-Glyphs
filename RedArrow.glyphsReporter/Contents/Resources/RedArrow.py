#!/usr/bin/env python
# encoding: utf-8

import objc
from Foundation import *
from AppKit import *
import sys, os, re
from string import strip

from helpers import getExtremaForCubic, RedArrowError

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
			return "y"
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
			return 0
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
		try:
			pass
		except Exception as e:
			self.logToConsole( "drawBackgroundForLayer_: %s" % str(e) )
	
	def drawBackgroundForInactiveLayer_( self, Layer ):
		"""
		Whatever you draw here will be displayed behind the paths, but for inactive masters.
		"""
		try:
			pass
		except Exception as e:
			self.logToConsole( "drawBackgroundForInactiveLayer_: %s" % str(e) )
	
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
		self.errors = {}
		for path in layer.paths:
			for i in range(len(path.segments)):
				segment = path.segments[i]
				if len(segment) == 4: # curve
					self._curveTests(segment)
		self._drawArrows()
	
	def _curveTests(self, segment):
		p1 = segment[0].pointValue()
		p2 = segment[1].pointValue()
		p3 = segment[2].pointValue()
		p4 = segment[3].pointValue()
		
		self._globalExtremumTest(p1, p2, p3, p4)
		self._localExtremumTest(p1, p2, p3, p4)
		
	def _localExtremumTest(self, p1, p2, p3, p4):
		myRect = NSMakeRect(
			min(p1.x, p4.x),
			min(p1.y, p4.y),
			max(p1.x, p4.x) - min(p1.x, p4.x),
			max(p1.y, p4.y) - min(p1.y, p4.y)
		)
		if not (NSMouseInRect(p2, myRect, False) and NSMouseInRect(p3, myRect, False)):
			points = getExtremaForCubic((p1.x, p1.y), (p2.x, p2.y), (p3.x, p3.y), (p4.x, p4.y))
			for p in points:
				if p in self.errors:
					self.errors[p].extend([RedArrowError(p, "Local extremum")])
				else:
					self.errors[p] = [RedArrowError(p, "Local extremum")]
	
	def _globalExtremumTest(self, p1, p2, p3, p4):
		myRect = self.current_layer.bounds
		if not (NSPointInRect(p2, myRect) and NSPointInRect(p3, myRect)):
			points = getExtremaForCubic((p1.x, p1.y), (p2.x, p2.y), (p3.x, p3.y), (p4.x, p4.y), h=True, v=True)
			for p in points:
				if p in self.errors:
					self.errors[p].extend([RedArrowError(p, "Bounding box extremum")])
				else:
					self.errors[p] = [RedArrowError(p, "Bounding box extremum")]
	
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
				(position[0] + 1.8 * size, position[1] - size),
				{
					NSFontAttributeName: NSFont.systemFontOfSize_(size),
					NSForegroundColorAttributeName: NSColor.colorWithCalibratedRed_green_blue_alpha_( 0.4, 0.4, 0.4, 0.7 ),
				}
			)
	
	def _drawArrows(self):
		scale = self.getScale()
		size = 10.0 / scale
		width = 3.0 / scale
		for pos, errors in self.errors.iteritems():
			message = ""
			for e in errors:
				message += "%s, " % e.kind
			self._drawArrow(pos, message.strip(", "), size, width)
