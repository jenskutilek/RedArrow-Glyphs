from math import atan2, cos, pi, sin, sqrt
from os import environ
from typing import TYPE_CHECKING

import objc
from AppKit import (
    NSAffineTransform,
    NSAlternateKeyMask,
    NSApplication,
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
    NSNotificationCenter,
    NSOffsetRect,
    NSRect,
    NSShiftKeyMask,
    NSString,
)
from GlyphsApp import MOUSEMOVED, WINDOW_MENU, Glyphs
from GlyphsApp.plugins import ReporterPlugin

from redArrow.defaults import default_checks, default_options, typechecked_options
from redArrow.outlineTestGlyphs import OutlineCheck

if TYPE_CHECKING:
    from AppKit import NSPoint
    from GlyphsApp import GSLayer

    from redArrow.outlineTestGlyphs import OutlineError, OutlineWarning
    from redArrow.typing import PointTuple, RedArrowOptionsDict


DEBUG = False


error_color = (0.9019, 0.25, 0.0, 0.85)
warning_color = (0.9019, 0.7215, 0.0, 0.85)
text_color = NSColor.textColor()
label_background = NSColor.textBackgroundColor()

normal_vector = (1, 1)


def points_distance(p0: "NSPoint", p1: "NSPoint") -> float:
    return sqrt((p1.y - p0.y) ** 2 + (p1.x - p0.x) ** 2)


class RedArrow(ReporterPlugin):
    @objc.python_method
    def settings(self) -> None:
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
        self.show_labels = Glyphs.defaults["RedArrowShowLabels"]
        self.show_labels = not (self.show_labels)
        self.toggleLabels_(None)

    @objc.python_method
    def start(self) -> None:
        if "GLYPHS_HEADLESS" not in environ:
            self.add_menu_item()
            if Glyphs.versionNumber < 4.0:
                self.add_window_menu_item()
            else:
                self.add_preferences_items()

        self.errors: list[OutlineError | OutlineWarning] = []
        self.mouse_position = NSMakePoint(0, 0)
        self.last_change_date = 0
        self.current_layer: GSLayer | None = None
        self.load_defaults()

    @objc.python_method
    def add_menu_item(self) -> None:
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
    def add_window_menu_item(self) -> None:
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
    def add_preferences_items(self) -> None:
        # Glyphs 4: Make settings editable from the Advanced Preferences dialog
        GSAdvancedPreferences = objc.lookUpClass("GSAdvancedPreferences")
        GSAdvancedPreferences.sharedAdvancedPreferences().registerEntries_forCategory_(
            [
                {
                    "title": "Implicit Extremum Points",
                    "key": "RedArrowCheckExtrema",
                    "type": "bool",
                },
                {
                    "title": "Calculate Extremum Badness",
                    "key": "RedArrowExtremaCalculateBadness",
                    "type": "bool",
                },
                {
                    "title": "Ignore Extremum Badness Below",
                    "key": "RedArrowExtremaIgnoreBadnessBelow",
                    "type": "float",
                },
                {
                    "title": "Implicit Inflection Points",
                    "key": "RedArrowCheckInflections",
                    "type": "bool",
                },
                {
                    "title": "Minimum Allowed Inflection t (0–0.5)",
                    "key": "RedArrowInflectionMin",
                    "type": "float",
                },
                {
                    "title": "Fractional Coordinates",
                    "key": "RedArrowCheckFractionalCoords",
                    "type": "bool",
                },
                {
                    "title": "Ignore .0 Fractional Values",
                    "key": "RedArrowCheckFractionalIgnorePointZero",
                    "type": "bool",
                },
                {
                    "title": "Grid Length",
                    "key": "RedArrowGridLength",
                    "type": "int",
                },
                {
                    "title": "Fractional Transformations",
                    "key": "RedArrowCheckFractionalTransform",
                    "type": "bool",
                },
                {
                    "title": "Nearly Smooth Connections",
                    "key": "RedArrowCheckSmooth",
                    "type": "bool",
                },
                {
                    "title": "Smooth Connection Tolerance",
                    "key": "RedArrowSmoothMaxDistance",
                    "type": "bool",
                },
                {
                    "title": "Zero-length Segments",
                    "key": "RedArrowCheckEmptySegments",
                    "type": "bool",
                },
                {
                    "title": "Collinear Lines",
                    "key": "RedArrowCheckCollinear",
                    "type": "bool",
                },
                {
                    "title": "Collinear Lines Tolerance",
                    "key": "RedArrowCollinearMaxDistance",
                    "type": "float",
                },
                {
                    "title": "Semi-horizontal/-vertical Segments",
                    "key": "RedArrowCheckSemiHV",
                    "type": "bool",
                },
                {
                    "title": "Minimum Length For H/V Segments",
                    "key": "RedArrowCheckSemiHVMinDistance",
                    "type": "int",
                },
                {
                    "title": "H/V Segments Tolerance",
                    "key": "RedArrowCheckSemiHVMaxDistance",
                    "type": "int",
                },
                {
                    "title": "Closepaths",
                    "key": "RedArrowCheckClosepath",
                    "type": "bool",
                },
                {
                    "title": "Short Handles",
                    "key": "RedArrowCheckZeroHandles",
                    "type": "bool",
                },
                {
                    "title": "Short Handles Tolerance",
                    "key": "RedArrowZeroHandlesMaxDistance",
                    "type": "int",
                },
                {
                    "title": "Handles Outside Bounding Box",
                    "key": "RedArrowCheckBboxHandles",
                    "type": "bool",
                },
                {
                    "title": "Short Segments",
                    "key": "RedArrowCheckShortSegments",
                    "type": "bool",
                },
                {
                    "title": "Spikes",
                    "key": "RedArrowCheckSpikes",
                    "type": "bool",
                },
                {
                    "title": "Maximum Spike Angle (radians)",
                    "key": "RedArrowSpikeAngle",
                    "type": "float",
                },
                {
                    "title": "Error color",
                    "key": "RedArrowErrorColor",
                    "type": "color",
                },
                {
                    "title": "Warning color",
                    "key": "RedArrowWarningColor",
                    "type": "color",
                },
                {
                    "title": "Ignore Warnings",
                    "key": "RedArrowIgnoreWarnings",
                    "type": "bool",
                },
            ],
            "Red Arrow",
        )

    @objc.python_method
    def load_defaults(self) -> None:
        Glyphs.registerDefaults(default_options)
        self.options: RedArrowOptionsDict = {
            k: Glyphs.defaults[k] for k in default_options
        }
        self.run_checks = Glyphs.defaults.get("RedArrowRunChecks", default_checks)
        self.outline_check = OutlineCheck(None, self.options, self.run_checks)
        self.current_layer = None
        Glyphs.redraw()

    @objc.python_method
    def save_defaults(self, options, run_checks) -> None:
        for k, v in default_options.items():
            Glyphs.defaults[k] = options.get(k, v)
        Glyphs.defaults["RedArrowRunChecks"] = run_checks

    def mouseDidMove_(self, notification) -> None:
        try:
            notification.object().window().windowController().activeEditViewController().graphicView().setNeedsDisplay_(
                True
            )
        except Exception:  # noqa: BLE001
            import traceback

            print(traceback.format_exc())

    def willActivate(self) -> None:
        try:
            if not self.show_labels:
                self.startMouseMoved()
        except Exception as e:  # noqa: BLE001
            self.logToConsole(f"willDeactivate: {e}")

    def willDeactivate(self) -> None:
        try:
            if not self.show_labels:
                self.stopMouseMoved()
        except Exception as e:  # noqa: BLE001
            self.logToConsole(f"willDeactivate: {e}")

    @objc.python_method
    def foreground(self, layer: "GSLayer | None") -> None:
        # self.logToConsole("_update_outline_check: %s" % layer)
        if layer is None:
            print("RedArrow: Plugin.foreground() called with None")
            return

        self._update_outline_check(layer)
        # self.logToConsole("foreground: Errors: %s" % self.errors )

        try:
            self.mouse_position = self.controller.graphicView().getActiveLocation_(
                Glyphs.currentEvent()
            )
        except Exception as e:  # noqa: BLE001
            self.logToConsole(f"foreground: mouse_position: {e}")
            self.mouse_position = NSMakePoint(0, 0)

        currentController = self.controller.view().window().windowController()
        if currentController:
            tool = currentController.toolDrawDelegate()
            # don't activate if on cursor tool, or pan tool
            if self.errors and not (
                tool.isKindOfClass_(NSClassFromString("GlyphsToolText"))
                or tool.isKindOfClass_(NSClassFromString("GlyphsToolHand"))
                or tool.isKindOfClass_(
                    NSClassFromString("GlyphsToolTrueTypeInstructor")
                )
            ):
                self._draw_arrows()

    def toggleLabels_(self, _) -> None:
        if self.show_labels:
            self.show_labels = False
            self.generalContextMenus = self.show_labels_menu
            self.startMouseMoved()
        else:
            self.show_labels = True
            self.generalContextMenus = self.hide_labels_menu
            self.stopMouseMoved()
        Glyphs.defaults["RedArrowShowLabels"] = self.show_labels
        Glyphs.redraw()

    def startMouseMoved(self) -> None:
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(
            self, self.mouseDidMove_, MOUSEMOVED, objc.nil
        )

    def stopMouseMoved(self) -> None:
        NSNotificationCenter.defaultCenter().removeObserver_(self)

    @objc.python_method
    def select_glyphs_options(
        self, title: str = "Select Glyphs With Errors"
    ) -> "tuple[bool, RedArrowOptionsDict | None, list[str] | None]":
        from redArrow.dialogs import SelectGlyphsWindowController

        ui = SelectGlyphsWindowController(self.options, self.run_checks, title)
        return ui.get()

    def selectGlyphsWithErrors(self) -> None:
        """
        Selects all glyphs with errors in the active layer
        """
        font = Glyphs.font
        if font is None:
            return

        self.options["RedArrowGridLength"] = font.gridLength
        save_global, options, run_checks = self.select_glyphs_options()
        if run_checks is None:
            return
        if options is None:
            return
        if save_global:
            self.save_defaults(options, run_checks)
            self.load_defaults()

        options = typechecked_options(options)

        font.disableUpdateInterface()
        mid = font.selectedFontMaster.id
        glyphlist = font.glyphs.keys()
        for glyph_name in glyphlist:
            glyph = font.glyphs[glyph_name]
            layer = glyph.layers[mid]
            if layer is not None:
                outline_check = OutlineCheck(layer, options, run_checks)
                try:
                    outline_check.check_layer()
                    if len(outline_check.errors) > 0:
                        glyph.selected = True
                    else:
                        glyph.selected = False
                except Exception as e:  # noqa: BLE001
                    self.logToConsole(
                        f"selectGlyphsWithErrors: Layer '{glyph_name}': {e}"
                    )
        font.enableUpdateInterface()

    def setRedArrowDefaults_(self, _) -> None:
        font = Glyphs.font
        self.options["RedArrowGridLength"] = font.gridLength if font else 1
        save_global, options, run_checks = self.select_glyphs_options(
            title="Red Arrow Preferences"
        )
        if options is None or run_checks is None:
            return

        self.options = typechecked_options(options)
        self.run_checks = run_checks
        if save_global:
            self.save_defaults(options, run_checks)
            self.load_defaults()
        else:
            # Apply changes for current session only
            self.outline_check = OutlineCheck(None, self.options, self.run_checks)
            self.current_layer = None
            Glyphs.redraw()

    @objc.python_method
    def _update_outline_check(self, layer: "GSLayer") -> None:
        if (
            self.current_layer is layer
            and self.last_change_date >= layer.parent.lastOperationInterval()
        ):
            return
        if DEBUG and hasattr(layer, "parent"):
            self.logToConsole(
                f"_update_outline_check: '{layer.parent.name}' from {layer.parent.parent}"
            )
        self.current_layer = layer
        self.last_change_date = layer.parent.lastOperationInterval()
        self.errors = []
        # TODO: Use Layer.gridLengthHorizontal(), Layer.gridLengthVertical()
        # See https://forum.glyphsapp.com/t/gsfont-vs-gsinterpolationfontproxy/37104/4
        if layer is not None and hasattr(layer, "parent"):
            # start = time()
            grid_length = layer.parent.parent.gridLength
            if isinstance(grid_length, (float, int)):
                self.options["RedArrowGridLength"] = grid_length
            else:
                # GSInterpolationFontProxy
                self.options["RedArrowGridLength"] = grid_length()
            self.outline_check.layer = layer
            self.outline_check.check_layer()
            # stop = time()
            self.errors = self.outline_check.errors
            # print(f"Updated layer check in {round((stop - start) * 1000)} ms.")
            # print("\n".join([str(e) for e in self.errors]))
        if DEBUG:
            self.logToConsole(f"Errors: {self.errors}")

    @objc.python_method
    def _draw_arrow(
        self,
        position: "NSPoint",
        kind: str,
        size: int,
        vector: "PointTuple | None" = normal_vector,
        level: str = "e",
    ) -> None:
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
            percent = -points_distance(self.mouse_position, position) / size * 2 + 2
        if self.show_labels or percent > 0.2:
            self._draw_text_label(
                transform=t,
                text=kind,
                size=size,
                vector=vector,
                percent=percent,
            )

    @objc.python_method
    def _draw_text_label(self, transform, text, size, vector, percent=1.0) -> None:
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
    def _draw_unspecified(
        self,
        position: "NSPoint",
        kind: str,
        size: int,
        vector: "PointTuple | None" = normal_vector,
        level: str = "e",
    ) -> None:
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
        percent = -points_distance(self.mouse_position, position) / size * 2 + 2
        if self.show_labels or percent > 0.2:
            self._draw_text_label(
                transform=t,
                text=kind,
                size=size,
                vector=vector,
                percent=percent,
            )

    @objc.python_method
    def _draw_arrows(self, debug: bool = False) -> None:
        size = Glyphs.defaults.get("RedArrowArrowSize", 10) / self.getScale()
        errors_by_position: dict[
            tuple[int, int] | None, list[OutlineError | OutlineWarning]
        ] = {}
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
            vector: PointTuple | None = normal_vector
            for e in errors:
                if e.badness is None or not debug:
                    if DEBUG:
                        if e.vector is None:
                            e.vector = normal_vector
                        message += (
                            f"{e.kind} ({e.vector[0]:02f}|{e.vector[1]:02f}) "
                            f"= {atan2(*e.vector) / pi} n), "
                        )
                    else:
                        message += f"{e.kind}, "
                else:
                    message += f"{e.kind} (Severity {e.badness:0.1f}), "
                if e.level == "e":
                    level = e.level
                if vector == normal_vector:
                    vector = e.vector
            if pos is None:
                x = 20 if self.current_layer is None else self.current_layer.width + 20
                p = NSMakePoint(x, -10)
                self._draw_unspecified(p, message.strip(", "), size, vector, level)
            else:
                self._draw_arrow(
                    NSMakePoint(*pos), message.strip(", "), size, vector, level
                )
