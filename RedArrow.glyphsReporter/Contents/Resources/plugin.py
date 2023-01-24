import objc

from geometry_functions import distance_between_points
from GlyphsApp import Glyphs, MOUSEMOVED
from GlyphsApp.plugins import ReporterPlugin
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
    NSMakeRect,
    NSMenuItem,
    # NSMutableParagraphStyle,
    NSPoint,
    NSRect,
    NSShiftKeyMask,
    NSString,
    NSNotificationCenter,
)
from math import atan2, cos, pi, sin
from outlineTestGlyphs import OutlineTest


plugin_id = "de.kutilek.RedArrow"
DEBUG = False


error_color = (0.9019, 0.25, 0.0, 0.85)
warning_color = (0.9019, 0.7215, 0.0, 0.85)
text_color = (0.4, 0.4, 0.6, 0.7)


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
        self.options = {
            "extremum_calculate_badness": False,
            "extremum_ignore_badness_below": 0,
            "smooth_connection_max_distance": 4,
            "fractional_ignore_point_zero": True,
            "collinear_vectors_max_distance": 2,
            # "test_closepath": False,
            "grid_length": 1,
            "inflection_min": 0.3,
            "inflection_max": 0.7,
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
            # "test_closepath",
            "test_zero_handles",
        ]
        self.errors = []
        self.mouse_position = (0, 0)
        self.lastChangeDate = 0
        self.current_layer = None
        self.vanilla_alerted = False

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
            self.mouse_position = (0, 0)

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
        Glyphs.defaults["%s.showLabels" % plugin_id] = self.show_labels
        Glyphs.redraw()

    def startMouseMoved(self):
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(
            self, self.mouseDidMove_, MOUSEMOVED, objc.nil
        )

    def stopMouseMoved(self):
        NSNotificationCenter.defaultCenter().removeObserver_(self)

    def selectGlyphsOptions(self):
        try:
            from raDialogs import SelectGlyphsWindowController
        except ImportError:
            if not self.vanilla_alerted:
                print(
                    "Please install vanilla to enable UI dialogs for "
                    "RedArrow. You can install vanilla through Glyphs > "
                    "Preferences > Addons > Modules."
                )
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
        font = Glyphs.font
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
        outline_test_pen = OutlineTest(font, options, run_tests)
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
                    self.logToConsole(
                        "selectGlyphsWithErrors: Layer '%s': %s" % (glyph_name, str(e))
                    )
        font.enableUpdateInterface()

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
            self.options["grid_length"] = layer.parent.parent.gridLength
            outline_test_pen = OutlineTest(
                layer.parent.parent, self.options, self.run_tests
            )
            layer.drawPoints(outline_test_pen)
            self.errors = outline_test_pen.errors
        if DEBUG:
            self.logToConsole("Errors: %s" % self.errors)

    @objc.python_method
    def _drawArrow(self, position, kind, size, vector=(-1, 1), level="e"):
        if vector is None:
            vector = (-1, 1)
        angle = atan2(vector[0], -vector[1])
        size *= 2
        x, y = position
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
        t.translateXBy_yBy_(x, y)
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
            vector = (-1, 1)
        angle = atan2(vector[0], -vector[1])
        text_size = 0.5 * size

        # para_style = NSMutableParagraphStyle.alloc().init()
        # para_style.setAlignment_(NSCenterTextAlignment)

        attrs = {
            NSFontAttributeName: NSFont.systemFontOfSize_(text_size),
            NSForegroundColorAttributeName: NSColor.colorWithCalibratedRed_green_blue_alpha_(
                text_color[0],
                text_color[1],
                text_color[2],
                text_color[3] * percent,
            ),
            # NSParagraphStyleAttributeName:  para_style,
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

        rr = NSRect(origin=(text_pt.x - bw / 2, text_pt.y - bh / 2), size=(bw, bh))

        if DEBUG:
            NSColor.colorWithCalibratedRed_green_blue_alpha_(0, 0, 0, 0.15).set()
            myRect = NSBezierPath.bezierPathWithRect_(rr)
            myRect.setLineWidth_(0.05 * size)
            myRect.stroke()

        myString.drawInRect_withAttributes_(rr, attrs)

        # myString.drawAtPoint_withAttributes_(
        # 	text_pt,
        # 	attrs
        # )

    @objc.python_method
    def _drawUnspecified(self, position, kind, size, vector=(-1, 1), level="e"):
        if vector is None:
            vector = (-1, 1)
        angle = atan2(vector[1], vector[0])
        circle_size = size * 1.3
        x, y = position
        if level == "e":
            arrow_color = error_color
        else:
            arrow_color = warning_color
        NSColor.colorWithCalibratedRed_green_blue_alpha_(*arrow_color).set()

        t = NSAffineTransform.transform()
        t.translateXBy_yBy_(x, y)
        t.rotateByRadians_(angle)

        myPath = NSBezierPath.alloc().init()
        myPath.setLineWidth_(0)
        myPath.appendBezierPathWithOvalInRect_(
            NSMakeRect(
                x - 0.5 * circle_size,
                y - 0.5 * circle_size,
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
            message = ""
            for e in errors:
                if e.badness is None or not debug:
                    if DEBUG:
                        if e.vector is None:
                            e.vector = (1, 1)
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
            if pos is None:
                pos = (self.current_layer.width + 20, -10)
                self._drawUnspecified(pos, message.strip(", "), size, e.vector, e.level)
            else:
                self._drawArrow(pos, message.strip(", "), size, e.vector, e.level)
