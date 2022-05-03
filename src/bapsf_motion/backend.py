# -*- coding: utf-8 -*-
"""
Created on Sat Apr 23 18:03:45 2022

@author: risha
"""

import numpy as np
import subprocess

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from .gui.main_window import TabPage, Ui_MainWindow
from .configurator.toml_loader import Loader


class MyMplCanvas(FigureCanvas):
    """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""

    def __init__(self, parent=None, width=10, height=8, dpi=100):
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

    def update_graph(self, poslist, nx, ny,nz, barlist, mode):
        ''' ROutine to update Matplotlib graph displaying actual data points defined so far, 
        as well as barriers and no-go zones'''
        self.ax.clear()

        self.ax.grid()
        self.initialize_visited_points()

        self.matrix = self.ax.scatter(0, 0, 0, color = 'blue', marker = 'o')
        self.point = self.ax.scatter(0, 0, 0, color = 'red', marker = '*')
        
        # self.ax.set_xticks(np.arange(-60,60,1))
        uss = np.linspace(0, 2 * np.pi, 32)
        zss = np.linspace(-100, 100, 2)

        uss, zss = np.meshgrid(uss, zss)

        xss = 50 * np.cos(uss)
        yss = 50 * np.sin(uss)
        self.ax.plot_surface(xss,yss,zss,alpha = 0.5, color = 'grey')

        xs = [x[0] for x in poslist]
        ys = [x[1] for x in poslist]
        zs = [x[2] for x in poslist]
        if mode == 'circle':
            size = nx/5
        else:
            size = min([nx/2, ny/2])

        self.ax.scatter(xs, ys, zs, s=size)

        # for posgroup in barlist:
        #     # posgroup is [(xorg,y,z),(xe),(xvo),(xve)]

        #     self.ax.plot([posgroup[0][0], posgroup[1][0]],
        #                          [posgroup[0][1], posgroup[1][1]], color='#800000'
        #                          )
        #     self.ax.plot([posgroup[0][0], posgroup[2][0]],
        #                          [posgroup[0][1], posgroup[2][1]], color='red'
        #                          )
        #     self.ax.plot([posgroup[1][0], posgroup[3][0]],
        #                          [posgroup[1][1], posgroup[3][1]], color='red'
        #                          )
        
        

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


    

        
class MainWindow(QMainWindow, Ui_MainWindow):

    def __init__(self, *args, **kwargs):
        '''connect UI to functions'''
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)
        
        self.i = 0
        self.tabs = {}
        
        self.button.clicked.connect(lambda: [self.addNewTab()])
        self.addNewTab()
        self.show()
        
     

        data_running = False

    def addNewTab(self):
        
        index = 'Tab %d' % (self.tabWidget.count())
        self.tabs[index] = TabPage(self.tabWidget)
        self.tabWidget.addTab(self.tabs[index], index)
        self.tabs[index].Loader = Loader()
        self.connect_buttons(index)
        self.i +=1
    def connect_buttons(self,index):
 
        self.tabs[index].load.clicked.connect(lambda: self.tabs[index].Loader.getgroup(self.tabs[index],self,self.i))
        
        self.tabs[index].canvas = MyMplCanvas()
        self.tabs[index].canvas.setMaximumSize(QtCore.QSize(400, 400))
        self.tabs[index].canvas.setObjectName("Canvas")
        self.tabs[index].mainHorizontalLayout.addWidget(self.tabs[index].canvas)
        
        self.tabs[index].create.clicked.connect(lambda: self.create_config())
        self.tabs[index].xcoord.editingFinished.connect(lambda: self.getVals())
        self.tabs[index].ycoord.editingFinished.connect(lambda: self.getVals())
        self.tabs[index].zcoord.editingFinished.connect(lambda: self.getVals())
        self.tabs[index].xspeed.editingFinished.connect(lambda: self.getVals())
        self.tabs[index].yspeed.editingFinished.connect(lambda: self.getVals())
        self.tabs[index].zspeed.editingFinished.connect(lambda: self.getVals())

        
    def update_timer(self):
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_current_position)
        self.timer.start(500)
        
    def create_config(self):
        subprocess.call(" python Configurator\\paintergui.py 1", shell = True)



    def getVals(self,index):
        try:
            if self.tabs[index].xcoord.text() != '':
                self.tabs[index].x = float(self.tabs[index].xcoord.text())
            if self.tabs[index].ycoord.text() != '':
                self.tabs[index].y = float(self.tabs[index].ycoord.text())
            if self.tabs[index].zcoord.text() != '':
                self.tabs[index].z = float(self.tabs[index].zcoord.text())
            if self.tabs[index].xspeed.text() != '':
                self.tabs[index].xv = float(self.tabs[index].xpeed.text())
            if self.tabs[index].yspeed.text() != '':
                self.tabs[index].yv = float(self.tabs[index].ypeed.text())
            if self.tabs[index].zspeed.text() != '':
                self.tabs[index].zv = float(self.tabs[index].zpeed.text())
        except ValueError:
            QMessageBox.about(self, "Error", "Position should be valid numbers.")

            
    def ConnectMotor(self,index):
        self.tabs[index].move.clicked.connect(lambda: self.tabs[index].Loader.mm.move_to_position(self.tabs[index].x,self.tabs[index].y))
        self.tabs[index].STOP.clicked.connect(lambda: self.tabs[index].Loader.mm.stop_now())
        self.tabs[index].zero.clicked.connect(lambda: self.tabs[index].Loader.mm.zero())
        self.tabs[index].set_speed.clicked.connect(lambda: self.tabs[index].Loader.mm.set_velocity(self.tabs[index].xv,self.tabs[index].xy))

        # Set timer to update current probe position and instant motor velocity
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(lambda: [self.update_current_position(index),self.update_current_speed(index) ])
        self.timer.start(500)



    def update_current_position(self,index):
        
        for i in range(index):
            self.tabs[i].xnow, self.tabs[i].ynow = self.tabs[i].Loader.mm.current_probe_position()
            self.tabs[i].canvas.point.remove()
            self.tabs[i].canvas.update_probe(self.tabs[i].xnow, self.tabs[i].ynow)
            self.tabs[i].PositionLabel.setText(f"Current Probe Position: ( {np.round(self.tabs[index].xnow, 2)} ,  {np.round(self.tabs[index].ynow, 2)} )")


    def mark_finished_positions(self, index, x, y):
        for i in range(index):
            self.tabs[i].xdone = x
            self.tabs[i].ydone = y
            self.tabs[i].canvas.visited_points.remove()
            self.tabs[i].canvas.finished_positions(self.tabs[i].xdone, self.tabs[i].ydone)
      

    def update_current_speed(self,index):
         for i in range(index):   
            self.tabs[i].speedx, self.tabs[i].speedy, self.tabs[i].speedz = self.tabs[i].Loader.mm.ask_velocity()
            self.tabs[i].VelocityLabel.setText(f"Current Motor Speed: ( {self.tabs[i].speedx}  , {self.tabs[i].speedy} )")
#################################################################################
if __name__ == '__main__':

    app = QApplication([])
    app.setQuitOnLastWindowClosed(True)
    window = MainWindow()
    
    app.exec_()

