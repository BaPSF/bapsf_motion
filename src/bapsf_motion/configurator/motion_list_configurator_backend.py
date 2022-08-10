__all__ = ["Canvas"]
import math
import numpy as np
import os
import tomli
import tomli_w

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

MODES = ["line", "polyline", "rect", "barrier", "circle", "ellipse"]
GRIDS = ["rect", "circle", "ellipse", "sphere"]

CANVAS_DIMENSIONS = 600, 600

SELECTION_PEN = QPen(QColor(0xFF, 0xFF, 0xFF), 1, Qt.DashLine)
PREVIEW_PEN = QPen(QColor(0xFF, 0xFF, 0xFF), 1, Qt.SolidLine)


class Canvas(QLabel):
    """
    This class controls the "canvas" where one can draw the shapes to
    define data acquisition regions in 2D (3D with z-axis extrusion).
    """

    mode = "rect"
    grid = "rect"

    primary_color = QColor(Qt.blue)
    # Store configuration settings, including pen width, fonts etc.
    config = {
        # Drawing options.
        "size": 1,
        "fill": True,
    }
    active_color = "#000000"
    preview_pen = None
    timer_event = None
    move = pyqtSignal()

    def initialize(self):
        self.background_color = QColor(Qt.gray)
        self.eraser_color = QColor(Qt.white)
        self.last_pos = None
        self.eraser_color.setAlpha(100)
        self.grid_spacing = 10  # 5pix per cm
        self.hand = 0
        self.plasmacolumn = True
        self.maincathode = False
        self.secondarycathode = False
        self.alpha = np.pi / 4
        self.xpos = []
        self.ypos = []
        self.nx = [10]
        self.ny = [10]
        self.nz = [1]
        self.z1 = 1
        self.z2 = 1
        self.poslist = []
        self.barlist = []
        self.cx = 0
        self.cy = 0
        self.bar = 0
        self.centers = ""
        self.closeit = False
        self.eccentricity = 0.5
        self.modelist = []
        self.reslist = []
        self.reset()
        self.oldpixmap = self.pixmap()
        p = QPainter(self.pixmap())

        xs = np.arange(50, 550, self.grid_spacing)
        ys = np.arange(50, 550, self.grid_spacing)

        p.setBrush(QBrush(QColor(Qt.white)))

        p.setPen(
            QPen(
                QColor(Qt.black),
                self.config["size"],
                Qt.SolidLine,
                Qt.RoundCap,
                Qt.RoundJoin,
            )
        )
        p.setOpacity(1)
        p.drawEllipse(QPointF(300, 300), 250, 250)
        if self.hand == 0:
            p.drawRect(QRectF(550, 290, 10, 20))
            p.drawLine(290, 50, 560, 310)
            p.drawLine(290, 550, 560, 290)
        elif self.hand == 1:
            p.drawRect(QRectF(50, 290, -10, 20))
            p.drawLine(290, 50, 40, 310)
            p.drawLine(290, 550, 40, 290)
        p.setPen(
            QPen(
                QColor(Qt.green),
                self.config["size"],
                Qt.SolidLine,
                Qt.RoundCap,
                Qt.RoundJoin,
            )
        )
        p.setOpacity(0.2)
        for x in xs:
            p.drawLine(
                QPointF(x, 300 + np.sqrt(250**2 - (x - 300) ** 2)),
                QPointF(x, 300 - np.sqrt(250**2 - (x - 300) ** 2)),
            )
        for y in ys:
            p.drawLine(
                QPointF(300 + np.sqrt(250**2 - (y - 300) ** 2), y),
                QPointF(300 - np.sqrt(250**2 - (y - 300) ** 2), y),
            )
        p.setPen(
            QPen(
                QColor(Qt.red),
                self.config["size"],
                Qt.SolidLine,
                Qt.RoundCap,
                Qt.RoundJoin,
            )
        )
        p.setOpacity(0.4)
        p.drawEllipse(QPoint(300, 300), 150, 150)

        p.setPen(
            QPen(
                QColor(Qt.black),
                self.config["size"],
                Qt.SolidLine,
                Qt.RoundCap,
                Qt.RoundJoin,
            )
        )
        p.setOpacity(1)

        p.setBrush(QBrush(QColor(Qt.red)))
        p.drawEllipse(QPointF(300, 300), 1, 1)

        p.end()
        self.update()

    def reset(self):
        """Reset the canvas, and associated data."""
        # Create the pixmap for display.
        self.setPixmap(QPixmap(*CANVAS_DIMENSIONS))

        # Clear the canvas.
        self.pixmap().fill(self.background_color)

        p = QPainter(self.pixmap())
        p.setPen(
            QPen(
                QColor(Qt.black),
                self.config["size"],
                Qt.SolidLine,
                Qt.RoundCap,
                Qt.RoundJoin,
            )
        )
        p.setBrush(QBrush(QColor(Qt.white)))
        p.drawEllipse(QPointF(300, 300), 250, 250)

        if self.hand == 0:
            p.drawRect(QRectF(550, 290, 10, 20))
            p.drawLine(290, 50, 560, 310)
            p.drawLine(290, 550, 560, 290)
        elif self.hand == 1:
            p.drawRect(QRectF(50, 290, -10, 20))
            p.drawLine(290, 50, 40, 310)
            p.drawLine(290, 550, 40, 290)
        # 5pix per cm
        xs = np.arange(50, 550, self.grid_spacing)
        ys = np.arange(50, 550, self.grid_spacing)
        p.setPen(
            QPen(
                QColor(Qt.green),
                self.config["size"],
                Qt.SolidLine,
                Qt.RoundCap,
                Qt.RoundJoin,
            )
        )
        p.setOpacity(0.2)
        for x in xs:
            p.drawLine(
                QPointF(x, 300 + np.sqrt(250**2 - (x - 300) ** 2)),
                QPointF(x, 300 - np.sqrt(250**2 - (x - 300) ** 2)),
            )
        for y in ys:
            p.drawLine(
                QPointF(300 + np.sqrt(250**2 - (y - 300) ** 2), y),
                QPointF(300 - np.sqrt(250**2 - (y - 300) ** 2), y),
            )
        if self.plasmacolumn is True:
            p.setPen(
                QPen(
                    QColor(Qt.red),
                    self.config["size"],
                    Qt.SolidLine,
                    Qt.RoundCap,
                    Qt.RoundJoin,
                )
            )
            p.setOpacity(0.4)
            p.drawEllipse(QPoint(300, 300), 150, 150)
        if self.maincathode is True:
            p.setPen(
                QPen(
                    QColor("#FFA500"),
                    self.config["size"],
                    Qt.SolidLine,
                    Qt.RoundCap,
                    Qt.RoundJoin,
                )
            )
            p.setOpacity(0.4)
            p.drawEllipse(QPoint(300, 300), 95, 95)
        if self.secondarycathode is True:
            p.setPen(
                QPen(
                    QColor("#ff4500"),
                    self.config["size"],
                    Qt.SolidLine,
                    Qt.RoundCap,
                    Qt.RoundJoin,
                )
            )
            p.setOpacity(0.4)
            p.drawRect(250, 250, 100, 100)
        p.setPen(
            QPen(
                QColor(Qt.black),
                self.config["size"],
                Qt.SolidLine,
                Qt.RoundCap,
                Qt.RoundJoin,
            )
        )
        p.setOpacity(1)
        p.setBrush(QBrush(QColor(Qt.red)))

        p.drawEllipse(QPointF(300, 300), 1, 1)
        p.end()

    def set_primary_color(self, hex):
        self.primary_color = QColor(hex)

    def set_spacing(self, arg):
        self.grid_spacing = 5 * arg.sl.value()
        arg.update_canvas(self.poslist)

    def set_hand(self, arg):
        """
        Sets ''chirality'' i.e. Left or Right entry point.  Can add
        more options for more entry angles.
        """
        if arg == 0:
            self.hand = 0
        elif arg == 1:
            self.hand = 1
        self.reset()

    def set_mode(self, mode):
        """
        This mode controls the shape painting function, as well as the
        point generator.
        """
        # Clean up active timer animations.
        self.timer_cleanup()
        # Reset mode-specific vars (all)
        self.active_shape_fn = None
        self.active_shape_args = ()

        self.origin_pos = None

        self.current_pos = None
        self.last_pos = None

        self.history_pos = None
        self.last_history = []
        # Apply Mode
        self.mode = mode

    def set_status(self, arg):
        """
        Register resolution and z-axis extrusion inputs.  5x factor for
        cm to pixel conversion.
        """

        def str_to_array(str1):
            str1 = np.array(
                str1.replace("(", "").replace(")", "").split(","), dtype=float
            )
            return str1

        self.nx = 5 * str_to_array(str(arg.xres.text()))
        self.ny = 5 * str_to_array(str(arg.yres.text()))
        self.nz = 5 * str_to_array(str(arg.zres.text()))
        self.z1 = 5 * float(arg.z1.text())
        self.z2 = 5 * float(arg.z2.text())
        self.centers = str(arg.gridCentre.text())
        self.closeit = arg.closeit
        self.eccentricity = arg.eccentricity

        if arg.MainCathode.isChecked():
            self.maincathode = True
        else:
            self.maincathode = False
        if arg.PlasmaColumn.isChecked():
            self.plasmacolumn = True
        else:
            self.plasmacolumn = False
        if arg.SecondaryCathode.isChecked():
            self.secondarycathode = True
        else:
            self.secondarycathode = False

    def set_grid(self, grid):
        """similar to mode system, sets the grid system."""
        self.grid = grid

    def reset_mode(self):
        self.set_mode(self.mode)

    def on_timer(self):
        if self.timer_event:
            self.timer_event()

    def timer_cleanup(self):
        if self.timer_event:
            # Stop the timer, then trigger cleanup.
            timer_event = self.timer_event
            self.timer_event = None
            timer_event(final=True)

    # Mouse events.
    # - redefining pyqt mouse events... depending on chosen mode,
    #   this will also call  a mode specific  drawing function to
    #   paint shape on the canvas
    #
    # - Everything internal is handled in coordinate units, EXCEPT the
    #   BARLIST
    # - All inputs are taken in cm units.  Means output list is also in
    #   coord units.
    # - 1 cm = 5 pixel, as per the set size of the canvas.
    # - self.xpos, self.ypos (and self.zpos) are containers for all
    #   vertex points.
    # - Basic point verification routine- distance from centre (is_inside_machine?)
    #
    ### CURRENTLY COMPLETELY AD-HOC #####
    # Angle from entry point (can probe reach via ball-valve. )
    # Current angle-restriction setup-
    # \_ Hole perfectly aligned with centre of lapd, + exactly at the
    # edge of lapd.
    #
    # valve is 2 cm long, and 2 cm above and below hole. SO shaft makes
    # 45 degree angles at max.. definitely incorrect.

    def mousePressEvent(self, e):
        fn = getattr(self, "%s_mousePressEvent" % self.mode, None)
        # calls mode_specific canvas drawing function-

        # Basic Point validity verification routine:
        dist = ((e.x() - 300) ** 2 + (e.y() - 300) ** 2) ** 0.5
        if dist > 250:

            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Error")
            msg.setInformativeText("Designated point is outside the Machine!")
            msg.setWindowTitle("Error")
            msg.exec_()
        if e.x() is not None and e.y() is not None:

            self.xpos = np.append(self.xpos, float(e.x() - 300))
            self.ypos = np.append(self.ypos, float(-e.y() + 300))
            # self.modelist = np.append(self.mode)
            if fn:
                return fn(e)

    def mouseMoveEvent(self, e):
        self.cx = e.x()
        self.cy = e.y()
        self.move.emit()
        fn = getattr(self, f"{self.mode}_mouseMoveEvent", None)
        if fn:
            return fn(e)

    def mouseReleaseEvent(self, e):

        fn = getattr(self, f"{self.mode}_mouseReleaseEvent", None)
        # calls mode_specific function-

        # Basic Point validity verification routine:
        dist = ((e.x() - 300) ** 2 + (e.y() - 300) ** 2) ** 0.5
        if dist > 250:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Error")
            msg.setInformativeText("Designated point is outside the Machine!")
            msg.setWindowTitle("Error")
            msg.exec_()
        if e.x() is not None and e.y() is not None:
            self.xpos = np.append(self.xpos, float(e.x() - 300))
            self.ypos = np.append(self.ypos, float(-e.y() + 300))
            # self.modelist = np.append(self.mode)

            if fn:
                return fn(e)

    def mouseDoubleClickEvent(self, e):
        fn = getattr(self, f"{self.mode}_mouseDoubleClickEvent", None)
        if fn:
            return fn(e)
        self.last_pos = None

    # Mode-specific events.

    # Line events

    def line_mousePressEvent(self, e):
        self.origin_pos = e.pos()
        self.current_pos = e.pos()
        self.preview_pen = PREVIEW_PEN
        self.timer_event = self.line_timerEvent

    def line_timerEvent(self, final=False):
        p = QPainter(self.pixmap())
        p.setCompositionMode(QPainter.RasterOp_SourceXorDestination)
        pen = self.preview_pen
        p.setPen(pen)
        if self.last_pos:
            p.drawLine(self.origin_pos, self.last_pos)
        if not final:
            p.drawLine(self.origin_pos, self.current_pos)
        self.update()
        self.last_pos = self.current_pos

    def line_mouseMoveEvent(self, e):
        self.current_pos = e.pos()

    def line_mouseReleaseEvent(self, e):
        if self.last_pos:
            # Clear up indicator.
            self.timer_cleanup()

            p = QPainter(self.pixmap())
            p.setPen(
                QPen(
                    self.primary_color,
                    self.config["size"],
                    Qt.SolidLine,
                    Qt.RoundCap,
                    Qt.RoundJoin,
                )
            )

            p.drawLine(self.origin_pos, e.pos())
            self.update()
        self.reset_mode()

    # barrier events

    def barrier_mousePressEvent(self, e):
        self.origin_pos = e.pos()
        self.current_pos = e.pos()
        self.preview_pen = PREVIEW_PEN
        self.timer_event = self.barrier_timerEvent

    def barrier_timerEvent(self, final=False):
        p = QPainter(self.pixmap())
        p.setCompositionMode(QPainter.RasterOp_SourceXorDestination)
        pen = self.preview_pen
        p.setPen(pen)
        if self.last_pos:
            p.drawLine(self.origin_pos, self.last_pos)
        if not final:
            p.drawLine(self.origin_pos, self.current_pos)
        self.update()
        self.last_pos = self.current_pos

    def barrier_mouseMoveEvent(self, e):
        self.current_pos = e.pos()

    def barrier_mouseReleaseEvent(self, e):
        if self.last_pos:
            # Clear up indicator.
            self.timer_cleanup()

            p = QPainter(self.pixmap())
            p.setPen(
                QPen(
                    QColor("#800000"),
                    self.config["size"],
                    Qt.SolidLine,
                    Qt.RoundCap,
                    Qt.RoundJoin,
                )
            )

            p.drawLine(self.origin_pos, e.pos())

            p.setPen(
                QPen(
                    QColor("#FF0000"),
                    self.config["size"],
                    Qt.SolidLine,
                    Qt.RoundCap,
                    Qt.RoundJoin,
                )
            )

            ye = 300 - e.y()
            xe = e.x() - 300
            yorg = 300 - self.origin_pos.y()
            xorg = self.origin_pos.x() - 300
            r = 250
            if self.hand == 0:
                theta = 0
            if self.hand == 1:
                theta = np.pi
            if theta >= np.pi:
                C = (yorg - r * np.sin(theta)) / (xorg - r * np.cos(theta))

                a = 1 + C**2
                b = -2 * xorg * (C**2) + 2 * C * yorg
                c = (C**2) * xorg + yorg**2 - 2 * C * yorg * xorg - r**2

                xvo = (-b + np.sqrt(b**2 - 4 * a * c)) / (2 * a)

                yvo = C * (xvo - xorg) + yorg
                p.drawLine(self.origin_pos, QPointF(xvo + 300, 300 - yvo))
                C = (ye - r * np.sin(theta)) / (xe - r * np.cos(theta))

                a = 1 + C**2
                b = -2 * xe * (C**2) + 2 * C * ye
                c = (C**2) * xe + ye**2 - 2 * C * ye * xe - r**2

                xve = (-b + np.sqrt(b**2 - 4 * a * c)) / (2 * a)

                yve = C * (xve - xe) + ye
                p.drawLine(e.pos(), QPointF(xve + 300, 300 - yve))
            if theta < np.pi:
                C = (yorg - r * np.sin(theta)) / (xorg - r * np.cos(theta))

                a = 1 + C**2
                b = -2 * xorg * (C**2) + 2 * C * yorg
                c = (C**2) * xorg + yorg**2 - 2 * C * yorg * xorg - r**2

                xvo = (-b - np.sqrt(b**2 - 4 * a * c)) / (2 * a)

                yvo = C * (xvo - xorg) + yorg
                p.drawLine(self.origin_pos, QPointF(xvo + 300, 300 - yvo))
                C = (ye - r * np.sin(theta)) / (xe - r * np.cos(theta))

                a = 1 + C**2
                b = -2 * xe * (C**2) + 2 * C * ye
                c = (C**2) * xe + ye**2 - 2 * C * ye * xe - r**2

                xve = (-b - np.sqrt(b**2 - 4 * a * c)) / (2 * a)
                yve = C * (xve - xe) + ye
                p.drawLine(e.pos(), QPointF(xve + 300, 300 - yve))
            self.update()
            self.bar += 2
        self.reset_mode()

    # Generic poly events
    def generic_poly_mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            if self.history_pos:
                self.history_pos.append(e.pos())
            else:
                self.history_pos = [e.pos()]
                self.current_pos = e.pos()
                self.timer_event = self.generic_poly_timerEvent
        elif e.button() == Qt.RightButton and self.history_pos:
            # Clean up, we're not drawing
            self.timer_cleanup()
            self.reset_mode()

    def generic_poly_timerEvent(self, final=False):
        p = QPainter(self.pixmap())
        p.setCompositionMode(QPainter.RasterOp_SourceXorDestination)
        pen = self.preview_pen
        p.setPen(pen)
        if self.last_history:
            getattr(p, self.active_shape_fn)(*self.last_history)
        if not final:
            p.setPen(pen)
            getattr(p, self.active_shape_fn)(*self.history_pos + [self.current_pos])
        self.update()
        self.last_pos = self.current_pos
        self.last_history = self.history_pos + [self.current_pos]

    def generic_poly_mouseMoveEvent(self, e):
        self.current_pos = e.pos()

    def generic_poly_mouseDoubleClickEvent(self, e):
        self.timer_cleanup()
        p = QPainter(self.pixmap())
        p.setPen(
            QPen(
                self.primary_color,
                self.config["size"],
                Qt.SolidLine,
                Qt.RoundCap,
                Qt.RoundJoin,
            )
        )

        getattr(p, self.active_shape_fn)(*self.history_pos + [e.pos()])
        self.update()
        self.reset_mode()

    # Polyline events

    def polyline_mousePressEvent(self, e):
        self.active_shape_fn = "drawPolyline"
        self.preview_pen = PREVIEW_PEN
        self.generic_poly_mousePressEvent(e)

    def polyline_timerEvent(self, final=False):
        self.generic_poly_timerEvent(final)

    def polyline_mouseMoveEvent(self, e):
        self.generic_poly_mouseMoveEvent(e)

    def polyline_mouseDoubleClickEvent(self, e):
        self.generic_poly_mouseDoubleClickEvent(e)

    # Rectangle events

    def rect_mousePressEvent(self, e):
        self.active_shape_fn = "drawRect"
        self.active_shape_args = ()
        self.preview_pen = PREVIEW_PEN
        self.origin_pos = e.pos()
        self.current_pos = e.pos()
        self.timer_event = self.rect_timerEvent

    def rect_timerEvent(self, final=False):
        p = QPainter(self.pixmap())
        p.setCompositionMode(QPainter.RasterOp_SourceXorDestination)
        pen = self.preview_pen
        p.setPen(pen)
        if self.last_pos:
            getattr(p, self.active_shape_fn)(
                QRect(self.origin_pos, self.last_pos), *self.active_shape_args
            )
        if not final:
            p.setPen(pen)
            getattr(p, self.active_shape_fn)(
                QRect(self.origin_pos, self.current_pos), *self.active_shape_args
            )
        self.update()
        self.last_pos = self.current_pos

    def rect_mouseMoveEvent(self, e):
        self.current_pos = e.pos()

    def rect_mouseReleaseEvent(self, e):
        if self.last_pos:
            # Clear up indicator.
            self.timer_cleanup()

            p = QPainter(self.pixmap())
            p.setPen(
                QPen(
                    self.primary_color,
                    self.config["size"],
                    Qt.SolidLine,
                    Qt.SquareCap,
                    Qt.MiterJoin,
                )
            )
            p.setOpacity(0.5)

            if self.config["fill"]:
                p.setBrush(QBrush(self.primary_color))
            getattr(p, self.active_shape_fn)(
                QRect(self.origin_pos, e.pos()), *self.active_shape_args
            )
            self.update()
        self.reset_mode()

    # Circle events

    def circle_mousePressEvent(self, e):
        self.active_shape_fn = "drawEllipse"
        self.active_shape_args = ()
        self.preview_pen = PREVIEW_PEN
        self.origin_pos = e.pos()
        self.current_pos = e.pos()
        self.timer_event = self.circle_timerEvent

    def circle_timerEvent(self, final=False):
        p = QPainter(self.pixmap())
        p.setCompositionMode(QPainter.RasterOp_SourceXorDestination)
        pen = self.preview_pen
        p.setPen(pen)
        if self.last_pos:
            r = np.sqrt(
                (self.origin_pos.x() - self.last_pos.x()) ** 2
                + (self.origin_pos.y() - self.last_pos.y()) ** 2
            )

            getattr(p, self.active_shape_fn)(
                self.origin_pos, r, r, *self.active_shape_args
            )
        if not final:
            p.setPen(pen)
            r = np.sqrt(
                (self.origin_pos.x() - self.current_pos.x()) ** 2
                + (self.origin_pos.y() - self.current_pos.y()) ** 2
            )
            getattr(p, self.active_shape_fn)(
                self.origin_pos, r, r, *self.active_shape_args
            )
        self.update()
        self.last_pos = self.current_pos

    def circle_mouseMoveEvent(self, e):
        self.current_pos = e.pos()

    def circle_mouseReleaseEvent(self, e):
        if self.last_pos:
            # Clear up indicator.
            self.timer_cleanup()
            r = np.sqrt(
                (self.origin_pos.x() - self.last_pos.x()) ** 2
                + (self.origin_pos.y() - self.last_pos.y()) ** 2
            )

            p = QPainter(self.pixmap())
            p.setPen(
                QPen(
                    self.primary_color,
                    self.config["size"],
                    Qt.SolidLine,
                    Qt.SquareCap,
                    Qt.MiterJoin,
                )
            )
            p.setOpacity(0.5)

            if self.config["fill"]:
                p.setBrush(QBrush(self.primary_color))
            getattr(p, self.active_shape_fn)(
                self.origin_pos, r, r, *self.active_shape_args
            )
            self.update()
        self.reset_mode()

    # Ellipse events
    def ellipse_mousePressEvent(self, e):
        self.active_shape_fn = "drawEllipse"
        self.active_shape_args = ()
        self.origin_pos = e.pos()
        self.preview_pen = PREVIEW_PEN
        self.current_pos = e.pos()
        self.timer_event = self.ellipse_timerEvent

    def ellipse_timerEvent(self, final=False):
        p = QPainter(self.pixmap())
        p.setCompositionMode(QPainter.RasterOp_SourceXorDestination)
        pen = self.preview_pen
        p.setPen(pen)
        if self.last_pos:
            getattr(p, self.active_shape_fn)(
                QRect(self.origin_pos, self.last_pos), *self.active_shape_args
            )
        if not final:
            p.setPen(pen)
            getattr(p, self.active_shape_fn)(
                QRect(self.origin_pos, self.current_pos), *self.active_shape_args
            )
        self.update()
        self.last_pos = self.current_pos

    def ellipse_mouseMoveEvent(self, e):
        self.current_pos = e.pos()

    def ellipse_mouseReleaseEvent(self, e):
        if self.last_pos:
            # Clear up indicator.
            self.timer_cleanup()

            p = QPainter(self.pixmap())
            p.setPen(
                QPen(
                    self.primary_color,
                    self.config["size"],
                    Qt.SolidLine,
                    Qt.SquareCap,
                    Qt.MiterJoin,
                )
            )
            p.setOpacity(0.5)

            if self.config["fill"]:
                p.setBrush(QBrush(self.primary_color))
            getattr(p, self.active_shape_fn)(
                QRect(self.origin_pos, e.pos()), *self.active_shape_args
            )
            self.update()
        self.reset_mode()

    def resetpos(self, arg):
        """
        Clear position lists and any defined data points, and settings.
        """
        self.xpos = []
        self.ypos = []
        self.poslist = []
        self.barlist = []
        self.bar = 0
        arg.saveButton.setEnabled(False)
        if self.mode == "rect":
            arg.la.setText("Length- X")
            arg.lb.setText("Length- Y")
            arg.lc.setText("Length- Z")
        elif self.mode == "circle":
            arg.la.setText("Radius")
            arg.lb.setText("")
            arg.lc.setText("Length- Z")
        elif self.mode == "ellipse":
            arg.lc.setText("Length- Z")
            arg.la.setText("Horizontal Axis")
            arg.lb.setText("Vertical Axis")

    def set_numpoint(self, arg):
        """
        Sets input (no. of points) for shape autogeneration scheme.
        """
        self.ea = str(arg.ea.text())
        self.eb = str(arg.eb.text())

    def print_positions(self, arg):
        """
        Position generating function, for display purposes.

        - Firstly, generates the barrier from given points, as well as
          the region that becomes no-go zone.  Currently based off
          ad-hoc assumptions for the angular reach of a probe shaft
          from a particular ball valve.
        - Secondly, calls point generating function depending on the
          mode.  Each point generating function further looks at grid
          config to set up points.
        """

        mode = self.mode
        bar = self.bar
        self.zpos = [self.z1, self.z2]  # Z-extrusion range
        barlist = []
        arg.saveButton.setEnabled(False)  # Must verify to reenable button
        if self.hand == 0:
            theta = 0
        if self.hand == 1:
            theta = np.pi
        r = 250
        # Generate the barrier from given points, as well as the
        # region that becomes no-go zone.  Currently based off ad-hoc
        # assumptions for the angular reach  of a probe shaft from a particular valve.
        for i in range(0, bar - 1, 2):
            xe = self.xpos[i + 1]
            xorg = self.xpos[i]
            ye = self.ypos[i + 1]
            yorg = self.ypos[i]

            if theta >= np.pi:
                C = (yorg - r * np.sin(theta)) / (xorg - r * np.cos(theta))

                a = 1 + C**2
                b = -2 * xorg * (C**2) + 2 * C * yorg
                c = (C**2) * xorg + yorg**2 - 2 * C * yorg * xorg - r**2

                xvo = (-b + np.sqrt(b**2 - 4 * a * c)) / (2 * a)

                yvo = C * (xvo - xorg) + yorg

                C = (ye - r * np.sin(theta)) / (xe - r * np.cos(theta))

                a = 1 + C**2
                b = -2 * xe * (C**2) + 2 * C * ye
                c = (C**2) * xe + ye**2 - 2 * C * ye * xe - r**2

                xve = (-b + np.sqrt(b**2 - 4 * a * c)) / (2 * a)

                yve = C * (xve - xe) + ye
                C = (yorg - r * np.sin(theta)) / (xorg - r * np.cos(theta))

                a = 1 + C**2
                b = -2 * xorg * (C**2) + 2 * C * yorg
                c = (C**2) * xorg + yorg**2 - 2 * C * yorg * xorg - r**2

                xvo = (-b + np.sqrt(b**2 - 4 * a * c)) / (2 * a)

                yvo = C * (xvo - xorg) + yorg

                C = (ye - r * np.sin(theta)) / (xe - r * np.cos(theta))

                a = 1 + C**2
                b = -2 * xe * (C**2) + 2 * C * ye
                c = (C**2) * xe + ye**2 - 2 * C * ye * xe - r**2

                xve = (-b + np.sqrt(b**2 - 4 * a * c)) / (2 * a)

                yve = C * (xve - xe) + ye
            if theta < np.pi:
                C = (yorg - r * np.sin(theta)) / (xorg - r * np.cos(theta))

                a = 1 + C**2
                b = -2 * xorg * (C**2) + 2 * C * yorg
                c = (C**2) * xorg + yorg**2 - 2 * C * yorg * xorg - r**2

                xvo = (-b - np.sqrt(b**2 - 4 * a * c)) / (2 * a)

                yvo = C * (xvo - xorg) + yorg

                C = (ye - r * np.sin(theta)) / (xe - r * np.cos(theta))

                a = 1 + C**2
                b = -2 * xe * (C**2) + 2 * C * ye
                c = (C**2) * xe + ye**2 - 2 * C * ye * xe - r**2

                xve = (-b - np.sqrt(b**2 - 4 * a * c)) / (2 * a)

                yve = C * (xve - xe) + ye
            barlist.append(
                [
                    (xorg, yorg, self.z1),
                    (xe, ye, self.z1),
                    (xvo, yvo, self.z1),
                    (xve, yve, self.z1),
                ]
            )
        barlist = np.array(barlist) / 5
        self.barlist = barlist

        if mode == "line":
            self.get_positionsline()
        elif mode == "rect":
            self.get_positionsrect(arg)
        elif mode == "polyline":
            self.get_positionspoly()
        elif mode == "circle":
            self.get_positionscircle(arg)
        elif mode == "ellipse":
            self.get_positionsellipse(arg)

    def get_positionsrect(self, arg):
        """
        Point generator for rectangular/cuboidal shapes. Defined by
        corner vertices.
        """
        bar = self.bar
        poslist = []
        strx = ""
        stry = ""
        strz = ""
        strc = ""
        zmax = self.z1
        zmin = self.z2
        if self.grid == "rect":
            for i in range(bar, len(self.xpos) - 1, 2):
                xmax = self.xpos[i + 1]
                xmin = self.xpos[i]
                ymax = self.ypos[i + 1]
                ymin = self.ypos[i]

                nx = self.nx[i // 2]
                ny = self.ny[i // 2]
                nz = self.nz[i // 2]
                lx = abs(xmax - xmin)
                ly = abs(ymax - ymin)
                lz = abs(zmax - zmin)
                strx += f"{lx / 5},"
                stry += f"{ly / 5},"
                strz += f"{lz / 5},"

                linvalz = abs(math.floor((self.z2 - self.z1) / nz))

                linvalx = abs(math.floor((xmax - xmin) / nx))
                linvaly = abs(math.floor((ymax - ymin) / ny))

                zvals = np.linspace(self.z1, self.z2, linvalz + 1)
                xvals = np.linspace(xmin, xmax, linvalx + 1)
                yvals = np.linspace(ymin, ymax, linvaly + 1)
                cx = (xmax + xmin) / 2
                cy = (ymax + ymin) / 2
                cz = (zmax + zmin) / 2
                strc += f"({cx / 5}, {cy / 5}, {cz / 5}), "
                positions = []
                for z in range(0, len(zvals)):
                    for x in range(0, len(xvals)):
                        for y in range(0, len(yvals)):
                            positions.append([xvals[x], yvals[y], zvals[z]])
                poslist.extend(positions)
            self.poslist = poslist
            strx = strx.rstrip(strx[-1])
            stry = stry.rstrip(stry[-1])
            strz = strz.rstrip(strz[-1])
            strc = strc.rstrip(strc[-1])
            strc = strc.rstrip(strc[-1])
            arg.gridCentre.setText(strc)
            arg.la.setText(strx)
            arg.lb.setText(stry)
            arg.lc.setText(strz)
        if self.grid == "circle":

            xpos = []
            ypos = []

            for i in range(bar, len(self.xpos) - 1, 2):
                xmax = max([self.xpos[i + 1], self.xpos[i]])
                xmin = min([self.xpos[i + 1], self.xpos[i]])
                ymax = max([self.ypos[i + 1], self.ypos[i]])
                ymin = min([self.ypos[i + 1], self.ypos[i]])
                dr = self.nx[i // 2]
                dtheta = self.ny[i // 2] / 5
                nz = self.nz[i // 2]
                lx = abs(xmax - xmin)
                ly = abs(ymax - ymin)
                lz = abs(zmax - zmin)
                strx += f"{lx / 5},"
                stry += f"{ly / 5},"
                strz += f"{lz / 5},"
                linvalz = abs(math.floor((self.z2 - self.z1) / nz))
                cx = (xmax + xmin) / 2
                cy = (ymax + ymin) / 2
                cz = (zmax + zmin) / 2
                strc += f"({cx / 5}, {cy / 5}, {cz / 5}), "

                zvals = np.linspace(self.z1, self.z2, linvalz + 1)
                xpos = np.append(xpos, cx)
                ypos = np.append(ypos, cy)

                r = 0.5 * (np.sqrt((xmax - xmin) ** 2 + (ymax - ymin) ** 2))

                linval = math.floor(r / (dr))

                thetavals = np.linspace(0, 1, math.floor(360 / dtheta) + 1)
                parvals = np.linspace(0, 1, linval + 1)
                positions = []
                # first start point already initialized in array.
                for t in parvals[1:]:
                    # Other start points are incorporated as the end points of
                    # previous segment.
                    for z in thetavals[1:]:
                        xval = cx + t * r * np.cos(z * 2 * np.pi)
                        yval = cy + t * r * np.sin(z * 2 * np.pi)

                        if (xval > xmax) or xval < xmin or yval > ymax or yval < ymin:
                            pass
                        else:
                            xpos = np.append(xpos, xval)
                            ypos = np.append(ypos, yval)
                for z in range(0, len(zvals)):
                    zpos = z * np.ones(len(xpos))
                    positions = list(zip(xpos, ypos, zpos))
                    poslist = poslist + positions
            self.poslist = poslist
            strx = strx.rstrip(strx[-1])
            stry = stry.rstrip(stry[-1])
            strz = strz.rstrip(strz[-1])
            strc = strc.rstrip(strc[-1])
            strc = strc.rstrip(strc[-1])
            arg.gridCentre.setText(strc)
            arg.la.setText(strx)
            arg.lb.setText(stry)
            arg.lc.setText(strz)
        if self.grid == "sphere":

            for i in range(bar, len(self.xpos) - 1, 2):
                xmax = max([self.xpos[i + 1], self.xpos[i]])
                xmin = min([self.xpos[i + 1], self.xpos[i]])
                ymax = max([self.ypos[i + 1], self.ypos[i]])
                ymin = min([self.ypos[i + 1], self.ypos[i]])
                zmax = max([self.z1, self.z2])
                zmin = min([self.z1, self.z2])
                dr = self.nx[i // 2]
                dtheta = self.ny[i // 2] / 5
                dphi = self.nz[i // 2] / 5
                lx = abs(xmax - xmin)
                ly = abs(ymax - ymin)
                lz = abs(zmax - zmin)
                strx += f"{lx / 5},"
                stry += f"{ly / 5},"
                strz += f"{lz / 5},"
                cx = (xmax + xmin) / 2
                cy = (ymax + ymin) / 2
                cz = (zmax + zmin) / 2
                strc += f"({cx / 5}, {cy / 5}, {cz / 5}), "

                r = (
                    np.sqrt((xmax - xmin) ** 2 + (ymax - ymin) ** 2)
                    + (zmax - zmin) ** 2
                )

                linval = math.floor(r / (dr))

                thetavals = np.linspace(0, 1, math.floor(360 / dtheta) + 1)
                phivals = np.linspace(0, 1, math.floor(180 / dphi) + 1)
                parvals = np.linspace(0, 1, linval + 1)
                positions = [[cx, cy, cz]]
                # first start point already initialized in array.
                for t in parvals[1:]:
                    # Other start points are incorporated as the end points of
                    # previous segment.
                    for z in thetavals[1:]:
                        for p in phivals[1:]:
                            xval = cx + t * r * np.cos(z * 2 * np.pi) * np.sin(
                                p * np.pi
                            )
                            yval = cy + t * r * np.sin(z * 2 * np.pi) * np.sin(
                                p * np.pi
                            )
                            zval = cz + t * r * np.cos(p * np.pi)
                        if (
                            (xval > xmax)
                            or xval < xmin
                            or yval > ymax
                            or yval < ymin
                            or zval > zmax
                            or zval < zmin
                        ):
                            pass
                        else:
                            positions.append([xval, yval, zval])
                poslist = poslist + positions
            self.poslist = poslist
            strx = strx.rstrip(strx[-1])
            stry = stry.rstrip(stry[-1])
            strz = strz.rstrip(strz[-1])
            strc = strc.rstrip(strc[-1])
            strc = strc.rstrip(strc[-1])
            arg.gridCentre.setText(strc)
            arg.la.setText(strx)
            arg.lb.setText(stry)
            arg.lc.setText(strz)
        if self.grid == "ellipse":

            e = self.eccentricity
            xpos = []
            ypos = []
            poslist = []
            for i in range(bar, len(self.xpos) - 1, 2):
                dr = self.nx[i // 2]
                dtheta = self.ny[i // 2] / 5
                dz = self.nz[i // 2]
                xmax = max([self.xpos[i + 1], self.xpos[i]])
                xmin = min([self.xpos[i + 1], self.xpos[i]])
                ymax = max([self.ypos[i + 1], self.ypos[i]])
                ymin = min([self.ypos[i + 1], self.ypos[i]])
                zmax = max([self.z1, self.z2])
                zmin = min([self.z1, self.z2])
                lx = abs(xmax - xmin)
                ly = abs(ymax - ymin)
                lz = abs(zmax - zmin)
                strx += f"{lx / 5},"
                stry += f"{ly / 5},"
                strz += f"{lz / 5},"
                cx = (xmax + xmin) / 2
                cy = (ymax + ymin) / 2
                cz = (zmax + zmin) / 2
                strc += f"({cx / 5}, {cy / 5}, {cz / 5}), "

                # NEED TO RECALCULATE POINT GENERATING PARAMETERS TO GET
                # APPROPRIATE ONES WITHIN THE REGION.
                linvalz = abs(math.floor((zmax - zmin) / dz))
                zvals = np.linspace(zmin, zmax, linvalz + 1)

                a = max([(xmax - xmin), (ymax - ymin)])
                b = a * np.sqrt(1 - e**2)

                xpos = np.append(xpos, cx)
                ypos = np.append(ypos, cy)

                linval = math.floor((min([a, b])) / dr)

                thetavals = np.linspace(0, 1, math.floor(360 / dtheta) + 1)
                parvals = np.linspace(0, 1, linval + 1)

                for t in parvals[1:]:
                    for z in thetavals[1:]:
                        xval = cx + t * a * np.cos(z * 2 * np.pi)
                        yval = cy + t * b * np.sin(z * 2 * np.pi)
                        if (xval > xmax) or xval < xmin or yval > ymax or yval < ymin:
                            pass
                        else:
                            xpos = np.append(xpos, xval)
                            ypos = np.append(ypos, yval)
            for z in range(0, len(zvals)):
                zpos = z * np.ones(len(xpos))
                positions = list(zip(xpos, ypos, zpos))
                poslist = poslist + positions
            self.poslist = poslist
            strx = strx.rstrip(strx[-1])
            stry = stry.rstrip(stry[-1])
            strz = strz.rstrip(strz[-1])
            strc = strc.rstrip(strc[-1])
            strc = strc.rstrip(strc[-1])
            arg.gridCentre.setText(strc)
            arg.la.setText(strx)
            arg.lb.setText(stry)
            arg.lc.setText(strz)
            arg.ea.setText(str(len(xpos)))
            arg.eb.setText(str(len(ypos)))
            arg.ec.setText(str(len(zvals)))

    def get_positionsline(self):
        """Point generator for lines."""

        poslist = []
        bar = self.bar
        xs = self.xpos
        ys = self.ypos

        linvalz = abs(math.floor((self.z2 - self.z1) / nz))
        zvals = np.linspace(self.z1, self.z2, linvalz + 1)
        xpos = []
        ypos = []
        #            zpos = [zs[0]]

        for i in range(bar, len(xs) - 1, 2):

            # general idea for motion list- user gave end points of line segments.
            # each point is essentially a location in the array. Get distance
            # between the two array points.  Get an equation of the line joining
            # two points in the array.  Get real coordinates of the point on
            # this line at every 'res' distance.

            # the coordinates of the two end points of line segment

            xposi = xs[i]
            xposi2 = xs[i + 1]

            yposi = ys[i]
            yposi2 = ys[i + 1]
            nz = self.nz[i]

            # zposi = zs[i]
            # zposi2 = zs[i+1]
            res = (self.nx[i // 2] ** 2 + self.ny[i // 2] ** 2) ** 0.5
            length = ((xposi2 - xposi) ** 2 + (yposi2 - yposi) ** 2) ** 0.5
            linval = math.floor(length / (res))

            parvals = np.linspace(0, 1, linval + 1)

            for t in parvals:

                xval = xposi + t * (xposi2 - xposi)
                yval = yposi + t * (yposi2 - yposi)
                # zval = zposi + t*(zposi2 - zposi)
                xpos = np.append(xpos, xval)
                ypos = np.append(ypos, yval)
        for z in range(0, len(zvals)):
            zpos = z * np.ones(len(xpos))
            positions = list(zip(xpos, ypos, zpos))
            poslist = poslist + positions
        self.poslist = poslist

    def get_positionspoly(self):
        """
        Point generator for polygonal lines. Currently defaults to not
        closing shape.
        """

        poslist = []
        if self.closeit is True:
            index = -1
        else:
            index = 0
        bar = int(self.bar / 2)
        xs = np.delete(self.xpos, -1)
        ys = np.delete(self.ypos, -1)

        xs = xs[1::2]
        ys = ys[1::2]
        xs = xs[bar:]
        ys = ys[bar:]
        xpos = [xs[bar]]
        ypos = [ys[bar]]

        if self.closeit is True:
            p = QPainter(self.pixmap())

            p.setPen(
                QPen(
                    QColor(Qt.blue),
                    self.config["size"],
                    Qt.SolidLine,
                    Qt.RoundCap,
                    Qt.RoundJoin,
                )
            )
            p.setBrush(QBrush(QColor(Qt.blue)))

            p.drawLine(
                QPointF(xs[-1] + 300, -ys[-1] + 300), QPointF(xs[0] + 300, -ys[0] + 300)
            )
        for i in range(index, len(xs) - 1):
            xposi = xs[i]
            xposi2 = xs[i + 1]

            yposi = ys[i]
            yposi2 = ys[i + 1]

            res = (self.nx[i] ** 2 + self.ny[i] ** 2) ** 0.5
            length = ((xposi2 - xposi) ** 2 + (yposi2 - yposi) ** 2) ** 0.5
            linval = math.floor(length / (res))

            parvals = np.linspace(0, 1, linval + 1)

            for t in parvals[1:]:

                xval = xposi + t * (xposi2 - xposi)
                yval = yposi + t * (yposi2 - yposi)
                # zval = zposi + t*(zposi2 - zposi)
                xpos = np.append(xpos, xval)
                ypos = np.append(ypos, yval)
        nz = self.nz[i]

        linvalz = abs(math.floor((self.z2 - self.z1) / nz))
        zvals = np.linspace(self.z1, self.z2, linvalz + 1)

        for z in range(0, len(zvals)):
            zpos = z * np.ones(len(xpos))
            positions = list(zip(xpos, ypos, zpos))
            poslist = poslist + positions
        self.poslist = poslist

    def get_positionscircle(self, arg):
        """
        Point generator for circular/cylindrical shapes.  Circles are
        defined by point at center and random point on the circular
        edge.
        """
        strc = ""
        poslist = []
        bar = self.bar
        xs = self.xpos
        ys = self.ypos
        strx = ""
        stry = ""
        strz = ""
        zmax = self.z1
        zmin = self.z2
        if self.grid == "rect":
            for i in range(bar, len(self.xpos) - 1, 2):

                xposi2 = self.xpos[i + 1]
                xposi = self.xpos[i]
                yposi2 = self.ypos[i + 1]
                yposi = self.ypos[i]

                r = np.sqrt((xposi - xposi2) ** 2 + (yposi - yposi2) ** 2)
                nx = self.nx[i // 2]
                ny = self.ny[i // 2]
                nz = self.nz[i // 2]

                cx = xposi
                cy = yposi
                cz = (zmax + zmin) / 2
                strc += f"({cx / 5}, {cy / 5}, {cz / 5}), "

                xmax = cx + r
                xmin = cx - r
                ymax = cy + r
                ymin = cy - r
                lz = abs(zmax - zmin)

                strx += f"{round(r / 5, 3)},"
                stry += f"{round(r / 5, 3)},"
                strz += f"{lz / 5},"

                linvalz = abs(math.floor(lz / nz))

                linvalx = abs(math.floor((xmax - xmin) / nx))
                linvaly = abs(math.floor((ymax - ymin) / ny))

                zvals = np.linspace(self.z1, self.z2, linvalz + 1)
                xpos = np.linspace(xmin, xmax, linvalx + 1)
                ypos = np.linspace(ymin, ymax, linvaly + 1)

                positions = []
                for z in range(0, len(zvals)):
                    for x in range(0, len(xpos)):
                        for y in range(0, len(ypos)):
                            r1 = np.sqrt((cx - xpos[x]) ** 2 + (cy - ypos[y]) ** 2)
                            if r1 <= r:
                                positions.append([xpos[x], ypos[y], zvals[z]])
                            else:
                                pass
                poslist.extend(positions)
            self.poslist = poslist
            strx = strx.rstrip(strx[-1])
            stry = stry.rstrip(stry[-1])
            strz = strz.rstrip(strz[-1])
            arg.la.setText(strx)
            arg.lb.setText(stry)
            arg.lc.setText(strz)
            strc = strc.rstrip(strc[-1])
            strc = strc.rstrip(strc[-1])
            arg.gridCentre.setText(strc)
            arg.ea.setText(str(len(xpos)))
            arg.eb.setText(str(len(ypos)))
            arg.ec.setText(str(len(zvals)))
        if self.grid == "circle":

            linvalz = abs(math.floor((self.z2 - self.z1) / (nz)))
            zvals = np.linspace(self.z1, self.z2, linvalz + 1)
            xpos = []
            ypos = []
            #
            for i in range(bar, len(xs) - 1, 2):

                xposi = xs[i]
                xposi2 = xs[i + 1]

                yposi = ys[i]
                yposi2 = ys[i + 1]
                cx = xposi
                cy = yposi
                dr = self.nx[i // 2]
                dtheta = self.ny[i // 2] / 5
                nz = self.nz[i // 2]
                cz = (zmax + zmin) / 2
                strc += f"({cx / 5}, {cy / 5}, {cz / 5}), "
                r = np.sqrt((xposi - xposi2) ** 2 + (yposi - yposi2) ** 2)
                lz = abs(zmax - zmin)

                strx += f"{round(r / 5, 3)},"
                stry += f"{round(r / 5, 3)},"
                strz += f"{lz / 5},"

                linval = math.floor(r / dr)

                thetavals = np.linspace(0, 1, math.floor(360 / dtheta) + 1)
                parvals = np.linspace(0, 1, linval + 1)
                xpos = np.append(xpos, xposi)
                ypos = np.append(ypos, yposi)

                for t in parvals[1:]:
                    for z in thetavals[1:]:
                        xval = xposi + t * r * np.cos(z * 2 * np.pi)
                        yval = yposi + t * r * np.sin(z * 2 * np.pi)

                        xpos = np.append(xpos, xval)
                        ypos = np.append(ypos, yval)
            for z in range(0, len(zvals)):
                zpos = z * np.ones(len(xpos))
                positions = list(zip(xpos, ypos, zpos))
                poslist = poslist + positions
            self.poslist = poslist
            strx = strx.rstrip(strx[-1])
            stry = stry.rstrip(stry[-1])
            strz = strz.rstrip(strz[-1])
            arg.la.setText(strx)
            arg.lb.setText(stry)
            arg.lc.setText(strz)
            strc = strc.rstrip(strc[-1])
            strc = strc.rstrip(strc[-1])
            arg.gridCentre.setText(strc)
            arg.ea.setText(str(len(xpos)))
            arg.eb.setText(str(len(ypos)))
            arg.ec.setText(str(len(zvals)))
        if self.grid == "sphere":

            zmax = max([self.z1, self.z2])
            zmin = min([self.z1, self.z2])

            for i in range(bar, len(xs) - 1, 2):
                dr = self.nx[i // 2]
                dtheta = self.ny[i // 2] / 5
                dphi = self.nz[i // 2] / 5
                xposi = xs[i]
                xposi2 = xs[i + 1]

                yposi = ys[i]
                yposi2 = ys[i + 1]
                cx = xposi
                cy = yposi
                cz = (zmax + zmin) / 2
                strc += f"({cx / 5}, {cy / 5}, {cz / 5}), "
                rc = np.sqrt((xposi - xposi2) ** 2 + (yposi - yposi2) ** 2)
                lz = abs(zmax - zmin)

                strx += f"{round(rc / 5, 3)},"
                stry += f"{round(rc / 5, 3)},"
                strz += f"{lz / 5},"
                if self.centers == "":
                    cx = xposi
                    cy = yposi
                    cz = (zmax + zmin) / 2
                else:
                    str1 = self.centers
                    str1 = np.array(
                        str1.replace("(", "").replace(")", "").split(","), dtype=float
                    ).reshape(-1, 3)
                    xs = [5 * x[0] for x in str1]
                    ys = [5 * x[1] for x in str1]
                    zs = [5 * x[2] for x in str1]
                    cx = xs[i / 2]
                    cy = ys[i / 2]
                    cz = zs[i / 2]
                xmax = cx + rc
                xmin = cx - rc
                ymax = cy + rc
                ymin = cy - rc

                r = 0.5 * (
                    np.sqrt((xmax - xmin) ** 2 + (ymax - ymin) ** 2)
                    + (zmax - zmin) ** 2
                )

                linval = math.floor(r / dr)

                thetavals = np.linspace(0, 1, math.floor(360 / dtheta) + 1)
                phivals = np.linspace(0, 1, math.floor(180 / dphi) + 1)
                parvals = np.linspace(0, 1, linval + 1)
                positions = [[cx, cy, cz]]
                # first start point already initialized in array.
                for t in parvals[1:]:
                    # Other start points are incorporated as the end points of
                    # previous segment.
                    for z in thetavals[1:]:
                        for p in phivals[1:]:
                            xval = cx + t * r * np.cos(z * 2 * np.pi) * np.sin(
                                p * np.pi
                            )
                            yval = cy + t * r * np.sin(z * 2 * np.pi) * np.sin(
                                p * np.pi
                            )
                            zval = cz + t * r * np.cos(p * np.pi)
                        if (
                            (xval - cx) ** 2 + (yval - cy) ** 2 > rc**2
                            or zval > zmax
                            or zval < zmin
                        ):
                            pass
                        else:
                            positions.append([xval, yval, zval])
                poslist = poslist + positions
            self.poslist = poslist
            strx = strx.rstrip(strx[-1])
            stry = stry.rstrip(stry[-1])
            strz = strz.rstrip(strz[-1])
            arg.la.setText(strx)
            arg.lb.setText(stry)
            arg.lc.setText(strz)
            strc = strc.rstrip(strc[-1])
            strc = strc.rstrip(strc[-1])
            arg.gridCentre.setText(strc)
            arg.ea.setText(str(len(xpos)))
            arg.eb.setText(str(len(ypos)))
            arg.ec.setText(str(len(zvals)))
        if self.grid == "ellipse":

            bar = self.bar

            e = self.eccentricity
            poslist = []
            xpos = []
            ypos = []
            for i in range(bar, len(self.xpos) - 1, 2):
                dr = self.nx[i // 2]
                dtheta = self.ny[i // 2] / 5
                dz = self.nz[i // 2]
                xposi = self.xpos[i]
                xposi2 = self.xpos[i + 1]

                yposi = self.ypos[i]
                yposi2 = self.ypos[i + 1]

                zmax = self.z1
                zmin = self.z2
                lz = abs(zmax - zmin)
                cx = xposi
                cy = yposi
                cz = (zmax + zmin) / 2
                strc += f"({cx / 5}, {cy / 5}, {cz / 5}), "

                strz += f"{lz / 5},"
                linvalz = abs(math.floor((zmax - zmin) / dz))

                zvals = np.linspace(zmin, zmax, linvalz + 1)
                b = np.sqrt((xposi - xposi2) ** 2 + (yposi - yposi2) ** 2)
                a = b / np.sqrt(1 - e**2)
                strx += f"{round(a / 5, 3)},"
                stry += f"{round(a / 5, 3)},"

                cx = xposi
                cy = yposi
                xpos = np.append(xpos, cx)
                ypos = np.append(ypos, cy)

                linval = math.floor((min([a, b])) / (dr))

                thetavals = np.linspace(0, 1, math.floor(360 / dtheta) + 1)
                parvals = np.linspace(0, 1, linval + 1)

                for t in parvals[1:]:
                    for z in thetavals[1:]:
                        xval = cx + t * a * np.cos(z * 2 * np.pi)
                        yval = cy + t * b * np.sin(z * 2 * np.pi)
                        if (xval - cx) ** 2 + (yval - cy) ** 2 <= b**2:
                            xpos = np.append(xpos, xval)
                            ypos = np.append(ypos, yval)
            for z in range(0, len(zvals)):
                zpos = z * np.ones(len(xpos))
                positions = list(zip(xpos, ypos, zpos))
                poslist = poslist + positions
            self.poslist = poslist
            strx = strx.rstrip(strx[-1])
            stry = stry.rstrip(stry[-1])
            strz = strz.rstrip(strz[-1])
            arg.la.setText(strx)
            arg.lb.setText(stry)
            arg.lc.setText(strz)
            strc = strc.rstrip(strc[-1])
            strc = strc.rstrip(strc[-1])
            arg.gridCentre.setText(strc)
            arg.ea.setText(str(len(xpos)))
            arg.eb.setText(str(len(ypos)))
            arg.ec.setText(str(len(zvals)))

    def get_positionsellipse(self, arg):
        """
        Point generator for elliptical shapes.  Ellipse defined by
        circumscribing rectangle.
        """

        poslist = []
        bar = self.bar
        xs = self.xpos
        ys = self.ypos

        linvalz = abs(math.floor((self.z2 - self.z1) / nz))
        zvals = np.linspace(self.z1, self.z2, linvalz + 1)
        strx = ""
        stry = ""
        strz = ""
        strc = ""
        zmax = self.z1
        zmin = self.z2

        if self.grid == "ellipse":

            for i in range(bar, len(xs) - 1, 2):
                nz = self.nz[i // 2]
                dr = self.nx[i // 2]
                dtheta = self.ny[i // 2] / 5
                xposi = xs[i]
                xposi2 = xs[i + 1]

                yposi = ys[i]
                yposi2 = ys[i + 1]

                a = np.abs(xposi2 - xposi) / 2
                b = np.abs(yposi2 - yposi) / 2

                lz = abs(zmax - zmin)

                strx += f"{round(a / 5, 3)},"
                stry += f"{round(b / 5, 3)},"
                strz += f"{lz / 5},"
                cx = (xposi + xposi2) / 2
                cy = (yposi + yposi2) / 2
                cz = (zmax + zmin) / 2
                strc += f"({cx / 5}, {cy / 5}, {cz / 5}), "
                xpos = [cx]
                ypos = [cy]
                linval = math.floor((min([a, b])) / dr)

                thetavals = np.linspace(0, 1, math.floor(360 / dtheta) + 1)
                parvals = np.linspace(0, 1, linval + 1)

                for t in parvals[1:]:
                    for z in thetavals[1:]:
                        xval = cx + t * a * np.cos(z * 2 * np.pi)
                        yval = cy + t * b * np.sin(z * 2 * np.pi)
                        if ((xval - cx) / a) ** 2 + ((yval - cy) / b) ** 2 <= 1:
                            xpos = np.append(xpos, xval)
                            ypos = np.append(ypos, yval)
                for z in range(0, len(zvals)):
                    zpos = z * np.ones(len(xpos))
                    positions = list(zip(xpos, ypos, zpos))
                    poslist = poslist + positions
            self.poslist = poslist
            strx = strx.rstrip(strx[-1])
            stry = stry.rstrip(stry[-1])
            strz = strz.rstrip(strz[-1])
            arg.la.setText(strx)
            arg.lb.setText(stry)
            arg.lc.setText(strz)
            strc = strc.rstrip(strc[-1])
            strc = strc.rstrip(strc[-1])
            arg.gridCentre.setText(strc)
            arg.ea.setText(str(len(xpos)))
            arg.eb.setText(str(len(ypos)))
            arg.ec.setText(str(len(zvals)))
        if self.grid == "rect":
            for i in range(bar, len(xs) - 1, 2):
                xmax = self.xpos[i + 1]
                xmin = self.xpos[i]
                ymax = self.ypos[i + 1]
                ymin = self.ypos[i]
                nx = self.nx[i // 2]
                ny = self.ny[i // 2]
                nz = self.nz[i // 2]
                a = np.abs(xmax - xmin) / 2
                b = np.abs(ymax - ymin) / 2
                lz = abs(zmax - zmin)
                cx = (xmax + xmin) / 2
                cy = (ymax + ymin) / 2
                cz = (zmax + zmin) / 2
                strc += f"({cx / 5}, {cy / 5}, {cz / 5}), "
                strx += f"{round(a / 5, 3)},"
                stry += f"{round(b / 5, 3)},"
                strz += f"{lz / 5},"

                linvalz = abs(math.floor((self.z2 - self.z1) / (nz)))

                linvalx = abs(math.floor((xmax - xmin) / (nx)))
                linvaly = abs(math.floor((ymax - ymin) / (ny)))

                zvals = np.linspace(self.z1, self.z2, linvalz + 1)
                xpos = np.linspace(xmin, xmax, linvalx + 1)
                ypos = np.linspace(ymin, ymax, linvaly + 1)

                positions = []
                for z in range(0, len(zvals)):
                    for x in range(0, len(xpos)):
                        for y in range(0, len(ypos)):
                            if ((xpos[x] - cx) / a) ** 2 + (
                                (ypos[y] - cy) / b
                            ) ** 2 <= 1:
                                positions.append([xpos[x], ypos[y], zvals[z]])
                            else:
                                pass
                poslist.extend(positions)
            self.poslist = poslist
            strx = strx.rstrip(strx[-1])
            stry = stry.rstrip(stry[-1])
            strz = strz.rstrip(strz[-1])
            arg.la.setText(strx)
            arg.lb.setText(stry)
            arg.lc.setText(strz)
            strc = strc.rstrip(strc[-1])
            strc = strc.rstrip(strc[-1])
            arg.gridCentre.setText(strc)
            arg.ea.setText(str(len(xpos)))
            arg.eb.setText(str(len(ypos)))
            arg.ec.setText(str(len(zvals)))
        if self.grid == "circle":

            for i in range(bar, len(xs) - 1, 2):
                dr = self.nx[i // 2]
                dtheta = self.ny[i // 2] / 5
                dz = self.nz[i // 2]
                xposi = xs[i]
                xposi2 = xs[i + 1]

                yposi = ys[i]
                yposi2 = ys[i + 1]
                a = np.abs(xposi - xposi2) / 2
                b = np.abs(yposi - yposi2) / 2
                r = np.sqrt((xposi2 - xposi) ** 2 + (yposi - yposi2) ** 2) * 0.5
                lz = abs(zmax - zmin)

                strx += f"{round(a / 5, 3)},"
                stry += f"{round(b / 5, 3)},"
                strz += f"{lz / 5},"
                cx = (xposi + xposi2) / 2
                cy = (yposi + yposi2) / 2
                cz = (zmax + zmin) / 2
                strc += f"({cx / 5}, {cy / 5}, {cz / 5}), "
                xpos = [cx]
                ypos = [cy]
                linval = math.floor(r / dr)

                thetavals = np.linspace(0, 1, math.floor(360 / dtheta) + 1)
                parvals = np.linspace(0, 1, linval + 1)

                for t in parvals[1:]:
                    for z in thetavals[1:]:
                        xval = cx + t * r * np.cos(z * 2 * np.pi)
                        yval = cy + t * r * np.sin(z * 2 * np.pi)
                        if ((xval - cx) / a) ** 2 + ((yval - cy) / b) ** 2 <= 1:
                            xpos = np.append(xpos, xval)
                            ypos = np.append(ypos, yval)
                for z in range(0, len(zvals)):
                    zpos = z * np.ones(len(xpos))
                    positions = list(zip(xpos, ypos, zpos))
                    poslist = poslist + positions
            self.poslist = poslist
            strx = strx.rstrip(strx[-1])
            stry = stry.rstrip(stry[-1])
            strz = strz.rstrip(strz[-1])
            arg.la.setText(strx)
            arg.lb.setText(stry)
            arg.lc.setText(strz)
            strc = strc.rstrip(strc[-1])
            strc = strc.rstrip(strc[-1])
            arg.gridCentre.setText(strc)
            arg.ea.setText(str(len(xpos)))
            arg.eb.setText(str(len(ypos)))
            arg.ec.setText(str(len(zvals)))
        if self.grid == "sphere":

            zmax = max([self.z1, self.z2])
            zmin = min([self.z1, self.z2])

            for i in range(bar, len(xs) - 1, 2):
                dr = self.nx[i // 2]
                dtheta = self.ny[i // 2] / 5
                dphi = self.nz[i // 2] / 5
                xposi = xs[i]
                xposi2 = xs[i + 1]

                yposi = ys[i]
                yposi2 = ys[i + 1]

                a = np.abs(xposi - xposi2) / 2
                b = np.abs(yposi - yposi2) / 2
                r = (
                    np.sqrt(
                        (xposi2 - xposi) ** 2 + (yposi - yposi2) ** 2 + (zmax - zmin)
                    )
                    * 0.5
                )
                lz = abs(zmax - zmin)

                strx += f"{round(a / 5, 3)},"
                stry += f"{round(b / 5, 3)},"
                strz += f"{lz / 5},"
                cx = (xposi + xposi2) / 2
                cy = (yposi + yposi2) / 2
                cz = (zmax + zmin) / 2
                strc += f"({cx / 5}, {cy / 5}, {cz / 5}), "

                linval = math.floor(r / dr)

                thetavals = np.linspace(0, 1, math.floor(360 / dtheta) + 1)
                phivals = np.linspace(0, 1, math.floor(180 / dphi) + 1)
                parvals = np.linspace(0, 1, linval + 1)
                positions = [[cx, cy, cz]]
                # first start point already initialized in array.
                for t in parvals[1:]:
                    # Other start points are incorporated as the end points of
                    # previous segment.
                    for z in thetavals[1:]:
                        for p in phivals[1:]:
                            xval = cx + t * r * np.cos(z * 2 * np.pi) * np.sin(
                                p * np.pi
                            )
                            yval = cy + t * r * np.sin(z * 2 * np.pi) * np.sin(
                                p * np.pi
                            )
                            zval = cz + t * r * np.cos(p * np.pi)
                        if (
                            ((xval - cx) / a) ** 2 + ((yval - cy) / b) ** 2 > 1
                            or zval > zmax
                            or zval < zmin
                        ):
                            pass
                        else:
                            positions.append([xval, yval, zval])
                poslist = poslist + positions
            self.poslist = poslist
            strx = strx.rstrip(strx[-1])
            stry = stry.rstrip(stry[-1])
            strz = strz.rstrip(strz[-1])
            arg.la.setText(strx)
            arg.lb.setText(stry)
            arg.lc.setText(strz)
            strc = strc.rstrip(strc[-1])
            strc = strc.rstrip(strc[-1])
            arg.gridCentre.setText(strc)
            arg.ea.setText(str(len(xpos)))
            arg.eb.setText(str(len(ypos)))
            arg.ec.setText(str(len(zvals)))

    def checklist(self, arg):
        """
        Final verification routine to check no point is in a no-go
        region or an unreachable region.  Must be run to save the
        config/text coordinate files.
        """
        self.set_status(arg)
        xs = [x[0] for x in self.poslist]
        ys = [x[1] for x in self.poslist]
        alpha = self.alpha
        barlist = self.barlist * 5
        if self.hand == 0:
            theta = 0
        if self.hand == 1:
            theta = np.pi
        for i in range(0, len(xs)):
            dist = ((xs[i]) ** 2 + (ys[i]) ** 2) ** 0.5

            if dist > 250:
                arg.saveButton.setEnabled(False)

                msg = QMessageBox()
                msg.setIcon(QMessageBox.Critical)
                msg.setText("Error")
                msg.setInformativeText(
                    "Some designated points are outside of the machine!"
                )
                msg.setWindowTitle("Error")
                msg.exec_()
                return

            if theta < np.pi:
                if (
                    ys[i]
                    - 250 * np.sin(theta)
                    - (
                        (np.sin(theta) + np.sin(2 * alpha + theta))
                        / (np.cos(theta) + np.cos(2 * alpha + theta))
                    )
                    * (xs[i] - 250 * np.cos(theta))
                    < 0
                ):
                    arg.saveButton.setEnabled(False)
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Critical)
                    msg.setText("Error")
                    msg.setInformativeText(
                        "Some designated points are outside of reach!!"
                    )
                    msg.setWindowTitle("Error")
                    msg.exec_()
                    return
                elif (
                    ys[i]
                    - 250 * np.sin(theta)
                    - (
                        (np.sin(theta) - np.sin(2 * alpha - theta))
                        / (np.cos(theta) + np.cos(2 * alpha - theta))
                    )
                    * (xs[i] - 250 * np.cos(theta))
                    > 0
                ):
                    arg.saveButton.setEnabled(False)
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Critical)
                    msg.setText("Error")
                    msg.setInformativeText(
                        "Some designated points are outside of reach!"
                    )
                    msg.setWindowTitle("Error")
                    msg.exec_()
                    return
            if theta >= np.pi:
                if (
                    ys[i]
                    - 250 * np.sin(theta)
                    - (
                        (np.sin(theta) + np.sin(2 * alpha + theta))
                        / (np.cos(theta) + np.cos(2 * alpha + theta))
                    )
                    * (xs[i] - 250 * np.cos(theta))
                    > 0
                ):
                    arg.saveButton.setEnabled(False)
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Critical)
                    msg.setText("Error")
                    msg.setInformativeText(
                        "Some designated points are outside of reach!!"
                    )
                    msg.setWindowTitle("Error")
                    msg.exec_()
                    return
                elif (
                    ys[i]
                    - 250 * np.sin(theta)
                    - (
                        (np.sin(theta) - np.sin(2 * alpha - theta))
                        / (np.cos(theta) + np.cos(2 * alpha - theta))
                    )
                    * (xs[i] - 250 * np.cos(theta))
                    < 0
                ):
                    arg.saveButton.setEnabled(False)
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Critical)
                    msg.setText("Error")
                    msg.setInformativeText(
                        "Some designated points are outside of reach!"
                    )
                    msg.setWindowTitle("Error")
                    msg.exec_()
                    return
            ######################## NO-GO ZONE CHECKS ################
            if theta >= np.pi:
                # posgroup is [(xorg,y,z),(xe),(xvo),(xve)]
                for posgroup in barlist:
                    if posgroup[0][0] - posgroup[1][0] == 0:
                        m1 = 1
                    else:
                        m1 = (posgroup[0][1] - posgroup[1][1]) / (
                            posgroup[0][0] - posgroup[1][0]
                        )
                        m2 = (posgroup[0][1] - posgroup[2][1]) / (
                            posgroup[0][0] - posgroup[2][0]
                        )
                        m3 = (posgroup[1][1] - posgroup[3][1]) / (
                            posgroup[1][0] - posgroup[3][0]
                        )
                    if (
                        (
                            ys[i] - m1 * (xs[i] - posgroup[0][0]) - posgroup[0][1] > 0
                            and m1 < 0
                        )
                        or (
                            ys[i] - m1 * (xs[i] - posgroup[0][0]) - posgroup[0][1] < 0
                            and m1 > 0
                        )
                    ) and (
                        (
                            (ys[i] - m2 * (xs[i] - posgroup[0][0]) - posgroup[0][1] < 0)
                            and (
                                ys[i]
                                - m3 * (xs[i] + m3 * posgroup[1][0])
                                - posgroup[1][1]
                                > 0
                            )
                            and (posgroup[0][1] > posgroup[1][1])
                        )
                        or (
                            (ys[i] - m2 * (xs[i] - posgroup[0][0]) - posgroup[0][1] > 0)
                            and (
                                ys[i]
                                - m3 * (xs[i] + m3 * posgroup[1][0])
                                - posgroup[1][1]
                                < 0
                            )
                            and (posgroup[0][1] < posgroup[1][1])
                        )
                    ):
                        arg.saveButton.setEnabled(False)
                        msg = QMessageBox()
                        msg.setIcon(QMessageBox.Critical)
                        msg.setText("Error")
                        msg.setInformativeText(
                            "Some designated points are in No-go zone!!"
                        )
                        msg.setWindowTitle("Error")
                        msg.exec_()
                        return
            if theta < np.pi:
                # posgroup is [(xorg,y,z),(xe),(xvo),(xve)]
                # posgroup is [(xorg,y,z),(xe),(xvo),(xve)]
                for posgroup in barlist:
                    if posgroup[0][0] - posgroup[1][0] == 0:
                        m1 = 1
                    else:
                        m1 = (posgroup[0][1] - posgroup[1][1]) / (
                            posgroup[0][0] - posgroup[1][0]
                        )
                        m2 = (posgroup[0][1] - posgroup[2][1]) / (
                            posgroup[0][0] - posgroup[2][0]
                        )
                        m3 = (posgroup[1][1] - posgroup[3][1]) / (
                            posgroup[1][0] - posgroup[3][0]
                        )
                    if (
                        (
                            ys[i] - m1 * (xs[i] - posgroup[0][0]) - posgroup[0][1] > 0
                            and m1 > 0
                        )
                        or (
                            ys[i] - m1 * (xs[i] - posgroup[0][0]) - posgroup[0][1] < 0
                            and m1 < 0
                        )
                    ) and (
                        (
                            (ys[i] - m2 * (xs[i] - posgroup[0][0]) - posgroup[0][1] < 0)
                            and (
                                ys[i]
                                - m3 * (xs[i] + m3 * posgroup[1][0])
                                - posgroup[1][1]
                                > 0
                            )
                            and (posgroup[0][1] > posgroup[1][1])
                        )
                        or (
                            (ys[i] - m2 * (xs[i] - posgroup[0][0]) - posgroup[0][1] > 0)
                            and (
                                ys[i]
                                - m3 * (xs[i] + m3 * posgroup[1][0])
                                - posgroup[1][1]
                                < 0
                            )
                            and (posgroup[0][1] < posgroup[1][1])
                        )
                    ):
                        arg.saveButton.setEnabled(False)
                        msg = QMessageBox()
                        msg.setIcon(QMessageBox.Critical)
                        msg.setText("Error")
                        msg.setInformativeText(
                            "Some designated points are in No-go zone!!"
                        )
                        msg.setWindowTitle("Error")
                        msg.exec_()
                        return
        arg.saveButton.setEnabled(True)

    def coordEnter(self, arg, n=0):
        """
        Massive function, should probably be restructured, rewritten?
        Same functionality as print_position() + get_*mode*_positions(),
        Used when precise coordinates are fed by the user to the module.
        """

        bar = arg.barcord.text()
        barlist = []

        if self.hand == 0:
            theta = 0
        if self.hand == 1:
            theta = np.pi
        try:
            if n == 0:
                str1 = arg.coordinates.text()
                # split the string by , in order to get an array
                str1 = np.array(
                    str1.replace("(", "").replace(")", "").split(","), dtype=float
                ).reshape(-1, 3)
            else:
                str1 = n
                str1 = np.array(
                    str1.replace("(", "").replace(")", "").split(","), dtype=float
                ).reshape(-1, 3)
        except ValueError:
            pass
            # QMessageBox.about(
            #     self,
            #     "Error",
            #     "Coordinates and number of points should be valid numbers. "
            #     "Coordinates should be specified as (x,y,z), (x,y,z)",
            # )

        if bar[0] == "(":
            try:
                bar = np.array(
                    bar.replace("(", "").replace(")", "").split(","), dtype=float
                ).reshape(-1, 3)
                xs = [5 * x[0] for x in bar]
                ys = [5 * x[1] for x in bar]
                zs = [5 * x[2] for x in bar]

                for i in range(0, len(xs) - 1, 2):
                    res = min(self.nx[i // 2], self.ny[i // 2], self.nz[i // 2])
                    xe = xs[i + 1]
                    xorg = xs[i]
                    ye = ys[i + 1]
                    yorg = ys[i]
                    r = 250

                    if theta >= np.pi:
                        C = (yorg - r * np.sin(theta)) / (xorg - r * np.cos(theta))

                        a = 1 + C**2
                        b = -2 * xorg * (C**2) + 2 * C * yorg
                        c = (C**2) * xorg + yorg**2 - 2 * C * yorg * xorg - r**2

                        xvo = (-b + np.sqrt(b**2 - 4 * a * c)) / (2 * a)

                        yvo = C * (xvo - xorg) + yorg

                        C = (ye - r * np.sin(theta)) / (xe - r * np.cos(theta))

                        a = 1 + C**2
                        b = -2 * xe * (C**2) + 2 * C * ye
                        c = (C**2) * xe + ye**2 - 2 * C * ye * xe - r**2

                        xve = (-b + np.sqrt(b**2 - 4 * a * c)) / (2 * a)

                        yve = C * (xve - xe) + ye
                    if theta < np.pi:
                        C = (yorg - r * np.sin(theta)) / (xorg - r * np.cos(theta))

                        a = 1 + C**2
                        b = -2 * xorg * (C**2) + 2 * C * yorg
                        c = (C**2) * xorg + yorg**2 - 2 * C * yorg * xorg - r**2

                        xvo = (-b - np.sqrt(b**2 - 4 * a * c)) / (2 * a)

                        yvo = C * (xvo - xorg) + yorg

                        C = (ye - r * np.sin(theta)) / (xe - r * np.cos(theta))

                        a = 1 + C**2
                        b = -2 * xe * (C**2) + 2 * C * ye
                        c = (C**2) * xe + ye**2 - 2 * C * ye * xe - r**2

                        xve = (-b - np.sqrt(b**2 - 4 * a * c)) / (2 * a)

                        yve = C * (xve - xe) + ye
                    p = QPainter(self.pixmap())
                    p.setPen(
                        QPen(
                            QColor(Qt.red),
                            self.config["size"],
                            Qt.SolidLine,
                            Qt.RoundCap,
                            Qt.RoundJoin,
                        )
                    )
                    p.setBrush(QBrush(QColor(Qt.red)))
                    p.drawLine(
                        QPointF(xorg + 300, -yorg + 300), QPointF(xvo + 300, -yvo + 300)
                    )
                    p.drawLine(
                        QPointF(xe + 300, -ye + 300), QPointF(xve + 300, -yve + 300)
                    )

                    p.setPen(
                        QPen(
                            QColor("#800000"),
                            self.config["size"],
                            Qt.SolidLine,
                            Qt.RoundCap,
                            Qt.RoundJoin,
                        )
                    )
                    p.drawLine(
                        QPointF(xorg + 300, -yorg + 300), QPointF(xe + 300, -ye + 300)
                    )

                    p.end()
                    barlist.append(
                        [
                            (xorg, yorg, self.z1),
                            (xe, ye, self.z1),
                            (xvo, yvo, self.z1),
                            (xve, yve, self.z1),
                        ]
                    )

                    barlist = np.array(barlist) / 5
                    self.barlist = barlist
            except ValueError:
                pass
        # p.end()
        p = QPainter(self.pixmap())
        p.setPen(
            QPen(
                QColor(Qt.blue),
                self.config["size"],
                Qt.SolidLine,
                Qt.RoundCap,
                Qt.RoundJoin,
            )
        )
        p.setBrush(QBrush(QColor(Qt.blue)))
        p.setOpacity(0.5)

        if self.mode == "polyline":

            try:

                xs = [5 * x[0] for x in str1]
                ys = [5 * x[1] for x in str1]
                zs = [5 * x[2] for x in str1]

                xpos = [xs[0]]
                ypos = [ys[0]]
                zpos = [zs[0]]
                self.xpos = xs
                self.ypos = ys
                self.zpos = zs
                p.setPen(
                    QPen(
                        QColor(Qt.black),
                        self.config["size"],
                        Qt.SolidLine,
                        Qt.RoundCap,
                        Qt.RoundJoin,
                    )
                )
                p.setBrush(QBrush(QColor(Qt.black)))

                index = -1 if self.closeit else 0
                for i in range(index, len(xs) - 1):
                    p.drawLine(
                        QPointF(xs[i] + 300, -ys[i] + 300),
                        QPointF(xs[i + 1] + 300, -ys[i + 1] + 300),
                    )
                for i in range(index, len(xs) - 1):
                    res = min(self.nx[i], self.ny[i], self.nz[i])
                    xposi = xs[i]
                    xposi2 = xs[i + 1]

                    yposi = ys[i]
                    yposi2 = ys[i + 1]

                    zposi = zs[i]
                    zposi2 = zs[i + 1]

                    length = (
                        (xposi2 - xposi) ** 2
                        + (yposi2 - yposi) ** 2
                        + (zposi2 - zposi) ** 2
                    ) ** 0.5
                    linval = math.floor(length / res)

                    parvals = np.linspace(0, 1, linval + 1)

                    for t in parvals[1:]:

                        xval = xposi + t * (xposi2 - xposi)
                        yval = yposi + t * (yposi2 - yposi)
                        zval = zposi + t * (zposi2 - zposi)
                        xpos = np.append(xpos, xval)
                        ypos = np.append(ypos, yval)
                        zpos = np.append(zpos, zval)
                positions = list(zip(xpos, ypos, zpos))
                self.poslist = positions
            except ValueError:
                QMessageBox.about(self, "Error", "Position should be valid numbers.")
        elif self.mode == "line":

            try:

                xs = [5 * x[0] for x in str1]
                ys = [5 * x[1] for x in str1]
                zs = [5 * x[2] for x in str1]
                xpos = [xs[0]]
                ypos = [ys[0]]
                zpos = [zs[0]]
                self.xpos = xs
                self.ypos = ys
                self.zpos = zs
                p.setPen(
                    QPen(
                        QColor(Qt.black),
                        self.config["size"],
                        Qt.SolidLine,
                        Qt.RoundCap,
                        Qt.RoundJoin,
                    )
                )
                p.setBrush(QBrush(QColor(Qt.black)))

                for i in range(0, len(xs) - 1, 2):
                    p.drawLine(
                        QPointF(xs[i] + 300, -ys[i] + 300),
                        QPointF(300 + xs[i + 1], -ys[i + 1] + 300),
                    )
                for i in range(0, len(xs) - 1, 2):
                    res = min(self.nx[i // 2], self.ny[i // 2], self.nz[i // 2])

                    xposi = xs[i]
                    xposi2 = xs[i + 1]

                    yposi = ys[i]
                    yposi2 = ys[i + 1]

                    zposi = zs[i]
                    zposi2 = zs[i + 1]

                    length = (
                        (xposi2 - xposi) ** 2
                        + (yposi2 - yposi) ** 2
                        + (zposi2 - zposi) ** 2
                    ) ** 0.5
                    linval = math.floor(length / res)

                    parvals = np.linspace(0, 1, linval + 1)

                    for t in parvals[1:]:

                        xval = xposi + t * (xposi2 - xposi)
                        yval = yposi + t * (yposi2 - yposi)
                        zval = zposi + t * (zposi2 - zposi)
                        xpos = np.append(xpos, xval)
                        ypos = np.append(ypos, yval)
                        zpos = np.append(zpos, zval)
                positions = list(zip(xpos, ypos, zpos))
                self.poslist = positions
            except ValueError:
                QMessageBox.about(self, "Error", "Position should be valid numbers.")
        elif self.mode == "rect":

            if self.grid == "rect":

                try:

                    xs = [5 * x[0] for x in str1]
                    ys = [5 * x[1] for x in str1]
                    zs = [5 * x[2] for x in str1]
                    self.xpos = xs
                    self.ypos = ys
                    self.zpos = zs

                    poslist = []
                    for i in range(0, len(self.xpos) - 1, 2):
                        p.drawRect(
                            QRectF(
                                xs[i] + 300,
                                -ys[i] + 300,
                                xs[i + 1] - xs[i],
                                -ys[i + 1] + ys[i],
                            )
                        )
                        nx = self.nx[i // 2]
                        ny = self.ny[i // 2]
                        nz = self.nz[i // 2]

                        xmax = self.xpos[i + 1]
                        xmin = self.xpos[i]
                        ymax = self.ypos[i + 1]
                        ymin = self.ypos[i]
                        zmax = self.zpos[i + 1]
                        zmin = self.zpos[i]
                        cx = (xmax + xmin) / 2
                        cy = (ymax + ymin) / 2
                        cz = (zmax + zmin) / 2
                        linvalz = abs(math.floor((zmax - zmin) / (nz)))
                        linvalx = abs(math.floor((xmax - xmin) / (nx)))
                        linvaly = abs(math.floor((ymax - ymin) / (ny)))
                        zvals = np.linspace(zmin, zmax, linvalz + 1)
                        xvals = np.linspace(xmin, xmax, linvalx + 1)
                        yvals = np.linspace(ymin, ymax, linvaly + 1)

                        positions = []
                        for z in zvals:
                            for x in xvals:
                                for y in yvals:
                                    positions.append([x, y, z])
                        poslist.extend(positions)
                        # print(poslist)
                    self.poslist = poslist
                except ValueError:
                    QMessageBox.about(
                        self, "Error", "Position should be valid numbers."
                    )
            if self.grid == "circle":

                try:

                    xs = [5 * x[0] for x in str1]
                    ys = [5 * x[1] for x in str1]
                    zs = [5 * x[2] for x in str1]
                    self.xpos = xs
                    self.ypos = ys
                    self.zpos = zs

                    xpos = []
                    ypos = []
                    poslist = []
                    for i in range(0, len(self.xpos) - 1, 2):
                        p.drawRect(
                            QRectF(
                                xs[i] + 300,
                                -ys[i] + 300,
                                xs[i + 1] - xs[i],
                                -ys[i + 1] + ys[i],
                            )
                        )
                        dr = self.nx[i // 2]
                        dtheta = self.ny[i // 2] / 5
                        nz = self.nz[i // 2]
                        xmax = max([self.xpos[i + 1], self.xpos[i]])
                        xmin = min([self.xpos[i + 1], self.xpos[i]])
                        ymax = max([self.ypos[i + 1], self.ypos[i]])
                        ymin = min([self.ypos[i + 1], self.ypos[i]])
                        zmax = max([self.zpos[i + 1], self.zpos[i]])
                        zmin = min([self.zpos[i + 1], self.zpos[i]])

                        linvalz = abs(math.floor((zmax - zmin) / (nz)))
                        cx = (xmax + xmin) / 2
                        cy = (ymax + ymin) / 2
                        cz = (zmax + zmin) / 2
                        # if self.centers == '':
                        #     cx = (xmax+xmin)/2
                        #     cy = (ymax+ymin)/2
                        #     cz = (zmax+zmin)/2
                        # else:
                        #     str1 = self.centers
                        #     str1 = np.array(
                        #         str1.replace('(', '').replace(')', '').split(','),
                        #         dtype=float,
                        #     ).reshape(-1, 3)
                        #     xs1 = [5*x[0] for x in str1]
                        #     ys1 = [5*x[1] for x in str1]
                        #     zs1 = [5*x[2] for x in str1]
                        #     cx = (xs1[i] + xs1[i+1])/2
                        #     cy = (ys1[i] + ys1[i+1])/2
                        #     cz = (zs1[i] + zs1[i+1])/2
                        # NEED TO RECALCULATE POINT GENERATING PARAMETERS TO GET
                        # APPROPRIATE ONES WITHIN THE REGION.
                        zvals = np.linspace(zmin, zmax, linvalz + 1)

                        r = 0.5 * (np.sqrt((xmax - xmin) ** 2 + (ymax - ymin) ** 2))

                        linval = math.floor(r / (dr))

                        thetavals = np.linspace(0, 1, math.floor(360 / dtheta) + 1)
                        parvals = np.linspace(0, 1, linval + 1)
                        positions = []
                        for t in parvals[1:]:
                            for z in thetavals[1:]:
                                xval = cx + t * r * np.cos(z * 2 * np.pi)
                                yval = cy + t * r * np.sin(z * 2 * np.pi)

                                if (
                                    (xval > xmax)
                                    or xval < xmin
                                    or yval > ymax
                                    or yval < ymin
                                ):
                                    pass
                                else:
                                    xpos = np.append(xpos, xval)
                                    ypos = np.append(ypos, yval)
                        for z in zvals:
                            zpos = z * np.ones(len(xpos))
                            positions = list(zip(xpos, ypos, zpos))
                            poslist = poslist + positions
                        self.poslist = poslist
                except ValueError:
                    QMessageBox.about(
                        self, "Error", "Position should be valid numbers."
                    )
            if self.grid == "ellipse":

                try:

                    xs = [5 * x[0] for x in str1]
                    ys = [5 * x[1] for x in str1]
                    zs = [5 * x[2] for x in str1]
                    self.xpos = xs
                    self.ypos = ys
                    self.zpos = zs

                    e = self.eccentricity
                    xpos = []
                    ypos = []
                    poslist = []
                    for i in range(0, len(self.xpos) - 1, 2):
                        dr = self.nx[i // 2]
                        dtheta = self.ny[i // 2] / 5
                        dz = self.nz[i // 2]
                        p.drawRect(
                            QRectF(
                                xs[i] + 300,
                                -ys[i] + 300,
                                xs[i + 1] - xs[i],
                                -ys[i + 1] + ys[i],
                            )
                        )

                        xmax = max([self.xpos[i + 1], self.xpos[i]])
                        xmin = min([self.xpos[i + 1], self.xpos[i]])
                        ymax = max([self.ypos[i + 1], self.ypos[i]])
                        ymin = min([self.ypos[i + 1], self.ypos[i]])
                        zmax = max([self.zpos[i + 1], self.zpos[i]])
                        zmin = min([self.zpos[i + 1], self.zpos[i]])
                        # if self.centers == '':
                        #     cx = (xmax+xmin)/2
                        #     cy = (ymax+ymin)/2
                        #     cz = (zmax+zmin)/2
                        # else:
                        #     str1 = self.centers
                        #     str1 = np.array(
                        #         str1.replace('(', '').replace(')', '').split(','),
                        #         dtype=float,
                        #     ).reshape(-1, 3)
                        #     xs1 = [5*x[0] for x in str1]
                        #     ys1 = [5*x[1] for x in str1]
                        #     zs1 = [5*x[2] for x in str1]
                        #     cx = (xs1[i] + xs1[i+1])/2
                        #     cy = (ys1[i] + ys1[i+1])/2
                        #     cz = (zs1[i] + zs1[i+1])/2
                        cx = (xmax + xmin) / 2
                        cy = (ymax + ymin) / 2
                        cz = (zmax + zmin) / 2
                        # NEED TO RECALCULATE POINT GENERATING PARAMETERS TO GET
                        # APPROPRIATE ONES WITHIN THE REGION.
                        linvalz = abs(math.floor((zmax - zmin) / (dz)))
                        zvals = np.linspace(zmin, zmax, linvalz + 1)

                        a = max([(xmax - xmin), (ymax - ymin)])
                        b = a * np.sqrt(1 - e**2)

                        xpos = np.append(xpos, cx)
                        ypos = np.append(ypos, cy)

                        linval = math.floor((min([a, b])) / (dr))

                        thetavals = np.linspace(0, 1, math.floor(360 / dtheta) + 1)
                        parvals = np.linspace(0, 1, linval + 1)

                        for t in parvals[1:]:
                            for z in thetavals[1:]:
                                xval = cx + t * a * np.cos(z * 2 * np.pi)
                                yval = cy + t * b * np.sin(z * 2 * np.pi)
                                if (
                                    (xval > xmax)
                                    or xval < xmin
                                    or yval > ymax
                                    or yval < ymin
                                ):
                                    pass
                                else:
                                    xpos = np.append(xpos, xval)
                                    ypos = np.append(ypos, yval)
                        for z in zvals:
                            zpos = z * np.ones(len(xpos))
                            positions = list(zip(xpos, ypos, zpos))
                            poslist = poslist + positions
                    self.poslist = poslist
                except ValueError:
                    QMessageBox.about(
                        self, "Error", "Position should be valid numbers."
                    )
            if self.grid == "sphere":

                try:

                    xs = [5 * x[0] for x in str1]
                    ys = [5 * x[1] for x in str1]
                    zs = [5 * x[2] for x in str1]
                    self.xpos = xs
                    self.ypos = ys
                    self.zpos = zs

                    poslist = []
                    for i in range(0, len(self.xpos) - 1, 2):
                        dr = self.nx[i // 2]
                        dtheta = self.ny[i // 2] / 5
                        dphi = self.nz[i // 2] / 5
                        p.drawRect(
                            QRectF(
                                xs[i] + 300,
                                -ys[i] + 300,
                                xs[i + 1] - xs[i],
                                -ys[i + 1] + ys[i],
                            )
                        )
                        xmax = max([self.xpos[i + 1], self.xpos[i]])
                        xmin = min([self.xpos[i + 1], self.xpos[i]])
                        ymax = max([self.ypos[i + 1], self.ypos[i]])
                        ymin = min([self.ypos[i + 1], self.ypos[i]])
                        zmax = max([self.zpos[i + 1], self.zpos[i]])
                        zmin = min([self.zpos[i + 1], self.zpos[i]])

                        # if self.centers == '':
                        #     cx = (xmax+xmin)/2
                        #     cy = (ymax+ymin)/2
                        #     cz = (zmax+zmin)/2
                        # else:
                        #     str1 = self.centers
                        #     str1 = np.array(
                        #         str1.replace('(', '').replace(')', '').split(','),
                        #         dtype=float,
                        #     ).reshape(-1, 3)
                        #     xs1 = [5*x[0] for x in str1]
                        #     ys1 = [5*x[1] for x in str1]
                        #     zs1 = [5*x[2] for x in str1]
                        #     cx = (xs1[i] + xs1[i+1])/2
                        #     cy = (ys1[i] + ys1[i+1])/2
                        #     cz = (zs1[i] + zs1[i+1])/2
                        # NEED TO RECALCULATE POINT GENERATING PARAMETERS TO GET APPROPRIATE ONES WITHIN THE REGION.
                        cx = (xmax + xmin) / 2
                        cy = (ymax + ymin) / 2
                        cz = (zmax + zmin) / 2
                        r = np.sqrt(
                            (xmax - xmin) ** 2 + (ymax - ymin) ** 2 + (zmax - zmin) ** 2
                        )

                        linval = math.floor(r / (dr))

                        thetavals = np.linspace(0, 1, math.floor(360 / dtheta) + 1)
                        phivals = np.linspace(0, 1, math.floor(180 / dphi) + 1)
                        parvals = np.linspace(0, 1, linval + 1)
                        positions = [[cx, cy, cz]]
                        for t in parvals[1:]:
                            for z in thetavals[1:]:
                                for p in phivals[1:]:
                                    xval = cx + t * r * np.cos(z * 2 * np.pi) * np.sin(
                                        p * np.pi
                                    )
                                    yval = cy + t * r * np.sin(z * 2 * np.pi) * np.sin(
                                        p * np.pi
                                    )
                                    zval = cz + t * r * np.cos(p * np.pi)
                                    if (
                                        (xval > xmax)
                                        or xval < xmin
                                        or yval > ymax
                                        or yval < ymin
                                        or zval > zmax
                                        or zval < zmin
                                    ):
                                        pass
                                    else:
                                        positions.append([xval, yval, zval])
                        poslist.extend(positions)
                    self.poslist = poslist
                except ValueError:
                    QMessageBox.about(
                        self, "Error", "Position should be valid numbers."
                    )
        elif self.mode == "circle":

            if self.grid == "circle":
                poslist = []
                bar = self.bar

                try:

                    xs = [5 * x[0] for x in str1]
                    ys = [5 * x[1] for x in str1]
                    zs = [5 * x[2] for x in str1]
                    self.xpos = xs
                    self.ypos = ys
                    self.zpos = zs

                    poslist = []

                    for i in range(0, len(self.xpos) - 1, 2):
                        dr = self.nx[i // 2]
                        dtheta = self.ny[i // 2] / 5
                        nz = self.nz[i // 2]

                        xpos = []
                        ypos = []
                        xposi = xs[i]
                        xposi2 = xs[i + 1]

                        yposi = ys[i]
                        yposi2 = ys[i + 1]

                        zmax = zs[i + 1]
                        zmin = zs[i]
                        linvalz = abs(math.floor((zmax - zmin) / (nz)))

                        xpos = np.append(xpos, xposi)
                        ypos = np.append(ypos, yposi)
                        zvals = np.linspace(zmin, zmax, linvalz + 1)
                        r = np.sqrt((xposi - xposi2) ** 2 + (yposi - yposi2) ** 2)

                        p.drawEllipse(QPointF(xs[i] + 300, -ys[i] + 300), r, r)
                        linval = math.floor(r / (dr))

                        thetavals = np.linspace(0, 1, math.floor(360 / dtheta) + 1)
                        parvals = np.linspace(0, 1, linval + 1)

                        for t in parvals[1:]:
                            for th in thetavals[1:]:
                                xval = xposi + t * r * np.cos(th * 2 * np.pi)
                                yval = yposi + t * r * np.sin(th * 2 * np.pi)

                                xpos = np.append(xpos, xval)
                                ypos = np.append(ypos, yval)
                        for z in zvals:
                            zpos = z * np.ones(len(xpos))
                            positions = list(zip(xpos, ypos, zpos))
                            poslist = poslist + positions
                    self.poslist = poslist
                except ValueError:
                    QMessageBox.about(
                        self, "Error", "Position should be valid numbers."
                    )
            if self.grid == "rect":
                poslist = []
                bar = self.bar

                try:

                    xs = [5 * x[0] for x in str1]
                    ys = [5 * x[1] for x in str1]
                    zs = [5 * x[2] for x in str1]
                    self.xpos = xs
                    self.ypos = ys
                    self.zpos = zs

                    poslist = []
                    xpos = []
                    ypos = []
                    zpos = []

                    for i in range(0, len(self.xpos) - 1, 2):
                        nx = self.nx[i // 2]
                        ny = self.ny[i // 2]
                        nz = self.nz[i // 2]
                        xposi = xs[i]
                        xposi2 = xs[i + 1]

                        yposi = ys[i]
                        yposi2 = ys[i + 1]

                        zmax = zs[i + 1]
                        zmin = zs[i]
                        cx = xposi
                        cy = yposi
                        cz = (zmax + zmin) / 2
                        # if self.centers == '':
                        #     cx = xposi
                        #     cy = yposi
                        #     cz = (zmax+zmin)/2
                        # else:
                        #     str1 = self.centers
                        #     str1 = np.array(
                        #         str1.replace('(', '').replace(')', '').split( ','),
                        #         dtype=float,
                        #     ).reshape(-1, 3)
                        #     xs = [5*x[0] for x in str1]
                        #     ys = [5*x[1] for x in str1]
                        #     zs = [5*x[2] for x in str1]
                        #     cx = xs[i]
                        #     cy = ys[i]
                        #     cz = zs[i]

                        r = np.sqrt((xposi - xposi2) ** 2 + (yposi - yposi2) ** 2)
                        xmax = cx + r
                        xmin = cx - r
                        ymax = cy + r
                        ymin = cy - r

                        p.drawEllipse(QPointF(xs[i] + 300, -ys[i] + 300), r, r)

                        linvalz = abs(math.floor((zmax - zmin) / (nz)))

                        linvalx = abs(math.floor((xmax - xmin) / (nx)))
                        linvaly = abs(math.floor((ymax - ymin) / (ny)))

                        zvals = np.linspace(zmin, zmax, linvalz + 1)
                        xvals = np.linspace(xmin, xmax, linvalx + 1)
                        yvals = np.linspace(ymin, ymax, linvaly + 1)

                        positions = []
                        for z in zvals:
                            for x in xvals:
                                for y in yvals:
                                    if (
                                        (xvals[x] - cx) ** 2 + (yvals[y] - cy) ** 2
                                        <= r**2
                                        and zvals[z] <= zmax
                                        and zvals[z] >= zmin
                                    ):
                                        positions.append([xvals[x], yvals[y], zvals[z]])
                                    else:
                                        pass
                    poslist.extend(positions)
                    self.poslist = poslist
                except ValueError:
                    QMessageBox.about(
                        self, "Error", "Position should be valid numbers."
                    )
            if self.grid == "sphere":
                poslist = []
                bar = self.bar

                try:

                    xs = [5 * x[0] for x in str1]
                    ys = [5 * x[1] for x in str1]
                    zs = [5 * x[2] for x in str1]
                    self.xpos = xs
                    self.ypos = ys
                    self.zpos = zs

                    poslist = []

                    for i in range(0, len(self.xpos) - 1, 2):
                        dr = self.nx[i // 2]
                        dtheta = self.ny[i // 2] / 5
                        dphi = self.nz[i // 2] / 5

                        xposi = xs[i]
                        xposi2 = xs[i + 1]

                        yposi = ys[i]
                        yposi2 = ys[i + 1]

                        zmax = zs[i + 1]
                        zmin = zs[i]
                        cx = xposi
                        cy = yposi
                        cz = (zmax + zmin) / 2
                        # if self.centers == '':
                        #     cx = xposi
                        #     cy = yposi
                        #     cz = (zmax+zmin)/2
                        # else:
                        #     str1 = self.centers
                        #     str1 = np.array(
                        #         str1.replace('(', '').replace(')', '').split(','),
                        #         dtype=float,
                        #     ).reshape(-1, 3)
                        #     xs = [5*x[0] for x in str1]
                        #     ys = [5*x[1] for x in str1]
                        #     zs = [5*x[2] for x in str1]
                        #     cx = xs[i]
                        #     cy = ys[i]
                        #     cz = zs[i]

                        rc = np.sqrt((xposi - xposi2) ** 2 + (yposi - yposi2) ** 2)
                        xmax = cx + rc
                        xmin = cx - rc
                        ymax = cy + rc
                        ymin = cy - rc

                        p.drawEllipse(QPointF(xs[i] + 300, -ys[i] + 300), rc, rc)

                        r = 0.5 * (
                            np.sqrt((xmax - xmin) ** 2 + (ymax - ymin) ** 2)
                            + (zmax - zmin) ** 2
                        )

                        linval = math.floor(r / dr)

                        thetavals = np.linspace(0, 1, math.floor(360 / dtheta) + 1)
                        phivals = np.linspace(0, 1, math.floor(180 / dphi) + 1)
                        parvals = np.linspace(0, 1, linval + 1)
                        positions = [[cx, cy, cz]]
                        # first start point already initialized in array.
                        for t in parvals[1:]:
                            # Other start points are incorporated as the end points
                            # of previous segment.
                            for z in thetavals[1:]:
                                for p in phivals[1:]:
                                    xval = cx + t * r * np.cos(z * 2 * np.pi) * np.sin(
                                        p * np.pi
                                    )
                                    yval = cy + t * r * np.sin(z * 2 * np.pi) * np.sin(
                                        p * np.pi
                                    )
                                    zval = cz + t * r * np.cos(p * np.pi)
                                if (
                                    (xval - cx) ** 2 + (yval - cy) ** 2 > rc**2
                                    or zval > zmax
                                    or zval < zmin
                                ):
                                    pass
                                else:
                                    positions.append([xval, yval, zval])
                        poslist = poslist + positions
                    self.poslist = poslist
                except ValueError:
                    QMessageBox.about(
                        self, "Error", "Position should be valid numbers."
                    )
            if self.grid == "ellipse":
                poslist = []
                bar = self.bar

                try:

                    xs = [5 * x[0] for x in str1]
                    ys = [5 * x[1] for x in str1]
                    zs = [5 * x[2] for x in str1]
                    self.xpos = xs
                    self.ypos = ys
                    self.zpos = zs

                    e = self.eccentricity
                    poslist = []
                    xpos = []
                    ypos = []
                    for i in range(0, len(self.xpos) - 1, 2):
                        dr = self.nx[i // 2]
                        dtheta = self.ny[i // 2] / 5
                        dz = self.nz[i // 2]

                        xposi = xs[i]
                        xposi2 = xs[i + 1]

                        yposi = ys[i]
                        yposi2 = ys[i + 1]

                        zmax = zs[i + 1]
                        zmin = zs[i]
                        linvalz = abs(math.floor((zmax - zmin) / dz))

                        zvals = np.linspace(zmin, zmax, linvalz + 1)
                        b = np.sqrt((xposi - xposi2) ** 2 + (yposi - yposi2) ** 2)
                        a = b / np.sqrt(1 - e**2)
                        # zposi = zs[i]
                        # zposi2 = zs[i+1]

                        cx = xposi
                        cy = yposi
                        cz = (zmax + zmin) / 2
                        xpos = np.append(xpos, cx)
                        ypos = np.append(ypos, cy)

                        p.drawEllipse(QPointF(xs[i] + 300, -ys[i] + 300), r, r)
                        linval = math.floor((min([a, b])) / dr)

                        thetavals = np.linspace(0, 1, math.floor(360 / dtheta) + 1)
                        parvals = np.linspace(0, 1, linval + 1)

                        for t in parvals[1:]:
                            for z in thetavals[1:]:
                                xval = cx + t * a * np.cos(z * 2 * np.pi)
                                yval = cy + t * b * np.sin(z * 2 * np.pi)
                                if (xval - cx) ** 2 + (yval - cy) ** 2 <= b**2:
                                    xpos = np.append(xpos, xval)
                                    ypos = np.append(ypos, yval)
                        for z in zvals:
                            zpos = z * np.ones(len(xpos))
                            positions = list(zip(xpos, ypos, zpos))
                            poslist = poslist + positions
                    self.poslist = poslist
                except ValueError:
                    QMessageBox.about(
                        self, "Error", "Position should be valid numbers."
                    )
        elif self.mode == "ellipse":

            if self.grid == "ellipse":
                poslist = []
                bar = self.bar

                try:

                    xs = [5 * x[0] for x in str1]
                    ys = [5 * x[1] for x in str1]
                    zs = [5 * x[2] for x in str1]
                    self.xpos = xs
                    self.ypos = ys
                    self.zpos = zs

                    poslist = []

                    for i in range(0, len(self.xpos) - 1, 2):
                        dr = self.nx[i // 2]
                        dtheta = self.ny[i // 2] / 5
                        nz = self.nz[i // 2]
                        xpos = []
                        ypos = []
                        xposi = xs[i]
                        xposi2 = xs[i + 1]

                        yposi = ys[i]
                        yposi2 = ys[i + 1]

                        zmax = zs[i + 1]
                        zmin = zs[i]
                        linvalz = abs(math.floor((zmax - zmin) / (nz)))

                        zvals = np.linspace(zmin, zmax, linvalz + 1)
                        a = np.abs(xposi2 - xposi) / 2
                        b = np.abs(yposi2 - yposi) / 2
                        # zposi = zs[i]
                        # zposi2 =zs[i+1]

                        cx = (xposi + xposi2) / 2
                        cy = (yposi + yposi2) / 2
                        cz = (zmax + zmin) / 2
                        xpos = np.append(xpos, cx)
                        ypos = np.append(ypos, cy)

                        p.drawEllipse(
                            QRect(
                                QPoint(xposi + 300, -yposi + 300),
                                QPoint(xposi2 + 300, -yposi2 + 300),
                            )
                        )
                        linval = math.floor((min([a, b])) / (dr))

                        thetavals = np.linspace(0, 1, math.floor(360 / dtheta) + 1)
                        parvals = np.linspace(0, 1, linval + 1)

                        for t in parvals[1:]:
                            for z in thetavals[1:]:
                                xval = cx + t * a * np.cos(z * 2 * np.pi)
                                yval = cy + t * b * np.sin(z * 2 * np.pi)

                                xpos = np.append(xpos, xval)
                                ypos = np.append(ypos, yval)
                        for z in zvals:
                            zpos = z * np.ones(len(xpos))
                            positions = list(zip(xpos, ypos, zpos))
                            poslist = poslist + positions
                    self.poslist = poslist
                except ValueError:
                    QMessageBox.about(
                        self, "Error", "Position should be valid numbers."
                    )
            if self.grid == "rect":
                poslist = []
                bar = self.bar

                try:

                    xs = [5 * x[0] for x in str1]
                    ys = [5 * x[1] for x in str1]
                    zs = [5 * x[2] for x in str1]
                    self.xpos = xs
                    self.ypos = ys
                    self.zpos = zs

                    poslist = []

                    for i in range(0, len(self.xpos) - 1, 2):
                        nx = self.nx[i // 2]
                        ny = self.ny[i // 2]
                        nz = self.nz[i // 2]
                        xmax = self.xpos[i + 1]
                        xmin = self.xpos[i]
                        ymax = self.ypos[i + 1]
                        ymin = self.ypos[i]
                        zmax = zs[i + 1]
                        zmin = zs[i]
                        linvalz = abs(math.floor((zmax - zmin) / (nz)))

                        zvals = np.linspace(zmin, zmax, linvalz + 1)

                        cx = (xposi + xposi2) / 2
                        cy = (yposi + yposi2) / 2
                        cz = (zmax + zmin) / 2

                        p.drawEllipse(
                            QRect(
                                QPoint(xposi + 300, -yposi + 300),
                                QPoint(xposi2 + 300, -yposi2 + 300),
                            )
                        )

                        a = np.abs(xmax - xmin) / 2
                        b = np.abs(ymax - ymin) / 2
                        # if self.centers == '':
                        #         cx = (xmax + xmin)/2
                        #         cy = (ymax + ymin)/2
                        # else:
                        #         str1 = self.centers
                        #         str1 = np.array(
                        #             str1.replace('(', '').replace(')', '').split(','),
                        #             dtype=float,
                        #         ).reshape(-1, 3)
                        #         xs = [5*x[0] for x in str1]
                        #         ys = [5*x[1] for x in str1]
                        #         zs = [5*x[2] for x in str1]
                        #         cx = xs[i]
                        #         cy = ys[i]
                        #         cz = zs[i]

                        linvalx = abs(math.floor((xmax - xmin) / (nx)))
                        linvaly = abs(math.floor((ymax - ymin) / (ny)))
                        xpos = np.linspace(xmin, xmax, linvalx + 1)
                        ypos = np.linspace(ymin, ymax, linvaly + 1)
                        positions = []
                        for z in range(0, len(zvals)):
                            for x in range(0, len(xpos)):
                                for y in range(0, len(ypos)):
                                    if ((xpos[x] - cx) / a) ** 2 + (
                                        (ypos[y] - cy) / b
                                    ) ** 2 <= 1:
                                        positions.append([xpos[x], ypos[y], zvals[z]])
                                    else:
                                        pass
                        poslist.extend(positions)
                    self.poslist = poslist
                except ValueError:
                    QMessageBox.about(
                        self, "Error", "Position should be valid numbers."
                    )
            if self.grid == "circle":
                poslist = []
                bar = self.bar

                try:

                    xs = [5 * x[0] for x in str1]
                    ys = [5 * x[1] for x in str1]
                    zs = [5 * x[2] for x in str1]
                    self.xpos = xs
                    self.ypos = ys
                    self.zpos = zs

                    poslist = []

                    for i in range(0, len(self.xpos) - 1, 2):
                        nx = self.nx[i // 2]
                        ny = self.ny[i // 2]
                        nz = self.nz[i // 2]
                        xmax = self.xpos[i + 1]
                        xmin = self.xpos[i]
                        ymax = self.ypos[i + 1]
                        ymin = self.ypos[i]
                        zmax = zs[i + 1]
                        zmin = zs[i]
                        linvalz = abs(math.floor((zmax - zmin) / nz))

                        zvals = np.linspace(zmin, zmax, linvalz + 1)
                        p.drawEllipse(
                            QRect(
                                QPoint(xposi + 300, -yposi + 300),
                                QPoint(xposi2 + 300, -yposi2 + 300),
                            )
                        )

                        cx = (xposi + xposi2) / 2
                        cy = (yposi + yposi2) / 2
                        cz = (zmax + zmin) / 2

                        a = np.abs(xmax - xmin) / 2
                        b = np.abs(ymax - ymin) / 2
                        r = np.sqrt((xposi2 - xposi) ** 2 + (yposi - yposi2) ** 2) * 0.5

                        # if self.centers == '':
                        #     cx = (xposi + xposi2)/2
                        #     cy = (yposi + yposi2)/2
                        # else:
                        #     str1 = self.centers
                        #     str1 = np.array(
                        #         str1.replace('(', '').replace(')', '').split(','),
                        #         dtype=float,
                        #     ).reshape(-1, 3)
                        #     xs = [5*x[0] for x in str1]
                        #     ys = [5*x[1] for x in str1]
                        #     zs = [5*x[2] for x in str1]
                        #     cx = xs[i]
                        #     cy = ys[i]
                        #     cz = zs[i]
                        xpos = [cx]
                        ypos = [cy]
                        linval = math.floor(r / dr)

                        thetavals = np.linspace(0, 1, math.floor(360 / dtheta) + 1)
                        parvals = np.linspace(0, 1, linval + 1)

                        for t in parvals[1:]:
                            for z in thetavals[1:]:
                                xval = cx + t * r * np.cos(z * 2 * np.pi)
                                yval = cy + t * r * np.sin(z * 2 * np.pi)
                                if ((xval - cx) / a) ** 2 + ((yval - cy) / b) ** 2 <= 1:
                                    xpos = np.append(xpos, xval)
                                    ypos = np.append(ypos, yval)
                    for z in range(0, len(zvals)):
                        zpos = z * np.ones(len(xpos))
                        positions = list(zip(xpos, ypos, zpos))
                        poslist = poslist + positions
                    self.poslist = poslist
                except ValueError:
                    QMessageBox.about(
                        self, "Error", "Position should be valid numbers."
                    )

    def enter(self, arg, mode):
        """
        Handles dynamic updating of shapes, points as per user input in
        autogeneration mode.
        """

        if (
            self.centers == ""
            or arg.ea.text() == ""
            or (arg.eb.text() == "" and mode == "rect")
            or arg.ec.text() == ""
        ):
            pass
        else:
            str1 = self.centers
            str1 = np.array(
                str1.replace("(", "").replace(")", "").split(","), dtype=float
            ).reshape(-1, 3)
            xs1 = [x[0] for x in str1]
            ys1 = [x[1] for x in str1]
            zs1 = [x[2] for x in str1]
            ec = str(arg.ec.text())
            eb = str(arg.eb.text())
            ea = str(arg.ea.text())

            try:
                ea = [int(s) for s in ea.split(",")]
                ec = [int(s) for s in ec.split(",")]
                if eb != "":
                    eb = [int(s) for s in eb.split(",")]
            except ValueError:
                pass

            str1 = ""
            strx = ""
            stry = ""
            strz = ""

            if mode == "circle":
                try:

                    for i in range(0, len(xs1)):
                        dr = self.nx[i] / 5
                        dtheta = self.ny[i] / 5
                        dz = self.nz[i] / 5
                        perRing = 360 / dtheta
                        ringnum = math.floor(ea[i] / perRing)
                        r = ringnum * dr
                        rz = (ec[i] - 1) * dz / 2
                        str0 = (
                            f"({xs1[i]}, {ys1[i]}, {zs1[i] + rz}), "
                            f"({xs1[i] + r}, {ys1[i]}, {zs1[i] - rz})"
                        )
                        str1 += f"{str0}, "
                        strz += f"{2 * rz},"
                        strx += f"{r},"
                    strx = f"{strx.rstrip(strz[-1])} cm"
                    strz = f"{strz.rstrip(strz[-1])} cm"
                    str1 = str1.rstrip(str1[-1])
                    str1 = str1.rstrip(str1[-1])
                    arg.la.setText(strx)
                    arg.lb.setText(strx)
                    arg.lc.setText(strz)
                    self.str1 = str1
                    self.coordEnter(arg, str1)
                except IndexError:
                    QMessageBox.about(
                        self,
                        "Error",
                        "Not enough parameters (centers or points or step-sizes) have been defined.",
                    )
                except ValueError:
                    pass
            elif mode == "rect":
                try:

                    for i in range(0, len(xs1)):
                        dx = self.nx[i] / 5
                        dy = self.ny[i] / 5
                        dz = self.nz[i] / 5
                        rx = (ea[i] - 1) * dx / 2
                        ry = (eb[i] - 1) * dy / 2
                        rz = (ec[i] - 1) * dz / 2
                        str0 = (
                            f"({rx + xs1[i]}, {ry + ys1[i]}, {rz + zs1[i]}), "
                            f"({xs1[i] - rx}, {ys1[i] - ry}, {zs1[i] - rz})"
                        )
                        str1 += f"{str0}, "
                        strx += f"{2 * rx},"
                        stry += f"{2 * ry},"
                        strz += f"{2 * rz},"
                    str1 = str1.rstrip(str1[-1])
                    str1 = str1.rstrip(str1[-1])
                    strx = f"{strx.rstrip(strx[-1])} cm"
                    stry = f"{stry.rstrip(stry[-1])} cm"
                    strz = f"{strz.rstrip(strz[-1])} cm"
                    arg.la.setText(strx)
                    arg.lb.setText(stry)
                    arg.lc.setText(strz)
                    self.str1 = str1
                    self.coordEnter(arg, str1)
                except IndexError:
                    QMessageBox.about(
                        self,
                        "Error",
                        "Not enough parameters (centers or points or step-sizes) have been defined.",
                    )
                except ValueError:
                    QMessageBox.about(
                        self,
                        "Error",
                        "Coordinates and number of points should be valid numbers. "
                        "Coordinates should be specified as (x,y,z), (x,y,z)",
                    )
            elif mode == "ellipse":
                try:

                    e = self.eccentricity

                    for i in range(0, len(xs1)):
                        dr = self.nx[i] / 5
                        dtheta = self.ny[i] / 5
                        dz = self.nz[i] / 5
                        perRing = 360 / dtheta
                        a = (ea[i] / perRing) * (dr / (1 - e**2) ** 0.5)
                        b = (ea[i] / perRing) * dr
                        rz = (ec[i] - 1) * dz / 2

                        str0 = (
                            f"({a + xs1[i]}, {b + ys1[i]}, {zs1[i] + rz}), "
                            f"({xs1[i] - a}, {ys1[i] - b}, {zs1[i] - rz})"
                        )
                        str1 += f"{str0}, "
                        strx = f"{round(2 * a, 3)},"
                        stry = f"{round(2 * b, 3)},"
                        strz = f"{round(2 * rz, 3)},"
                    str1 = str1.rstrip(str1[-1])
                    str1 = str1.rstrip(str1[-1])
                    strx = f"{strx.rstrip(strx[-1])} cm"
                    stry = f"{stry.rstrip(stry[-1])} cm"
                    strz = f"{strz.rstrip(strz[-1])} cm"
                    arg.la.setText(strx)
                    arg.lb.setText(stry)
                    arg.lc.setText(strz)
                    self.str1 = str1
                    self.coordEnter(arg, str1)
                except IndexError:
                    QMessageBox.about(
                        self,
                        "Error",
                        "Not enough parameters (centers or points or step-sizes) have been defined.",
                    )
                except ValueError:
                    QMessageBox.about(
                        self,
                        "Error",
                        "Coordinates and number of points should be valid numbers. "
                        "Coordinates should be specified as (x,y,z), (x,y,z)",
                    )
            elif mode == "sphere":
                pass

    def set_name(self, name):
        # outdated
        self.name = name
        self.id = self.name.replace(" ", "_").lower()

    def save_file(self):

        zs = []
        for z in self.zpos:
            zs.append(z / 5)
        self.zpos = zs

        xs = []
        for x in self.xpos:
            xs.append(x / 5)
        self.xpos = xs

        ys = []
        for y in self.ypos:
            ys.append(y / 5)
        self.ypos = ys

        Dict1 = {
            "group.id": self.id,
            "mode": self.mode,
            "grid": self.grid,
            "dx": self.nx / 5,
            "dy": self.ny / 5,
            "dz": self.nz / 5,
            "xs": self.xpos,
            "ys": self.ypos,
            "zs": self.zpos,
            "bar": self.barlist.tolist(),
            "close": self.closeit,
            "centers": self.centers,
        }

        # tomli_string = tomli_w.dumps(Dict1)  # Output to a string
        save_path = "Groups"
        output_file_name = f"{self.name}"
        completeName = os.path.join(save_path, f"{output_file_name}.toml")

        with open(completeName, "rb") as f:
            self.toml_dict = tomli.load(f)

        self.toml_dict["Motion List"] = Dict1

        with open(completeName, "wb") as tomli_file:
            tomli_w.dump(self.toml_dict, tomli_file)
