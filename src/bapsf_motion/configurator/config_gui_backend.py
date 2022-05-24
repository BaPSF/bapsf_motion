import datetime
import numpy as np
import os

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from PyQt5 import QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from motion_list_configurator_backend import Canvas

from main_window import Ui_MainWindow
from group_configurator_backend import ProbeConfig, ProbeDriveConfig, MotionGroup


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):

        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.ax = self.fig.add_subplot(111, projection="3d")
        self.ax.grid()
        self.ax.mouse_init()

        # self.ax.set_xticks(np.arange(-60,60,1))
        uss = np.linspace(0, 2 * np.pi, 32)
        zss = np.linspace(-3, 3, 2)

        uss, zss = np.meshgrid(uss, zss)

        xss = 50 * np.cos(uss)
        yss = 50 * np.sin(uss)
        self.ax.plot_surface(xss, yss, zss, alpha=0.5, color="grey")
        super(MplCanvas, self).__init__(self.fig)


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        """connect UI to functions"""
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.mode = "rect"
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

        # Connect preset Probe Config box:
        # self.probeBox.currentIndexChanged.connect(lambda: self.probeBoxsetter())

        self.SaveProbeButton.clicked.connect(lambda: self.probe.getAttributes(self))

        ################PROBE DRIVE BUTTON CONNECTIONS
        # Connect IPBox:
        self.AxesBox.currentIndexChanged.connect(
            lambda: self.probedrive.IPBoxsetter(self)
        )

        # Connect TPI box to TPI input
        self.TPIBox.currentIndexChanged.connect(
            lambda: [self.probedrive.TPIsetter(self), self.probedrive.getStepCm(self)]
        )

        # Connect preset Probe drive box:
        self.probeDriveBox.currentIndexChanged.connect(
            lambda: [self.probedrive.pdBoxsetter(self)]
        )
        # Connect to step/cm calculation:
        self.customThreading.editingFinished.connect(
            lambda: self.probedrive.getStepCm(self)
        )
        self.stepRev.editingFinished.connect(lambda: self.probedrive.getStepCm(self))
        # Connect save button:
        self.SaveDriveButton.clicked.connect(
            lambda: self.probedrive.getAttributes(self)
        )
        ##########################  MotionGroup button connections

        self.MgroupBox.currentIndexChanged.connect(lambda: self.MGroupBoxsetter())
        self.SaveGroupButton.clicked.connect(lambda: self.group.getAttributes(self))
        self.DriveChoose.clicked.connect(lambda: self.group.getdrive(self))
        self.ProbeChoose.clicked.connect(lambda: self.group.getprobe(self))
        self.ConfirmButton.clicked.connect(
            lambda: [self.group.getAttributes(self), self.group.moveon(self)]
        )
        ##########################  MotionList button connections

        # Connect mode Box
        self.modeBox.currentIndexChanged.connect(
            lambda: [
                self.get_index(),
                self.canvas.set_mode(self.mode),
                self.btnstate2(self.generateBox, n=1),
            ]
        )

        # Setup Grid Box
        self.gridBox.currentIndexChanged.connect(
            lambda: [self.get_index2(), self.canvas.set_grid(self.grid)]
        )
        # Other buttons
        self.printButton.clicked.connect(
            lambda: [
                self.canvas.set_status(self),
                self.canvas.print_positions(self),
                self.update_graph(
                    self.canvas.poslist,
                    self.canvas.nx,
                    self.canvas.ny,
                    self.canvas.barlist,
                    self.canvas.mode,
                ),
            ]
        )
        self.clearButton.clicked.connect(
            lambda: [
                self.canvas.reset(),
                self.canvas.resetpos(self),
                self.update_graph(
                    self.canvas.poslist,
                    self.canvas.nx,
                    self.canvas.ny,
                    self.canvas.barlist,
                    self.canvas.mode,
                ),
            ]
        )
        self.saveButton.clicked.connect(lambda: self.canvas.save_file())
        self.verifyButton.clicked.connect(lambda: self.canvas.checklist(self))
        self.EntButton.clicked.connect(
            lambda: [
                self.canvas.reset(),
                self.canvas.resetpos(self),
                self.canvas.coordEnter(self),
                self.update_graph(
                    self.canvas.poslist,
                    self.canvas.nx,
                    self.canvas.ny,
                    self.canvas.barlist,
                    self.canvas.mode,
                ),
            ]
        )

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
        self.canvas.move.connect(
            lambda: self.updateCoord(
                self.canvas.cx, self.canvas.cy, self.canvas.poslist, self.canvas.bar
            )
        )
        self.generateBox.stateChanged.connect(lambda: self.btnstate2(self.generateBox))
        self.ea.editingFinished.connect(
            lambda: [
                self.canvas.reset(),
                self.canvas.resetpos(self),
                self.canvas.enter(self, self.mode),
                self.update_graph(
                    self.canvas.poslist,
                    self.canvas.nx,
                    self.canvas.ny,
                    self.canvas.barlist,
                    self.canvas.mode,
                ),
            ]
        )
        self.eb.editingFinished.connect(
            lambda: [
                self.canvas.reset(),
                self.canvas.resetpos(self),
                self.canvas.enter(self, self.mode),
                self.update_graph(
                    self.canvas.poslist,
                    self.canvas.nx,
                    self.canvas.ny,
                    self.canvas.barlist,
                    self.canvas.mode,
                ),
            ]
        )
        self.ec.editingFinished.connect(
            lambda: [
                self.canvas.reset(),
                self.canvas.resetpos(self),
                self.canvas.enter(self, self.mode),
                self.update_graph(
                    self.canvas.poslist,
                    self.canvas.nx,
                    self.canvas.ny,
                    self.canvas.barlist,
                    self.canvas.mode,
                ),
            ]
        )

        self.sl.valueChanged.connect(lambda: self.canvas.set_spacing(self))
        self.PlasmaColumn.stateChanged.connect(
            lambda: [
                self.canvas.set_status(self),
                self.update_canvas(self.canvas.poslist),
            ]
        )
        self.MainCathode.stateChanged.connect(
            lambda: [
                self.canvas.set_status(self),
                self.update_canvas(self.canvas.poslist),
            ]
        )
        self.SecondaryCathode.stateChanged.connect(
            lambda: [
                self.canvas.set_status(self),
                self.update_canvas(self.canvas.poslist),
            ]
        )

        sizeicon = QLabel()
        sizeicon.setPixmap(QPixmap(os.path.join("images", "border-weight.png")))

        self.show()

    def update_graph(self, poslist, nx, ny, barlist, mode):
        """
        Routine to update Matplotlib graph displaying actual data
        points defined so far, as well as barriers and no-go zones.
        """
        self.canvasLayout.removeWidget(self.canvas2)
        self.canvas2.deleteLater()
        self.canvas2 = None
        self.canvas2 = MplCanvas()
        self.canvas2.ax.set_xlim3d(-100, 100)
        self.canvas2.ax.set_ylim3d(-100, 100)
        self.canvas2.ax.set_zlim3d(-5, 5)

        xs = [x[0] / 5 for x in poslist]
        ys = [x[1] / 5 for x in poslist]
        zs = [x[2] / 5 for x in poslist]
        if mode == "circle":
            size = nx / 10
        else:
            size = min([nx / 5, ny / 5])
        self.canvas2.ax.scatter(xs, ys, zs, s=size)

        for posgroup in barlist:
            # posgroup is [(xorg,y,z),(xe),(xvo),(xve)]

            self.canvas2.ax.plot(
                [posgroup[0][0], posgroup[1][0]],
                [posgroup[0][1], posgroup[1][1]],
                color="#800000",
            )
            self.canvas2.ax.plot(
                [posgroup[0][0], posgroup[2][0]],
                [posgroup[0][1], posgroup[2][1]],
                color="red",
            )
            self.canvas2.ax.plot(
                [posgroup[1][0], posgroup[3][0]],
                [posgroup[1][1], posgroup[3][1]],
                color="red",
            )
        self.canvasLayout.addWidget(self.canvas2)
        self.update_canvas(poslist)

    def update_canvas(self, poslist):
        """
        Updates points onto the 2D projection. Redraws defined shapes,
        draws points on top.  Size of the points is determined by
        resolution values.
        """

        self.canvas.reset()

        xs = [x for x in self.canvas.xpos[0 : self.canvas.bar]]
        ys = [x for x in self.canvas.ypos[0 : self.canvas.bar]]

        for i in range(0, len(xs) - 1, 2):
            p = QPainter(self.canvas.pixmap())
            p.setPen(
                QPen(
                    QColor(Qt.red),
                    self.canvas.config["size"],
                    Qt.SolidLine,
                    Qt.RoundCap,
                    Qt.RoundJoin,
                )
            )
            p.setBrush(QBrush(QColor(Qt.red)))
            xe = xs[i + 1]
            xorg = xs[i]
            ye = ys[i + 1]
            yorg = ys[i]
            if self.canvas.hand == 1:
                C = (yorg) / (xorg + 250)
                xvo = (
                    -(500 * C * C)
                    + np.sqrt((C * C * 500) ** 2 - 4 * (C * C * C * C - 1) * (250**2))
                ) / (2 * (C * C + 1))
                yvo = C * (xvo + 250)

                C = ye / (xe + 250)
                xve = (
                    -(C * C * 500)
                    + np.sqrt((C * C * 500) ** 2 - 4 * (C * C * C * C - 1) * (250**2))
                ) / (2 * (C * C + 1))
                yve = C * (xve + 250)
            elif self.canvas.hand == 0:
                C = (yorg) / (xorg - 250)
                xvo = (
                    (C * C * 500)
                    - np.sqrt((C * C * 500) ** 2 - 4 * (C * C * C * C - 1) * (250**2))
                ) / (2 * (C * C + 1))
                yvo = C * (xvo - 250)

                C = (ye) / (xe - 250)
                xve = (
                    (C * C * 500)
                    - np.sqrt((C * C * 500) ** 2 - 4 * (C * C * C * C - 1) * (250**2))
                ) / (2 * (C * C + 1))
                yve = C * (xve - 250)
            else:
                raise ValueError("AAAAAAAA")
            p.drawLine(QPointF(xorg + 300, -yorg + 300), QPointF(xvo + 300, -yvo + 300))
            p.drawLine(QPointF(xe + 300, -ye + 300), QPointF(xve + 300, -yve + 300))

            p.setPen(
                QPen(
                    QColor("#800000"),
                    self.canvas.config["size"],
                    Qt.SolidLine,
                    Qt.RoundCap,
                    Qt.RoundJoin,
                )
            )
            p.drawLine(QPointF(xorg + 300, -yorg + 300), QPointF(xe + 300, -ye + 300))
            p.end()
        xs = self.canvas.xpos
        ys = self.canvas.ypos
        p = QPainter(self.canvas.pixmap())
        p.setPen(
            QPen(
                QColor(Qt.blue),
                self.canvas.config["size"],
                Qt.SolidLine,
                Qt.RoundCap,
                Qt.RoundJoin,
            )
        )
        p.setBrush(QBrush(QColor(Qt.blue)))
        p.setOpacity(0.5)

        if self.mode == "rect":
            for i in range(self.canvas.bar, len(xs) - 1, 2):

                p.drawRect(
                    QRectF(
                        xs[i] + 300, -ys[i] + 300, xs[i + 1] - xs[i], -ys[i + 1] + ys[i]
                    )
                )
            p.end()

        elif self.mode == "line":
            for i in range(self.canvas.bar, len(xs) - 1, 2):
                p.drawLine(
                    QPointF(xs[i] + 300, -ys[i] + 300),
                    QPointF(300 + xs[i + 1], -ys[i + 1] + 300),
                )
            p.end()

        elif self.mode == "polyline":
            xs = np.delete(self.canvas.xpos, -1)
            ys = np.delete(self.canvas.ypos, -1)
            if self.closeit is True:
                index = -1
            else:
                index = 0
            bar = int(self.canvas.bar / 2)
            xs = xs[1::2]
            ys = ys[1::2]
            xs = xs[bar:]
            ys = ys[bar:]

            if self.closeit is True:
                index = -1
            elif self.closeit is False:
                index = 0
            for i in range(index, len(xs) - 1):
                p.drawLine(
                    QPointF(xs[i] + 300, -ys[i] + 300),
                    QPointF(xs[i + 1] + 300, -ys[i + 1] + 300),
                )
            p.end()

        elif self.mode == "circle":
            for i in range(self.canvas.bar, len(xs) - 1, 2):

                r = np.sqrt((xs[i] - xs[i + 1]) ** 2 + (ys[i] - ys[i + 1]) ** 2)

                p.drawEllipse(QPointF(xs[i] + 300, -ys[i] + 300), r, r)
            p.end()

        elif self.mode == "ellipse":
            for i in range(self.canvas.bar, len(xs) - 1):

                p.drawEllipse(
                    QRect(
                        QPoint(xs[i] + 300, -ys[i] + 300),
                        QPoint(xs[i + 1] + 300, -ys[i + 1] + 300),
                    )
                )
            p.end()

        if len(poslist) != 0:
            p = QPainter(self.canvas.pixmap())
            xss = [300 + x[0] for x in poslist]
            yss = [300 - x[1] for x in poslist]
            p.setPen(
                QPen(
                    QColor(Qt.black),
                    self.canvas.config["size"],
                    Qt.SolidLine,
                    Qt.SquareCap,
                    Qt.MiterJoin,
                )
            )
            p.setBrush(QBrush(QColor(Qt.black)))

            # for i in range(0,len(xss)):
            #     p.drawPoint(QPointF(xss[i],yss[i]))
            # p.end()

            if self.mode == "circle":
                s = self.canvas.nx / 10
            else:
                s = min([self.canvas.nx / 5, self.canvas.ny / 5])
            for i in range(0, len(xss)):
                p.drawEllipse(QPointF(xss[i], yss[i]), s, s)
            p.end()

    def updateCoord(self, x, y, poslist, bar):
        """Display current cursor coordinates in LAPD, cm units."""
        self.cursorLabel.setText(
            "Cursor Coordinates:\n" + "( %d , %d )" % ((x - 300) / 5, (-y + 300) / 5)
        )
        self.pointnumberLabel.setText(f"Number of points defined: {len(poslist)}")
        self.timeLabel.setText(
            "Estimated Time Required: "
            + str(datetime.timedelta(seconds=12 * len(poslist)))
        )

    def probeBoxSetter(self):
        """
        Preset probe configurations are saved here. This function
        automatically fills out the configuration details as per the
        presets.
        """
        index = self.probeBox.getCurrentIndex()
        if index is None:
            pass
        if index == 0:
            pass
        pass

    def get_index(self):
        """
        UI dynamism. Changes resolution text etc. as per shape mode
        selected.
        """
        index = self.modeBox.currentIndex()
        if index is None:
            pass
        if index == 5:
            self.mode = "barrier"
            if self.checkBoxlabel:
                self.vl.removeWidget(self.checkBoxlabel)
                self.vl.removeWidget(self.checkBox)
                self.checkBox.deleteLater()
                self.checkBox = None
                self.checkBoxlabel.deleteLater()
                self.checkBoxlabel = None
        elif index == 0:
            self.mode = "rect"
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
            self.mode = "circle"
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
            self.mode = "line"
            if self.checkBoxlabel:
                self.vl.removeWidget(self.checkBoxlabel)
                self.vl.removeWidget(self.checkBox)
                self.checkBox.deleteLater()
                self.checkBox = None
                self.checkBoxlabel.deleteLater()
                self.checkBoxlabel = None
        elif index == 3:
            self.mode = "polyline"
            self.checkBoxlabel = QtWidgets.QLabel(self.groupBox)
            self.checkBoxlabel.setMaximumWidth(150)
            self.vl.addWidget(self.checkBoxlabel)
            self.checkBoxlabel.setText("Auto-close polygon?")
            self.checkBox = QtWidgets.QCheckBox(self.groupBox)
            self.checkBox.setObjectName("checkBox")
            self.checkBox.setMaximumWidth(150)
            self.vl.addWidget(self.checkBox)
            self.checkBox.stateChanged.connect(lambda: self.btnstate(self.checkBox))
        elif index == 4:
            self.mode = "ellipse"
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
        """
        UI dynamism. Changes resolution text etc. as per grid mode
        selected.
        """

        index = self.gridBox.currentIndex()

        if index is None:
            pass
        if index == 0:
            self.grid = "rect"
            self.xreslabel.setText("dx (cm)")
            self.yreslabel.setText("dy (cm)")
            self.zreslabel.setText("dz (cm)")
            if self.ecc:
                self.gridV.removeWidget(self.ecc)
                self.ecc.deleteLater()
                self.ecc = None
        elif index == 1:
            self.grid = "circle"
            self.xreslabel.setText("dr (cm) ")
            self.yreslabel.setText("dθ (deg)")
            self.zreslabel.setText("dz (cm) ")
            if self.ecc:
                self.gridV.removeWidget(self.ecc)
                self.ecc.deleteLater()
                self.ecc = None
        elif index == 3:
            self.grid = "ellipse"
            self.xreslabel.setText("dr (cm)")
            self.yreslabel.setText("dθ (deg)")
            self.zreslabel.setText("dz (cm)")
            self.ecc = QtWidgets.QLineEdit(self.groupBox)
            self.ecc.setMaximumWidth(150)
            self.ecc.setObjectName("ecc")
            self.ecc.setText("Enter eccentricity of ellipse")
            self.gridV.addWidget(self.ecc)
            self.ecc.editingFinished.connect(lambda: self.getecc())
        elif index == 2:
            self.grid = "sphere"
            self.xreslabel.setText("dr (cm)")
            self.yreslabel.setText("dθ (deg)")
            self.zreslabel.setText("dφ (deg)")
            if self.ecc:
                self.gridV.removeWidget(self.ecc)
                self.ecc.deleteLater()
                self.ecc = None

    def getecc(self):
        """Gets user input for ellipse eccentricity"""
        try:
            self.eccentricity = float(self.ecc.text())
            self.canvas.set_status(self)
        except ValueError:
            QMessageBox.about(self, "Error", "Eccentricity should be valid numbers.")

    def btnstate(self, b):
        """Updates polygon auto-close setting"""
        if b.isChecked() is True:
            self.closeit = True
        else:
            self.closeit = False
        self.canvas.set_status(self)

    def btnstate2(self, b, n=0):
        """
        UI Dynamism. Controls switching between drawn vs autogenerated
        data regions.
        """
        if b.isChecked() is True:
            self.gridBox.setEnabled(False)
            self.la.setEnabled(False)
            self.lb.setEnabled(False)
            self.lc.setEnabled(False)
            self.ea.setEnabled(True)
            self.eb.setEnabled(True)
            self.ec.setEnabled(True)
            self.z1.setEnabled(False)
            self.z2.setEnabled(False)

            if self.mode == "rect":
                self.gridBox.setCurrentIndex(0)
                self.canvas.set_grid("rect")
                self.canvas.mode = "rect"

                self.ea.setText("No. of points: X")
                self.eb.setText("No. of points: Y")
                self.ec.setText("No. of points: Z")

                self.gridCentre.editingFinished.connect(
                    lambda: [
                        self.canvas.set_status(self),
                        self.canvas.reset(),
                        self.canvas.resetpos(self),
                        self.canvas.enter(self, self.mode),
                        self.update_graph(
                            self.canvas.poslist,
                            self.canvas.nx,
                            self.canvas.ny,
                            self.canvas.barlist,
                            self.canvas.mode,
                        ),
                    ]
                )
                self.xres.editingFinished.connect(
                    lambda: [
                        self.canvas.set_status(self),
                        self.canvas.reset(),
                        self.canvas.resetpos(self),
                        self.canvas.enter(self, self.mode),
                        self.update_graph(
                            self.canvas.poslist,
                            self.canvas.nx,
                            self.canvas.ny,
                            self.canvas.barlist,
                            self.canvas.mode,
                        ),
                    ]
                )
                self.yres.editingFinished.connect(
                    lambda: [
                        self.canvas.set_status(self),
                        self.canvas.reset(),
                        self.canvas.resetpos(self),
                        self.canvas.enter(self, self.mode),
                        self.update_graph(
                            self.canvas.poslist,
                            self.canvas.nx,
                            self.canvas.ny,
                            self.canvas.barlist,
                            self.canvas.mode,
                        ),
                    ]
                )
                self.zres.editingFinished.connect(
                    lambda: [
                        self.canvas.set_status(self),
                        self.canvas.reset(),
                        self.canvas.resetpos(self),
                        self.canvas.enter(self, self.mode),
                        self.update_graph(
                            self.canvas.poslist,
                            self.canvas.nx,
                            self.canvas.ny,
                            self.canvas.barlist,
                            self.canvas.mode,
                        ),
                    ]
                )
            elif self.mode == "circle":

                self.gridBox.setCurrentIndex(1)
                self.canvas.set_grid("circle")
                self.canvas.mode = "circle"

                self.ea.setText("No. of points: ")
                self.eb.setText("No. of points: Y")
                self.ec.setText("No. of points: Z")
                self.eb.setEnabled(False)
                self.lb.setEnabled(False)

                self.gridCentre.editingFinished.connect(
                    lambda: [
                        self.canvas.set_status(self),
                        self.canvas.reset(),
                        self.canvas.resetpos(self),
                        self.canvas.enter(self, self.mode),
                        self.update_graph(
                            self.canvas.poslist,
                            self.canvas.nx,
                            self.canvas.ny,
                            self.canvas.barlist,
                            self.canvas.mode,
                        ),
                    ]
                )
                self.xres.editingFinished.connect(
                    lambda: [
                        self.canvas.set_status(self),
                        self.canvas.reset(),
                        self.canvas.resetpos(self),
                        self.canvas.enter(self, self.mode),
                        self.update_graph(
                            self.canvas.poslist,
                            self.canvas.nx,
                            self.canvas.ny,
                            self.canvas.barlist,
                            self.canvas.mode,
                        ),
                    ]
                )
                self.yres.editingFinished.connect(
                    lambda: [
                        self.canvas.set_status(self),
                        self.canvas.reset(),
                        self.canvas.resetpos(self),
                        self.canvas.enter(self, self.mode),
                        self.update_graph(
                            self.canvas.poslist,
                            self.canvas.nx,
                            self.canvas.ny,
                            self.canvas.barlist,
                            self.canvas.mode,
                        ),
                    ]
                )
                self.zres.editingFinished.connect(
                    lambda: [
                        self.canvas.set_status(self),
                        self.canvas.reset(),
                        self.canvas.resetpos(self),
                        self.canvas.enter(self, self.mode),
                        self.update_graph(
                            self.canvas.poslist,
                            self.canvas.nx,
                            self.canvas.ny,
                            self.canvas.barlist,
                            self.canvas.mode,
                        ),
                    ]
                )
            elif self.mode == "ellipse":
                self.gridBox.setCurrentIndex(3)
                self.canvas.set_grid("ellipse")
                self.canvas.mode = "ellipse"

                self.ea.setText("No. of points: ")
                self.eb.setText("No. of points: Y")
                self.ec.setText("No. of points: Z")
                self.eb.setEnabled(False)

                self.ecc.editingFinished.connect(
                    lambda: [
                        self.canvas.reset(),
                        self.canvas.resetpos(self),
                        self.canvas.enter(self, self.mode),
                        self.update_graph(
                            self.canvas.poslist,
                            self.canvas.nx,
                            self.canvas.ny,
                            self.canvas.barlist,
                            self.canvas.mode,
                        ),
                    ]
                )
                self.gridCentre.editingFinished.connect(
                    lambda: [
                        self.canvas.set_status(self),
                        self.canvas.reset(),
                        self.canvas.resetpos(self),
                        self.canvas.enter(self, self.mode),
                        self.update_graph(
                            self.canvas.poslist,
                            self.canvas.nx,
                            self.canvas.ny,
                            self.canvas.barlist,
                            self.canvas.mode,
                        ),
                    ]
                )
                self.xres.editingFinished.connect(
                    lambda: [
                        self.canvas.set_status(self),
                        self.canvas.reset(),
                        self.canvas.resetpos(self),
                        self.canvas.enter(self, self.mode),
                        self.update_graph(
                            self.canvas.poslist,
                            self.canvas.nx,
                            self.canvas.ny,
                            self.canvas.barlist,
                            self.canvas.mode,
                        ),
                    ]
                )
                self.yres.editingFinished.connect(
                    lambda: [
                        self.canvas.set_status(self),
                        self.canvas.reset(),
                        self.canvas.resetpos(self),
                        self.canvas.enter(self, self.mode),
                        self.update_graph(
                            self.canvas.poslist,
                            self.canvas.nx,
                            self.canvas.ny,
                            self.canvas.barlist,
                            self.canvas.mode,
                        ),
                    ]
                )
                self.zres.editingFinished.connect(
                    lambda: [
                        self.canvas.set_status(self),
                        self.canvas.reset(),
                        self.canvas.resetpos(self),
                        self.canvas.enter(self, self.mode),
                        self.update_graph(
                            self.canvas.poslist,
                            self.canvas.nx,
                            self.canvas.ny,
                            self.canvas.barlist,
                            self.canvas.mode,
                        ),
                    ]
                )
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
        """
        Preset motion group configurations are saved here. This function
        automatically fills out the configuration details as per the
        presets.
        """
        index = self.MgroupBox.currentIndex()
        if index is None:
            pass
        if index == 0:
            self.GroupName.setText("Name1")
            self.Dist1.setText("1")
            self.Dist2.setText("2")
            self.PortNumber.setText("1")
            self.PortLocation.setText("1")


#################################################################################


if __name__ == "__main__":

    app = QApplication([])
    app.setQuitOnLastWindowClosed(True)
    window = MainWindow()
    app.exec_()
