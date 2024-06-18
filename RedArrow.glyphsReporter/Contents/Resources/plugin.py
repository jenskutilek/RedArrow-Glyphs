# encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import objc

from AppKit import (
    NSAffineTransform,
    NSApplication,
    NSAlternateKeyMask,
    NSBezierPath,
    NSClassFromString,
    NSColor,
    NSCommandKeyMask,
    NSFont,
    NSFontAttributeName,
    NSForegroundColorAttributeName,
    NSInsetRect,
    NSMakePoint,
    NSMakeRect,
    NSMenuItem,
    NSOffsetRect,
    NSRect,
    NSShiftKeyMask,
    NSString,
    NSNotificationCenter,
)
from GlyphsApp import Glyphs, MOUSEMOVED, WINDOW_MENU
from GlyphsApp.plugins import ReporterPlugin
from math import atan2, cos, pi, sin

from redArrow.defaults import default_options, default_tests, typechecked_options
from redArrow.geometry_functions import distance_between_points
from redArrow.outlineTestGlyphs import OutlineTest

# from time import time


plugin_id = "de.kutilek.RedArrow"
DEBUG = False


error_color = (0.9019, 0.25, 0.0, 0.85)
warning_color = (0.9019, 0.7215, 0.0, 0.85)
text_color = NSColor.textColor()
label_background = NSColor.textBackgroundColor()

normal_vector = (1, 1)


def full_libkey(key):
    return "%s.%s" % (plugin_id, key)


class RedArrow(ReporterPlugin):
    @objc.python_method
    def settings(self):
        self.menuName = "Red Arrows"
        self.keyboardShortcut = "a"
        self.keyboardShortcutModifier = (
            NSCommandKeyMask | NSShiftKeyMask | NSAlternateKeyMask
        )
        self.hide_labels_menu = [
            {
                "name": Glyphs.localize(
                    {
                        "en": "Hide Error Labels",
                        "de": "Fehlerbeschriftung ausblenden",
                    }
                ),
                "action": self.toggleLabels_,
            },
        ]
        self.show_labels_menu = [
            {
                "name": Glyphs.localize(
                    {
                        "en": "Show Error Labels",
                        "de": "Fehlerbeschriftung anzeigen",
                    }
                ),
                "action": self.toggleLabels_,
            },
        ]
        self.show_labels = Glyphs.defaults["%s.showLabels" % plugin_id]
        self.show_labels = not (self.show_labels)
        self.toggleLabels_(None)

    @objc.python_method
    def start(self):
        self.addMenuItem()
        self.addWindowMenuItem()
        self.options = default_options
        self.run_tests = default_tests
        self.errors = []
        self.mouse_position = NSMakePoint(0, 0)
        self.lastChangeDate = 0
        self.current_layer = None
        self.load_defaults()

    @objc.python_method
    def addMenuItem(self):
        mainMenu = NSApplication.sharedApplication().mainMenu()
        s = objc.selector(self.selectGlyphsWithErrors, signature=b"v@:@")
        newMenuItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            Glyphs.localize(
                {
                    "en": "Select Glyphs With Outline Errors",
                    "de": "Glyphen mit Outlinefehlern auswählen",
                    "ko": "윤곽선 오류가 있는 글리프 선택",
                }
            ),
            s,
            "",
        )
        newMenuItem.setTarget_(self)
        mainMenu.itemAtIndex_(2).submenu().insertItem_atIndex_(newMenuItem, 12)

    @objc.python_method
    def addWindowMenuItem(self):
        newMenuItem = NSMenuItem.alloc().init()
        newMenuItem.setTitle_(
            Glyphs.localize(
                {
                    "en": "Red Arrow Preferences...",
                    "de": "Red-Arrow-Einstellungen ...",
                }
            )
        )
        newMenuItem.setAction_(self.setRedArrowDefaults_)
        newMenuItem.setTarget_(self)
        Glyphs.menu[WINDOW_MENU].append(newMenuItem)

    @objc.python_method
    def load_defaults(self):
        # print("Loading defaults:")
        options = {
            k: Glyphs.defaults.get(full_libkey(k), v)
            for k, v in default_options.items()
        }
        self.options = typechecked_options(options)
        self.run_tests = Glyphs.defaults.get(full_libkey("run-tests"), default_tests)
        self.outline_test = OutlineTest(None, self.options, self.run_tests)
        self.current_layer = None
        Glyphs.redraw()

    @objc.python_method
    def save_defaults(self, options, run_tests):
        for k, v in default_options.items():
            Glyphs.defaults[full_libkey(k)] = options.get(k, v)
        Glyphs.defaults[full_libkey("run-tests")] = run_tests

    def mouseDidMove_(self, notification):
        try:
            notification.object().window().windowController().activeEditViewController().graphicView().setNeedsDisplay_(
                True
            )
        except Exception:
            import traceback

            print(traceback.format_exc())

    def willActivate(self):
        try:
            if not self.show_labels:
                self.startMouseMoved()
        except Exception as e:
            self.logToConsole("willDeactivate: %s" % str(e))

    def willDeactivate(self):
        try:
            if not self.show_labels:
                self.stopMouseMoved()
        except Exception as e:
            self.logToConsole("willDeactivate: %s" % str(e))

    @objc.python_method
    def foreground(self, layer):
        # self.logToConsole("_updateOutlineCheck: %s" % layer)
        self._updateOutlineCheck(layer)
        # self.logToConsole("foreground: Errors: %s" % self.errors )

        try:
            self.mouse_position = self.controller.graphicView().getActiveLocation_(
                Glyphs.currentEvent()
            )
        except Exception as e:
            self.logToConsole("foreground: mouse_position: %s" % str(e))
            self.mouse_position = NSMakePoint(0, 0)

        currentController = self.controller.view().window().windowController()
        if currentController:
            tool = currentController.toolDrawDelegate()
            # don't activate if on cursor tool, or pan tool
            if not (
                tool.isKindOfClass_(NSClassFromString("GlyphsToolText"))
                or tool.isKindOfClass_(NSClassFromString("GlyphsToolHand"))
                or tool.isKindOfClass_(
                    NSClassFromString("GlyphsToolTrueTypeInstructor")
                )
            ):
                if self.errors:
                    self._drawArrows()

    def toggleLabels_(self, sender):
        if self.show_labels:
            self.show_labels = False
            self.generalContextMenus = self.show_labels_menu
            self.startMouseMoved()
        else:
            self.show_labels = True
            self.generalContextMenus = self.hide_labels_menu
            self.stopMouseMoved()
        Glyphs.defaults[full_libkey("showLabels")] = self.show_labels
        Glyphs.redraw()

    def startMouseMoved(self):
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(
            self, self.mouseDidMove_, MOUSEMOVED, objc.nil
        )

    def stopMouseMoved(self):
        NSNotificationCenter.defaultCenter().removeObserver_(self)

    @objc.python_method
    def selectGlyphsOptions(self, title="Select Glyphs With Errors"):
        from redArrow.dialogs import SelectGlyphsWindowController

        ui = SelectGlyphsWindowController(self.options, self.run_tests, title)
        return ui.get()

    def selectGlyphsWithErrors(self):
        """
        Selects all glyphs with errors in the active layer
        """
        font = Glyphs.font
        if font is None:
            return None

        self.options["grid_length"] = font.gridLength
        save_global, options, run_tests = self.selectGlyphsOptions()
        if run_tests is None:
            return
        if options is None:
            return
        if save_global:
            self.save_defaults(options, run_tests)
            self.load_defaults()

        options = typechecked_options(options)

        font.disableUpdateInterface()
        mid = font.selectedFontMaster.id
        glyphlist = font.glyphs.keys()
        for glyph_name in glyphlist:
            glyph = font.glyphs[glyph_name]
            layer = glyph.layers[mid]
            if layer is not None:
                outline_test = OutlineTest(layer, options, run_tests)
                try:
                    outline_test.checkLayer()
                    if len(outline_test.errors) > 0:
                        glyph.selected = True
                    else:
                        glyph.selected = False
                except Exception as e:
                    self.logToConsole(
                        "selectGlyphsWithErrors: Layer '%s': %s" % (glyph_name, str(e))
                    )
        font.enableUpdateInterface()

    def setRedArrowDefaults_(self, sender):
        font = Glyphs.font
        self.options["grid_length"] = font.gridLength if font else 1
        save_global, options, run_tests = self.selectGlyphsOptions(
            title="Red Arrow Preferences"
        )
        if options is None or run_tests is None:
            return

        self.options = typechecked_options(options)
        self.run_tests = run_tests
        if save_global:
            self.save_defaults(options, run_tests)
            self.load_defaults()
        else:
            # Apply changes for current session only
            self.outline_test = OutlineTest(None, self.options, self.run_tests)
            self.current_layer = None
            Glyphs.redraw()

    @objc.python_method
    def _updateOutlineCheck(self, layer):
        if (
            self.current_layer is layer
            and self.lastChangeDate >= layer.parent.lastOperationInterval()
        ):
            return
        if DEBUG and hasattr(layer, "parent"):
            self.logToConsole(
                "_updateOutlineCheck: '%s' from %s"
                % (layer.parent.name, layer.parent.parent)
            )
        self.current_layer = layer
        self.lastChangeDate = layer.parent.lastOperationInterval()
        self.errors = []
        if layer is not None and hasattr(layer, "parent"):
            # start = time()
            self.options["grid_length"] = layer.parent.parent.gridLength
            self.outline_test.layer = layer
            self.outline_test.checkLayer()
            # stop = time()
            self.errors = self.outline_test.errors
            # print(f"Updated layer check in {round((stop - start) * 1000)} ms.")
            # print("\n".join([str(e) for e in self.errors]))
        if DEBUG:
            self.logToConsole("Errors: %s" % self.errors)

    @objc.python_method
    def _drawArrow(self, position, kind, size, vector=normal_vector, level="e"):
        if vector is None:
            vector = normal_vector
        angle = atan2(vector[0], -vector[1])
        size *= 2
        head_ratio = 0.7
        w = size * 0.5
        tail_width = 0.3

        chin = 0.5 * (w - w * tail_width)  # part under the head

        if level == "e":
            arrow_color = error_color
        else:
            arrow_color = warning_color
        NSColor.colorWithCalibratedRed_green_blue_alpha_(*arrow_color).set()
        t = NSAffineTransform.transform()
        t.translateXBy_yBy_(position.x, position.y)
        t.rotateByRadians_(angle)
        myPath = NSBezierPath.alloc().init()

        myPath.moveToPoint_((0, 0))
        myPath.relativeLineToPoint_((-size * head_ratio, w * 0.5))
        myPath.relativeLineToPoint_((0, -chin))
        myPath.relativeLineToPoint_((-size * (1 - head_ratio), 0))
        myPath.relativeLineToPoint_((0, -w * tail_width))
        myPath.relativeLineToPoint_((size * (1 - head_ratio), 0))
        myPath.relativeLineToPoint_((0, -chin))
        myPath.closePath()
        myPath.transformUsingAffineTransform_(t)
        myPath.fill()

        percent = 1
        if not self.show_labels:
            percent = (
                -distance_between_points(self.mouse_position, position) / size * 2 + 2
            )
        if self.show_labels or percent > 0.2:
            self._drawTextLabel(
                transform=t,
                text=kind,
                size=size,
                vector=vector,
                percent=percent,
            )

    @objc.python_method
    def _drawTextLabel(self, transform, text, size, vector, percent=1.0):
        if text is None:
            return

        if vector is None:
            vector = normal_vector
        angle = atan2(vector[0], -vector[1])
        text_size = 0.5 * size

        attrs = {
            NSFontAttributeName: NSFont.systemFontOfSize_(text_size),
            NSForegroundColorAttributeName: text_color.colorWithAlphaComponent_(
                percent
            ),
        }
        myString = NSString.string().stringByAppendingString_(text)
        bbox = myString.sizeWithAttributes_(attrs)
        bw = bbox.width
        bh = bbox.height
        scale = self.getScale()

        text_pt = NSMakePoint(0, 0)

        if -0.5 * pi < angle <= 0.5 * pi:
            text_pt.x = -1.3 * size - bw / 2 * cos(angle) - bh / 2 * sin(angle)
        else:
            text_pt.x = -1.3 * size + bw / 2 * cos(angle) + bh / 2 * sin(angle)

        text_pt = transform.transformPoint_(text_pt)

        rr = NSRect(
            origin=(text_pt.x - bw / 2, text_pt.y - bh / 2),
            size=(bw, bh),
        )

        # Draw background box for the text label
        myRect = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            NSInsetRect(NSOffsetRect(rr, 0, -1 / scale), -6 / scale, -3 / scale),
            4 / scale,
            4 / scale,
        )

        label_background.colorWithAlphaComponent_(0.8 * percent).setFill()
        myRect.fill()

        # text_color.colorWithAlphaComponent_(0.8 * percent).setStroke()
        # myRect.setLineWidth_(0.05 * size)
        # myRect.stroke()

        myString.drawInRect_withAttributes_(rr, attrs)

    @objc.python_method
    def _drawUnspecified(self, position, kind, size, vector=normal_vector, level="e"):
        if vector is None:
            vector = normal_vector
        angle = atan2(vector[1], vector[0])
        circle_size = size * 1.3
        if level == "e":
            arrow_color = error_color
        else:
            arrow_color = warning_color
        NSColor.colorWithCalibratedRed_green_blue_alpha_(*arrow_color).set()

        t = NSAffineTransform.transform()
        t.translateXBy_yBy_(position.x, position.y)
        t.rotateByRadians_(angle)

        myPath = NSBezierPath.alloc().init()
        myPath.setLineWidth_(0)
        myPath.appendBezierPathWithOvalInRect_(
            NSMakeRect(
                position.x - 0.5 * circle_size,
                position.y - 0.5 * circle_size,
                circle_size,
                circle_size,
            )
        )
        myPath.stroke()
        percent = -distance_between_points(self.mouse_position, position) / size * 2 + 2
        if self.show_labels or percent > 0.2:
            self._drawTextLabel(
                transform=t,
                text=kind,
                size=size,
                vector=vector,
                percent=percent,
            )

    @objc.python_method
    def _drawArrows(self, debug=False):
        size = Glyphs.defaults.get(full_libkey("arrowSize"), 10) / self.getScale()
        errors_by_position = {}
        for e in self.errors:
            if e.position is not None:
                pos_key = (int(e.position.x), int(e.position.y))
                if pos_key in errors_by_position:
                    errors_by_position[pos_key].append(e)
                else:
                    errors_by_position[pos_key] = [e]
            else:
                if None in errors_by_position:
                    errors_by_position[None].append(e)
                else:
                    errors_by_position[None] = [e]
        for pos, errors in errors_by_position.items():
            message = ""
            level = "w"
            vector = normal_vector
            for e in errors:
                if e.badness is None or not debug:
                    if DEBUG:
                        if e.vector is None:
                            e.vector = normal_vector
                        message += "%s (%0.2f|%0.2f = %0.2f π), " % (
                            e.kind,
                            e.vector[0],
                            e.vector[1],
                            atan2(*e.vector) / pi,
                        )
                    else:
                        message += "%s, " % e.kind
                else:
                    message += "%s (Severity %0.1f), " % (e.kind, e.badness)
                if e.level == "e":
                    level = e.level
                if vector == normal_vector:
                    vector = e.vector
            if pos is None:
                x = 20 if self.current_layer is None else self.current_layer.width + 20
                pos = NSMakePoint(x, -10)
                self._drawUnspecified(pos, message.strip(", "), size, vector, level)
            else:
                self._drawArrow(
                    NSMakePoint(*pos), message.strip(", "), size, vector, level
                )
