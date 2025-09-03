# encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from AppKit import (
    NSApp,
    NSModalPanelWindowLevel,
    NSWindowCloseButton,
    NSWindowMiniaturizeButton,
    NSWindowZoomButton,
)
from objc import super
from vanilla import Button, Window


class _RAModalWindow(Window):
    nsWindowLevel = NSModalPanelWindowLevel

    def __init__(self, *args, **kwargs):
        super(_RAModalWindow, self).__init__(*args, **kwargs)
        for button in (
            NSWindowCloseButton,
            NSWindowZoomButton,
            NSWindowMiniaturizeButton,
        ):
            self._window.standardWindowButton_(button).setHidden_(True)

    def open(self):
        super(_RAModalWindow, self).open()
        self.center()
        NSApp().runModalForWindow_(self._window)

    def windowWillClose_(self, notification):
        super(_RAModalWindow, self).windowWillClose_(notification)
        NSApp().stopModal()


class _RAbaseWindowController(object):
    def setUpBaseWindowBehavior(self):
        self._getValue = None

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

        self.cancelled = False

    def okCallback(self, sender):
        self.w.close()

    def closeCallback(self, sender):
        self.cancelled = True
        self.w.close()

    def get(self):
        raise NotImplementedError
