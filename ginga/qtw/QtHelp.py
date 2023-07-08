#
# QtHelp.py -- customized Qt widgets and convenience functions
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import glob
import os
import math
import weakref
import time

import ginga.toolkit
from ginga.util import iohelper
from ginga.misc import Callback, Bunch
from ginga.fonts import font_asst

configured = False

toolkit = ginga.toolkit.toolkit

# if user wants to force a toolkit
if toolkit == 'qt6':
    os.environ['QT_API'] = 'pyqt6'

elif toolkit == 'qt5':
    os.environ['QT_API'] = 'pyqt5'

elif toolkit == 'pyside6':
    os.environ['QT_API'] = 'pyside6'

elif toolkit == 'pyside2':
    os.environ['QT_API'] = 'pyside2'

have_pyqt5 = False
have_pyqt6 = False
have_pyside2 = False
have_pyside6 = False
qtpy_import_error = ""

try:
    from qtpy import QtCore
    from qtpy import QtWidgets as QtGui
    from qtpy.QtGui import (QImage, QColor, QFont, QPixmap, QIcon,  # noqa
                            QPainter, QPen, QPolygonF, QPolygon, QTextCursor,
                            QDrag, QPainterPath, QBrush, QFontDatabase,
                            QCursor, QFontMetrics, QSurfaceFormat,
                            QMouseEvent, QDrag)
    from qtpy.QtWidgets import QOpenGLWidget  # noqa
    from qtpy.QtCore import QItemSelectionModel  # noqa
    from qtpy.QtWidgets import QApplication  # noqa
    ## try:
    ##     from qtpy import sip
    ## except ImportError as e:
    ##     import sip
    try:
        from qtpy.QtWebEngineWidgets import QWebEngineView as QWebView  # noqa
    except ImportError as e:
        pass

    # Let's see what qtpy configured for us...
    from qtpy import PYQT5, PYQT6, PYSIDE2, PYSIDE6
    have_pyqt5 = PYQT5
    have_pyqt6 = PYQT6
    have_pyside2 = PYSIDE2
    have_pyside6 = PYSIDE6

    configured = True
except ImportError as e:
    qtpy_import_error = "Error importing 'qtpy': {}".format(e)
    # for debugging purposes, uncomment this to get full traceback
    #raise e

if have_pyqt6:
    ginga.toolkit.use('qt6')
    os.environ['QT_API'] = 'pyqt6'
elif have_pyqt5:
    ginga.toolkit.use('qt5')
    os.environ['QT_API'] = 'pyqt5'
elif have_pyside6:
    ginga.toolkit.use('pyside6')
    os.environ['QT_API'] = 'pyside6'
elif have_pyside2:
    ginga.toolkit.use('pyside2')
    os.environ['QT_API'] = 'pyside2'
else:
    raise ImportError("Failed to configure qt5, qt6, pyside2 or pyside6. "
                      "Is the 'qtpy' package installed? (%s)" % (
                          qtpy_import_error))


tabwidget_style = """
QTabWidget::pane { margin: 0px,0px,0px,0px; padding: 0px; }
QMdiSubWindow { margin: 0px; padding: 2px; }
"""


class TopLevel(QtGui.QWidget):

    app = None
    ## def __init__(self, *args, **kwdargs):
    ##     return super(TopLevel, self).__init__(self, *args, **kwdargs)

    def closeEvent(self, event):
        if not (self.app is None):
            self.app.quit()

    def setApp(self, app):
        self.app = app


class ComboBox(QtGui.QComboBox):

    def insert_alpha(self, text):
        index = 0
        while True:
            itemText = self.itemText(index)
            if len(itemText) == 0:
                break
            if itemText > text:
                self.insertItem(index, text)
                return
            index += 1
        self.addItem(text)

    def delete_alpha(self, text):
        index = self.findText(text)
        self.removeItem(index)

    def show_text(self, text):
        index = self.findText(text)
        self.setCurrentIndex(index)

    def append_text(self, text):
        self.addItem(text)


class VBox(QtGui.QWidget):
    def __init__(self, *args, **kwdargs):
        super(VBox, self).__init__(*args, **kwdargs)

        layout = QtGui.QVBoxLayout()
        # because of ridiculous defaults
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def addWidget(self, w, **kwdargs):
        self.layout().addWidget(w, **kwdargs)

    def setSpacing(self, val):
        self.layout().setSpacing(val)


class HBox(QtGui.QWidget):
    def __init__(self, *args, **kwdargs):
        super(HBox, self).__init__(*args, **kwdargs)

        layout = QtGui.QHBoxLayout()
        # because of ridiculous defaults
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def addWidget(self, w, **kwdargs):
        self.layout().addWidget(w, **kwdargs)

    def setSpacing(self, val):
        self.layout().setSpacing(val)


# See https://stackoverflow.com/questions/48901854/is-it-possible-to-drag-a-qtabwidget-and-open-a-new-window-containing-whats-in-t
class DetachableTabWidget(QtGui.QTabWidget):
    def __init__(self, parent=None):
        QtGui.QTabWidget.__init__(self, parent)

        self._tabBar = self.TabBar(self)
        self._tabBar.onDetachTabSignal.connect(self.detachTab)
        self._tabBar.onMoveTabSignal.connect(self.moveTab)

        self.setTabBar(self._tabBar)

    #  Move a tab from one position (index) to another
    #
    #  @param    fromIndex    the original index location of the tab
    #  @param    toIndex      the new index location of the tab
    @QtCore.Slot(int, int)
    def moveTab(self, fromIndex, toIndex):
        widget = self.widget(fromIndex)
        icon = self.tabIcon(fromIndex)
        text = self.tabText(fromIndex)

        self.removeTab(fromIndex)
        self.insertTab(toIndex, widget, icon, text)
        self.setCurrentIndex(toIndex)

    #  Detach the tab by removing it's contents and placing them in
    #  a DetachedTab dialog
    #
    #  @param    index    the index location of the tab to be detached
    #  @param    point    the screen position for creating the new
    #                     DetachedTab dialog
    @QtCore.Slot(int, QtCore.QPoint)
    def detachTab(self, index, point):

        # Get the tab content
        name = self.tabText(index)
        icon = self.tabIcon(index)
        if icon.isNull():
            icon = self.window().windowIcon()
        contentWidget = self.widget(index)
        contentWidgetRect = contentWidget.frameGeometry()

        # Create a new detached tab window
        detachedTab = self.DetachedTab(contentWidget, self.parentWidget())
        detachedTab.setWindowModality(QtCore.Qt.NonModal)
        detachedTab.setWindowTitle(name)
        detachedTab.setWindowIcon(icon)
        detachedTab.setObjectName(name)
        detachedTab.setGeometry(contentWidgetRect)
        detachedTab.onCloseSignal.connect(self.attachTab)
        detachedTab.move(point)
        detachedTab.show()

    #  Re-attach the tab by removing the content from the DetachedTab dialog,
    #  closing it, and placing the content back into the DetachableTabWidget
    #
    #  @param    contentWidget    the content widget from the DetachedTab dialog
    #  @param    name             the name of the detached tab
    #  @param    icon             the window icon for the detached tab
    @QtCore.Slot(QtGui.QWidget, type(''), QIcon)
    def attachTab(self, contentWidget, name, icon):

        # Make the content widget a child of this widget
        contentWidget.setParent(self)

        # Create an image from the given icon
        if not icon.isNull() and len(list(icon.availableSizes())) > 0:
            tabIconPixmap = icon.pixmap(icon.availableSizes()[0])
            tabIconImage = tabIconPixmap.toImage()
        else:
            tabIconImage = None

        # Create an image of the main window icon
        if not icon.isNull() and len(list(icon.availableSizes())) > 0:
            windowIconPixmap = self.window().windowIcon().pixmap(icon.availableSizes()[0])
            windowIconImage = windowIconPixmap.toImage()
        else:
            windowIconImage = None

        # Determine if the given image and the main window icon are the same.
        # If they are, then do not add the icon to the tab
        if tabIconImage == windowIconImage:
            index = self.addTab(contentWidget, name)
        else:
            index = self.addTab(contentWidget, icon, name)

        # Make this tab the current tab
        if index > -1:
            self.setCurrentIndex(index)

    #  When a tab is detached, the contents are placed into this QDialog.
    # The tab can be re-attached by closing the dialog or by double clicking
    # on its window frame.
    class DetachedTab(QtGui.QDialog):
        onCloseSignal = QtCore.Signal(QtGui.QWidget, type(''), QIcon)

        def __init__(self, contentWidget, parent=None):
            QtGui.QDialog.__init__(self, parent)

            layout = QtGui.QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            self.contentWidget = contentWidget
            layout.addWidget(self.contentWidget)
            self.contentWidget.show()
            self.setWindowFlags(QtCore.Qt.Window)

        #  Capture a double click event on the dialog's window frame
        #
        #  @param    event    an event
        #  @return            true if the event was recognized
        def event(self, event):

            # If the event type is a double click then close the dialog
            if event.type() == QtCore.QEvent.NonClientAreaMouseButtonDblClick:
                event.accept()
                self.close()

            return QtGui.QDialog.event(self, event)

        #  If the dialog is closed, emit the onCloseSignal and give the
        #  content widget back to the DetachableTabWidget
        #
        #  @param    event    a close event
        def closeEvent(self, event):
            self.onCloseSignal.emit(self.contentWidget, self.objectName(),
                                    self.windowIcon())

    # The TabBar class re-implements some of the functionality of the
    # QTabBar widget
    class TabBar(QtGui.QTabBar):
        onDetachTabSignal = QtCore.Signal(int, QtCore.QPoint)
        onMoveTabSignal = QtCore.Signal(int, int)

        def __init__(self, parent=None):
            QtGui.QTabBar.__init__(self, parent)

            self.setAcceptDrops(True)
            self.setElideMode(QtCore.Qt.ElideRight)
            self.setSelectionBehaviorOnRemove(QtGui.QTabBar.SelectLeftTab)

            self.dragStartPos = QtCore.QPoint()
            self.dragDroppedPos = QtCore.QPoint()
            self.mouseCursor = QCursor()
            self.dragInitiated = False

        # Send the onDetachTabSignal when a tab is double clicked
        #
        #  @param    event    a mouse double click event
        def mouseDoubleClickEvent(self, event):
            event.accept()
            self.onDetachTabSignal.emit(self.tabAt(event.pos()),
                                        self.mouseCursor.pos())

        # Set the starting position for a drag event when the mouse
        # button is pressed
        #
        #  @param    event    a mouse press event
        def mousePressEvent(self, event):
            if event.button() == QtCore.Qt.LeftButton:
                self.dragStartPos = event.pos()

            self.dragDroppedPos.setX(0)
            self.dragDroppedPos.setY(0)

            self.dragInitiated = False

            QtGui.QTabBar.mousePressEvent(self, event)

        # Determine if the current movement is a drag.  If it is, convert
        # it into a QDrag.  If the drag ends inside the tab bar, emit an
        # onMoveTabSignal.  If the drag ends outside the tab bar,
        # emit an onDetachTabSignal.
        #
        #  @param    event    a mouse move event
        def mouseMoveEvent(self, event):

            # Determine if the current movement is detected as a drag.
            if (not self.dragStartPos.isNull() and
                ((event.pos() - self.dragStartPos).manhattanLength() > QApplication.startDragDistance() * 2)):

                self.dragInitiated = True

            # If the current movement is a drag initiated by the left button
            if (((event.buttons() & QtCore.Qt.LeftButton)) and self.dragInitiated):

                # Stop the move event
                pos = getattr(event, 'position', event.pos)()
                pos = pos.__class__(self.dragStartPos.x(),
                                    self.dragStartPos.y())
                finishMoveEvent = QMouseEvent(QtCore.QEvent.MouseMove,
                                              pos,
                                              QtCore.Qt.NoButton,
                                              QtCore.Qt.NoButton,
                                              QtCore.Qt.NoModifier)
                QtGui.QTabBar.mouseMoveEvent(self, finishMoveEvent)

                # Convert the move event into a drag
                drag = QDrag(self)
                mimeData = QtCore.QMimeData()
                mimeData.setData('action', b'application/tab-detach')
                drag.setMimeData(mimeData)

                # Create the appearance of dragging the tab content
                pixmap = self.parentWidget().grab()
                targetPixmap = QPixmap(pixmap.size())
                targetPixmap.fill(QtCore.Qt.transparent)
                painter = QPainter(targetPixmap)
                painter.setOpacity(0.85)
                painter.drawPixmap(0, 0, pixmap)
                painter.end()
                drag.setPixmap(targetPixmap)

                # Initiate the drag
                dropAction = drag.exec_(QtCore.Qt.MoveAction |
                                        QtCore.Qt.CopyAction)

                # if the drag completed outside of the tab bar, detach
                # the tab and move the content to the current cursor position
                if dropAction == QtCore.Qt.IgnoreAction:
                    event.accept()
                    self.onDetachTabSignal.emit(self.tabAt(self.dragStartPos),
                                                self.mouseCursor.pos())

                # else if the drag completed inside the tab bar, move the
                # selected tab to the new position
                elif dropAction == QtCore.Qt.MoveAction:
                    if not self.dragDroppedPos.isNull():
                        event.accept()
                        self.onMoveTabSignal.emit(self.tabAt(self.dragStartPos),
                                                  self.tabAt(self.dragDroppedPos))
            else:
                QtGui.QTabBar.mouseMoveEvent(self, event)

        # Determine if the drag has entered a tab position from
        # another tab position
        #
        #  @param    event    a drag enter event
        def dragEnterEvent(self, event):
            mimeData = event.mimeData()
            formats = mimeData.formats()

            if ('action' in formats and
                mimeData.data('action') == 'application/tab-detach'):
                event.acceptProposedAction()

            QtGui.QTabBar.dragMoveEvent(self, event)

        #  Get the position of the end of the drag
        #
        #  @param    event    a drop event
        def dropEvent(self, event):
            event.setDropAction(QtCore.Qt.MoveAction)
            event.accept()
            self.dragDroppedPos = getattr(event, 'position', event.pos)()
            QtGui.QTabBar.dropEvent(self, event)


class FileSelection(object):
    """Handle Load Image file dialog from File menu."""
    # TODO: deprecate the functionality when all_at_once == False
    # and make the default to be True
    def __init__(self, parent_w, all_at_once=False):
        self.parent = parent_w
        self.all_at_once = all_at_once
        self.cb = None

    def popup(self, title, callfn, initialdir=None, filename=None):
        """Let user select and load file(s). This allows wildcards and
        extensions, like in FBrowser.

        Parameters
        ----------
        title : str
            Title for the file dialog.

        callfn : func
            Function used to open the file(s).

        initialdir : str or `None`
            Directory for file dialog.

        filename : str
            Filter for file dialog.

        """
        self.cb = callfn
        filenames = QtGui.QFileDialog.getOpenFileNames(
            self.parent, title, initialdir, filename)

        # Special handling for PyQt5, see
        # https://www.reddit.com/r/learnpython/comments/2xhagb/pyqt5_trouble_with_openinggetting_the_name_of_the/
        filenames = filenames[0]

        all_paths = []
        for filename in filenames:

            # Special handling for wildcard or extension.
            # This is similar to open_files() in FBrowser plugin.
            if '*' in filename or '[' in filename:
                info = iohelper.get_fileinfo(filename)
                ext = iohelper.get_hdu_suffix(info.numhdu)
                files = glob.glob(info.filepath)  # Expand wildcard
                paths = ['{0}{1}'.format(f, ext) for f in files]
                if self.all_at_once:
                    all_paths.extend(paths)
                else:
                    for path in paths:
                        self.cb(path)

            else:
                # Normal load
                if self.all_at_once:
                    all_paths.append(filename)
                else:
                    self.cb(filename)

        if self.all_at_once and len(all_paths) > 0:
            self.cb(all_paths)


class DirectorySelection(object):
    """Handle directory selection dialog."""
    def __init__(self, parent_w):
        self.parent = parent_w
        self.cb = None

    def popup(self, title, callfn, initialdir=None):
        """Let user select a directory.

        Parameters
        ----------
        title : str
            Title for the dialog.

        callfn : func
            Function used to handle selected directory.

        initialdir : str or `None`
            Directory for dialog.

        """
        self.cb = callfn
        dirname = QtGui.QFileDialog.getExistingDirectory(
            self.parent, title, initialdir)
        if dirname:
            self.cb(dirname)


class Timer(Callback.Callbacks):
    """Abstraction of a GUI-toolkit implemented timer."""

    def __init__(self, duration=0.0):
        """Create a timer set to expire after `duration` sec.
        """
        super(Timer, self).__init__()

        self.duration = duration
        # For storing aritrary data with timers
        self.data = Bunch.Bunch()

        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.setTimerType(QtCore.Qt.PreciseTimer)
        self.timer.timeout.connect(self._expired_cb)
        self.start_time = 0.0
        self.deadline = 0.0

        for name in ('expired', 'canceled'):
            self.enable_callback(name)

    def start(self, duration=None):
        """Start the timer.  If `duration` is not None, it should
        specify the time to expiration in seconds.
        """
        if duration is None:
            duration = self.duration

        self.set(duration)

    def set(self, duration):
        self.stop()

        self.start_time = time.time()
        self.deadline = self.start_time + duration
        # QTimer set in milliseconds
        ms = int(duration * 1000.0)
        self.timer.start(ms)

    def _expired_cb(self):
        self.make_callback('expired')

    def is_set(self):
        return self.timer.isActive()

    def cond_set(self, time_sec):
        if not self.is_set():
            # TODO: probably a race condition here
            self.set(time_sec)

    def elapsed_time(self):
        return time.time() - self.start_time

    def time_left(self):
        #return max(0.0, self.deadline - time.time())
        # remainingTime() returns value in msec, or -1 if timer is not set
        t = self.timer.remainingTime()
        t = max(0.0, t)
        return t / 1000.0

    def get_deadline(self):
        return self.deadline

    def stop(self):
        try:
            self.timer.stop()
        except Exception:
            pass

    def cancel(self):
        """Cancel this timer.  If the timer is not running, there
        is no error.
        """
        self.stop()
        self.make_callback('canceled')

    clear = cancel


def cmap2pixmap(cmap, steps=50):
    """Convert a Ginga colormap into a QPixmap
    """
    import numpy as np

    inds = np.linspace(0, 1, steps)
    n = len(cmap.clst) - 1
    tups = [cmap.clst[int(x * n)] for x in inds]
    rgbas = [QColor(int(r * 255), int(g * 255),
                    int(b * 255), 255).rgba() for r, g, b in tups]
    im = QImage(steps, 1, QImage.Format_Indexed8)
    im.setColorTable(rgbas)
    for i in range(steps):
        im.setPixel(i, 0, i)
    im = im.scaled(128, 32)
    pm = QPixmap.fromImage(im)
    return pm


def get_scroll_info(event):
    """
    Returns the (degrees, direction) of a scroll motion Qt event.
    """

    # 15 deg is standard 1-click turn for a wheel mouse
    # TODO: use pixelDelta() for better handling on hi-res devices?
    point = event.angleDelta()
    dx, dy = point.x(), point.y()
    delta = math.sqrt(dx ** 2 + dy ** 2)
    if dy < 0:
        delta = -delta

    ang_rad = math.atan2(dy, dx)
    direction = math.degrees(ang_rad) - 90.0
    direction = math.fmod(direction + 360.0, 360.0)

    num_degrees = abs(delta) / 8.0

    return (num_degrees, direction)


def get_icon(iconpath, size=None):
    image = QImage(iconpath)
    if size is not None:
        qsize = QtCore.QSize(*size)
        image = image.scaled(qsize)
    pixmap = QPixmap.fromImage(image)
    iconw = QIcon(pixmap)
    return iconw


def get_cached_font(font_name, font_size):
    key = ('qt', font_name, font_size)
    try:
        return font_asst.get_cache(key)

    except KeyError:
        pass

    # font not loaded? try and load it
    try:
        info = font_asst.get_font_info(font_name, subst_ok=False)
        font_family = load_font(font_name, info.font_path)
        font = QFont(font_family, font_size)
        font.setStyleStrategy(QFont.PreferAntialias)
        font_asst.add_cache(key, font)

    except KeyError:
        pass

    # see if we can build the font from the name
    try:
        font = QFont(font_name, font_size)
        font_asst.add_cache(key, font)
        return font

    except Exception:
        pass

    # try and substitute one of the built in fonts
    info = font_asst.get_font_info(font_name, subst_ok=True)
    font_family = load_font(font_name, info.font_path)
    font = QFont(font_family, font_size)
    font.setStyleStrategy(QFont.PreferAntialias)
    font_asst.add_cache(key, font)

    return font


# holds mapping of Qt font names to "ginga" font names
qt_fonts = dict()


def get_font(font_name, font_size):
    font_name = font_asst.resolve_alias(font_name, font_name)
    return get_cached_font(font_name, font_size)


def load_font(font_name, font_file):
    global qt_fonts
    if font_name in qt_fonts:
        # <-- this font is already loaded, just look up Qt's name for it
        font_family = qt_fonts[font_name]
        return font_family

    # NOTE: you need to have created a QApplication() first (see
    # qtw.Widgets.Application) for this to work correctly, or you will get
    # a crash!
    font_id = QFontDatabase.addApplicationFont(font_file)
    if font_id < 0:
        raise ValueError("Unspecified Qt problem loading font from '%s'" % (
            font_file))

    font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
    qt_fonts[font_name] = font_family

    if font_name != font_family:
        # If Qt knows this under a different name, add an alias
        #print("overriding alias '{}' with '{}'".format(font_name, font_family))
        font_asst.add_alias(font_family, font_name)

    return font_family


# cache of QPainters for surfaces
_painters = weakref.WeakKeyDictionary()


def get_painter(surface):
    # QImage is not hashable
    if not isinstance(surface, QImage):
        if surface in _painters:
            return _painters[surface]

    painter = QPainter(surface)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.TextAntialiasing)
    if not isinstance(surface, QImage):
        _painters[surface] = painter
    return painter


def set_default_opengl_context():
    from ginga.opengl.glsl import req
    fmt = QSurfaceFormat()
    fmt.setVersion(req.major, req.minor)
    fmt.setProfile(QSurfaceFormat.CoreProfile)
    fmt.setDefaultFormat(fmt)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)


def delete_widget(w):
    ## sip.delete(w)
    w.deleteLater()


# END
