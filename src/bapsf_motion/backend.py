# -*- coding: utf-8 -*-
"""
Created on Sat Apr 23 18:03:45 2022

@author: risha
"""

import numpy as np
import subprocess

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import *
from typing import ClassVar, Dict, List

from bapsf_motion.configurator.toml_loader import Loader
from bapsf_motion.gui import GroupLayout, TabPage, Ui_MainWindow


class MyMplCanvas(FigureCanvas):
    """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""

    def __init__(self, parent=None, width=10, height=8, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = fig.add_subplot(111, projection="3d")
        self.ax.grid()
        self.s = 1

        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

        self.ax.grid()
        # self.ax.add_patch(
        #     patches.Rectangle((-38, -50), 76, 100, fill=False, edgecolor='red')
        # )

        self.matrix = self.ax.scatter(0, 0, 0, color="blue", marker="o")
        self.point = self.ax.scatter(0, 0, 0, color="red", marker="*")
        self.initialize_visited_points()

        # self.ax.set_xticks(np.arange(-60,60,1))
        uss = np.linspace(0, 2 * np.pi, 32)
        zss = np.linspace(-100, 100, 2)

        uss, zss = np.meshgrid(uss, zss)

        xss = 50 * np.cos(uss)
        yss = 50 * np.sin(uss)
        self.ax.plot_surface(xss, yss, zss, alpha=0.5, color="grey")

    def update_graph(self, poslist, nx, ny, nz, barlist, mode):
        """
        Routine to update Matplotlib graph displaying actual data
        points defined so far, as well as barriers and no-go zones.
        """
        self.ax.clear()

        self.ax.grid()
        self.initialize_visited_points()

        self.matrix = self.ax.scatter(0, 0, 0, color="blue", marker="o")
        self.point = self.ax.scatter(0, 0, 0, color="red", marker="*")

        # self.ax.set_xticks(np.arange(-60,60,1))
        uss = np.linspace(0, 2 * np.pi, 32)
        zss = np.linspace(-100, 100, 2)

        uss, zss = np.meshgrid(uss, zss)

        xss = 50 * np.cos(uss)
        yss = 50 * np.sin(uss)
        self.ax.plot_surface(xss, yss, zss, alpha=0.5, color="grey")

        xs = [x[0] for x in poslist]
        ys = [x[1] for x in poslist]
        zs = [x[2] for x in poslist]
        if mode == "circle":
            size = nx / 5
        else:
            size = min([nx / 2, ny / 2])
        self.ax.scatter(xs, ys, zs, s=size)

    def update_probe(self, xnow, ynow):
        self.point = self.ax.scatter(xnow, ynow, 0, color="red", marker="*", s=self.s)
        self.draw()

    def update_axis(self, x1, y1, x2, y2):
        self.ax.set_xlim(x2, x1)
        self.ax.set_ylim(y2, y1)

    def finished_positions(self, x, y):
        self.finished_x.append(x)
        self.finished_y.append(y)
        self.visited_points = self.ax.scatter(
            self.finished_x, self.finished_y, 0, color="green", marker="o", s=self.s
        )
        self.draw()

    def initialize_visited_points(self):
        self.finished_x = []
        self.finished_y = []
        self.visited_points = self.ax.scatter(
            self.finished_x, self.finished_y, 0, color="green", marker="o"
        )


class MainWindow(QMainWindow, Ui_MainWindow):
    _filenames = None  # type: List[str]
    _tabs = None  # type: Dict[int, ClassVar[TabPage]]
    _groups = None  # type: Dict[int, ClassVar[GroupLayout]]

    def __init__(self, *args, **kwargs):
        """connect UI to functions"""
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.i = 1
        self.button.clicked.connect(lambda: [self.addNewTab()])
        self.next.clicked.connect(lambda: self.move_all(self.i, 0))
        self.previous.clicked.connect(lambda: self.move_all(self.i, 1))

        self.addNewTab()
        self.show()

    @property
    def filenames(self):
        if self._filenames is None:
            self._filenames = []

        return self._filenames

    @filenames.setter
    def filenames(self, value):
        if not isinstance(value, list):
            raise TypeError(
                f"Expected a list for 'filenames', got type {type(value)}."
            )
        if not all(isinstance(item, str) for item in value):
            raise ValueError("All elements of the 'filenames' list must be strings.")

        self._filenames = value

    @property
    def tabs(self):
        if self._tabs is None:
            self._tabs = {}

        return self._tabs

    @property
    def groups(self):
        if self._groups is None:
            self._groups = {}

        return self._groups

    def addNewTab(self):

        name = f"Group {self.tabWidget.count()}"
        index = self.tabWidget.count()
        self.tabs[index] = TabPage(self.tabWidget)
        self.tabWidget.addTab(self.tabs[index], name)
        self.groups[index] = GroupLayout(self.scrollAreaWidgetContents)

        self.verticalLayout_6.addWidget(self.groups[index])
        self.tabs[index].Loader = Loader()
        self.connect_buttons(index)
        self.i += 1
        self.tabs[index].xv = None
        self.tabs[index].yv = None
        self.tabs[index].zv = None
        self.tabs[index].x = None
        self.tabs[index].y = None
        self.tabs[index].z = None

        for i in range(1, index):
            self.tabs[i].remove.setEnabled(False)

    def remove_tab(self, index):

        qm = QtWidgets.QMessageBox
        ret = qm.warning(
            self.centralwidget,
            "WARNING",
            "Are you sure you want to delete this group?",
            qm.Yes | qm.No,
        )

        if ret == qm.Yes:
            self.tabWidget.widget(index).deleteLater()
            self.tabWidget.removeTab(index)
            self.tabs[index] = None
            self.tabs[index - 1].remove.setEnabled(True)
            self.groups[index].deleteLater()
            self.verticalLayout_6.removeWidget(self.groups[index])
            self.groups[index] = None
        else:
            pass

    def connect_buttons(self, index):

        self.tabs[index].load.clicked.connect(
            lambda: self.tabs[index].Loader.getgroup(self.tabs[index], self, index)
        )
        self.groups[index].Groupedit.clicked.connect(lambda: self.EditConfig(index))
        self.tabs[index].edit.clicked.connect(lambda: self.EditConfig(index))

        self.tabs[index].canvas = MyMplCanvas()
        self.tabs[index].canvas.setMaximumSize(QtCore.QSize(400, 400))
        self.tabs[index].canvas.setObjectName("Canvas")
        self.tabs[index].mainHorizontalLayout.addWidget(self.tabs[index].canvas)

        self.tabs[index].create.clicked.connect(lambda: self.create_config())
        self.tabs[index].xcoord.editingFinished.connect(lambda: self.getVals(index))
        self.tabs[index].ycoord.editingFinished.connect(lambda: self.getVals(index))
        self.tabs[index].zcoord.editingFinished.connect(lambda: self.getVals(index))
        self.tabs[index].xspeed.editingFinished.connect(lambda: self.getVals(index))
        self.tabs[index].yspeed.editingFinished.connect(lambda: self.getVals(index))
        self.tabs[index].zspeed.editingFinished.connect(lambda: self.getVals(index))
        self.groups[index].x.editingFinished.connect(lambda: self.getVals(index))
        self.groups[index].y.editingFinished.connect(lambda: self.getVals(index))
        self.groups[index].z.editingFinished.connect(lambda: self.getVals(index))
        self.groups[index].list.currentIndexChanged.connect(
            lambda: self.list_mover(index)
        )

        self.tabs[index].remove.clicked.connect(lambda: self.remove_tab(index))

    def update_timer(self):
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.heartbeat)
        self.timer.start(500)

    def create_config(self):
        subprocess.call(" python configurator\\config_gui_backend.py 1", shell=True)

    def getVals(self, index):
        try:
            if self.tabs[index].xcoord.text() != "":
                self.tabs[index].x = float(self.tabs[index].xcoord.text())
            if self.tabs[index].ycoord.text() != "":
                self.tabs[index].y = float(self.tabs[index].ycoord.text())
            if self.tabs[index].zcoord.text() != "":
                self.tabs[index].z = float(self.tabs[index].zcoord.text())
            if self.tabs[index].xspeed.text() != "":
                self.tabs[index].xv = float(self.tabs[index].xpeed.text())
            if self.tabs[index].yspeed.text() != "":
                self.tabs[index].yv = float(self.tabs[index].ypeed.text())
            if self.tabs[index].zspeed.text() != "":
                self.tabs[index].zv = float(self.tabs[index].zpeed.text())
            if self.groups[index].x.text() != ("" or "X"):
                self.tabs[index].x = float(self.groups[index].x.text())
                self.tabs[index].xcoord.setText(self.groups[index].x.text())
            if self.groups[index].y.text() != ("" or "Y"):
                self.tabs[index].y = float(self.groups[index].y.text())
                self.tabs[index].ycoord.setText(self.groups[index].y.text())
            if self.groups[index].z.text() != ("" or "Z"):
                self.tabs[index].z = float(self.groups[index].z.text())
                self.tabs[index].zcoord.setText(self.groups[index].z.text())
        except ValueError:
            QMessageBox.about(self, "Error", "Position should be valid numbers.")

    def EditConfig(self, index):

        self.tabWidget.setCurrentIndex(index)
        filename = self.tabs[index].Loader.drivefile
        subprocess.call(filename, shell=True)
        self.tabs[index].Loader.getgroup(self.tabs[index], self, index, filename)

    def save(self):
        filenames = []
        for tab in self.tabs.values():
            filenames.append(tab.Loader.drivefile)

        self.filenames = filenames

        return filenames

    def ConnectMotor(self, index):
        self.tabs[index].move.clicked.connect(
            lambda: self.tabs[index].Loader.mm.move_to_position(
                self.tabs[index].x, self.tabs[index].y, self.tabs[index].z
            )
        )
        self.tabs[index].STOP.clicked.connect(
            lambda: self.tabs[index].Loader.mm.stop_now()
        )
        self.tabs[index].zero.clicked.connect(lambda: self.tabs[index].Loader.mm.zero())
        self.tabs[index].set_speed.clicked.connect(
            lambda: self.tabs[index].Loader.mm.set_velocity(
                self.tabs[index].xv, self.tabs[index].yv, self.tabs[index].zv
            )
        )

        self.groups[index].move.clicked.connect(
            lambda: self.tabs[index].Loader.mm.move_to_position(
                self.tabs[index].x, self.tabs[index].y, self.tabs[index].z
            )
        )

        # Set timer to update current probe position and instant motor velocity
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(lambda: [self.heartbeat(index)])
        self.timer.start(500)

    def heartbeat(self, index):

        for i in range(1, index + 1):
            (
                codex,
                codey,
                codez,
                posx,
                posy,
                posz,
                velx,
                vely,
                velz,
                is_movingx,
                is_movingy,
                is_movingz,
            ) = self.tabs[i].Loader.mm.heartbeat()
            self.update_current_position(i, posx, posy, posz)
            self.update_current_speed(i, velx, vely, velz)
            self.update_alarm_code(i, codex, codey, codez)

    def update_alarm_code(self, index, codex, codey, codez):
        status1, status2, status3 = codex, codey, codez
        if status1 is None:
            status1 = "None"
        if status2 is None:
            status2 = "None"
        if status3 is None:
            status3 = "None"
        self.tabs[index].statuslabel.setText(
            f"Motor X:{status1}, Motor Y:{status2}, Motor Z:{status3}"
        )

    def update_current_speed(self, i, velx, vely, velz):
        if velx is None:
            velx = "None"
        if vely is None:
            vely = "None"
        if velz is None:
            velz = "None"
        self.tabs[i].speedx, self.tabs[i].speedy, self.tabs[i].speedz = velx, vely, velz
        self.tabs[i].VelocityLabel.setText(
            f"Current Motor Speed: ( {self.tabs[i].speedx}  , {self.tabs[i].speedy} )"
        )

    def update_current_position(self, i, posx, posy, posz):
        if posx is None:
            posx = "None"
        if posy is None:
            poys = "None"
        if posz is None:
            posz = "None"
        self.tabs[i].xnow, self.tabs[i].ynow, self.tabs[i].znow = posx, posy, posz
        self.tabs[i].canvas.point.remove()
        self.tabs[i].canvas.update_probe(self.tabs[i].xnow, self.tabs[i].ynow)
        self.tabs[i].PositionLabel.setText(
            f"Current Probe Position: ( {np.round(self.tabs[i].xnow, 2)} ,  "
            f"{np.round(self.tabs[i].ynow, 2)}, {np.round(self.tabs[i].znow, 2)} )"
        )

    def list_mover(self, index):
        coord = self.groups[index].list.currentText()

        coord = np.array(
            coord.replace("[", "").replace("]", "").split(","), dtype=float
        ).reshape(-1, 3)
        x = str(coord[0][0])
        y = str(coord[0][1])
        z = str(coord[0][2])
        self.groups[index].x.setText(x)
        self.groups[index].y.setText(y)
        self.groups[index].z.setText(z)
        self.getVals(index)

    def move_all(self, index, p):
        if p in (0, 1):
            for i in range(1, index):
                y = self.groups[i].list.currentIndex() + 1 - 2 * p
                self.groups[i].list.setCurrentIndex(y)
                self.movelabel.setText(f"Move all to index: {y}")

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self,
            "Window Close",
            "Are you sure you want to close the window?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            event.accept()
            return self.filenames
        else:
            event.ignore()


if __name__ == "__main__":

    app = QApplication([])
    app.setQuitOnLastWindowClosed(True)
    window = MainWindow()
    app.exec_()
