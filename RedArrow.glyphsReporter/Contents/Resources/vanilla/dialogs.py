import objc
from objc import selector
from Foundation import NSObject
from AppKit import *


__all__ = ["message", "askYesNoCancel", "askYesNo", "getFile", "getFolder", "getFileOrFolder", "putFile"]


class BaseMessageDialog(NSObject):

    def initWithMessageText_informativeText_alertStyle_buttonTitlesValues_window_resultCallback_(self,
        messageText="", informativeText="", alertStyle=NSInformationalAlertStyle, buttonTitlesValues=[], parentWindow=None, resultCallback=None):

        self = super(BaseMessageDialog, self).init()
        self.retain()
        self._resultCallback = resultCallback
        self._buttonTitlesValues = buttonTitlesValues
        #
        alert = NSAlert.alloc().init()
        alert.setMessageText_(messageText)
        alert.setInformativeText_(informativeText)
        alert.setAlertStyle_(alertStyle)
        for buttonTitle, value in buttonTitlesValues:
            alert.addButtonWithTitle_(buttonTitle)
        self._value = None
        if parentWindow is None:
            code = alert.runModal()
            self._translateValue(code)
        else:
            alert.beginSheetModalForWindow_modalDelegate_didEndSelector_contextInfo_(parentWindow, self, "alertDidEnd:returnCode:contextInfo:", 0)
        return self

    def _translateValue(self, code):
        if code == NSAlertFirstButtonReturn:
            value = 1
        elif code == NSAlertSecondButtonReturn:
            value = 2
        elif code == NSAlertThirdButtonReturn:
            value = 3
        else:
            value = code - NSThirdButtonReturn + 3
        self._value = self._buttonTitlesValues[value-1][1]

    def alertDidEnd_returnCode_contextInfo_(self, alert, code, context):
        alert.window().close()
        self._translateValue(code)
        if self._resultCallback is not None:
            self._resultCallback(self._value)

    alertDidEnd_returnCode_contextInfo_ = selector(alertDidEnd_returnCode_contextInfo_, signature="v@:@i@")

    def windowWillClose_(self, notification):
        self.autorelease()


class BasePutGetPanel(NSObject):

    def initWithWindow_resultCallback_(self, parentWindow=None, resultCallback=None):
        self = super(BasePutGetPanel, self).init()
        self.retain()
        self._parentWindow = parentWindow
        self._resultCallback = resultCallback
        return self

    def windowWillClose_(self, notification):
        self.autorelease()


class PutFilePanel(BasePutGetPanel):

    def initWithWindow_resultCallback_(self, parentWindow=None, resultCallback=None):
        self = super(PutFilePanel, self).initWithWindow_resultCallback_(parentWindow, resultCallback)
        self.messageText = None
        self.title = None
        self.fileTypes = None
        self.directory = None
        self.fileName = None
        self.canCreateDirectories = True
        self.accessoryView = None
        self._result = None
        return self

    def run(self):
        panel = NSSavePanel.alloc().init()
        if self.messageText:
            panel.setMessage_(self.messageText)
        if self.title:
            panel.setTitle_(self.title)
        if self.directory:
            panel.setDirectory_(self.directory)
        if self.fileTypes:
            panel.setAllowedFileTypes_(self.fileTypes)
        panel.setCanCreateDirectories_(self.canCreateDirectories)
        panel.setCanSelectHiddenExtension_(True)
        panel.setAccessoryView_(self.accessoryView)
        if self._parentWindow is not None:
            panel.beginSheetForDirectory_file_modalForWindow_modalDelegate_didEndSelector_contextInfo_(
                    self.directory, self.fileName, self._parentWindow, self, "savePanelDidEnd:returnCode:contextInfo:", 0)
        else:
            isOK = panel.runModalForDirectory_file_(self.directory, self.fileName)
            if isOK == NSOKButton:
                self._result = panel.filename()

    def savePanelDidEnd_returnCode_contextInfo_(self, panel, returnCode, context):
        panel.close()
        if returnCode:
            self._result = panel.filename()
            if self._resultCallback is not None:
                self._resultCallback(self._result)

    savePanelDidEnd_returnCode_contextInfo_ = objc.selector(savePanelDidEnd_returnCode_contextInfo_, signature="v@:@ii")


class GetFileOrFolderPanel(BasePutGetPanel):

    def initWithWindow_resultCallback_(self, parentWindow=None, resultCallback=None):
        self = super(GetFileOrFolderPanel, self).initWithWindow_resultCallback_(parentWindow, resultCallback)
        self.messageText = None
        self.title = None
        self.directory = None
        self.fileName = None
        self.fileTypes = None
        self.allowsMultipleSelection = False
        self.canChooseDirectories = True
        self.canChooseFiles = True
        self.resolvesAliases = True
        self._result = None
        return self

    def run(self):
        panel = NSOpenPanel.alloc().init()
        if self.messageText:
            panel.setMessage_(self.messageText)
        if self.title:
            panel.setTitle_(self.title)
        if self.directory:
            panel.setDirectory_(self.directory)
        if self.fileTypes:
            panel.setAllowedFileTypes_(self.fileTypes)
        panel.setCanChooseDirectories_(self.canChooseDirectories)
        panel.setCanChooseFiles_(self.canChooseFiles)
        panel.setAllowsMultipleSelection_(self.allowsMultipleSelection)
        panel.setResolvesAliases_(self.resolvesAliases)
        if self._parentWindow is not None:
            panel.beginSheetForDirectory_file_types_modalForWindow_modalDelegate_didEndSelector_contextInfo_(
                    self.directory, self.fileName, self.fileTypes, self._parentWindow, self, "openPanelDidEnd:returnCode:contextInfo:", 0)
        else:
            isOK = panel.runModalForDirectory_file_types_(self.directory, self.fileName, self.fileTypes)
            if isOK == NSOKButton:
                self._result = panel.filenames()

    def openPanelDidEnd_returnCode_contextInfo_(self, panel, returnCode, context):
        panel.close()
        if returnCode:
            self._result = panel.filenames()
            if self._resultCallback is not None:
                self._resultCallback(self._result)

    openPanelDidEnd_returnCode_contextInfo_ = objc.selector(openPanelDidEnd_returnCode_contextInfo_, signature="v@:@ii")


def _unwrapWindow(window):
    from vanilla.vanillaWindows import Window
    if window is None:
        return window
    if isinstance(window, Window):
        window = window.getNSWindow()
    return window

def message(messageText="", informativeText="", alertStyle=NSInformationalAlertStyle, parentWindow=None, resultCallback=None):
    parentWindow = _unwrapWindow(parentWindow)
    alert = BaseMessageDialog.alloc().initWithMessageText_informativeText_alertStyle_buttonTitlesValues_window_resultCallback_(
        messageText=messageText, informativeText=informativeText, alertStyle=alertStyle, buttonTitlesValues=[("OK", 1)], parentWindow=parentWindow, resultCallback=resultCallback)
    if resultCallback is None:
        return 1

def askYesNoCancel(messageText="", informativeText="", alertStyle=NSInformationalAlertStyle, parentWindow=None, resultCallback=None):
    parentWindow = _unwrapWindow(parentWindow)
    alert = BaseMessageDialog.alloc().initWithMessageText_informativeText_alertStyle_buttonTitlesValues_window_resultCallback_(
        messageText=messageText, informativeText=informativeText, alertStyle=alertStyle, buttonTitlesValues=[("Cancel", -1), ("Yes", 1), ("No", 0)], parentWindow=parentWindow, resultCallback=resultCallback)
    if resultCallback is None:
        return alert._value

def askYesNo(messageText="", informativeText="", alertStyle=NSInformationalAlertStyle, parentWindow=None, resultCallback=None):
    parentWindow = _unwrapWindow(parentWindow)
    alert = BaseMessageDialog.alloc().initWithMessageText_informativeText_alertStyle_buttonTitlesValues_window_resultCallback_(
        messageText=messageText, informativeText=informativeText, alertStyle=alertStyle, buttonTitlesValues=[("Yes", 1), ("No", 0)], parentWindow=parentWindow, resultCallback=resultCallback)
    if resultCallback is None:
        return alert._value

def getFile(messageText=None, title=None, directory=None, fileName=None, allowsMultipleSelection=False, fileTypes=None, parentWindow=None, resultCallback=None):
    parentWindow = _unwrapWindow(parentWindow)
    basePanel = GetFileOrFolderPanel.alloc().initWithWindow_resultCallback_(parentWindow, resultCallback)
    basePanel.messageText = messageText
    basePanel.title = title
    basePanel.directory = directory
    basePanel.fileName = fileName
    basePanel.fileTypes = fileTypes
    basePanel.allowsMultipleSelection = allowsMultipleSelection
    basePanel.canChooseDirectories = False
    basePanel.canChooseFiles = True
    basePanel.run()
    if resultCallback is None:
        return basePanel._result

def getFolder(messageText=None, title=None, directory=None, allowsMultipleSelection=False, parentWindow=None, resultCallback=None):
    parentWindow = _unwrapWindow(parentWindow)
    basePanel = GetFileOrFolderPanel.alloc().initWithWindow_resultCallback_(parentWindow, resultCallback)
    basePanel.messageText = messageText
    basePanel.title = title
    basePanel.directory = directory
    basePanel.allowsMultipleSelection = allowsMultipleSelection
    basePanel.canChooseDirectories = True
    basePanel.canChooseFiles = False
    basePanel.run()
    if resultCallback is None:
        return basePanel._result

def getFileOrFolder(messageText=None, title=None, directory=None, fileName=None, allowsMultipleSelection=False, fileTypes=None, parentWindow=None, resultCallback=None):
    parentWindow = _unwrapWindow(parentWindow)
    basePanel = GetFileOrFolderPanel.alloc().initWithWindow_resultCallback_(parentWindow, resultCallback)
    basePanel.messageText = messageText
    basePanel.title = title
    basePanel.directory = directory
    basePanel.fileName = fileName
    basePanel.fileTypes = fileTypes
    basePanel.allowsMultipleSelection = allowsMultipleSelection
    basePanel.canChooseDirectories = True
    basePanel.canChooseFiles = True
    basePanel.run()
    if resultCallback is None:
        return basePanel._result

def putFile(messageText=None, title=None, directory=None, fileName=None, canCreateDirectories=True, fileTypes=None, parentWindow=None, resultCallback=None, accessoryView=None):
    parentWindow = _unwrapWindow(parentWindow)
    basePanel = PutFilePanel.alloc().initWithWindow_resultCallback_(parentWindow, resultCallback)
    basePanel.messageText = messageText
    basePanel.title = title
    basePanel.directory = directory
    basePanel.fileName = fileName
    basePanel.fileTypes = fileTypes
    basePanel.canCreateDirectories = canCreateDirectories
    basePanel.accessoryView = accessoryView
    basePanel.run()
    if resultCallback is None:
        return basePanel._result

