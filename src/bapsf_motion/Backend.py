# -*- coding: utf-8 -*-
"""
Created on Sat Apr 23 18:03:45 2022

@author: risha
"""


from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from Controllers.Drive import Motor_Control_ND
import os
from datetime import date
import numpy as np
import math
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from mpl_toolkits.mplot3d import Axes3D
import tomli
from matplotlib.figure import Figure
# from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from GUI.MainWindow import Ui_MainWindow
import datetime
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar


class MyMplCanvas(FigureCanvas):
    """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""

    def __init__(self, parent=None, width=6, height=3, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = fig.add_subplot(111,projection='3d')
        self.ax.grid()
        self.s = 1
 

        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self,
                                   QSizePolicy.Expanding,
                                   QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

        self.ax.grid()
        #self.ax.add_patch(patches.Rectangle((-38, -50), 76, 100, fill = False, edgecolor = 'red'))

        self.matrix = self.ax.scatter(0, 0, 0, color = 'blue', marker = 'o')
        self.point = self.ax.scatter(0, 0, 0, color = 'red', marker = '*')
        self.initialize_visited_points()


        # self.ax.set_xticks(np.arange(-60,60,1))
        uss = np.linspace(0, 2 * np.pi, 32)
        zss = np.linspace(-100, 100, 2)

        uss, zss = np.meshgrid(uss, zss)

        xss = 50 * np.cos(uss)
        yss = 50 * np.sin(uss)
        self.ax.plot_surface(xss,yss,zss,alpha = 0.5, color = 'grey')

    def update_figure(self,x,y,z):
        with open('res.txt') as f:
            p = [float(l) for l in next(f).split()]

        s = min(p[0],p[1],p[2])
        self.s = s
        self.matrix = self.ax.scatter(x, y,z, color = 'blue', marker = 'o',s = self.s)
        self.draw()

    def update_probe(self, xnow, ynow):
        self.point = self.ax.scatter(xnow, ynow, 0, color = 'red', marker = '*', s = self.s)
        self.draw()

    def update_axis(self, x1, y1, x2, y2):
        self.ax.set_xlim(x2, x1)
        self.ax.set_ylim(y2, y1)

    def finished_positions(self, x, y):
        self.finished_x.append(x)
        self.finished_y.append(y)
        self.visited_points = self.ax.scatter(self.finished_x, self.finished_y,0, color = 'green', marker = 'o', s = self.s)
        self.draw()

    def initialize_visited_points(self):
        self.finished_x = []
        self.finished_y = []
        self.visited_points = self.ax.scatter(self.finished_x, self.finished_y,0, color = 'green', marker = 'o')

class Motor_Movement():

    def __init__(self, x_ip_addr = None, y_ip_addr = None, MOTOR_PORT = None):
        super().__init__()

        self.x_ip_addr = x_ip_addr
        self.y_ip_addr = y_ip_addr
        self.MOTOR_PORT = MOTOR_PORT
        self.mc = Motor_Control_ND(x_ip_addr = self.x_ip_addr, y_ip_addr = self.y_ip_addr)

    def move_to_position(self,x,y):
        # Directly move the motor to their absolute position
        self.mc.move_to_position(x, y)

    def stop_now(self):
        # Stop motor movement now
        self.mc.stop_now()


    def zero(self):
        zeroreply=QMessageBox.question(self, "Set Zero",
            "You are about to set the current probe position to (0,0). Are you sure?",
            QMessageBox.Yes, QMessageBox.No)
        if zeroreply == QMessageBox.Yes:
            QMessageBox.about(self, "Set Zero", "Probe position is now (0,0).")
            self.mc.set_zero()


    def ask_velocity(self):
        return self.mc.ask_velocity()


    def set_velocity(self,xv,yv):
        self.mc.set_velocity(xv, yv)


    def current_probe_position(self):
        return self.mc.current_probe_position()

    def update_current_speed(self):
        self.speedx, self.speedy = self.ask_velocity()
        self.velocityInput.setText("(" + str(self.speedx) + " ," + str(self.speedy) +")")

    # def set_input_usage(self, usage):
    #     self.mc.set_input_usage(usage)
    
    
class Loader():
      
    def getgroup(self,arg):
        
        filename , check = QFileDialog.getOpenFileName(None, "QFileDialog.getOpenFileName()",
                                               "C:\\Users\\risha\\Desktop\\daq-mod-probedrives\\Groups", "toml files (*.toml)")       
        self.drivefile = filename

        if check:
            f = open(filename, 'r')
            
            with f:
                data = f.read()
                arg.GroupText.setText(data)
            f = open(filename, 'rb')
            with f:
                self.toml_dict = tomli.load(f)
                self.x_ip = self.toml_dict['drive']['IPx']
                self.y_ip = self.toml_dict['drive']['IPy']
                self.z_ip = self.toml_dict['drive']['IPz']

        self.ConnectMotor(arg)
        
    def ConnectMotor(self,arg):
        self.port_ip = int(7776)
        self.mm = Motor_Movement(x_ip_addr = self.x_ip, y_ip_addr = self.y_ip, MOTOR_PORT = self.port_ip)
        arg.ConnectMotor()
    
class MainWindow(QMainWindow, Ui_MainWindow):

    def __init__(self, *args, **kwargs):
        '''connect UI to functions'''
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.canvas = MyMplCanvas()
        self.canvas.setMaximumSize(QtCore.QSize(300, 300))
        self.canvas.setObjectName("Canvas")
        # self.canvas.initialize()
        # self.canvas = QtWidgets.QTextEdit(self.horizontalLayoutWidget_6)
        self.horizontalLayout_7.removeWidget(self.Canvas)
        self.Canvas.deleteLater()
        self.Canvas = None    
        self.horizontalLayout_7.addWidget(self.canvas)
        self.Loader = Loader()
        self.load.clicked.connect(lambda: self.Loader.getgroup(self))
        self.xcoord.editingFinished.connect(lambda: self.getVals())
        self.ycoord.editingFinished.connect(lambda: self.getVals())
        self.zcoord.editingFinished.connect(lambda: self.getVals())
        self.xspeed.editingFinished.connect(lambda: self.getVals())
        self.yspeed.editingFinished.connect(lambda: self.getVals())
        self.zspeed.editingFinished.connect(lambda: self.getVals())

        self.show()


        data_running = False

    def update_timer(self):
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_current_position)
        self.timer.start(500)
        


    def getVals(self):
        try:
            if self.xcoord.text() != '':
                self.x = float(self.xcoord.text())
            if self.ycoord.text() != '':
                self.y = float(self.ycoord.text())
            if self.zcoord.text() != '':
                self.z = float(self.zcoord.text())
            if self.xspeed.text() != '':
                self.xv = float(self.xpeed.text())
            if self.yspeed.text() != '':
                self.yv = float(self.ypeed.text())
            if self.zspeed.text() != '':
                self.zv = float(self.zpeed.text())
        except ValueError:
            QMessageBox.about(self, "Error", "Position should be valid numbers.")

            
    def ConnectMotor(self):
        self.move.clicked.connect(lambda: self.Loader.mm.move_to_position(self.x,self.y))
        self.STOP.clicked.connect(lambda: self.Loader.mm.stop_now())
        self.zero.clicked.connect(lambda: self.Loader.mm.zero())
        self.set_speed.clicked.connect(lambda: self.Loader.mm.set_velocity(self.xv,self.xy))

        # Set timer to update current probe position and instant motor velocity
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(lambda: [self.update_current_position(),self.update_current_speed() ])
        self.timer.start(500)




    def update_current_position(self):
        self.xnow, self.ynow = self.Loader.mm.current_probe_position()
        self.canvas.point.remove()
        self.canvas.update_probe(self.xnow, self.ynow)
        self.PositionLabel.setText(f"Current Probe Position: ( {np.round(self.xnow, 2)} ,  {np.round(self.ynow, 2)} )")


    def mark_finished_positions(self, x, y):
        self.xdone = x
        self.ydone = y
        self.canvas.visited_points.remove()
        self.canvas.finished_positions(self.xdone, self.ydone)
      

    def update_current_speed(self):
        self.speedx, self.speedy, self.speedz = self.Loader.mm.ask_velocity()
        self.VelocityLabel.setText(f"Current Motor Speed: ( {self.speedx}  , {self.speedy} )")
#################################################################################
if __name__ == '__main__':

    app = QApplication([])
    app.setQuitOnLastWindowClosed(True)
    window = MainWindow()
    
    app.exec_()

