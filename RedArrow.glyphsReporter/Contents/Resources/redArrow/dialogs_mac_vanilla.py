from typing import TYPE_CHECKING

from AppKit import (
    NSApp,
    NSModalPanelWindowLevel,
    NSWindowCloseButton,
    NSWindowMiniaturizeButton,
    NSWindowZoomButton,
)
from objc import super
from vanilla import Button, Window

if TYPE_CHECKING:
    from redArrow.typing import RedArrowOptionsDict


class _RAModalWindow(Window):
    nsWindowLevel = NSModalPanelWindowLevel

    okButton: Button
    closeButton: Button

    def __init__(self, *args, **kwargs) -> None:
        super(_RAModalWindow, self).__init__(*args, **kwargs)
        for button in (
            NSWindowCloseButton,
            NSWindowZoomButton,
            NSWindowMiniaturizeButton,
        ):
            self._window.standardWindowButton_(button).setHidden_(True)

    def open(self) -> None:
        super(_RAModalWindow, self).open()
        self.center()
        NSApp().runModalForWindow_(self._window)

    def windowWillClose_(self, notification) -> None:
        super(_RAModalWindow, self).windowWillClose_(notification)
        NSApp().stopModal()


class _RAbaseWindowController:
    w: _RAModalWindow | None

    def setUpBaseWindowBehavior(self) -> None:
        self._getValue = None
        self.cancelled = False

        if self.w is None:
            return

        self.w.okButton = Button(
            (-70, -30, -15, 20), "OK", callback=self.okCallback, sizeStyle="small"
        )
        self.w.setDefaultButton(self.w.okButton)

        self.w.closeButton = Button(
            (-150, -30, -80, 20),
            "Cancel",
            callback=self.closeCallback,
            sizeStyle="small",
        )
        self.w.closeButton.bind(".", ["command"])
        self.w.closeButton.bind(chr(27), [])

    def okCallback(self, _) -> None:
        if self.w is None:
            return

        self.w.close()

    def closeCallback(self, _) -> None:
        self.cancelled = True
        if self.w is None:
            return

        self.w.close()

    def get(self) -> "tuple[bool, RedArrowOptionsDict | None, list[str] | None]":
        raise NotImplementedError
