
import datetime
import math
import numpy as np
import os
import tomli
import tomli_w

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from PyQt5 import QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from .main_window import Ui_MainWindow


MODES = [

    'line', 'polyline',
    'rect', 'barrier', 'circle', 'ellipse'
]


GRIDS = [


    'rect', 'circle', 'ellipse', 'sphere'
]


CANVAS_DIMENSIONS = 600, 600

SELECTION_PEN = QPen(QColor(0xff, 0xff, 0xff), 1, Qt.DashLine)
PREVIEW_PEN = QPen(QColor(0xff, 0xff, 0xff), 1, Qt.SolidLine)


class MplCanvas(FigureCanvas):

    def __init__(self, parent=None, width=5, height=4, dpi=100):

        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.ax.grid()
        self.ax.mouse_init()

        # self.ax.set_xticks(np.arange(-60,60,1))
        uss = np.linspace(0, 2 * np.pi, 32)
        zss = np.linspace(-3, 3, 2)

        uss, zss = np.meshgrid(uss, zss)

        xss = 50 * np.cos(uss)
        yss = 50 * np.sin(uss)
        self.ax.plot_surface(xss, yss, zss, alpha=0.5, color='grey')
        super(MplCanvas, self).__init__(self.fig)
       




class Canvas(QLabel):
    '''This class controls the "canvas" where one can draw the shapes to define
    data acquisition regions in 2D (3D with z-axis extrusion). '''

    mode = 'rect'
    grid = 'rect'

    primary_color = QColor(Qt.blue)
    # Store configuration settings, including pen width, fonts etc.
    config = {
        # Drawing options.
        'size': 1,
        'fill': True,

    }
    active_color = '#000000'
    preview_pen = None
    timer_event = None
    move = pyqtSignal()

    def initialize(self):
        self.background_color = QColor(Qt.gray)
        self.eraser_color = QColor(Qt.white)
        self.last_pos = None
        self.eraser_color.setAlpha(100)
        self.grid_spacing = 10 # 5pix per cm
        self.hand = 0
        self.plasmacolumn = True
        self.maincathode = False
        self.secondarycathode = False
        self.alpha = np.pi/4
        self.xpos = []
        self.ypos = []
        self.nx = 10
        self.ny = 10
        self.nz = 1
        self.z1 = 1
        self.z2 = 1
        self.poslist = []
        self.barlist = []
        self.cx = 0
        self.cy = 0
        self.bar = 0
        self.centers = ''
        self.closeit = False
        self.eccentricity = 0.5
        self.modelist = []
        self.reslist = []
        self.reset()
        self.oldpixmap = self.pixmap()
        p = QPainter(self.pixmap())

        
        xs = np.arange(50,550,self.grid_spacing)
        ys = np.arange(50,550,self.grid_spacing)
            
        p.setBrush(QBrush(QColor(Qt.white)))
        
        p.setPen(QPen(QColor(Qt.black),
                 self.config['size'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
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
        
        p.setPen(QPen(QColor(Qt.green),
                 self.config['size'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setOpacity(0.2)
        for x in xs:
            p.drawLine(QPointF(x,300+np.sqrt(250**2-(x-300)**2)),QPointF(x,300-np.sqrt(250**2-(x-300)**2)))
        for y in ys:
            p.drawLine(QPointF(300+np.sqrt(250**2-(y-300)**2),y),QPointF(300-np.sqrt(250**2-(y-300)**2),y))
       
        p.setPen(QPen(QColor(Qt.red),
                 self.config['size'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setOpacity(0.4)
        p.drawEllipse(QPoint(300,300), 150, 150)
        
        p.setPen(QPen(QColor(Qt.black),
                 self.config['size'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setOpacity(1)

        p.setBrush(QBrush(QColor(Qt.red)))
        p.drawEllipse(QPointF(300, 300), 1, 1)
        
        p.end()
        self.update()

    def reset(self):
        ''' Reset the canvas, and associated data'''
        # Create the pixmap for display.
        self.setPixmap(QPixmap(*CANVAS_DIMENSIONS))

        # Clear the canvas.
        self.pixmap().fill(self.background_color)

        p = QPainter(self.pixmap())
        p.setPen(QPen(QColor(Qt.black),
                 self.config['size'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
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
        xs = np.arange(50,550,self.grid_spacing)
        ys = np.arange(50,550,self.grid_spacing)
        p.setPen(QPen(QColor(Qt.green),
                 self.config['size'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setOpacity(0.2)
        for x in xs:
            p.drawLine(QPointF(x,300+np.sqrt(250**2-(x-300)**2)),QPointF(x,300-np.sqrt(250**2-(x-300)**2)))
        for y in ys:
            p.drawLine(QPointF(300+np.sqrt(250**2-(y-300)**2),y),QPointF(300-np.sqrt(250**2-(y-300)**2),y))
       
       
        if self.plasmacolumn == True:
            p.setPen(QPen(QColor(Qt.red),
                 self.config['size'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setOpacity(0.4)
            p.drawEllipse(QPoint(300,300), 150, 150)
       
        if self.maincathode == True:
            p.setPen(QPen(QColor('#FFA500'),
                 self.config['size'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setOpacity(0.4)
            p.drawEllipse(QPoint(300,300), 95, 95)
            
        if self.secondarycathode == True:
            p.setPen(QPen(QColor("#ff4500"),
                 self.config['size'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setOpacity(0.4)
            p.drawRect(250,250, 100, 100)
            
        
        p.setPen(QPen(QColor(Qt.black),
                 self.config['size'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setOpacity(1)
        p.setBrush(QBrush(QColor(Qt.red)))

        p.drawEllipse(QPointF(300, 300), 1, 1)
        p.end()
    
    def set_primary_color(self, hex):
        self.primary_color = QColor(hex)



            
    def set_spacing(self,arg):
        self.grid_spacing = 5*arg.sl.value()
        arg.update_canvas(self.poslist)

    def set_hand(self,arg):
        ''' Sets ''chirality'' i.e. Left or Right entry point.'''
        if arg == 0:
            self.hand = 0
        elif arg == 1:
            self.hand = 1

        self.reset()

    def set_mode(self, mode):
        ''' This mode controls the shape painting function,
        as well as the point generator'''
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
        """ Register resolution and z-axis extrusion inputs.
        5x factor for cm to pixel conversion"""
        self.nx = 5*float(arg.xres.text())
        self.ny = 5*float(arg.yres.text())
        self.nz = 5*float(arg.zres.text())
        self.z1 = 5*float(arg.z1.text())
        self.z2 = 5*float(arg.z2.text())
        self.centers = str(arg.gridCentre.text())
        self.closeit = arg.closeit
        self.eccentricity = arg.eccentricity
        
        if arg.MainCathode.isChecked():
            self.maincathode = True
        else :
            self.maincathode = False
            
        if arg.PlasmaColumn.isChecked():
            self.plasmacolumn = True
        else :
            self.plasmacolumn = False
            
        if arg.SecondaryCathode.isChecked():
            self.secondarycathode = True
        else :
            self.secondarycathode = False         
            
            
    def set_grid(self, grid):
        ''' similar to mode system, sets the grid system'''
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
    ''' redefining pyqt mouse events... depending on chosen mode,
    this will also call  a mode specific  drawing function to paint shape
    on the canvas'''

    """Everything internal is handled in coordinate units.
    # EXCEPT THE BARLIST
    # All inputs are taken in cm units.
    # means output list is also in coord units.
    # 1 cm = 5pixel, as per the set size of the canvas.
    # self.xpos, self.ypos (and self.zpos) are containers for all vertex points.
    Basic point verification routine- distance from centre (is_inside_machine?)

    ### CURRENTLY COMPLETELY AD-HOC #####
    Angle from entry point (can probe reach via ball-valve. )
    Current angle-restriction setup-
    \_ Hole perfectly aligned with centre of lapd, + exacty at the edge of lapd.
    valve is 2 cm long, and 2 cm above and below hole. SO shaft makes 45 degree angles at max.. definitely incorrect.
    """

    def mousePressEvent(self, e):
        fn = getattr(self, "%s_mousePressEvent" % self.mode, None)
# calls mode_specific canvas drawing function-

# Basic Point validity verification routine:
        dist = ((e.x() - 300)**2 + (e.y()-300)**2)**0.5
        if dist > 250:

            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Error")
            msg.setInformativeText('Designated point is outside the Machine!')
            msg.setWindowTitle("Error")
            msg.exec_()

        
        if e.x() is not None and e.y() is not None:

            self.xpos = np.append(self.xpos, float(e.x()-300))
            self.ypos = np.append(self.ypos, float(-e.y()+300))
            # self.modelist = np.append(self.mode)
            if fn:
                return fn(e)

    def mouseMoveEvent(self, e):
        self.cx = e.x()
        self.cy = e.y()
        self.move.emit()
        fn = getattr(self, "%s_mouseMoveEvent" % self.mode, None)
        if fn:
            return fn(e)

    def mouseReleaseEvent(self, e):

        fn = getattr(self, "%s_mouseReleaseEvent" % self.mode, None)
# calls mode_specific function-

# Basic Point validity verification routine:
        dist = ((e.x() - 300)**2 + (e.y()-300)**2)**0.5
        if dist > 250:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Error")
            msg.setInformativeText('Designated point is outside the Machine!')
            msg.setWindowTitle("Error")
            msg.exec_()
     

        if e.x() is not None and e.y() is not None:
            self.xpos = np.append(self.xpos, float(e.x()-300))
            self.ypos = np.append(self.ypos, float(-e.y()+300))
            # self.modelist = np.append(self.mode)

            if fn:
                return fn(e)

    def mouseDoubleClickEvent(self, e):
        fn = getattr(self, "%s_mouseDoubleClickEvent" % self.mode, None)
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
            p.setPen(QPen(self.primary_color,
                     self.config['size'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

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
            p.setPen(QPen(QColor('#800000'),
                     self.config['size'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

            p.drawLine(self.origin_pos, e.pos())

            p.setPen(QPen(QColor('#FF0000'),
                     self.config['size'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            
            ye = 300-e.y()
            xe = e.x()-300
            yorg = 300-self.origin_pos.y()
            xorg = self.origin_pos.x()-300
            r = 250
            if self.hand ==0:
                theta = 0
            if self.hand ==1:
                theta = np.pi
                  
            if theta >= np.pi:
                C = (yorg-r*np.sin(theta))/(xorg- r*np.cos(theta))
                        
                a = 1 + C**2
                b = -2*xorg*(C**2) + 2*C*yorg
                c = (C**2)*xorg + yorg**2 -2*C*yorg*xorg - r**2
                        
                xvo = (-b + np.sqrt(b**2 -4*a*c))/(2*a)
                        
                yvo = C*(xvo-xorg) + yorg
                p.drawLine(self.origin_pos,QPointF(xvo+300,300-yvo))
                C = (ye-r*np.sin(theta))/(xe- r*np.cos(theta))
                     
                a = 1 + C**2
                b = -2*xe*(C**2) + 2*C*ye
                c = (C**2)*xe + ye**2 -2*C*ye*xe - r**2
                     
                xve = (-b + np.sqrt(b**2 -4*a*c))/(2*a)
                     
                yve = C*(xve-xe) + ye
                p.drawLine(e.pos(),QPointF(xve+300,300-yve))
            if theta < np.pi:
                 C = (yorg-r*np.sin(theta))/(xorg- r*np.cos(theta))
                        
                 a = 1 + C**2
                 b = -2*xorg*(C**2) + 2*C*yorg
                 c = (C**2)*xorg + yorg**2 -2*C*yorg*xorg - r**2
                        
                 xvo = (-b - np.sqrt(b**2 -4*a*c))/(2*a)
                        
                 yvo = C*(xvo-xorg) + yorg
                 p.drawLine(self.origin_pos,QPointF(xvo+300,300-yvo))
                 C = (ye-r*np.sin(theta))/(xe- r*np.cos(theta))
                     
                 a = 1 + C**2
                 b = -2*xe*(C**2) + 2*C*ye
                 c = (C**2)*xe + ye**2 -2*C*ye*xe - r**2
                     
                 xve = (-b - np.sqrt(b**2 -4*a*c))/(2*a)
                 yve = C*(xve-xe) + ye
                 p.drawLine(e.pos(),QPointF(xve+300,300-yve))

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
            getattr(p, self.active_shape_fn)(
                *self.history_pos + [self.current_pos])

        self.update()
        self.last_pos = self.current_pos
        self.last_history = self.history_pos + [self.current_pos]

    def generic_poly_mouseMoveEvent(self, e):
        self.current_pos = e.pos()

    def generic_poly_mouseDoubleClickEvent(self, e):
        self.timer_cleanup()
        p = QPainter(self.pixmap())
        p.setPen(QPen(self.primary_color,
                 self.config['size'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

        getattr(p, self.active_shape_fn)(*self.history_pos + [e.pos()])
        self.update()
        self.reset_mode()

    # Polyline events

    def polyline_mousePressEvent(self, e):
        self.active_shape_fn = 'drawPolyline'
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
        self.active_shape_fn = 'drawRect'
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
                QRect(self.origin_pos, self.last_pos), *self.active_shape_args)

        if not final:
            p.setPen(pen)
            getattr(p, self.active_shape_fn)(
                QRect(self.origin_pos, self.current_pos), *self.active_shape_args)

        self.update()
        self.last_pos = self.current_pos

    def rect_mouseMoveEvent(self, e):
        self.current_pos = e.pos()

    def rect_mouseReleaseEvent(self, e):
        if self.last_pos:
            # Clear up indicator.
            self.timer_cleanup()

            p = QPainter(self.pixmap())
            p.setPen(QPen(self.primary_color,
                     self.config['size'], Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin))
            p.setOpacity(0.5)

            if self.config['fill']:
                p.setBrush(QBrush(self.primary_color))
            getattr(p, self.active_shape_fn)(
                QRect(self.origin_pos, e.pos()), *self.active_shape_args)
            self.update()
        self.reset_mode()

    # Circle events

    def circle_mousePressEvent(self, e):
        self.active_shape_fn = 'drawEllipse'
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
            r = np.sqrt((self.origin_pos.x() - self.last_pos.x()) **
                        2 + (self.origin_pos.y() - self.last_pos.y())**2)

            getattr(p, self.active_shape_fn)(
                self.origin_pos, r, r, *self.active_shape_args)

        if not final:
            p.setPen(pen)
            r = np.sqrt((self.origin_pos.x() - self.current_pos.x())
                        ** 2 + (self.origin_pos.y() - self.current_pos.y())**2)
            getattr(p, self.active_shape_fn)(
                self.origin_pos, r, r, *self.active_shape_args)

        self.update()
        self.last_pos = self.current_pos

    def circle_mouseMoveEvent(self, e):
        self.current_pos = e.pos()

    def circle_mouseReleaseEvent(self, e):
        if self.last_pos:
            # Clear up indicator.
            self.timer_cleanup()
            r = np.sqrt((self.origin_pos.x() - self.last_pos.x()) **
                        2 + (self.origin_pos.y() - self.last_pos.y())**2)

            p = QPainter(self.pixmap())
            p.setPen(QPen(self.primary_color,
                     self.config['size'], Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin))
            p.setOpacity(0.5)

            if self.config['fill']:
                p.setBrush(QBrush(self.primary_color))
            getattr(p, self.active_shape_fn)(
                self.origin_pos, r, r, *self.active_shape_args)
            self.update()

        self.reset_mode()

# Ellipse events
    def ellipse_mousePressEvent(self, e):
        self.active_shape_fn = 'drawEllipse'
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
                QRect(self.origin_pos, self.last_pos), *self.active_shape_args)

        if not final:
            p.setPen(pen)
            getattr(p, self.active_shape_fn)(
                QRect(self.origin_pos, self.current_pos), *self.active_shape_args)

        self.update()
        self.last_pos = self.current_pos

    def ellipse_mouseMoveEvent(self, e):
        self.current_pos = e.pos()

    def ellipse_mouseReleaseEvent(self, e):
        if self.last_pos:
            # Clear up indicator.
            self.timer_cleanup()

            p = QPainter(self.pixmap())
            p.setPen(QPen(self.primary_color,
                     self.config['size'], Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin))
            p.setOpacity(0.5)

            if self.config['fill']:
                p.setBrush(QBrush(self.primary_color))
            getattr(p, self.active_shape_fn)(
                QRect(self.origin_pos, e.pos()), *self.active_shape_args)
            self.update()

        self.reset_mode()

    def resetpos(self, arg):
        self.xpos = []
        self.ypos = []
        self.poslist = []
        self.barlist = []
        self.bar = 0
        arg.saveButton.setEnabled(False)
        if self.mode == 'rect':
            arg.la.setText("Length- X")
            arg.lb.setText("Length- Y")
            arg.lc.setText("Length- Z")
        elif self.mode == 'circle':
            arg.la.setText("Radius")
            arg.lb.setText("")
            arg.lc.setText("Length- Z")
        elif self.mode == 'ellipse':
            arg.lc.setText("Length- Z")
            arg.la.setText("Horizontal Axis")
            arg.lb.setText("Vertical Axis")

            
            
    def set_numpoint(self, arg):
        '''
        sets input (no. of points) for shape autogeneration scheme.
        '''
        self.ea = str(arg.ea.text())
        self.eb = str(arg.eb.text())

    def print_positions(self, arg):
        """ Position generating function, for display purposes.
        First- Generates the barrier from given points, as well as the
         region that becomes no-go zone.  Currently based off ad-hoc
         assumptions for the angular reach of a probe shaft from a particular
         valve.
        Second- Calls point generating function depending on the mode.
        Each point generating function further looks at grid config to setup points.
        """

        mode = self.mode
        bar = self.bar
        self.zpos = [self.z1, self.z2]  # Z-extrusion range
        barlist = []
        arg.saveButton.setEnabled(False)  # Must verify to reenable button
        if self.hand ==0:
            theta = 0
        if self.hand ==1:
            theta = np.pi
        r = 250
        # Generate the barrier from given points, as well as the
        # region that becomes no-go zone.  Currently based off ad-hoc
        # assumptions for the angular reach  of a probe shaft from a particular valve.
        for i in range(0, bar-1, 2):
            xe = self.xpos[i+1]
            xorg = self.xpos[i]
            ye = self.ypos[i+1]
            yorg = self.ypos[i]

                     
            if theta >= np.pi:
                C = (yorg-r*np.sin(theta))/(xorg- r*np.cos(theta))
                        
                a = 1 + C**2
                b = -2*xorg*(C**2) + 2*C*yorg
                c = (C**2)*xorg + yorg**2 -2*C*yorg*xorg - r**2
                
                xvo = (-b + np.sqrt(b**2 -4*a*c))/(2*a)
                
                yvo = C*(xvo-xorg) + yorg
     
                C = (ye-r*np.sin(theta))/(xe- r*np.cos(theta))
                     
                a = 1 + C**2
                b = -2*xe*(C**2) + 2*C*ye
                c = (C**2)*xe + ye**2 -2*C*ye*xe - r**2
                     
                xve = (-b + np.sqrt(b**2 -4*a*c))/(2*a)
                     
                yve = C*(xve-xe) + ye
                C = (yorg-r*np.sin(theta))/(xorg- r*np.cos(theta))
                        
                a = 1 + C**2
                b = -2*xorg*(C**2) + 2*C*yorg
                c = (C**2)*xorg + yorg**2 -2*C*yorg*xorg - r**2
                        
                xvo = (-b + np.sqrt(b**2 -4*a*c))/(2*a)
                        
                yvo = C*(xvo-xorg) + yorg
      
                C = (ye-r*np.sin(theta))/(xe- r*np.cos(theta))
                     
                a = 1 + C**2
                b = -2*xe*(C**2) + 2*C*ye
                c = (C**2)*xe + ye**2 -2*C*ye*xe - r**2
                     
                xve = (-b + np.sqrt(b**2 -4*a*c))/(2*a)
                     
                yve = C*(xve-xe) + ye

   

            if theta < np.pi:
                C = (yorg-r*np.sin(theta))/(xorg- r*np.cos(theta))
                        
                a = 1 + C**2
                b = -2*xorg*(C**2) + 2*C*yorg
                c = (C**2)*xorg + yorg**2 -2*C*yorg*xorg - r**2
                        
                xvo = (-b - np.sqrt(b**2 -4*a*c))/(2*a)
                        
                yvo = C*(xvo-xorg) + yorg
      
                C = (ye-r*np.sin(theta))/(xe- r*np.cos(theta))
                     
                a = 1 + C**2
                b = -2*xe*(C**2) + 2*C*ye
                c = (C**2)*xe + ye**2 -2*C*ye*xe - r**2
                     
                xve = (-b - np.sqrt(b**2 -4*a*c))/(2*a)
                     
                yve = C*(xve-xe) + ye


            barlist.append([(xorg, yorg, self.z1), (xe, ye, self.z1),
                           (xvo, yvo, self.z1), (xve, yve, self.z1)])

        barlist = np.array(barlist)/5
        self.barlist = barlist

        if mode == "line":
            self.get_positionsline()

        elif mode == "rect":
            self.get_positionsrect(arg)

        elif mode == "polyline":
            self.get_positionspoly()

        elif mode == 'circle':
            self.get_positionscircle(arg)

        elif mode == 'ellipse':
            self.get_positionsellipse(arg)

    def get_positionsrect(self, arg):
        ''' point generator for rectangular/cuboidal shapes. Defined by corner vertices'''
        bar = self.bar
        poslist = []
        strx = ''
        stry = ''
        strz = ''
        strc = ''
        zmax = self.z1
        zmin = self.z2
        if self.grid == 'rect':
            for i in range(bar, len(self.xpos)-1, 2):
                xmax = self.xpos[i+1]
                xmin = self.xpos[i]
                ymax = self.ypos[i+1]
                ymin = self.ypos[i]

                nx = self.nx
                ny = self.ny
                nz = self.nz
                lx = abs(xmax-xmin)
                ly = abs(ymax-ymin)
                lz = abs(zmax-zmin)
                strx = strx + str(lx/5) + ','
                stry = stry + str(ly/5) + ','
                strz = strz + str(lz/5) + ','

                linvalz = abs(math.floor((self.z2-self.z1)/(nz)))

                linvalx = abs(math.floor((xmax-xmin)/(nx)))
                linvaly = abs(math.floor((ymax-ymin)/(ny)))

                zvals = np.linspace(self.z1, self.z2, linvalz+1)
                xvals = np.linspace(xmin, xmax, linvalx+1)
                yvals = np.linspace(ymin, ymax, linvaly+1)
                cx = (xmax+xmin)/2
                cy = (ymax+ymin)/2
                cz = (zmax+zmin)/2
                strc = strc + '(' + str(cx/5) + ',' + str(cy/5)+','+str(cz/5)+'), '
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
          

        if self.grid == 'circle':

            xpos = []
            ypos = []
            dr = self.nx
            dtheta = self.ny/5
            nz = self.nz
            for i in range(bar, len(self.xpos)-1, 2):
                xmax = max([self.xpos[i+1], self.xpos[i]])
                xmin = min([self.xpos[i+1], self.xpos[i]])
                ymax = max([self.ypos[i+1], self.ypos[i]])
                ymin = min([self.ypos[i+1], self.ypos[i]])
                lx = abs(xmax-xmin)
                ly = abs(ymax-ymin)
                lz = abs(zmax-zmin)
                strx = strx + str(lx/5) + ','
                stry = stry + str(ly/5) + ','
                strz = strz + str(lz/5) + ','
                linvalz = abs(math.floor((self.z2-self.z1)/(nz)))
                cx = (xmax+xmin)/2
                cy = (ymax+ymin)/2
                cz = (zmax+zmin)/2
                strc = strc + '(' + str(cx/5) + ',' + str(cy/5)+','+str(cz/5)+'), '

                zvals = np.linspace(self.z1, self.z2, linvalz+1)
                xpos = np.append(xpos, cx)
                ypos = np.append(ypos, cy)

                r = 0.5*(np.sqrt((xmax-xmin)**2 + (ymax-ymin)**2))

                linval = math.floor(r/(dr))

                thetavals = np.linspace(0, 1, math.floor(360/dtheta) + 1)
                parvals = np.linspace(0, 1, linval+1)
                positions = []
                # first start point already initialized in array.
                for t in parvals[1:]:
                    # Other start points are incorporated as the end points of previous segment.
                    for z in thetavals[1:]:
                        xval = cx + t*r*np.cos(z*2*np.pi)
                        yval = cy + t*r*np.sin(z*2*np.pi)

                        if (xval > xmax) or xval < xmin or yval > ymax or yval < ymin:
                            pass
                        else:
                            xpos = np.append(xpos, xval)
                            ypos = np.append(ypos, yval)

                for z in range(0, len(zvals)):
                    zpos = z*np.ones(len(xpos))
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
           
        if self.grid == 'sphere':

            dr = self.nx
            dtheta = self.ny/5
            dphi = self.nz/5
            for i in range(bar, len(self.xpos)-1, 2):
                xmax = max([self.xpos[i+1], self.xpos[i]])
                xmin = min([self.xpos[i+1], self.xpos[i]])
                ymax = max([self.ypos[i+1], self.ypos[i]])
                ymin = min([self.ypos[i+1], self.ypos[i]])
                zmax = max([self.z1, self.z2])
                zmin = min([self.z1, self.z2])
                lx = abs(xmax-xmin)
                ly = abs(ymax-ymin)
                lz = abs(zmax-zmin)
                strx = strx + str(lx/5) + ','
                stry = stry + str(ly/5) + ','
                strz = strz + str(lz/5) + ','
                cx = (xmax+xmin)/2
                cy = (ymax+ymin)/2
                cz = (zmax+zmin)/2
                strc = strc + '(' + str(cx/5) + ',' + str(cy/5)+','+str(cz/5)+'), '

                r = (np.sqrt((xmax-xmin)**2 + (ymax-ymin)**2) + (zmax-zmin)**2)

                linval = math.floor(r/(dr))

                thetavals = np.linspace(0, 1, math.floor(360/dtheta) + 1)
                phivals = np.linspace(0, 1, math.floor(180/dphi)+1)
                parvals = np.linspace(0, 1, linval+1)
                positions = [[cx, cy, cz]]
                # first start point already initialized in array.
                for t in parvals[1:]:
                    # Other start points are incorporated as the end points of previous segment.
                    for z in thetavals[1:]:
                        for p in phivals[1:]:
                            xval = cx + t*r*np.cos(z*2*np.pi)*np.sin(p*np.pi)
                            yval = cy + t*r*np.sin(z*2*np.pi)*np.sin(p*np.pi)
                            zval = cz + t*r*np.cos(p*np.pi)
                        if (xval > xmax) or xval < xmin or yval > ymax or yval < ymin or zval > zmax or zval < zmin:
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
        
   
        if self.grid == 'ellipse':

            dr = self.nx
            dtheta = self.ny/5
            dz = self.nz

            e = self.eccentricity
            xpos = []
            ypos = []
            poslist = []
            for i in range(bar, len(self.xpos)-1, 2):

                    xmax = max([self.xpos[i+1], self.xpos[i]])
                    xmin = min([self.xpos[i+1], self.xpos[i]])
                    ymax = max([self.ypos[i+1], self.ypos[i]])
                    ymin = min([self.ypos[i+1], self.ypos[i]])
                    zmax = max([self.z1, self.z2])
                    zmin = min([self.z1, self.z2])
                    lx = abs(xmax-xmin)
                    ly = abs(ymax-ymin)
                    lz = abs(zmax-zmin)
                    strx = strx + str(lx/5) + ','
                    stry = stry + str(ly/5) + ','
                    strz = strz + str(lz/5) + ','
                    cx = (xmax+xmin)/2
                    cy = (ymax+ymin)/2
                    cz = (zmax+zmin)/2
                    strc = strc + '(' + str(cx/5) + ',' +  str(cy/5)+','+str(cz/5)+'), '

                    # NEED TO RECALCULATE POINT GENERATING PARAMETERS TO GET APPROPRIATE ONES WITHIN THE REGION.
                    linvalz = abs(math.floor((zmax-zmin)/(dz)))
                    zvals = np.linspace(zmin, zmax, linvalz+1)

                    a = max([(xmax - xmin), (ymax-ymin)])
                    b = a*np.sqrt(1-e**2)

                    xpos = np.append(xpos, cx)
                    ypos = np.append(ypos, cy)

                    linval = math.floor((min([a, b]))/(dr))

                    thetavals = np.linspace(
                        0, 1, math.floor(360/dtheta) + 1)
                    parvals = np.linspace(0, 1, linval+1)

                    for t in parvals[1:]:
                        for z in thetavals[1:]:
                            xval = cx + t*a*np.cos(z*2*np.pi)
                            yval = cy + t*b*np.sin(z*2*np.pi)
                            if (xval > xmax) or xval < xmin or yval > ymax or yval < ymin:
                                pass
                            else:
                                xpos = np.append(xpos, xval)
                                ypos = np.append(ypos, yval)

            for z in range(0, len(zvals)):
                    zpos = z*np.ones(len(xpos))
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
        ''' point generator for lines'''

        poslist = []
        bar = self.bar
        xs = self.xpos
        ys = self.ypos

        nz = self.nz

        linvalz = abs(math.floor((self.z2-self.z1)/(nz)))
        zvals = np.linspace(self.z1, self.z2, linvalz+1)
        xpos = []
        ypos = []
#            zpos = [zs[0]]

        for i in range(bar, len(xs)-1, 2):

            # general idea for motion list- user gave end points of line segments.
            # each point is essentially a location in the array. Get distance between the
            # two array points.    #Get an equation of the line joining two points in the array.
            # Get real coordinates of the point on this line at every
            #  'res' distance.

            # the coordinates of the two end points of line segment

            xposi = xs[i]
            xposi2 = xs[i+1]

            yposi = ys[i]
            yposi2 = ys[i+1]

            # zposi = zs[i]
            # zposi2 =zs[i+1]
            res = (self.nx**2 + self.ny**2)**0.5
            length = ((xposi2-xposi)**2 + (yposi2-yposi)**2)**0.5
            linval = math.floor(length/(res))

            parvals = np.linspace(0, 1, linval+1)

            for t in parvals:

                xval = xposi + t*(xposi2 - xposi)
                yval = yposi + t*(yposi2 - yposi)
                # zval = zposi + t*(zposi2 - zposi)
                xpos = np.append(xpos, xval)
                ypos = np.append(ypos, yval)

        for z in range(0, len(zvals)):
            zpos = z*np.ones(len(xpos))
            positions = list(zip(xpos, ypos, zpos))
            poslist = poslist + positions

        self.poslist = poslist
        
    def get_positionspoly(self):
        ''' point generator for polygonal lines. Currently defaults to not closing shape'''

        poslist = []
        if self.closeit == True:
                    index = -1
        else :
                    index = 0
        bar = int(self.bar/2)
        xs = np.delete(self.xpos, -1)
        ys = np.delete(self.ypos, -1)

        xs = xs[1::2]
        ys = ys[1::2]
        xs = xs[bar:]
        ys = ys[bar:]
        xpos = [xs[bar]]
        ypos = [ys[bar]]

        if self.closeit == True:
            p = QPainter(self.pixmap())

            p.setPen(QPen(
                QColor(Qt.blue), self.config['size'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(QBrush(QColor(Qt.blue)))

            p.drawLine(QPointF(xs[-1]+300, -ys[-1]+300),
                   QPointF(xs[0]+300, -ys[0]+300))

        for i in range(index, len(xs)-1):
            xposi = xs[i]
            xposi2 = xs[i+1]

            yposi = ys[i]
            yposi2 = ys[i+1]

            res = (self.nx**2 + self.ny**2)**0.5
            length = ((xposi2-xposi)**2 + (yposi2-yposi)**2)**0.5
            linval = math.floor(length/(res))

            parvals = np.linspace(0, 1, linval+1)

            for t in parvals[1:]:

                xval = xposi + t*(xposi2 - xposi)
                yval = yposi + t*(yposi2 - yposi)
                # zval = zposi + t*(zposi2 - zposi)
                xpos = np.append(xpos, xval)
                ypos = np.append(ypos, yval)

        nz = self.nz

        linvalz = abs(math.floor((self.z2-self.z1)/(nz)))
        zvals = np.linspace(self.z1, self.z2, linvalz+1)

        for z in range(0, len(zvals)):
            zpos = z*np.ones(len(xpos))
            positions = list(zip(xpos, ypos, zpos))
            poslist = poslist + positions

        self.poslist = poslist

    def get_positionscircle(self, arg):
        ''' point generator for circular/cylindrical shapes.
        Circles are defined by point at centrre and random point on the circular edge.'''
        strc = ''
        poslist = []
        bar = self.bar
        xs = self.xpos
        ys = self.ypos
        strx = ''
        stry = ''
        strz = ''
        zmax = self.z1
        zmin = self.z2
        if self.grid == 'rect':
            for i in range(bar, len(self.xpos)-1, 2):

                xposi2 = self.xpos[i+1]
                xposi = self.xpos[i]
                yposi2 = self.ypos[i+1]
                yposi = self.ypos[i]

                r = np.sqrt((xposi - xposi2)**2 + (yposi-yposi2)**2)
                nx = self.nx
                ny = self.ny
                nz = self.nz

                cx = xposi
                cy = yposi
                cz = (zmax+zmin)/2
                strc = strc + '(' + str(cx/5) + ',' + str(cy/5)+','+str(cz/5)+'), '

                xmax= cx + r
                xmin= cx - r
                ymax= cy + r
                ymin= cy - r
                lz= abs(zmax-zmin)

                strx = strx + str(round(r/5, 3)) + ','
                stry = stry + str(round(r/5, 3)) + ','
                strz= strz + str(lz/5) + ','

                linvalz= abs(math.floor(lz/nz))

                linvalx= abs(math.floor((xmax-xmin)/(nx)))
                linvaly= abs(math.floor((ymax-ymin)/(ny)))

                zvals= np.linspace(self.z1, self.z2, linvalz+1)
                xpos= np.linspace(xmin, xmax, linvalx+1)
                ypos= np.linspace(ymin, ymax, linvaly+1)

                positions= []
                for z in range(0, len(zvals)):
                    for x in range(0, len(xpos)):
                        for y in range(0, len(ypos)):
                            r1= np.sqrt((cx-xpos[x])**2 + (cy-ypos[y])**2)
                            if r1 <= r:
                                positions.append([xpos[x], ypos[y], zvals[z]])
                            else:
                                pass

                poslist.extend(positions)
            self.poslist= poslist
            strx= strx.rstrip(strx[-1])
            stry= stry.rstrip(stry[-1])
            strz= strz.rstrip(strz[-1])
            arg.la.setText(strx)
            arg.lb.setText(stry)
            arg.lc.setText(strz)
            strc= strc.rstrip(strc[-1])
            strc= strc.rstrip(strc[-1])
            arg.gridCentre.setText(strc)
            arg.ea.setText(str(len(xpos)))
            arg.eb.setText(str(len(ypos)))
            arg.ec.setText(str(len(zvals)))

        if self.grid == 'circle':

            dr= self.nx
            dtheta= self.ny/5
            nz= self.nz

            linvalz= abs(math.floor((self.z2-self.z1)/(nz)))
            zvals= np.linspace(self.z1, self.z2, linvalz+1)
            xpos= []
            ypos= []
#
            for i in range(bar, len(xs)-1, 2):

                xposi= xs[i]
                xposi2= xs[i+1]

                yposi= ys[i]
                yposi2= ys[i+1]
                cx = xposi
                cy = yposi
                cz = (zmax+zmin)/2
                strc = strc + '(' + str(cx/5) + ',' + str(cy/5)+','+str(cz/5)+'), '
                r= np.sqrt((xposi - xposi2)**2 + (yposi-yposi2)**2)
                lz= abs(zmax-zmin)

                strx = strx + str(round(r/5, 3)) + ','
                stry = stry + str(round(r/5, 3)) + ','
                strz= strz + str(lz/5) + ','

                linval= math.floor(r/(dr))

                thetavals= np.linspace(0, 1, math.floor(360/dtheta) + 1)
                parvals= np.linspace(0, 1, linval+1)
                xpos= np.append(xpos, xposi)
                ypos= np.append(ypos, yposi)

                for t in parvals[1: ]:
                    for z in thetavals[1: ]:
                        xval= xposi + t*r*np.cos(z*2*np.pi)
                        yval= yposi + t*r*np.sin(z*2*np.pi)

                        xpos= np.append(xpos, xval)
                        ypos= np.append(ypos, yval)

            for z in range(0, len(zvals)):
                zpos= z*np.ones(len(xpos))
                positions= list(zip(xpos, ypos, zpos))
                poslist= poslist + positions

            self.poslist= poslist
            strx= strx.rstrip(strx[-1])
            stry= stry.rstrip(stry[-1])
            strz= strz.rstrip(strz[-1])
            arg.la.setText(strx)
            arg.lb.setText(stry)
            arg.lc.setText(strz)
            strc= strc.rstrip(strc[-1])
            strc= strc.rstrip(strc[-1])
            arg.gridCentre.setText(strc)
            arg.ea.setText(str(len(xpos)))
            arg.eb.setText(str(len(ypos)))
            arg.ec.setText(str(len(zvals)))

        if self.grid == 'sphere':

            dr= self.nx
            dtheta= self.ny/5
            dphi= self.nz/5
            zmax = max([self.z1, self.z2])
            zmin = min([self.z1, self.z2])

            for i in range(bar, len(xs)-1, 2):

                xposi= xs[i]
                xposi2= xs[i+1]

                yposi= ys[i]
                yposi2= ys[i+1]
                cx = xposi
                cy = yposi
                cz = (zmax+zmin)/2
                strc = strc + '(' + str(cx/5) + ',' + str(cy/5)+','+str(cz/5)+'), '
                rc = np.sqrt((xposi - xposi2)**2 + (yposi-yposi2)**2)
                lz= abs(zmax-zmin)

                strx = strx + str(round(rc/5, 3)) + ','
                stry = stry + str(round(rc/5, 3)) + ','
                strz= strz + str(lz/5) + ','
                if self.centers == '':
                    cx= xposi
                    cy= yposi
                    cz= (zmax+zmin)/2
                else:
                    str1= self.centers
                    str1= np.array(str1.replace('(', '').replace(')', '').split(
                        ','), dtype=float).reshape(-1, 3)
                    xs= [5*x[0] for x in str1]
                    ys= [5*x[1] for x in str1]
                    zs= [5*x[2] for x in str1]
                    cx= xs[i/2]
                    cy= ys[i/2]
                    cz= zs[i/2]

                xmax= cx + rc
                xmin= cx - rc
                ymax= cy + rc
                ymin = cy - rc

                r= 0.5*(np.sqrt((xmax-xmin)**2 + (ymax-ymin)**2) + (zmax-zmin)**2)

                linval= math.floor(r/(dr))

                thetavals= np.linspace(0, 1, math.floor(360/dtheta) + 1)
                phivals= np.linspace(0, 1, math.floor(180/dphi)+1)
                parvals= np.linspace(0, 1, linval+1)
                positions= [[cx, cy, cz]]
                # first start point already initialized in array.
                for t in parvals[1: ]:
                    # Other start points are incorporated as the end points of previous segment.
                    for z in thetavals[1: ]:
                        for p in phivals[1: ]:
                            xval= cx + t*r*np.cos(z*2*np.pi)*np.sin(p*np.pi)
                            yval= cy + t*r*np.sin(z*2*np.pi)*np.sin(p*np.pi)
                            zval= cz + t*r*np.cos(p*np.pi)
                        if (xval-cx)**2 + (yval-cy)**2 > rc**2 or zval > zmax or zval < zmin:
                            pass
                        else:
                            positions.append([xval, yval, zval])

                poslist= poslist + positions

            self.poslist= poslist
            strx= strx.rstrip(strx[-1])
            stry= stry.rstrip(stry[-1])
            strz= strz.rstrip(strz[-1])
            arg.la.setText(strx)
            arg.lb.setText(stry)
            arg.lc.setText(strz)
            strc= strc.rstrip(strc[-1])
            strc= strc.rstrip(strc[-1])
            arg.gridCentre.setText(strc)
            arg.ea.setText(str(len(xpos)))
            arg.eb.setText(str(len(ypos)))
            arg.ec.setText(str(len(zvals)))

        if self.grid == 'ellipse':

            bar= self.bar

            dr= self.nx
            dtheta= self.ny/5
            dz= self.nz


            e= self.eccentricity
            poslist= []
            xpos= []
            ypos= []
            for i in range(bar, len(self.xpos)-1, 2):

                        xposi= self.xpos[i]
                        xposi2= self.xpos[i+1]

                        yposi= self.ypos[i]
                        yposi2= self.ypos[i+1]

                        zmax= self.z1
                        zmin= self.z2
                        lz= abs(zmax-zmin)
                        cx = xposi
                        cy = yposi
                        cz = (zmax+zmin)/2
                        strc = strc + '(' + str(cx/5) + ',' + str(cy/5)+','+str(cz/5)+'), '

                        strz= strz + str(lz/5) + ','
                        linvalz= abs(math.floor((zmax-zmin)/(dz)))

                        zvals= np.linspace(zmin, zmax, linvalz+1)
                        b= np.sqrt((xposi - xposi2)**2 + (yposi-yposi2)**2)
                        a= b/np.sqrt(1-e**2)
                        strx = strx + str(round(a/5, 3)) + ','
                        stry = stry + str(round(a/5, 3)) + ','

                        cx = xposi
                        cy = yposi
                        xpos= np.append(xpos, cx)
                        ypos= np.append(ypos, cy)

                        linval= math.floor((min([a, b]))/(dr))

                        thetavals= np.linspace(
                            0, 1, math.floor(360/dtheta) + 1)
                        parvals = np.linspace(0, 1, linval+1)

                        for t in parvals[1:]:
                            for z in thetavals[1:]:
                                xval = cx + t*a*np.cos(z*2*np.pi)
                                yval = cy + t*b*np.sin(z*2*np.pi)
                                if (xval - cx)**2 + (yval - cy)**2 <= b**2 :
                                    xpos = np.append(xpos, xval)
                                    ypos = np.append(ypos, yval)

            for z in range(0, len(zvals)):
                        zpos = z*np.ones(len(xpos))
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
            
    def get_positionsellipse(self,arg):
        ''' point generator for elliptical shapes. 
        Ellipse defined by circumscribing rectangle'''


        poslist = []
        bar = self.bar
        xs = self.xpos
        ys = self.ypos

        nz = self.nz
        linvalz = abs(math.floor((self.z2-self.z1)/(nz)))
        zvals = np.linspace(self.z1, self.z2, linvalz+1)
        strx = ''
        stry = ''
        strz = ''
        strc = ''
        zmax = self.z1
        zmin = self.z2
        
        if self.grid == 'ellipse':

            dr = self.nx
            dtheta = self.ny/5

            for i in range(bar, len(xs)-1, 2):

                xposi = xs[i]
                xposi2 = xs[i+1]

                yposi = ys[i]
                yposi2 = ys[i+1]

                a = np.abs(xposi2 - xposi)/2
                b = np.abs(yposi2 - yposi)/2
                
                lz = abs(zmax-zmin)

                strx = strx + str(round(a/5,3)) + ','
                stry = stry + str(round(b/5,3)) + ','
                strz = strz + str(lz/5) + ','
                cx = (xposi + xposi2)/2
                cy = (yposi + yposi2)/2
                cz = (zmax+zmin)/2
                strc = strc + '(' + str(cx/5) + ',' + str(cy/5)+','+str(cz/5)+'), '
                xpos = [cx]
                ypos = [cy]
                linval = math.floor((min([a, b]))/(dr))

                thetavals = np.linspace(0, 1, math.floor(360/dtheta) + 1)
                parvals = np.linspace(0, 1, linval+1)

                for t in parvals[1:]:
                    for z in thetavals[1:]:
                        xval = cx + t*a*np.cos(z*2*np.pi)
                        yval = cy + t*b*np.sin(z*2*np.pi)
                        if ((xval-cx)/a)**2 + ((yval-cy)/b)**2 <= 1:
                            xpos = np.append(xpos, xval)
                            ypos = np.append(ypos, yval)

                for z in range(0, len(zvals)):
                    zpos = z*np.ones(len(xpos))
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
            
        if self.grid == 'rect':
            for i in range(bar, len(xs)-1, 2):
                xmax = self.xpos[i+1]
                xmin = self.xpos[i]
                ymax = self.ypos[i+1]
                ymin = self.ypos[i]
                nx = self.nx
                ny = self.ny
                nz = self.nz
                a = np.abs(xmax - xmin)/2
                b = np.abs(ymax-ymin)/2
                lz = abs(zmax-zmin)
                cx = (xmax + xmin)/2
                cy = (ymax + ymin)/2
                cz = (zmax + zmin)/2
                strc = strc + '(' + str(cx/5) + ',' + str(cy/5)+','+str(cz/5)+'), '
                strx = strx + str(round(a/5,3)) + ','
                stry = stry + str(round(b/5,3)) + ','
                strz = strz + str(lz/5) + ','
                
                linvalz = abs(math.floor((self.z2-self.z1)/(nz)))

                linvalx = abs(math.floor((xmax-xmin)/(nx)))
                linvaly = abs(math.floor((ymax-ymin)/(ny)))

                zvals = np.linspace(self.z1, self.z2, linvalz+1)
                xpos = np.linspace(xmin, xmax, linvalx+1)
                ypos = np.linspace(ymin, ymax, linvaly+1)

                positions = []
                for z in range(0, len(zvals)):
                    for x in range(0, len(xpos)):
                        for y in range(0, len(ypos)):
                            if (((xpos[x]-cx)/a)**2 + ((ypos[y]-cy)/b)**2 <= 1):
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
            
        if self.grid == 'circle':
            dr = self.nx
            dtheta = self.ny/5
            
            for i in range(bar, len(xs)-1, 2):

                xposi = xs[i]
                xposi2 = xs[i+1]

                yposi = ys[i]
                yposi2 = ys[i+1]
                a = np.abs(xposi - xposi2)/2
                b = np.abs(yposi-yposi2)/2
                r = np.sqrt((xposi2 - xposi)**2 + (yposi -yposi2)**2)*0.5
                lz = abs(zmax-zmin)

                strx = strx + str(round(a/5,3)) + ','
                stry = stry + str(round(b/5,3)) + ','
                strz = strz + str(lz/5) + ','
                cx = (xposi + xposi2)/2
                cy = (yposi + yposi2)/2
                cz = (zmax+zmin)/2
                strc = strc + '(' + str(cx/5) + ',' + str(cy/5)+','+str(cz/5)+'), '
                xpos = [cx]
                ypos = [cy]
                linval = math.floor(r/dr)

                thetavals = np.linspace(0, 1, math.floor(360/dtheta) + 1)
                parvals = np.linspace(0, 1, linval+1)

                for t in parvals[1:]:
                    for z in thetavals[1:]:
                        xval = cx + t*r*np.cos(z*2*np.pi)
                        yval = cy + t*r*np.sin(z*2*np.pi)
                        if ((xval-cx)/a)**2 + ((yval-cy)/b)**2 <= 1:
                            xpos = np.append(xpos, xval)
                            ypos = np.append(ypos, yval)

                for z in range(0, len(zvals)):
                    zpos = z*np.ones(len(xpos))
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
            
        if self.grid == 'sphere':

            dr = self.nx
            dtheta = self.ny/5
            dphi = self.nz/5
            zmax = max([self.z1,self.z2])
            zmin = min([self.z1,self.z2])

            for i in range(bar, len(xs)-1, 2):

                xposi = xs[i]
                xposi2 = xs[i+1]

                yposi = ys[i]
                yposi2 = ys[i+1]

                
                
                a = np.abs(xposi - xposi2)/2
                b = np.abs(yposi-yposi2)/2
                r = np.sqrt((xposi2 - xposi)**2 + (yposi -yposi2)**2 + (zmax-zmin))*0.5
                lz = abs(zmax-zmin)

                strx = strx + str(round(a/5,3)) + ','
                stry = stry + str(round(b/5,3)) + ','
                strz = strz + str(lz/5) + ','
                cx = (xposi + xposi2)/2
                cy = (yposi + yposi2)/2
                cz = (zmax+zmin)/2
                strc = strc + '(' + str(cx/5) + ',' + str(cy/5)+','+str(cz/5)+'), '
                          

                linval = math.floor(r/(dr))

                thetavals = np.linspace(0, 1, math.floor(360/dtheta) + 1)
                phivals = np.linspace(0,1,math.floor(180/dphi)+1)
                parvals = np.linspace(0, 1, linval+1)
                positions = [[cx,cy,cz]]
                # first start point already initialized in array.
                for t in parvals[1:]:
                    # Other start points are incorporated as the end points of previous segment.
                    for z in thetavals[1:]:
                        for p in phivals[1:]:
                            xval = cx + t*r*np.cos(z*2*np.pi)*np.sin(p*np.pi)
                            yval = cy + t*r*np.sin(z*2*np.pi)*np.sin(p*np.pi)
                            zval = cz + t*r*np.cos(p*np.pi)
                        if ((xval-cx)/a)**2 + ((yval-cy)/b)**2 > 1 or zval > zmax or zval < zmin:
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
        '''Final verification routine to check no point is in a no-go region or an unreachable 
        region.
        Must be run to save the config/text coordinate files. 
        '''
        self.set_status(arg)
        xs = [x[0] for x in self.poslist]
        ys = [x[1] for x in self.poslist]
        alpha = self.alpha
        barlist = self.barlist*5
        if self.hand == 0:
            theta = 0
        if self.hand == 1:
            theta = np.pi
            
        for i in range(0, len(xs)):
            dist = ((xs[i])**2 + (ys[i])**2)**0.5

            if (dist > 250):
                arg.saveButton.setEnabled(False)

                msg = QMessageBox()
                msg.setIcon(QMessageBox.Critical)
                msg.setText("Error")
                msg.setInformativeText(
                    'Some designated points are outside of the machine!')
                msg.setWindowTitle("Error")
                msg.exec_()
                return
            if theta < np.pi:    
                if (ys[i] - 250*np.sin(theta) -( (np.sin(theta)+np.sin(2*alpha+theta))/(np.cos(theta)+np.cos(2*alpha+theta))    )*(xs[i] - 250*np.cos(theta)) < 0):
                    arg.saveButton.setEnabled(False)
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Critical)
                    msg.setText("Error")
                    msg.setInformativeText(
                        'Some designated points are outside of reach!!')
                    msg.setWindowTitle("Error")
                    msg.exec_()
                    return
            
                elif (ys[i] - 250*np.sin(theta) -( (np.sin(theta)-np.sin(2*alpha-theta))/(np.cos(theta)+np.cos(2*alpha-theta))    )*(xs[i] - 250*np.cos(theta)) > 0):
                    arg.saveButton.setEnabled(False)
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Critical)
                    msg.setText("Error")
                    msg.setInformativeText(
                    'Some designated points are outside of reach!')
                    msg.setWindowTitle("Error")
                    msg.exec_()
                    return
           
            if theta >= np.pi:    
                if (ys[i] - 250*np.sin(theta) -( (np.sin(theta)+np.sin(2*alpha+theta))/(np.cos(theta)+np.cos(2*alpha+theta))    )*(xs[i] - 250*np.cos(theta)) > 0):
                    arg.saveButton.setEnabled(False)
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Critical)
                    msg.setText("Error")
                    msg.setInformativeText(
                        'Some designated points are outside of reach!!')
                    msg.setWindowTitle("Error")
                    msg.exec_()
                    return
            
                elif (ys[i] - 250*np.sin(theta) -( (np.sin(theta)-np.sin(2*alpha-theta))/(np.cos(theta)+np.cos(2*alpha-theta))    )*(xs[i] - 250*np.cos(theta)) < 0):
                    arg.saveButton.setEnabled(False)
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Critical)
                    msg.setText("Error")
                    msg.setInformativeText(
                    'Some designated points are outside of reach!')
                    msg.setWindowTitle("Error")
                    msg.exec_()
                    return
               
   #########################NO-GO ZONE CHECKS#################
            if theta >= np.pi:
                # posgroup is [(xorg,y,z),(xe),(xvo),(xve)]
                    for posgroup in barlist:
                        if posgroup[0][0]-posgroup[1][0] == 0:
                            m1 = 1
                        else:
                                m1 = (posgroup[0][1]-posgroup[1][1]) / \
                            (posgroup[0][0]-posgroup[1][0])
                                m2 = (posgroup[0][1] - posgroup[2][1]) / \
                        (posgroup[0][0]-posgroup[2][0])
                                m3 = (posgroup[1][1] - posgroup[3][1]) / \
                        (posgroup[1][0]-posgroup[3][0])

                        if (
                                ((ys[i] - m1*(xs[i] - posgroup[0][0]) - posgroup[0][1] > 0 and m1 < 0)
                                 or (ys[i] - m1*(xs[i] - posgroup[0][0]) - posgroup[0][1] < 0 and m1 > 0))

                            and (
                                ((ys[i] - m2*(xs[i]-posgroup[0][0]) - posgroup[0][1] < 0) and (ys[i] - m3*(
                                    xs[i] + m3*posgroup[1][0]) - posgroup[1][1] > 0) and (posgroup[0][1] > posgroup[1][1]))
                            or
                                ((ys[i] - m2*(xs[i]-posgroup[0][0]) - posgroup[0][1] > 0) and (ys[i] - m3*(
                                    xs[i] + m3*posgroup[1][0]) - posgroup[1][1] < 0) and (posgroup[0][1] < posgroup[1][1]))
                                )



                        ):
                            arg.saveButton.setEnabled(False)
                            msg = QMessageBox()
                            msg.setIcon(QMessageBox.Critical)
                            msg.setText("Error")
                            msg.setInformativeText(
                                'Some designated points are in No-go zone!!')
                            msg.setWindowTitle("Error")
                            msg.exec_()
                            return

            
            if theta < np.pi:
                # posgroup is [(xorg,y,z),(xe),(xvo),(xve)]
                    # posgroup is [(xorg,y,z),(xe),(xvo),(xve)]
                    for posgroup in barlist:
                        if posgroup[0][0]-posgroup[1][0] == 0:
                            m1 = 1
                        else:
                            m1 = (posgroup[0][1]-posgroup[1][1]) / \
                            (posgroup[0][0]-posgroup[1][0])
                            m2 = (posgroup[0][1] - posgroup[2][1]) / \
                        (posgroup[0][0]-posgroup[2][0])
                            m3 = (posgroup[1][1] - posgroup[3][1]) / \
                        (posgroup[1][0]-posgroup[3][0])

                        if (
                                ((ys[i] - m1*(xs[i] - posgroup[0][0]) - posgroup[0][1] > 0 and m1 > 0)
                                 or (ys[i] - m1*(xs[i] - posgroup[0][0]) - posgroup[0][1] < 0 and m1 < 0))
                                
                                and (
                                    ((ys[i] - m2*(xs[i]-posgroup[0][0]) - posgroup[0][1] < 0) and (ys[i] - m3*(
                                        xs[i] + m3*posgroup[1][0]) - posgroup[1][1] > 0) and (posgroup[0][1] > posgroup[1][1]))
                                    or
                                    ((ys[i] - m2*(xs[i]-posgroup[0][0]) - posgroup[0][1] > 0) and (ys[i] - m3*(
                                        xs[i] + m3*posgroup[1][0]) - posgroup[1][1] < 0) and (posgroup[0][1] < posgroup[1][1]))
                                    )



                            ):
                            arg.saveButton.setEnabled(False)
                            msg = QMessageBox()
                            msg.setIcon(QMessageBox.Critical)
                            msg.setText("Error")
                            msg.setInformativeText(
                                'Some designated points are in No-go zone!!')
                            msg.setWindowTitle("Error")
                            msg.exec_()
                            return

        arg.saveButton.setEnabled(True)

    def coordEnter(self, arg, n =0):
        '''massive function, should probably be restructured, rewritten? 
        Same functionality as print_position() + get_*mode*_positions(), 
        Used when precise coordinates are fed by the user to the module.
        '''
        res = min(self.nx, self.ny, self.nz)
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
                str1 = np.array(str1.replace('(', '').replace(')', '').split(','), dtype=float).reshape(-1, 3)
            else:
                    str1 = n
                    str1 = np.array(str1.replace('(', '').replace(')', '').split(','), dtype=float).reshape(-1, 3)
        except ValueError:
            pass
            # QMessageBox.about(
            #     self, "Error", "Coordinates and number of points should be valid numbers. Coordinates should be specified as (x,y,z), (x,y,z)")          
            
        
        if bar[0] == '(':
            try: 
                bar = np.array(bar.replace('(', '').replace(')', '').split(
                ','), dtype=float).reshape(-1, 3)
                xs = [5*x[0] for x in bar]
                ys = [5*x[1] for x in bar]
                zs = [5*x[2] for x in bar]
                  
                for i in range(0, len(xs)-1, 2):
                    xe = xs[i+1]
                    xorg = xs[i]
                    ye = ys[i+1]
                    yorg = ys[i]
                    r = 250
                    
                    if theta >= np.pi:
                        C = (yorg-r*np.sin(theta))/(xorg- r*np.cos(theta))
                        
                        a = 1 + C**2
                        b = -2*xorg*(C**2) + 2*C*yorg
                        c = (C**2)*xorg + yorg**2 -2*C*yorg*xorg - r**2
                        
                        xvo = (-b + np.sqrt(b**2 -4*a*c))/(2*a)
                        
                        yvo = C*(xvo-xorg) + yorg
      
                        C = (ye-r*np.sin(theta))/(xe- r*np.cos(theta))
                     
                        a = 1 + C**2
                        b = -2*xe*(C**2) + 2*C*ye
                        c = (C**2)*xe + ye**2 -2*C*ye*xe - r**2
                     
                        xve = (-b + np.sqrt(b**2 -4*a*c))/(2*a)
                     
                        yve = C*(xve-xe) + ye
   
                    if theta < np.pi:
                        C = (yorg-r*np.sin(theta))/(xorg- r*np.cos(theta))
                        
                        a = 1 + C**2
                        b = -2*xorg*(C**2) + 2*C*yorg
                        c = (C**2)*xorg + yorg**2 -2*C*yorg*xorg - r**2
                        
                        xvo = (-b - np.sqrt(b**2 -4*a*c))/(2*a)
                        
                        yvo = C*(xvo-xorg) + yorg
      
                        C = (ye-r*np.sin(theta))/(xe- r*np.cos(theta))
                     
                        a = 1 + C**2
                        b = -2*xe*(C**2) + 2*C*ye
                        c = (C**2)*xe + ye**2 -2*C*ye*xe - r**2
                     
                        xve = (-b - np.sqrt(b**2 -4*a*c))/(2*a)
                     
                        yve = C*(xve-xe) + ye
  
                    p = QPainter(self.pixmap())
                    p.setPen(QPen(QColor(Qt.red), self.config['size'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                    p.setBrush(QBrush(QColor(Qt.red)))
                    p.drawLine(QPointF(xorg+300, -yorg+300),
                           QPointF(xvo+300, -yvo+300))
                    p.drawLine(QPointF(xe+300, -ye+300),
                           QPointF(xve+300, -yve+300))

                    p.setPen(QPen(QColor(
                    '#800000'), self.config['size'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                    p.drawLine(QPointF(xorg+300, -yorg+300),
                           QPointF(xe+300, -ye+300))

                    p.end()
                    barlist.append([(xorg, yorg, self.z1), (xe, ye, self.z1),
                               (xvo, yvo, self.z1), (xve, yve, self.z1)])

                    barlist = np.array(barlist)/5
                    self.barlist = barlist
            
            except ValueError:
                   pass
        
        # p.end()
        p = QPainter(self.pixmap())
        p.setPen(QPen(QColor(Qt.blue), self.config['size'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(QBrush(QColor(Qt.blue)))
        p.setOpacity(0.5)

        if self.mode == 'polyline':
  
            try:

                xs = [5*x[0] for x in str1]
                ys = [5*x[1] for x in str1]
                zs = [5*x[2] for x in str1]
                xpos = [xs[0]]
                ypos = [ys[0]]
                zpos = [zs[0]]
                self.xpos = xs
                self.ypos = ys
                self.zpos = zs
                p.setPen(QPen(
                    QColor(Qt.black), self.config['size'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                p.setBrush(QBrush(QColor(Qt.black)))
                
                if self.closeit == True:
                    index = -1
                elif self.closeit == False:
                    index = 0
                
                
                for i in range(index, len(xs)-1):
                    p.drawLine(QPointF(xs[i]+300, -ys[i]+300),
                               QPointF(xs[i+1]+300, -ys[i+1]+300))

                for i in range(index, len(xs)-1):

                    xposi = xs[i]
                    xposi2 = xs[i+1]

                    yposi = ys[i]
                    yposi2 = ys[i+1]

                    zposi = zs[i]
                    zposi2 = zs[i+1]

                    length = ((xposi2-xposi)**2 + (yposi2-yposi)
                              ** 2 + (zposi2-zposi)**2)**0.5
                    linval = math.floor(length/(res))

                    parvals = np.linspace(0, 1, linval+1)

                    for t in parvals[1:]:

                        xval = xposi + t*(xposi2 - xposi)
                        yval = yposi + t*(yposi2 - yposi)
                        zval = zposi + t*(zposi2 - zposi)
                        xpos = np.append(xpos, xval)
                        ypos = np.append(ypos, yval)
                        zpos = np.append(zpos, zval)

                positions = list(zip(xpos, ypos, zpos))
                self.poslist = positions

            except ValueError:
                QMessageBox.about(
                    self, "Error", "Position should be valid numbers.")

        elif self.mode == 'line':
           
            try:

                xs = [5*x[0] for x in str1]
                ys = [5*x[1] for x in str1]
                zs = [5*x[2] for x in str1]
                xpos = [xs[0]]
                ypos = [ys[0]]
                zpos = [zs[0]]
                self.xpos = xs
                self.ypos = ys
                self.zpos = zs
                p.setPen(QPen(
                    QColor(Qt.black), self.config['size'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                p.setBrush(QBrush(QColor(Qt.black)))

                for i in range(0, len(xs)-1, 2):
                    p.drawLine(QPointF(xs[i]+300, -ys[i]+300),
                               QPointF(300+xs[i+1], -ys[i+1]+300))

                for i in range(0, len(xs)-1, 2):

                    xposi = xs[i]
                    xposi2 = xs[i+1]

                    yposi = ys[i]
                    yposi2 = ys[i+1]

                    zposi = zs[i]
                    zposi2 = zs[i+1]

                    length = ((xposi2-xposi)**2 + (yposi2-yposi)
                              ** 2 + (zposi2-zposi)**2)**0.5
                    linval = math.floor(length/(res))

                    parvals = np.linspace(0, 1, linval+1)

                    for t in parvals[1:]:

                        xval = xposi + t*(xposi2 - xposi)
                        yval = yposi + t*(yposi2 - yposi)
                        zval = zposi + t*(zposi2 - zposi)
                        xpos = np.append(xpos, xval)
                        ypos = np.append(ypos, yval)
                        zpos = np.append(zpos, zval)

                positions = list(zip(xpos, ypos, zpos))
                self.poslist = positions

            except ValueError:
                QMessageBox.about(
                    self, "Error", "Position should be valid numbers.")

        elif self.mode == 'rect':

            if self.grid == 'rect':
               
                try:

                    xs = [5*x[0] for x in str1]
                    ys = [5*x[1] for x in str1]
                    zs = [5*x[2] for x in str1]
                    self.xpos = xs
                    self.ypos = ys
                    self.zpos = zs
                    nx = self.nx
                    ny = self.ny
                    nz = self.nz
                  
                    poslist = []
                    for i in range(0, len(self.xpos)-1, 2):
                        p.drawRect(
                        QRectF(xs[i]+300, -ys[i]+300, xs[i+1]-xs[i], -ys[i+1]+ys[i]))
                        xmax = self.xpos[i+1]
                        xmin = self.xpos[i]
                        ymax = self.ypos[i+1]
                        ymin = self.ypos[i]
                        zmax = self.zpos[i+1]
                        zmin = self.zpos[i]
                        cx = (xmax+xmin)/2
                        cy = (ymax+ymin)/2
                        cz = (zmax+zmin)/2
                        linvalz = abs(math.floor((zmax-zmin)/(nz)))
                        linvalx = abs(math.floor((xmax-xmin)/(nx)))
                        linvaly = abs(math.floor((ymax-ymin)/(ny)))
                        zvals = np.linspace(zmin, zmax, linvalz+1)
                        xvals = np.linspace(xmin, xmax, linvalx+1)
                        yvals = np.linspace(ymin, ymax, linvaly+1)

                        positions = []
                        for z in zvals:
                            for x in xvals:
                                for y in yvals:
                                    positions.append(
                                            [x,y,z])

                        poslist.extend(positions)
                        # print(poslist)
                    self.poslist = poslist

                except ValueError:
                    QMessageBox.about(
                        self, "Error", "Position should be valid numbers.")

            if self.grid == 'circle':
               
                try:

                    xs = [5*x[0] for x in str1]
                    ys = [5*x[1] for x in str1]
                    zs = [5*x[2] for x in str1]
                    self.xpos = xs
                    self.ypos = ys
                    self.zpos = zs
                    dr = self.nx
                    dtheta = self.ny/5
                    nz = self.nz
                    
                    xpos = []
                    ypos = []
                    poslist = []
                    for i in range(0, len(self.xpos)-1, 2):
                        p.drawRect(
                            QRectF(xs[i]+300, -ys[i]+300, xs[i+1]-xs[i], -ys[i+1]+ys[i]))
                        xmax = max([self.xpos[i+1], self.xpos[i]])
                        xmin = min([self.xpos[i+1], self.xpos[i]])
                        ymax = max([self.ypos[i+1], self.ypos[i]])
                        ymin = min([self.ypos[i+1], self.ypos[i]])
                        zmax = max([self.zpos[i+1], self.zpos[i]])
                        zmin = min([self.zpos[i+1], self.zpos[i]])

                        linvalz = abs(math.floor((zmax-zmin)/(nz)))
                        cx = (xmax+xmin)/2
                        cy = (ymax+ymin)/2
                        cz = (zmax+zmin)/2
                        # if self.centers == '':
                        #     cx = (xmax+xmin)/2
                        #     cy = (ymax+ymin)/2
                        #     cz = (zmax+zmin)/2
                        # else:
                        #     str1 = self.centers
                        #     str1 = np.array(str1.replace('(', '').replace(')', '').split(
                        #         ','), dtype=float).reshape(-1, 3)
                        #     xs1 = [5*x[0] for x in str1]
                        #     ys1 = [5*x[1] for x in str1]
                        #     zs1 = [5*x[2] for x in str1]
                        #     cx = (xs1[i] + xs1[i+1])/2
                        #     cy = (ys1[i] + ys1[i+1])/2
                        #     cz = (zs1[i] + zs1[i+1])/2
                        # NEED TO RECALCULATE POINT GENERATING PARAMETERS TO GET APPROPRIATE ONES WITHIN THE REGION.
                        zvals = np.linspace(zmin, zmax, linvalz+1)

                        r = 0.5*(np.sqrt((xmax-xmin)**2 + (ymax-ymin)**2))

                        linval = math.floor(r/(dr))

                        thetavals = np.linspace(
                            0, 1, math.floor(360/dtheta) + 1)
                        parvals = np.linspace(0, 1, linval+1)
                        positions = []
                        for t in parvals[1:]:
                            for z in thetavals[1:]:
                                xval = cx + t*r*np.cos(z*2*np.pi)
                                yval = cy + t*r*np.sin(z*2*np.pi)

                                if (xval > xmax) or xval < xmin or yval > ymax or yval < ymin:
                                    pass
                                else:
                                    xpos = np.append(xpos, xval)
                                    ypos = np.append(ypos, yval)

                        for z in zvals:
                            zpos = z*np.ones(len(xpos))
                            positions = list(zip(xpos, ypos, zpos))
                            poslist = poslist + positions
                        self.poslist = poslist

                except ValueError:
                    QMessageBox.about(
                        self, "Error", "Position should be valid numbers.")
      
            if self.grid == 'ellipse':
               
                try:

                    xs = [5*x[0] for x in str1]
                    ys = [5*x[1] for x in str1]
                    zs = [5*x[2] for x in str1]
                    self.xpos = xs
                    self.ypos = ys
                    self.zpos = zs
                    dr = self.nx
                    dtheta = self.ny/5
                    dz = self.nz
                    
                    e = self.eccentricity
                    xpos = []
                    ypos = []
                    poslist = []
                    for i in range(0, len(self.xpos)-1, 2):
                        p.drawRect(
                           QRectF(xs[i]+300, -ys[i]+300, xs[i+1]-xs[i], -ys[i+1]+ys[i]))
                       
                        xmax = max([self.xpos[i+1], self.xpos[i]])
                        xmin = min([self.xpos[i+1], self.xpos[i]])
                        ymax = max([self.ypos[i+1], self.ypos[i]])
                        ymin = min([self.ypos[i+1], self.ypos[i]])
                        zmax = max([self.zpos[i+1], self.zpos[i]])
                        zmin = min([self.zpos[i+1], self.zpos[i]])
                        # if self.centers == '':
                        #     cx = (xmax+xmin)/2
                        #     cy = (ymax+ymin)/2
                        #     cz = (zmax+zmin)/2
                        # else:
                        #     str1 = self.centers
                        #     str1 = np.array(str1.replace('(', '').replace(')', '').split(
                        #         ','), dtype=float).reshape(-1, 3)
                        #     xs1 = [5*x[0] for x in str1]
                        #     ys1 = [5*x[1] for x in str1]
                        #     zs1 = [5*x[2] for x in str1]
                        #     cx = (xs1[i] + xs1[i+1])/2
                        #     cy = (ys1[i] + ys1[i+1])/2
                        #     cz = (zs1[i] + zs1[i+1])/2
                        cx = (xmax+xmin)/2
                        cy = (ymax+ymin)/2
                        cz = (zmax+zmin)/2
                        # NEED TO RECALCULATE POINT GENERATING PARAMETERS TO GET APPROPRIATE ONES WITHIN THE REGION.
                        linvalz = abs(math.floor((zmax-zmin)/(dz)))
                        zvals = np.linspace(zmin, zmax, linvalz+1)
     
                        a = max([(xmax - xmin) , (ymax-ymin)])
                        b = a*np.sqrt(1-e**2)

                        xpos = np.append(xpos, cx)
                        ypos = np.append(ypos, cy)

                        linval = math.floor((min([a, b]))/(dr))

                        thetavals = np.linspace(
                            0, 1, math.floor(360/dtheta) + 1)
                        parvals = np.linspace(0, 1, linval+1)

                        for t in parvals[1:]:
                            for z in thetavals[1:]:
                                xval = cx + t*a*np.cos(z*2*np.pi)
                                yval = cy + t*b*np.sin(z*2*np.pi)
                                if (xval > xmax) or xval < xmin or yval > ymax or yval < ymin:
                                    pass
                                else:
                                    xpos = np.append(xpos, xval)
                                    ypos = np.append(ypos, yval)

                        for z in zvals:
                            zpos = z*np.ones(len(xpos))
                            positions = list(zip(xpos, ypos, zpos))
                            poslist = poslist + positions

                    self.poslist = poslist

                        

                except ValueError:
                    QMessageBox.about(
                        self, "Error", "Position should be valid numbers.")


            if self.grid == 'sphere':
              
                try:

                    xs = [5*x[0] for x in str1]
                    ys = [5*x[1] for x in str1]
                    zs = [5*x[2] for x in str1]
                    self.xpos = xs
                    self.ypos = ys
                    self.zpos = zs
                    dr = self.nx
                    dtheta = self.ny/5
                    dphi = self.nz/5
                    

                    poslist = []
                    for i in range(0, len(self.xpos)-1, 2):
                        p.drawRect(
                            QRectF(xs[i]+300, -ys[i]+300, xs[i+1]-xs[i], -ys[i+1]+ys[i]))
                        xmax = max([self.xpos[i+1], self.xpos[i]])
                        xmin = min([self.xpos[i+1], self.xpos[i]])
                        ymax = max([self.ypos[i+1], self.ypos[i]])
                        ymin = min([self.ypos[i+1], self.ypos[i]])
                        zmax = max([self.zpos[i+1], self.zpos[i]])
                        zmin = min([self.zpos[i+1], self.zpos[i]])

                        # if self.centers == '':
                        #     cx = (xmax+xmin)/2
                        #     cy = (ymax+ymin)/2
                        #     cz = (zmax+zmin)/2
                        # else:
                        #     str1 = self.centers
                        #     str1 = np.array(str1.replace('(', '').replace(')', '').split(
                        #         ','), dtype=float).reshape(-1, 3)
                        #     xs1 = [5*x[0] for x in str1]
                        #     ys1 = [5*x[1] for x in str1]
                        #     zs1 = [5*x[2] for x in str1]
                        #     cx = (xs1[i] + xs1[i+1])/2
                        #     cy = (ys1[i] + ys1[i+1])/2
                        #     cz = (zs1[i] + zs1[i+1])/2
                        # NEED TO RECALCULATE POINT GENERATING PARAMETERS TO GET APPROPRIATE ONES WITHIN THE REGION.
                        cx = (xmax+xmin)/2
                        cy = (ymax+ymin)/2
                        cz = (zmax+zmin)/2
                        r = (np.sqrt((xmax-xmin)**2 +
                             (ymax-ymin)**2 + (zmax-zmin)**2))

                        linval = math.floor(r/(dr))

                        thetavals = np.linspace(
                            0, 1, math.floor(360/dtheta) + 1)
                        phivals = np.linspace(0, 1, math.floor(180/dphi) + 1)
                        parvals = np.linspace(0, 1, linval+1)
                        positions = [[cx,cy,cz]]
                        for t in parvals[1:]:
                            for z in thetavals[1:]:
                                for p in phivals[1:]:
                                    xval = cx + t*r * \
                                        np.cos(z*2*np.pi)*np.sin(p*np.pi)
                                    yval = cy + t*r * \
                                        np.sin(z*2*np.pi)*np.sin(p*np.pi)
                                    zval = cz + t*r*np.cos(p*np.pi)
                                    if (xval > xmax) or xval < xmin or yval > ymax or yval < ymin or zval > zmax or zval < zmin:
                                        pass
                                    else:
                                        positions.append([xval, yval, zval])

                        poslist.extend(positions)

                    self.poslist = poslist
                except ValueError:
                    QMessageBox.about(
                        self, "Error", "Position should be valid numbers.")

        elif self.mode == 'circle':

            if self.grid == 'circle':
                poslist = []
                bar = self.bar

                try:

                    xs = [5*x[0] for x in str1]
                    ys = [5*x[1] for x in str1]
                    zs = [5*x[2] for x in str1]
                    self.xpos = xs
                    self.ypos = ys
                    self.zpos = zs
                    dr = self.nx
                    dtheta = self.ny/5
                    nz = self.nz
                  
                    poslist = []
             

                    for i in range(0, len(self.xpos)-1, 2):
                        xpos = []
                        ypos = []
                        xposi = xs[i]
                        xposi2 = xs[i+1]

                        yposi = ys[i]
                        yposi2 = ys[i+1]

                        zmax = zs[i+1]
                        zmin = zs[i]
                        linvalz = abs(math.floor((zmax-zmin)/(nz)))
                        
                        xpos = np.append(xpos, xposi)
                        ypos = np.append(ypos, yposi)
                        zvals = np.linspace(zmin, zmax, linvalz+1)
                        r = np.sqrt((xposi - xposi2)**2 + (yposi-yposi2)**2)

                        dr = self.nx
                        dtheta = self.ny/5

                        p.drawEllipse(QPointF(xs[i]+300, -ys[i]+300), r, r)
                        linval = math.floor(r/(dr))

                        thetavals = np.linspace(
                            0, 1, math.floor(360/dtheta) + 1)
                        parvals = np.linspace(0, 1, linval+1)

                        for t in parvals[1:]:
                            for th in thetavals[1:]:
                                xval = xposi + t*r*np.cos(th*2*np.pi)
                                yval = yposi + t*r*np.sin(th*2*np.pi)

                                xpos = np.append(xpos, xval)
                                ypos = np.append(ypos, yval)

                        for z in zvals:
                            zpos = z*np.ones(len(xpos))
                            positions = list(zip(xpos, ypos, zpos))
                            poslist = poslist + positions
                        
                    self.poslist = poslist

                except ValueError:
                    QMessageBox.about(
                        self, "Error", "Position should be valid numbers.")

            if self.grid == 'rect':
                poslist = []
                bar = self.bar

                try:

                    xs = [5*x[0] for x in str1]
                    ys = [5*x[1] for x in str1]
                    zs = [5*x[2] for x in str1]
                    self.xpos = xs
                    self.ypos = ys
                    self.zpos = zs
                    nx = self.nx
                    ny = self.ny
                    nz = self.nz
                  

                    poslist = []
                    xpos = []
                    ypos = []
                    zpos = []

                    for i in range(0, len(self.xpos)-1, 2):

                        xposi = xs[i]
                        xposi2 = xs[i+1]

                        yposi = ys[i]
                        yposi2 = ys[i+1]

                        zmax = zs[i+1]
                        zmin = zs[i]
                        cx = xposi
                        cy = yposi
                        cz = (zmax+zmin)/2
                        # if self.centers == '':
                        #     cx = xposi
                        #     cy = yposi
                        #     cz = (zmax+zmin)/2
                        # else:
                        #     str1 = self.centers
                        #     str1 = np.array(str1.replace('(', '').replace(')', '').split(
                        #         ','), dtype=float).reshape(-1, 3)
                        #     xs = [5*x[0] for x in str1]
                        #     ys = [5*x[1] for x in str1]
                        #     zs = [5*x[2] for x in str1]
                        #     cx = xs[i]
                        #     cy = ys[i]
                        #     cz = zs[i]

                        r = np.sqrt((xposi - xposi2)**2 + (yposi-yposi2)**2)
                        xmax = cx + r
                        xmin = cx - r
                        ymax = cy + r
                        ymin = cy - r

                        p.drawEllipse(QPointF(xs[i]+300, -ys[i]+300), r, r)

                        linvalz = abs(math.floor((zmax-zmin)/(nz)))

                        linvalx = abs(math.floor((xmax-xmin)/(nx)))
                        linvaly = abs(math.floor((ymax-ymin)/(ny)))

                        zvals = np.linspace(zmin, zmax, linvalz+1)
                        xvals = np.linspace(xmin, xmax, linvalx+1)
                        yvals = np.linspace(ymin, ymax, linvaly+1)

                        positions = []
                        for z in zvals:
                            for x in xvals:
                                for y in yvals:
                                    if (xvals[x] - cx)**2 + (yvals[y] - cy)**2 <= r**2 and zvals[z] <= zmax and zvals[z] >= zmin:
                                        positions.append(
                                            [xvals[x], yvals[y], zvals[z]])
                                    else:
                                        pass

                    poslist.extend(positions)
                    self.poslist = poslist

                except ValueError:
                    QMessageBox.about(
                        self, "Error", "Position should be valid numbers.")

            if self.grid == 'sphere':
                poslist = []
                bar = self.bar

              
                try:

                    xs = [5*x[0] for x in str1]
                    ys = [5*x[1] for x in str1]
                    zs = [5*x[2] for x in str1]
                    self.xpos = xs
                    self.ypos = ys
                    self.zpos = zs
                    dr = self.nx
                    dtheta = self.ny/5
                    dphi = self.nz/5
                   
               

                    poslist = []
                    
                    for i in range(0, len(self.xpos)-1, 2):

                        xposi = xs[i]
                        xposi2 = xs[i+1]

                        yposi = ys[i]
                        yposi2 = ys[i+1]

                        zmax = zs[i+1]
                        zmin = zs[i]
                        cx = xposi
                        cy = yposi
                        cz = (zmax+zmin)/2
                        # if self.centers == '':
                        #     cx = xposi
                        #     cy = yposi
                        #     cz = (zmax+zmin)/2
                        # else:
                        #     str1 = self.centers
                        #     str1 = np.array(str1.replace('(', '').replace(')', '').split(
                        #         ','), dtype=float).reshape(-1, 3)
                        #     xs = [5*x[0] for x in str1]
                        #     ys = [5*x[1] for x in str1]
                        #     zs = [5*x[2] for x in str1]
                        #     cx = xs[i]
                        #     cy = ys[i]
                        #     cz = zs[i]

                        rc = np.sqrt((xposi - xposi2)**2 + (yposi-yposi2)**2)
                        xmax = cx + rc
                        xmin = cx - rc
                        ymax = cy + rc
                        ymin = cy - rc

                        p.drawEllipse(QPointF(xs[i]+300, -ys[i]+300), rc, rc)

                        r = 0.5*(np.sqrt((xmax-xmin)**2 + (ymax-ymin)**2) + (zmax-zmin)**2)

                        linval = math.floor(r/(dr))

                        thetavals = np.linspace(0, 1, math.floor(360/dtheta) + 1)
                        phivals = np.linspace(0,1,math.floor(180/dphi)+1)
                        parvals = np.linspace(0, 1, linval+1)
                        positions = [[cx,cy,cz]]
                        # first start point already initialized in array.
                        for t in parvals[1:]:
                            # Other start points are incorporated as the end points of previous segment.
                            for z in thetavals[1:]:
                                for p in phivals[1:]:
                                    xval = cx + t*r*np.cos(z*2*np.pi)*np.sin(p*np.pi)
                                    yval = cy + t*r*np.sin(z*2*np.pi)*np.sin(p*np.pi)
                                    zval = cz + t*r*np.cos(p*np.pi)
                                if (xval-cx)**2 + (yval-cy)**2 > rc**2 or zval > zmax or zval < zmin:
                                    pass
                                else:
                                    positions.append([xval, yval, zval])

                        poslist = poslist + positions

                    self.poslist = poslist

                except ValueError:
                    QMessageBox.about(
                        self, "Error", "Position should be valid numbers.")
        
            if self.grid == 'ellipse':
                poslist = []
                bar = self.bar

              
                try:

                    xs = [5*x[0] for x in str1]
                    ys = [5*x[1] for x in str1]
                    zs = [5*x[2] for x in str1]
                    self.xpos = xs
                    self.ypos = ys
                    self.zpos = zs
                    dr = self.nx
                    dtheta = self.ny/5
                    dz = self.nz
                   
                  
                    e = self.eccentricity
                    poslist = []
                    xpos = []
                    ypos = []
                    for i in range(0, len(self.xpos)-1, 2):

                        xposi = xs[i]
                        xposi2 = xs[i+1]

                        yposi = ys[i]
                        yposi2 = ys[i+1]

                        zmax = zs[i+1]
                        zmin = zs[i]
                        linvalz = abs(math.floor((zmax-zmin)/(dz)))

                        zvals = np.linspace(zmin, zmax, linvalz+1)
                        b = np.sqrt((xposi - xposi2)**2 + (yposi-yposi2)**2)
                        a = b/np.sqrt(1-e**2)
                        # zposi = zs[i]
                        # zposi2 =zs[i+1]

                        cx = xposi
                        cy = yposi
                        cz = (zmax+zmin)/2 
                        xpos = np.append(xpos, cx)
                        ypos = np.append(ypos, cy)

                        p.drawEllipse(QPointF(xs[i]+300, -ys[i]+300), r, r)
                        linval = math.floor((min([a, b]))/(dr))

                        thetavals = np.linspace(
                            0, 1, math.floor(360/dtheta) + 1)
                        parvals = np.linspace(0, 1, linval+1)

                        for t in parvals[1:]:
                            for z in thetavals[1:]:
                                xval = cx + t*a*np.cos(z*2*np.pi)
                                yval = cy + t*b*np.sin(z*2*np.pi)
                                if (xval - cx)**2 + (yval - cy)**2 <= b**2 :
                                    xpos = np.append(xpos, xval)
                                    ypos = np.append(ypos, yval)

                        for z in zvals:
                            zpos = z*np.ones(len(xpos))
                            positions = list(zip(xpos, ypos, zpos))
                            poslist = poslist + positions

                    self.poslist = poslist

                except ValueError:
                    QMessageBox.about(
                        self, "Error", "Position should be valid numbers.")

  
        
        
        elif self.mode == 'ellipse':
            
            if self.grid == 'ellipse':
                poslist = []
                bar = self.bar

                try:

                    xs = [5*x[0] for x in str1]
                    ys = [5*x[1] for x in str1]
                    zs = [5*x[2] for x in str1]
                    self.xpos = xs
                    self.ypos = ys
                    self.zpos = zs
                    dr = self.nx
                    dtheta = self.ny/5
                    nz = self.nz
                  

                    poslist = []
        

                    for i in range(0, len(self.xpos)-1, 2):
                        xpos = []
                        ypos = []
                        xposi = xs[i]
                        xposi2 = xs[i+1]

                        yposi = ys[i]
                        yposi2 = ys[i+1]

                        zmax = zs[i+1]
                        zmin = zs[i]
                        linvalz = abs(math.floor((zmax-zmin)/(nz)))

                        zvals = np.linspace(zmin, zmax, linvalz+1)
                        a = np.abs(xposi2-xposi)/2
                        b = np.abs(yposi2-yposi)/2
                        # zposi = zs[i]
                        # zposi2 =zs[i+1]

                        cx = (xposi + xposi2)/2
                        cy = (yposi + yposi2)/2
                        cz = (zmax + zmin)/2
                        xpos = np.append(xpos, cx)
                        ypos = np.append(ypos, cy)

                        p.drawEllipse(
                            QRect(QPoint(xposi+300, -yposi+300), QPoint(xposi2+300, -yposi2+300)))
                        linval = math.floor((min([a, b]))/(dr))

                        thetavals = np.linspace(
                            0, 1, math.floor(360/dtheta) + 1)
                        parvals = np.linspace(0, 1, linval+1)

                        for t in parvals[1:]:
                            for z in thetavals[1:]:
                                xval = cx + t*a*np.cos(z*2*np.pi)
                                yval = cy + t*b*np.sin(z*2*np.pi)

                                xpos = np.append(xpos, xval)
                                ypos = np.append(ypos, yval)

                        for z in zvals:
                            zpos = z*np.ones(len(xpos))
                            positions = list(zip(xpos, ypos, zpos))
                            poslist = poslist + positions

                    self.poslist = poslist

                except ValueError:
                    QMessageBox.about(
                        self, "Error", "Position should be valid numbers.")
                    
            if self.grid == 'rect':
                poslist = []
                bar = self.bar

                try:

                    xs = [5*x[0] for x in str1]
                    ys = [5*x[1] for x in str1]
                    zs = [5*x[2] for x in str1]
                    self.xpos = xs
                    self.ypos = ys
                    self.zpos = zs
               
                    nx = self.nx
                    ny = self.ny 
                    nz = self.nz
                    poslist = []
                  

                    for i in range(0, len(self.xpos)-1, 2):

                        xmax = self.xpos[i+1]
                        xmin = self.xpos[i]
                        ymax = self.ypos[i+1]
                        ymin = self.ypos[i]
                        zmax = zs[i+1]
                        zmin = zs[i]
                        linvalz = abs(math.floor((zmax-zmin)/(nz)))

                        zvals = np.linspace(zmin, zmax, linvalz+1)


                        cx = (xposi + xposi2)/2 
                        cy = (yposi + yposi2)/2
                        cz = (zmax + zmin)/2

                        p.drawEllipse(
                            QRect(QPoint(xposi+300, -yposi+300), QPoint(xposi2+300, -yposi2+300)))
                       
                        nx = self.nx
                        ny = self.ny
                        nz = self.nz
                        a = np.abs(xmax - xmin)/2
                        b = np.abs(ymax-  ymin)/2
                        # if self.centers == '':
                        #         cx = (xmax + xmin)/2
                        #         cy = (ymax + ymin)/2
                        # else:
                        #         str1 = self.centers
                        #         str1 = np.array(str1.replace('(', '').replace(')', '').split(
                        #             ','), dtype=float).reshape(-1, 3)
                        #         xs = [5*x[0] for x in str1]
                        #         ys = [5*x[1] for x in str1]
                        #         zs = [5*x[2] for x in str1]
                        #         cx = xs[i]
                        #         cy = ys[i]
                        #         cz = zs[i]

                        linvalx = abs(math.floor((xmax-xmin)/(nx)))
                        linvaly = abs(math.floor((ymax-ymin)/(ny)))
                        xpos = np.linspace(xmin, xmax, linvalx+1)
                        ypos = np.linspace(ymin, ymax, linvaly+1)
                        positions = []
                        for z in range(0, len(zvals)):
                                for x in range(0, len(xpos)):
                                    for y in range(0, len(ypos)):
                                        if (((xpos[x]-cx)/a)**2 + ((ypos[y]-cy)/b)**2 <= 1):
                                            positions.append([xpos[x], ypos[y], zvals[z]])
                                        else:
                                            pass

                        poslist.extend(positions)
                    self.poslist = poslist

                except ValueError:
                    QMessageBox.about(
                        self, "Error", "Position should be valid numbers.")
                    
            if self.grid == 'circle':
                poslist = []
                bar = self.bar

                try:

                    xs = [5*x[0] for x in str1]
                    ys = [5*x[1] for x in str1]
                    zs = [5*x[2] for x in str1]
                    self.xpos = xs
                    self.ypos = ys
                    self.zpos = zs
                 
                    nx = self.nx
                    ny = self.ny 
                    nz = self.nz
                    poslist = []
                  

                    for i in range(0, len(self.xpos)-1, 2):

                        xmax = self.xpos[i+1]
                        xmin = self.xpos[i]
                        ymax = self.ypos[i+1]
                        ymin = self.ypos[i]
                        zmax = zs[i+1]
                        zmin = zs[i]
                        linvalz = abs(math.floor((zmax-zmin)/(nz)))

                        zvals = np.linspace(zmin, zmax, linvalz+1)
                        p.drawEllipse(
                            QRect(QPoint(xposi+300, -yposi+300), QPoint(xposi2+300, -yposi2+300)))
                       
                       
                        cx = (xposi + xposi2)/2
                        cy = (yposi + yposi2)/2
                        cz = (zmax + zmin)/2
                        
                        nx = self.nx
                        ny = self.ny
                        nz = self.nz
                        a = np.abs(xmax - xmin)/2
                        b = np.abs(ymax-  ymin)/2
                        r = np.sqrt((xposi2 - xposi)**2 + (yposi -yposi2)**2)*0.5

                        # if self.centers == '':
                        #     cx = (xposi + xposi2)/2
                        #     cy = (yposi + yposi2)/2
                        # else:
                        #     str1 = self.centers
                        #     str1 = np.array(str1.replace('(', '').replace(')', '').split(
                        #         ','), dtype=float).reshape(-1, 3)
                        #     xs = [5*x[0] for x in str1]
                        #     ys = [5*x[1] for x in str1]
                        #     zs = [5*x[2] for x in str1]
                        #     cx = xs[i]
                        #     cy = ys[i]
                        #     cz = zs[i]
                        xpos = [cx]
                        ypos = [cy]
                        linval = math.floor(r/dr)

                        thetavals = np.linspace(0, 1, math.floor(360/dtheta) + 1)
                        parvals = np.linspace(0, 1, linval+1)

                        for t in parvals[1:]:
                            for z in thetavals[1:]:
                                xval = cx + t*r*np.cos(z*2*np.pi)
                                yval = cy + t*r*np.sin(z*2*np.pi)
                                if ((xval-cx)/a)**2 + ((yval-cy)/b)**2 <= 1:
                                    xpos = np.append(xpos, xval)
                                    ypos = np.append(ypos, yval)

                    for z in range(0, len(zvals)):
                        zpos = z*np.ones(len(xpos))
                        positions = list(zip(xpos, ypos, zpos))
                        poslist = poslist + positions

                    self.poslist = poslist

                except ValueError:
                    QMessageBox.about(
                        self, "Error", "Position should be valid numbers.")

    def enter(self,arg, mode):
        ''' Handles dynamic updating of shapes, points as per user input in autogeneration mode'''
        
        if self.centers == '' or arg.ea.text() == '' or (arg.eb.text() == '' and mode == 'rect') or arg.ec.text() == '':
            pass
        else:
            str1 = self.centers
            str1 = np.array(str1.replace('(', '').replace(')', '').split(','), dtype=float).reshape(-1, 3)
            xs1 = [x[0] for x in str1]
            ys1 = [x[1] for x in str1]
            zs1 = [x[2] for x in str1]
            ec = str(arg.ec.text())
            eb = str(arg.eb.text())
            ea = str(arg.ea.text())
            
            try:
                ea = [int(s) for s in ea.split(',')]
                ec = [int(s) for s in ec.split(',')]
                if eb != '':
                    eb = [int(s) for s in eb.split(',')]            
            except ValueError:
              pass
            
            str1 = ''
            strx = ''
            stry = ''
            strz = ''

            if mode == 'circle':
                try:
                    dr = self.nx/5
                    dtheta = self.ny/5
                    dz = self.nz/5

                    for i in range(0,len(xs1)):
                        perRing = 360/dtheta
                        ringnum = math.floor(ea[i]/perRing)
                        r = ringnum*dr
                        rz = (ec[i]-1)*dz/2
                        str0 = '(' + str(xs1[i])+','+str(ys1[i])+','+str(zs1[i]+rz)+'), ('+str(xs1[i]+r)+','+str(ys1[i])+','+str(zs1[i]-rz)+')'
                        str1 = str1 + str0 + ', '
                        strz = strz + str(2*rz) + ','
                        strx = strx + str(r) + ','
                    
                    strx = strx.rstrip(strz[-1]) + 'cm'
                    strz = strz.rstrip(strz[-1]) + 'cm'
                    str1 = str1.rstrip(str1[-1])
                    str1 = str1.rstrip(str1[-1])
                    arg.la.setText(strx)
                    arg.lb.setText(strx)
                    arg.lc.setText(strz)
                    self.str1 = str1
                    self.coordEnter(arg, str1)
                except IndexError:
                    QMessageBox.about(
                        self, "Error", "Not enough parameters (centers or points) have been defined.")
                except ValueError:
                    pass
            if mode == 'rect':
                try:
                    dx = self.nx/5
                    dy = self.ny/5
                    dz = self.nz/5
                    for i in range(0,len(xs1)):
                    
                        rx = (ea[i]-1)*dx/2
                        ry = (eb[i]-1)*dy/2
                        rz = (ec[i]-1)*dz/2
                        str0 = '('+ str(rx + xs1[i])+','+str(ry+ys1[i])+','+str(rz+ zs1[i])+'), ('+str(xs1[i]-rx)+','+str(ys1[i]-ry)+','+str(zs1[i]-rz)+')'
                        str1 = str1 + str0  + ', '
                        strx = strx + str(2*rx) + ','
                        stry = stry + str(2*ry) + ','
                        strz = strz + str(2*rz) + ','
                    str1 = str1.rstrip(str1[-1])
                    str1 = str1.rstrip(str1[-1])
                    strx = strx.rstrip(strx[-1]) + 'cm'
                    stry = stry.rstrip(stry[-1]) + 'cm'
                    strz = strz.rstrip(strz[-1]) + 'cm'
                    arg.la.setText(strx)
                    arg.lb.setText(stry)
                    arg.lc.setText(strz)
                    self.str1 = str1
                    self.coordEnter(arg, str1)
                except IndexError:
                   QMessageBox.about(
                       self, "Error", "Not enough parameters (centers or points) have been defined.")
                except ValueError:
                   QMessageBox.about(
                       self, "Error", "Coordinates and number of points should be valid numbers. Coordinates should be specified as (x,y,z), (x,y,z)")                
          
                
            if mode == 'ellipse':
                try: 
                    dr = self.nx/5
                    dtheta = self.ny/5
                    dz = self.nz/5
                    e = self.eccentricity

                    for i in range(0,len(xs1)):
                        perRing = 360/dtheta
                        a = (ea[i]/perRing)*(dr/(1-e**2)**0.5)
                        b = (ea[i]/perRing)*dr
                        rz = (ec[i]-1)*dz/2

                        str0 = '('+ str(a + xs1[i])+','+str(b+ys1[i])+','+str(zs1[i]+rz)+'), ('+str(xs1[i]-a)+','+str(ys1[i]-b)+','+str(zs1[i]-rz)+')'
                        str1 = str1 + str0 + ', '
                        strx = str(round(2*a,3)) + ','
                        stry = str(round(2*b,3)) + ','
                        strz = str(round(2*rz,3))+ ','
                    str1 = str1.rstrip(str1[-1])
                    str1 = str1.rstrip(str1[-1])
                    strx = strx.rstrip(strx[-1]) + 'cm'
                    stry = stry.rstrip(stry[-1]) + 'cm'
                    strz = strz.rstrip(strz[-1]) + 'cm'
                    arg.la.setText(strx)
                    arg.lb.setText(stry)
                    arg.lc.setText(strz)
                    self.str1 = str1
                    self.coordEnter(arg, str1)
                except IndexError:
                   QMessageBox.about(
                       self, "Error", "Not enough parameters (centers or points) have been defined.")
                except ValueError:
                   QMessageBox.about(
                       self, "Error", "Coordinates and number of points should be valid numbers. Coordinates should be specified as (x,y,z), (x,y,z)")
            
            if mode == 'sphere':
                pass

    def set_name(self,name):
        self.name = name
        self.id = self.name.replace(" ", "_").lower()

    def save_file(self):
        
        zs = []
        for z in self.zpos:
            zs.append(z/5)     
        self.zpos = zs
        
        xs = []
        for x in self.xpos:
            xs.append(x/5)     
        self.xpos = xs
        
        ys = []
        for y in self.ypos:
            ys.append(y/5)     
        self.ypos = ys
        
        Dict1 = {'group.id': self.id, 'mode': self.mode, 'grid': self.grid, 'dx': self.nx/5, 'dy': self.ny/5, 'dz': self.nz/5,
                'xs': self.xpos, 'ys': self.ypos  , 'zs': self.zpos, 'bar': self.barlist.tolist(),  'close': self.closeit, 'centers': self.centers}
        

        
        # tomli_string = tomli_w.dumps(Dict1)  # Output to a string
        save_path = 'C:\\Users\\risha\\Desktop\\daq-mod-probedrives\\Groups'
        output_file_name = str(self.name)
        completeName = os.path.join(save_path, output_file_name+".toml")
    
        f = open(completeName, 'rb')
        with f:
            self.toml_dict = tomli.load(f)
    
        self.toml_dict['Motion List'] = Dict1    
    
        with open(completeName, "wb") as tomli_file:
            tomli_w.dump(self.toml_dict, tomli_file)

class ProbeDriveConfig():
    
    def IPBoxsetter(self,arg):
        ''' Disables third motor ip address input for <3 axes drives'''
        index = arg.AxesBox.currentIndex()
        if index == None:
            pass
        if index ==0:
           
            arg.ipz.setEnabled(False)
            arg.ymotorLabel.setText("Y-motor")

            
        if index ==1:
            arg.ipz.setEnabled(True)
            arg.ymotorLabel.setText("Y-motor")

            
        if index ==2:
            arg.ipz.setEnabled(False)
            arg.ymotorLabel.setText("ϴ-motor")
            
    def getAttributes(self,arg):
        
        self.name = arg.templatename.text()
        self.id = self.name.replace(" ", "_").lower()
        self.axes = arg.AxesBox.currentText()
        self.IPx = arg.ipx.text()
        self.IPy = arg.ipy.text()
        self.IPz = arg.ipz.text()
        self.Countperstep = float(arg.countStep.text())
        self.Stepperrev = float(arg.stepRev.text())
        self.Threading = float(arg.customThreading.text())
        # self.date = today.strftime("%m/%d/%y")

        self.save(arg)
        
    
    def TPIsetter(self,arg):
        index = arg.TPIBox.currentIndex()
        if index == 0:
            arg.customThreading.setText("0.0508")
        if index == 1:
            arg.customThreading.setText("0.254")
        if index == 2:
            arg.customThreading.setText("0.508")
        if index == 3:
            arg.customThreading.setText("0.02")
            
    def pdBoxsetter(self,arg):
        ''' Preset probe drive configurations are saved here. This function 
        automatically fills out the configuration details as per the presets'''
        index = arg.probeDriveBox.currentIndex()
        if index == None:
            pass
        if index == 0:
            pass
        if index == 1:
            arg.templatename.setText("Standard X-Y")
            arg.AxesBox.setCurrentIndex(0)
            arg.ipx.setText("2")
            arg.ipy.setText("1")
            arg.ipz.setText("1")
            arg.countStep.setText("5")
            arg.stepRev.setText("1")
            arg.TPIBox.setCurrentIndex(1)  #in order to trigger threading label update
            arg.TPIBox.setCurrentIndex(0)
            pass
        if index == 2:
            arg.templatename.setText("Standard XYZ")
            arg.AxesBox.setCurrentIndex(1)
            arg.ipx.setText("2")
            arg.ipy.setText("1")
            arg.ipz.setText("1")
            arg.countStep.setText("5")
            arg.stepRev.setText("1")
            arg.TPIBox.setCurrentIndex(1)  #in order to trigger threading label update
            arg.TPIBox.setCurrentIndex(0)
            pass
        if index == 3:
            arg.templatename.setText("Standard X-ϴ")
            arg.AxesBox.setCurrentIndex(2)
            arg.ipx.setText("2")
            arg.ipy.setText("1")
            arg.ipz.setText("1")
            arg.countStep.setText("5")
            arg.stepRev.setText("1")
            arg.TPIBox.setCurrentIndex(1) #in order to trigger threading label update
            arg.TPIBox.setCurrentIndex(0)
            pass    
   
    def getStepCm(self,arg):
        try:
            StepPerRev = float(arg.stepRev.text())
            CmPerRev = float(arg.customThreading.text())
            StepPerCm = StepPerRev/CmPerRev
            arg.StepPerCmLabel.setText("Calculated Steps/cm :" + str(StepPerCm))
        except ValueError:
            pass
        
        
    def save(self,arg):
        Dict = {'id': self.id,'name': self.name , 'axes' : self.axes, 'IPx' : self.IPx, 'IPy': self.IPy,
                'IPz': self.IPz, 'count_per_step' : self.Countperstep, 'step_per_rev': self.Stepperrev, 'threading' : self.Threading                
                }
        
        tomli_string = tomli_w.dumps(Dict)  # Output to a string
        save_path = 'C:\\Users\\risha\\Desktop\\daq-mod-probedrives\\Probe Drives'
        output_file_name = str(self.name)
        completeName = os.path.join(save_path, output_file_name+".toml")
        if os.path.exists(completeName):
            qm = QtWidgets.QMessageBox
            ret = qm.warning(arg.centralwidget,'WARNING', "A Probe Drive configuration with the same name already exists. Are you sure you want to overwrite it?", qm.Yes | qm.No)
            if ret == qm.Yes:

                modifiedTime = os.path.getmtime(completeName) 

                timestamp = datetime.datetime.fromtimestamp(modifiedTime).strftime("%b-%d-%Y_%H.%M.%S")

                
                newName = save_path + '\\Backup\\' + output_file_name 

                os.rename(completeName, newName+"_"+timestamp + ".toml")
                
                with open(completeName, "wb") as tomli_file:
                    tomli_w.dump(Dict, tomli_file)
            else:
                pass
        
        else:
            qm = QtWidgets.QMessageBox
            ret = qm.question(arg.centralwidget,'', "Are you sure you want to save this configuration?", qm.Yes | qm.No)
            if ret == qm.Yes:
                with open(completeName, "wb") as tomli_file:
                    tomli.dump(Dict, tomli_file)
            else:
                pass

         
class ProbeConfig():
    

    
    def getAttributes(self,arg):
        self.name = arg.ProbeName.text()
        self.datefabricated = str(arg.dateedit.date().toPyDate())
        self.dateserviced = str(arg.dateedit2.date().toPyDate())
        self.type = arg.ProbeType.currentText()
        self.units = arg.UnitType.currentText()
        self.diameter = float(arg.Diameter.text())
        self.thickness = float(arg.Thickness.text())
        self.length = float(arg.Length.text())
        self.material = arg.Material.currentText()
        self.id = self.name.replace(" ", "_").lower()
        # self.date = today.strftime("%m/%d/%y")
        self.save(arg)


    def save(self,arg):
        Dict = {'id': self.id,'name': self.name , 'made' : self.datefabricated, 'serviced' : self.dateserviced, 'type': self.type,
                'units': self.units, 'diameter' : self.diameter, 'thickness': self.thickness, 'length' : self.length, 'material' : self.material                
                
                }
        tomli_string = tomli_w.dumps(Dict)  # Output to a string
        save_path = 'C:\\Users\\risha\\Desktop\\daq-mod-probedrives\\Probes'
        output_file_name = str(self.name)
        completeName = os.path.join(save_path, output_file_name+".toml")
        if os.path.exists(completeName):
            qm = QtWidgets.QMessageBox
            ret = qm.warning(arg.centralwidget,'WARNING', "A Probe configuration with the same name already exists. Are you sure you want to overwrite it?", qm.Yes | qm.No)
            if ret == qm.Yes:
                modifiedTime = os.path.getmtime(completeName) 

                timestamp = datetime.datetime.fromtimestamp(modifiedTime).strftime("%b-%d-%Y_%H.%M.%S")

                
                newName = save_path + '\\Backup\\' + output_file_name 
                os.rename(completeName, newName+"_"+timestamp + ".toml")
                with open(completeName, "wb") as tomli_file:
                    tomli_w.dump(Dict, tomli_file)
            else:
                pass
        
        else:
            qm = QtWidgets.QMessageBox
            ret = qm.question(arg.centralwidget,'', "Are you sure you want to save this configuration?", qm.Yes | qm.No)
            if ret == qm.Yes:
                with open(completeName, "wb") as tomli_file:
                    tomli_w.dump(Dict, tomli_file)
            else:
                pass

class MotionGroup():
    
    def getdrive(self,arg):
        
        filename , check = QFileDialog.getOpenFileName(None, "QFileDialog.getOpenFileName()",
                                               "C:\\Users\\risha\\Desktop\\daq-mod-probedrives\\Probe Drives", "toml files (*.toml)")       
        self.drivefile = filename

        if check:
            f = open(filename, 'r')
            
            with f:
                data = f.read()
                arg.DriveContents.setText(data)
                
    def getprobe(self,arg):
        
        filename , check = QFileDialog.getOpenFileName(None, "QFileDialog.getOpenFileName()",
                                               "C:\\Users\\risha\\Desktop\\daq-mod-probedrives\\Probes", "toml files (*.toml)")       
        self.probefile = filename
        if check:
            f = open(filename, 'r')
            
            with f:
                data = f.read()
                arg.ProbeContents.setText(data)
    
    
    def getAttributes(self,arg):
        try:
            self.name = arg.GroupName.text()
            self.d1 = float(arg.Dist1.text())
            self.d2 = float(arg.Dist2.text())
            self.portnumber = arg.PortNumber.text()
            self.portloc = arg.PortLocation.text()
            self.id = self.name.replace(" ", "_").lower()
            # self.date = today.strftime("%m/%d/%y")
            self.save(arg)

        except ValueError:
            QMessageBox.about(
                    None, "Error", "Missing Information.")
   
    def save(self,arg):
        Dict = {'group.id': self.id,'name': self.name, 'pivot_valve_distance': self.d1, 'valve_centre_distance': self.d2 ,
                'port_number': self.portnumber, 'port_location': self.portloc                
                }
        tomli_string = tomli_w.dumps(Dict)  # Output to a string

        save_path = 'C:\\Users\\risha\\Desktop\\daq-mod-probedrives\\Groups'
        output_file_name = str(self.name)
        completeName = os.path.join(save_path, output_file_name+".toml")
       
        if os.path.exists(completeName):
            qm = QtWidgets.QMessageBox
            ret = qm.warning(arg.centralwidget,'WARNING', "A Motion Group with the same name already exists. Are you sure you want to overwrite it?", qm.Yes | qm.No)
            if ret == qm.Yes:
                modifiedTime = os.path.getmtime(completeName) 

                timestamp = datetime.datetime.fromtimestamp(modifiedTime).strftime("%b-%d-%Y_%H.%M.%S")

                
                newName = save_path + '\\Backup\\' + output_file_name 

                os.rename(completeName, newName+"_"+timestamp + ".toml")
                
                with open(completeName, "wb") as tomli_file:
                    tomli_w.dump(Dict, tomli_file)
            else:
                pass
        
        else:
            qm = QtWidgets.QMessageBox
            ret = qm.question(arg.centralwidget,'', "Are you sure you want to save this configuration?", qm.Yes | qm.No)
            if ret == qm.Yes:
                with open(completeName, "wb") as tomli_file:
                    tomli_w.dump(Dict, tomli_file)
            else:
                pass
            
    def moveon(self,arg):
        
        Dict = {'group.id': self.id,'name': self.name, 'pivot_valve_distance': self.d1, 'valve_centre_distance': self.d2 ,
                'port_number': self.portnumber, 'port_location': self.portloc                
                }
        
        def Merge(dict1, dict2,dict3):
            # res = {**dict1, **dict2, **dict3}
            res = dict1
            res['probe']= dict2
            res['drive'] = dict3
            return res
        try:
            
            with open(self.probefile, "rb") as f:
                Dict2 = tomli.load(f)
            with open(self.drivefile, "rb") as f:
                Dict3 = tomli.load(f)

            Dict = Merge(Dict,Dict2,Dict3)
        except AttributeError:
            QMessageBox.about(
                    None, "Error", "Please Choose associated configurations.")
       
        if Dict['port_number'] == '0':
            self.hand = 0
        elif Dict['port_number'] == '1':
            self.hand = 1

        arg.canvas.set_hand(self.hand)
        arg.canvas.set_name(self.name)
        tomli_string = tomli_w.dumps(Dict)  # Output to a string

        save_path = 'C:\\Users\\risha\\Desktop\\daq-mod-probedrives\\Groups'
        output_file_name = str(self.name)
        completeName = os.path.join(save_path, output_file_name+".toml")
        qm = QtWidgets.QMessageBox
        ret = qm.question(arg.centralwidget,'', "Are you sure you want to proceed?", qm.Yes | qm.No)
        
        
        if ret == qm.Yes:
            with open(completeName, "wb") as tomli_file:
                    tomli_w.dump(Dict, tomli_file)
            arg.tabWidget.setCurrentIndex(3)
            arg.tabWidget.setTabEnabled(0,False)
            arg.tabWidget.setTabEnabled(1,False)
            arg.tabWidget.setTabEnabled(2,False)
            arg.tabWidget.setTabEnabled(3,True)
       
        else:
            pass
        

class MainWindow(QMainWindow, Ui_MainWindow):

    def __init__(self, *args, **kwargs):
        '''connect UI to functions'''
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.mode = 'rect'
        self.checkBoxlabel = None
        self.ecc = None
        self.eccentricity = 0.5
        self.closeit = False
        self.probedrive = ProbeDriveConfig()
        self.probe = ProbeConfig()
        self.group = MotionGroup()
        self.canvas = Canvas()
        self.canvas.initialize()
        self.canvas.setFixedHeight(600)
        self.canvas.setFixedWidth(600)
        # We need to enable mouse tracking to follow the mouse without the button pressed.
        self.canvas.setMouseTracking(True)
        # # Enable focus to capture key inputs.
        # self.canvas.setFocusPolicy(Qt.StrongFocus)
        self.horizontalLayout.addWidget(self.canvas)
        
        self.canvas2 = MplCanvas()
        self.toolbar = NavigationToolbar(self.canvas2, self)
        self.canvasLayout = QtWidgets.QVBoxLayout(self.widget)
        self.canvasLayout.addWidget(self.canvas2)
        self.canvasLayout.addWidget(self.toolbar)

        self.horizontalLayout.addLayout(self.canvasLayout)
        # self.horizontalLayout.addWidget(self.canvas2)


################PROBE CONFIG BUTTON CONNECTIONS
      
        #Connect preset Probe Config box:
        # self.probeBox.currentIndexChanged.connect(lambda: self.probeBoxsetter())
       
        self.SaveProbeButton.clicked.connect(lambda: self.probe.getAttributes(self))


################PROBE DRIVE BUTTON CONNECTIONS
        # Connect IPBox:
        self.AxesBox.currentIndexChanged.connect(lambda: self.probedrive.IPBoxsetter(self))
        
        #Connect TPI box to TPI input
        self.TPIBox.currentIndexChanged.connect(lambda: self.probedrive.TPIsetter(self))

        #Connect preset Probe drive box:
        self.probeDriveBox.currentIndexChanged.connect(lambda: self.probedrive.pdBoxsetter(self))
       #Connect to step/cm calculation:
        self.customThreading.editingFinished.connect(lambda: self.probedrive.getStepCm(self))
        self.stepRev.editingFinished.connect(lambda: self.probedrive.getStepCm(self))
        #Connect save button:
        self.SaveDriveButton.clicked.connect(lambda: self.probedrive.getAttributes(self))
 ##########################  MotionGroup button connections

        self.MgroupBox.currentIndexChanged.connect(lambda: self.MGroupBoxsetter())
        self.SaveGroupButton.clicked.connect(lambda: self.group.getAttributes(self))
        self.DriveChoose.clicked.connect(lambda: self.group.getdrive(self))
        self.ProbeChoose.clicked.connect(lambda: self.group.getprobe(self))
        self.ConfirmButton.clicked.connect(lambda: [self.group.getAttributes(self), self.group.moveon(self)])
 ##########################  MotionList button connections
 
        # Connect mode Box
        self.modeBox.currentIndexChanged.connect(lambda: [self.get_index(), self.canvas.set_mode(self.mode),  self.btnstate2(self.generateBox, n = 1)])

        # Setup Grid Box
        self.gridBox.currentIndexChanged.connect(lambda: [self.get_index2(), self.canvas.set_grid(self.grid)])
        #Other buttons
        self.printButton.clicked.connect(lambda: [self.canvas.set_status(self),self.canvas.print_positions(self), self.update_graph(
            self.canvas.poslist, self.canvas.nx, self.canvas.ny, self.canvas.barlist, self.canvas.mode)])
        self.clearButton.clicked.connect(lambda: [self.canvas.reset(), self.canvas.resetpos(self), self.update_graph(
            self.canvas.poslist, self.canvas.nx, self.canvas.ny, self.canvas.barlist, self.canvas.mode)])
        self.saveButton.clicked.connect(lambda: self.canvas.save_file())
        self.verifyButton.clicked.connect(lambda: self.canvas.checklist(self))
        self.EntButton.clicked.connect(lambda: [self.canvas.reset(), self.canvas.resetpos(self), self.canvas.coordEnter(
            self), self.update_graph(self.canvas.poslist, self.canvas.nx, self.canvas.ny, self.canvas.barlist, self.canvas.mode)])


        # Initialize animation timer.
        self.timer = QTimer()
        self.timer.timeout.connect(self.canvas.on_timer)
        self.timer.setInterval(100)
        self.timer.start()

        self.xres.editingFinished.connect(lambda: self.canvas.set_status(self))
        self.yres.editingFinished.connect(lambda: self.canvas.set_status(self))
        self.zres.editingFinished.connect(lambda: self.canvas.set_status(self))
        self.gridCentre.editingFinished.connect(lambda: self.canvas.set_status(self))
        self.z1.editingFinished.connect(lambda: self.canvas.set_status(self))
        self.z2.editingFinished.connect(lambda: self.canvas.set_status(self))
        self.canvas.move.connect(lambda: self.updateCoord(
            self.canvas.cx, self.canvas.cy, self.canvas.poslist, self.canvas.bar))
        self.generateBox.stateChanged.connect(lambda: self.btnstate2(self.generateBox))
        self.ea.editingFinished.connect(lambda: [self.canvas.reset(), self.canvas.resetpos(self), self.canvas.enter(self,self.mode), self.update_graph(self.canvas.poslist, self.canvas.nx, self.canvas.ny, self.canvas.barlist, self.canvas.mode)])
        self.eb.editingFinished.connect(lambda: [self.canvas.reset(), self.canvas.resetpos(self), self.canvas.enter(self,self.mode), self.update_graph(self.canvas.poslist, self.canvas.nx, self.canvas.ny, self.canvas.barlist, self.canvas.mode)])
        self.ec.editingFinished.connect(lambda: [self.canvas.reset(), self.canvas.resetpos(self), self.canvas.enter(self,self.mode), self.update_graph(self.canvas.poslist, self.canvas.nx, self.canvas.ny, self.canvas.barlist, self.canvas.mode)])


        self.sl.valueChanged.connect(lambda: self.canvas.set_spacing(self))
        self.PlasmaColumn.stateChanged.connect(lambda: [self.canvas.set_status(self), self.update_canvas(self.canvas.poslist)])
        self.MainCathode.stateChanged.connect(lambda: [self.canvas.set_status(self),  self.update_canvas(self.canvas.poslist)])
        self.SecondaryCathode.stateChanged.connect(lambda: [self.canvas.set_status(self), self.update_canvas(self.canvas.poslist)])

        sizeicon = QLabel()
        sizeicon.setPixmap(
            QPixmap(os.path.join('images', 'border-weight.png')))

        self.show()

    def update_graph(self, poslist, nx, ny, barlist, mode):
        ''' ROutine to update Matplotlib graph displaying actual data points defined so far, 
        as well as barriers and no-go zones'''
        self.canvasLayout.removeWidget(self.canvas2)
        self.canvas2.deleteLater()
        self.canvas2 = None
        self.canvas2 = MplCanvas()
        self.canvas2.ax.set_xlim3d(-100, 100)
        self.canvas2.ax.set_ylim3d(-100, 100)
        self.canvas2.ax.set_zlim3d(-5, 5)

        xs = [x[0]/5 for x in poslist]
        ys = [x[1]/5 for x in poslist]
        zs = [x[2]/5 for x in poslist]
        if mode == 'circle':
            size = nx/10
        else:
            size = min([nx/5, ny/5])

        self.canvas2.ax.scatter(xs, ys, zs, s=size)

        for posgroup in barlist:
            # posgroup is [(xorg,y,z),(xe),(xvo),(xve)]

            self.canvas2.ax.plot([posgroup[0][0], posgroup[1][0]],
                                 [posgroup[0][1], posgroup[1][1]], color='#800000'
                                 )
            self.canvas2.ax.plot([posgroup[0][0], posgroup[2][0]],
                                 [posgroup[0][1], posgroup[2][1]], color='red'
                                 )
            self.canvas2.ax.plot([posgroup[1][0], posgroup[3][0]],
                                 [posgroup[1][1], posgroup[3][1]], color='red'
                                 )
        
        
        self.canvasLayout.addWidget(self.canvas2)
        self.update_canvas(poslist)
    
    def update_canvas(self, poslist):
        ''' Updates points onto the 2D projection. Redraws defined shapes, draws points ontop. 
        Size of the points is determined by resolution values. 
        '''
        
        self.canvas.reset()

        xs = [x for x in self.canvas.xpos[0:self.canvas.bar]]
        ys = [x for x in self.canvas.ypos[0:self.canvas.bar]]

        for i in range(0, len(xs)-1, 2):
                p = QPainter(self.canvas.pixmap())
                p.setPen(QPen(
                    QColor(Qt.red), self.canvas.config['size'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                p.setBrush(QBrush(QColor(Qt.red)))
                xe = xs[i+1]
                xorg = xs[i]
                ye = ys[i+1]
                yorg = ys[i]
                if self.canvas.hand == 1:
                    C = (yorg)/(xorg + 250)
                    xvo = (-(500*C*C) + np.sqrt((C*C*500)**2 -
                       4*(C*C*C*C-1)*(250**2)))/(2*(C*C+1))
                    yvo = C*(xvo+250)

                    C = ye/(xe + 250)
                    xve = (-(C*C*500) + np.sqrt((C*C*500)**2 -
                       4*(C*C*C*C-1)*(250**2)))/(2*(C*C+1))
                    yve = C*(xve+250)

                elif self.canvas.hand == 0:
                    C = (yorg)/(xorg - 250)
                    xvo = ((C*C*500) - np.sqrt((C*C*500)**2 -
                       4*(C*C*C*C-1)*(250**2)))/(2*(C*C+1))
                    yvo = C*(xvo-250)

                    C = (ye)/(xe - 250)
                    xve = ((C*C*500) - np.sqrt((C*C*500)**2 -
                       4*(C*C*C*C-1)*(250**2)))/(2*(C*C+1))
                    yve = C*(xve-250)
                else:
                    raise ValueError("AAAAAAAA")
                
                p.drawLine(QPointF(xorg+300, -yorg+300),
                       QPointF(xvo+300, -yvo+300))
                p.drawLine(QPointF(xe+300, -ye+300),
                       QPointF(xve+300, -yve+300))

                p.setPen(QPen(QColor(
                '#800000'), self.canvas.config['size'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                p.drawLine(QPointF(xorg+300, -yorg+300),
                       QPointF(xe+300, -ye+300))
                p.end()
                
           
        xs = self.canvas.xpos
        ys = self.canvas.ypos
        p = QPainter(self.canvas.pixmap())
        p.setPen(QPen(QColor(Qt.blue), self.canvas.config['size'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(QBrush(QColor(Qt.blue)))
        p.setOpacity(0.5)
            
            
        
        if self.mode == 'rect':
            
                for i in range(self.canvas.bar, len(xs)-1, 2):
  
                    p.drawRect(
                        QRectF(xs[i]+300, -ys[i]+300, xs[i+1]-xs[i], -ys[i+1]+ys[i]))
                p.end()

        if self.mode == 'line':

                for i in range(self.canvas.bar, len(xs)-1, 2):
                    p.drawLine(QPointF(xs[i]+300, -ys[i]+300),
                                QPointF(300+xs[i+1], -ys[i+1]+300))
                p.end()

        if self.mode == 'polyline':
                xs = np.delete(self.canvas.xpos, -1)
                ys = np.delete(self.canvas.ypos, -1)
                if self.closeit == True:
                            index = -1
                else :
                            index = 0
                bar = int(self.canvas.bar/2)
                xs = xs[1::2]
                ys = ys[1::2]
                xs = xs[bar:]
                ys = ys[bar:]
                
                
                if self.closeit == True:
                    index = -1
                elif self.closeit == False:
                    index = 0

                for i in range(index, len(xs)-1):
                    p.drawLine(QPointF(xs[i]+300, -ys[i]+300),
                                QPointF(xs[i+1]+300, -ys[i+1]+300))
                p.end()

        if self.mode == 'circle':
                for i in range(self.canvas.bar, len(xs)-1,2):

                    r = np.sqrt((xs[i]- xs[i+1])**2 + (ys[i]-ys[i+1])**2)

                    p.drawEllipse(QPointF(xs[i]+300, -ys[i]+300), r, r)
                p.end()

        if self.mode == 'ellipse':
                for i in range(self.canvas.bar, len(xs)-1):

                    p.drawEllipse(
                            QRect(QPoint(xs[i]+300, -ys[i]+300), QPoint(xs[i+1]+300, -ys[i+1]+300)))
                p.end()

        if (len(poslist) != 0):
            
            p = QPainter(self.canvas.pixmap())
            xss = [300+x[0] for x in poslist]
            yss = [300-x[1] for x in poslist]
            p.setPen(QPen(QColor(Qt.black),
                      self.canvas.config['size'], Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin))
            p.setBrush(QBrush(QColor(Qt.black)))

            # for i in range(0,len(xss)):
            #     p.drawPoint(QPointF(xss[i],yss[i]))
            # p.end()
        
            if self.mode == 'circle':
                s = self.canvas.nx/10
            else:
                s = min([self.canvas.nx/5, self.canvas.ny/5])
                
            for i in range(0,len(xss)):
                p.drawEllipse(QPointF(xss[i],yss[i]), s,s)
            p.end()
             
    def updateCoord(self, x, y, poslist, bar):
        '''Display current cursor coordinates in LAPD, cm units'''
        self.cursorLabel.setText("Cursor Coordinates:\n"+
            '( %d , %d )' % ((x-300)/5, (-y+300)/5))
        self.pointnumberLabel.setText('Number of points defined: '+ str(len(poslist)))
        self.timeLabel.setText('Estimated Time Required: '+ str( datetime.timedelta(seconds = 12*len(poslist) )))


        
    def probeBoxSetter(self):
        ''' Preset probe configurations are saved here. This function 
        automatically fills out the configuration details as per the presets'''
        index = self.probeBox.getCurrentIndex()
        if index == None:
            pass
        if index ==  0:
            pass
        
        pass
        
    
    def get_index(self):
        '''UI dynamism. Changes resolution text etc as per shape mode selected'''
        index = self.modeBox.currentIndex()
        if index == None:
            pass
        if index == 5:
            self.mode = 'barrier'
            if self.checkBoxlabel:
                self.vl.removeWidget(self.checkBoxlabel)
                self.vl.removeWidget(self.checkBox)
                self.checkBox.deleteLater()
                self.checkBox = None
                self.checkBoxlabel.deleteLater()
                self.checkBoxlabel = None

        elif index == 0:
            self.mode = 'rect'
            self.la.setText("Length- X")
            self.lb.setText("Length- Y")
            self.lc.setText("Length- Z")
            if self.checkBoxlabel:
                self.vl.removeWidget(self.checkBoxlabel)
                self.vl.removeWidget(self.checkBox)
                self.checkBox.deleteLater()
                self.checkBox = None
                self.checkBoxlabel.deleteLater()
                self.checkBoxlabel = None
 

        elif index == 1:
            self.mode = 'circle'
            self.la.setText("Radius (cm)")
            self.lb.setText("")
            self.lc.setText("Length- Z")
            if self.checkBoxlabel:
                self.vl.removeWidget(self.checkBoxlabel)
                self.vl.removeWidget(self.checkBox)
                self.checkBox.deleteLater()
                self.checkBox = None
                self.checkBoxlabel.deleteLater()
                self.checkBoxlabel = None

        elif index == 2:
            self.mode = 'line'
            if self.checkBoxlabel:
                self.vl.removeWidget(self.checkBoxlabel)
                self.vl.removeWidget(self.checkBox)
                self.checkBox.deleteLater()
                self.checkBox = None
                self.checkBoxlabel.deleteLater()
                self.checkBoxlabel = None

        elif index == 3:
            self.mode = 'polyline'
            self.checkBoxlabel = QtWidgets.QLabel(self.groupBox)
            self.checkBoxlabel.setMaximumWidth(150)
            self.vl.addWidget(self.checkBoxlabel)
            self.checkBoxlabel.setText( "Auto-close polygon?")
            self.checkBox = QtWidgets.QCheckBox(self.groupBox)
            self.checkBox.setObjectName("checkBox")
            self.checkBox.setMaximumWidth(150)
            self.vl.addWidget(self.checkBox)
            self.checkBox.stateChanged.connect(lambda: self.btnstate(self.checkBox))
    
        elif index == 4: 
            self.mode = 'ellipse'
            self.lc.setText("Length- Z")
            self.la.setText("Horizontal Axis")
            self.lb.setText("Vertical Axis")

            if self.checkBoxlabel:
                self.vl.removeWidget(self.checkBoxlabel)
                self.vl.removeWidget(self.checkBox)
                self.checkBox.deleteLater()
                self.checkBox = None
                self.checkBoxlabel.deleteLater()
                self.checkBoxlabel = None

    def get_index2(self):
        '''UI dynamism. Changes resolution text etc as per grid mode selected'''

        index = self.gridBox.currentIndex()
        
        if index == None:
            pass
        if index ==0:
            self.grid = 'rect'
            self.xreslabel.setText( "dx (cm)")
            self.yreslabel.setText( "dy (cm)")
            self.zreslabel.setText("dz (cm)")
            if self.ecc:
                self.gridV.removeWidget(self.ecc)
                self.ecc.deleteLater()
                self.ecc = None
        elif index == 1:
            self.grid = 'circle'
            self.xreslabel.setText( "dr (cm) ")
            self.yreslabel.setText( "dθ (deg)")
            self.zreslabel.setText("dz (cm) ")
            if self.ecc:
                self.gridV.removeWidget(self.ecc)
                self.ecc.deleteLater()
                self.ecc = None
        elif index ==3 :
            self.grid = 'ellipse'
            self.xreslabel.setText( "dr (cm)")
            self.yreslabel.setText( "dθ (deg)")
            self.zreslabel.setText("dz (cm)")
            self.ecc = QtWidgets.QLineEdit(self.groupBox)
            self.ecc.setMaximumWidth(150)
            self.ecc.setObjectName("ecc")
            self.ecc.setText("Enter eccentricity of ellipse")
            self.gridV.addWidget(self.ecc)
            self.ecc.editingFinished.connect(lambda: self.getecc() )
            
            
        elif index ==2 :
            self.grid = 'sphere'
            self.xreslabel.setText( "dr (cm)")
            self.yreslabel.setText( "dθ (deg)")
            self.zreslabel.setText("dφ (deg)")
            if self.ecc:
                self.gridV.removeWidget(self.ecc)
                self.ecc.deleteLater()
                self.ecc = None
    
    def getecc(self): 
        '''Gets user input for ellipse eccentricity'''
        try:
            self.eccentricity = float(self.ecc.text())
            self.canvas.set_status(self)
        except ValueError:
            QMessageBox.about(
            self, "Error", "Eccentricity should be valid numbers.")
  
    def btnstate(self,b):
        ''' Updates polygon auto-close setting'''
        if b.isChecked() == True:
            self.closeit = True
        else:
            self.closeit = False
        self.canvas.set_status(self)
        
    def btnstate2(self,b,n = 0):
        '''UI Dynamism. Controls switching between drawn vs autogenerated data regions'''
        if b.isChecked() == True:
            self.gridBox.setEnabled(False)
            self.la.setEnabled(False)
            self.lb.setEnabled(False)
            self.lc.setEnabled(False)
            self.ea.setEnabled(True)
            self.eb.setEnabled(True)
            self.ec.setEnabled(True)
            self.z1.setEnabled(False)       
            self.z2.setEnabled(False) 
            
            if self.mode == 'rect':
                self.gridBox.setCurrentIndex(0)
                self.canvas.set_grid('rect')
                self.canvas.mode = 'rect'
                
                self.ea.setText("No. of points: X")
                self.eb.setText("No. of points: Y")
                self.ec.setText("No. of points: Z")

                self.gridCentre.editingFinished.connect(lambda: [self.canvas.set_status(self),self.canvas.reset(), self.canvas.resetpos(self), self.canvas.enter(self,self.mode), self.update_graph(self.canvas.poslist, self.canvas.nx, self.canvas.ny, self.canvas.barlist, self.canvas.mode)] )
                self.xres.editingFinished.connect(lambda: [self.canvas.set_status(self),self.canvas.reset(), self.canvas.resetpos(self), self.canvas.enter(self,self.mode), self.update_graph(self.canvas.poslist, self.canvas.nx, self.canvas.ny, self.canvas.barlist, self.canvas.mode)] )
                self.yres.editingFinished.connect(lambda: [self.canvas.set_status(self),self.canvas.reset(), self.canvas.resetpos(self), self.canvas.enter(self,self.mode), self.update_graph(self.canvas.poslist, self.canvas.nx, self.canvas.ny, self.canvas.barlist, self.canvas.mode)] )
                self.zres.editingFinished.connect(lambda: [self.canvas.set_status(self),self.canvas.reset(), self.canvas.resetpos(self), self.canvas.enter(self,self.mode), self.update_graph(self.canvas.poslist, self.canvas.nx, self.canvas.ny, self.canvas.barlist, self.canvas.mode )] )


                
            elif self.mode == 'circle':
                
                self.gridBox.setCurrentIndex(1)
                self.canvas.set_grid('circle')
                self.canvas.mode = 'circle'

                self.ea.setText("No. of points: ")
                self.eb.setText("No. of points: Y")
                self.ec.setText("No. of points: Z")
                self.eb.setEnabled(False)
                self.lb.setEnabled(False)

                self.gridCentre.editingFinished.connect(lambda: [self.canvas.set_status(self),self.canvas.reset(), self.canvas.resetpos(self), self.canvas.enter(self,self.mode), self.update_graph(self.canvas.poslist, self.canvas.nx, self.canvas.ny, self.canvas.barlist, self.canvas.mode)] )
                self.xres.editingFinished.connect(lambda: [self.canvas.set_status(self),self.canvas.reset(), self.canvas.resetpos(self), self.canvas.enter(self,self.mode), self.update_graph(self.canvas.poslist, self.canvas.nx, self.canvas.ny, self.canvas.barlist, self.canvas.mode)] )
                self.yres.editingFinished.connect(lambda: [self.canvas.set_status(self),self.canvas.reset(), self.canvas.resetpos(self), self.canvas.enter(self,self.mode), self.update_graph(self.canvas.poslist, self.canvas.nx, self.canvas.ny, self.canvas.barlist, self.canvas.mode)] )
                self.zres.editingFinished.connect(lambda: [self.canvas.set_status(self),self.canvas.reset(), self.canvas.resetpos(self), self.canvas.enter(self,self.mode), self.update_graph(self.canvas.poslist, self.canvas.nx, self.canvas.ny, self.canvas.barlist, self.canvas.mode)] )


            elif self.mode == 'ellipse':
                self.gridBox.setCurrentIndex(3)
                self.canvas.set_grid('ellipse')
                self.canvas.mode = 'ellipse'

                self.ea.setText("No. of points: ")
                self.eb.setText("No. of points: Y")
                self.ec.setText("No. of points: Z")
                self.eb.setEnabled(False)


                self.ecc.editingFinished.connect(lambda:  [self.canvas.reset(), self.canvas.resetpos(self), self.canvas.enter(self,self.mode), self.update_graph(self.canvas.poslist, self.canvas.nx, self.canvas.ny, self.canvas.barlist, self.canvas.mode)])
                self.gridCentre.editingFinished.connect(lambda: [self.canvas.set_status(self),self.canvas.reset(), self.canvas.resetpos(self), self.canvas.enter(self,self.mode), self.update_graph(self.canvas.poslist, self.canvas.nx, self.canvas.ny, self.canvas.barlist, self.canvas.mode)] )
                self.xres.editingFinished.connect(lambda: [self.canvas.set_status(self),self.canvas.reset(), self.canvas.resetpos(self), self.canvas.enter(self,self.mode), self.update_graph(self.canvas.poslist, self.canvas.nx, self.canvas.ny, self.canvas.barlist, self.canvas.mode)] )
                self.yres.editingFinished.connect(lambda: [self.canvas.set_status(self),self.canvas.reset(), self.canvas.resetpos(self), self.canvas.enter(self,self.mode), self.update_graph(self.canvas.poslist, self.canvas.nx, self.canvas.ny, self.canvas.barlist, self.canvas.mode)] )
                self.zres.editingFinished.connect(lambda: [self.canvas.set_status(self),self.canvas.reset(), self.canvas.resetpos(self), self.canvas.enter(self,self.mode), self.update_graph(self.canvas.poslist, self.canvas.nx, self.canvas.ny, self.canvas.barlist, self.canvas.mode)] )
            else:
                    
                    self.ea.setEnabled(False)
                    self.eb.setEnabled(False)
                    self.ec.setEnabled(False)
                    self.la.setEnabled(True)
                    self.lb.setEnabled(True)
                    self.lc.setEnabled(True)


        
        else:
            self.gridBox.setEnabled(True)
            self.la.setEnabled(True)
            self.lb.setEnabled(True)
            self.lc.setEnabled(True)
            self.ea.setEnabled(False)
            self.eb.setEnabled(False)
            self.ec.setEnabled(False)
            self.z1.setEnabled(True)       
            self.z2.setEnabled(True)       



    def MGroupBoxsetter(self):
        ''' Preset motion group configurations are saved here. This function 
        automatically fills out the configuration details as per the presets'''
        index = self.MgroupBox.currentIndex()
        if index == None:
            pass
        if index == 0:
            self.GroupName.setText("Name1")
            self.Dist1.setText("1")
            self.Dist2.setText("2")
            self.PortNumber.setText("1")
            self.PortLocation.setText("1")
            

        
        
#################################################################################


if __name__ == '__main__':

    app = QApplication([])
    app.setQuitOnLastWindowClosed(True)
    window = MainWindow()
    app.exec_()
