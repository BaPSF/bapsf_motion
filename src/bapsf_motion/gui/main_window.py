# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'newgui.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets
from matplotlib.pyplot import imread
import sys


class Ui_MainWindow(QtWidgets.QWidget):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1200, 700)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.tabWidget = QtWidgets.QTabWidget(self.centralwidget)
        self.tabWidget.setSizePolicy(
            QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
            )
        )
        self.tabWidget.setGeometry(QtCore.QRect(0, 0, 1200, 700))
        self.tabWidget.setObjectName("tabWidget")
        self.button = QtWidgets.QPushButton()
        self.button.setText("Add New Tab")
        self.button.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_DialogYesButton)
        )
        self.tabWidget.setCornerWidget(self.button, QtCore.Qt.TopRightCorner)

        #######################RUN TAB#############################
        self.RunTab = QtWidgets.QWidget()
        self.RunTab.setObjectName("RunTab")
        self.runVerticalControlLayout = QtWidgets.QWidget(self.RunTab)
        self.runVerticalControlLayout.setGeometry(QtCore.QRect(0, 150, 160, 450))
        self.runVerticalControlLayout.setObjectName("runVerticalControlLayout")
        self.verticalLayout_5 = QtWidgets.QVBoxLayout(self.runVerticalControlLayout)
        self.verticalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.AllLabel = QtWidgets.QLabel(self.runVerticalControlLayout)
        self.AllLabel.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.AllLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.AllLabel.setObjectName("AllLabel")
        self.verticalLayout_5.addWidget(self.AllLabel)
        self.HomeAll = QtWidgets.QPushButton(self.runVerticalControlLayout)
        self.HomeAll.setObjectName("HomeAll")
        self.verticalLayout_5.addWidget(self.HomeAll)

        self.DisconnectAll = QtWidgets.QPushButton(self.runVerticalControlLayout)
        self.DisconnectAll.setObjectName("DisconnectAll")
        self.verticalLayout_5.addWidget(self.DisconnectAll)
        self.Save = QtWidgets.QPushButton(self.runVerticalControlLayout)
        self.Save.setObjectName("Save")
        self.verticalLayout_5.addWidget(self.Save)
        
        self.movelabel = QtWidgets.QLabel(self.runVerticalControlLayout)
        self.movelabel.setText("Move all to index: 0")
        self.movelabel.setAlignment(QtCore.Qt.AlignCenter)
        self.verticalLayout_5.addWidget(self.movelabel)
        
        self.moverlayout = QtWidgets.QHBoxLayout(self.runVerticalControlLayout)
        
        self.next = QtWidgets.QPushButton(self.runVerticalControlLayout)
        self.next.setText("Next")
        self.next.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_ArrowForward)
        )
       
        self.previous = QtWidgets.QPushButton(self.runVerticalControlLayout)
        self.previous.setText("Prev")
        self.previous.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_ArrowBack)
        )
        
        self.moverlayout.addWidget(self.previous)
        self.moverlayout.addWidget(self.next)

        self.verticalLayout_5.addLayout(self.moverlayout)
        
        self.moveall = QtWidgets.QPushButton(self.runVerticalControlLayout)
        self.moveall.setText("Execute Move")
        self.verticalLayout_5.addWidget(self.moveall)
        
               
        self.StopAll = QtWidgets.QPushButton(self.runVerticalControlLayout)
        self.StopAll.setObjectName("StopAll")
        self.verticalLayout_5.addWidget(self.StopAll)
        self.StopAll.setMinimumHeight(300)
        self.StopAll.setStyleSheet(    "QPushButton"
            "{"
            "background-color : #D21404;"
            "border:5px solid #E3242B; font-size: 20px; font: Agency"
            "}"
            "QPushButton::pressed"
            "{"
            "background-color : red;"
            "}"
            
            )
            
            
        self.StopAll.setText("STOP ALL")


        self.img = QtWidgets.QLabel(self.RunTab)
        self.img.setGeometry(QtCore.QRect(0, 0, 965, 151))
        self.img.setObjectName("img")
        
        self.scroll = QtWidgets.QScrollArea(self.RunTab)  
        # # Scroll Area which contains the widgets, set as the centralWidget
        self.scroll.setGeometry(QtCore.QRect(170, 160, 800, 490))

        self.scroll.setWidgetResizable(True)
        self.scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 750, 490))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        
    
        self.verticalLayout_6 = QtWidgets.QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.scrollAreaWidgetContents.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_6.setObjectName("verticalLayout_6")



        self.labelslayout = QtWidgets.QHBoxLayout(self.scrollAreaWidgetContents)
        self.labelslayout.setContentsMargins(0, 0, 0, 0)
        self.label1 = QtWidgets.QLabel()
        self.label1.setMaximumSize(QtCore.QSize(16777215, 30))
        self.label1.setAlignment(QtCore.Qt.AlignCenter)
        self.label1.setObjectName("label1")
        self.labelslayout.addWidget(self.label1)
        self.label1.setText("Add Motion Groups to Run to control or configure them.")
        self.verticalLayout_6.addLayout(self.labelslayout)
        self.scroll.setWidget(self.scrollAreaWidgetContents)

        self.tabWidget.addTab(self.RunTab, "")
        #####################################Image Stuff###################################################################
        input_image = imread(
            "C:\\Users\\risha\\Desktop\\daq-mod-probedrives-main\\src\\bapsf_motion\\gui\\LAPD.jpg"
        )
        height, width, channels = input_image.shape
        bytesPerLine = channels * width
        qImg = QtGui.QImage(
            input_image.data, width, height, bytesPerLine, QtGui.QImage.Format_RGB888
        )
        pixmap01 = QtGui.QPixmap.fromImage(qImg)
        pixmap_image = QtGui.QPixmap(pixmap01)

        self.img.setPixmap(pixmap_image)
        self.img.setAlignment(QtCore.Qt.AlignCenter)
        self.img.setScaledContents(True)
        self.img.setMinimumSize(1, 1)

        ###############################################################################
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.AllLabel.setText(_translate("MainWindow", "For all connected drives"))
        self.HomeAll.setText(_translate("MainWindow", "Home All"))
        self.DisconnectAll.setText(_translate("MainWindow", "Disconnect All"))
        self.Save.setText(_translate("MainWindow", "Save Run"))

        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.RunTab), _translate("MainWindow", "Run")
        )


class TabPage(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.groupBox = QtWidgets.QGroupBox(self)
        self.groupBox.setGeometry(QtCore.QRect(0, 0, 942, 650))
        self.groupBox.setSizePolicy(
            QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.MinimumExpanding,
                QtWidgets.QSizePolicy.MinimumExpanding,
            )
        )
        self.groupBox.setTitle("")
        self.groupBox.setObjectName("groupBox")
        self.groupBox.setContentsMargins(1, 1, 1, 1)

        self.groupBox.setFlat(True)

        self.mainHorizontalLayoutWidget = QtWidgets.QWidget(self.groupBox)
        self.mainHorizontalLayoutWidget.setGeometry(QtCore.QRect(0, 0, 940, 321))
        self.mainHorizontalLayoutWidget.setObjectName("mainHorizontalLayoutWidget")
        self.mainHorizontalLayout = QtWidgets.QHBoxLayout(
            self.mainHorizontalLayoutWidget
        )
        self.mainHorizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.mainHorizontalLayout.setObjectName("mainHorizontalLayout")

        self.mainVerticalLayout = QtWidgets.QVBoxLayout()
        self.mainVerticalLayout.setObjectName("mainVerticalLayout")
        self.divide = QtWidgets.QFrame(self.mainHorizontalLayoutWidget)
        self.divide.setFrameShape(QtWidgets.QFrame.HLine)
        self.divide.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.divide.setObjectName("divide")
        self.mainVerticalLayout.addWidget(self.divide)
        self.firstButtonHLayout = QtWidgets.QHBoxLayout()
        self.firstButtonHLayout.setObjectName("firstButtonHLayout")
        self.configButtonVLayout = QtWidgets.QVBoxLayout()
        self.configButtonVLayout.setObjectName("configButtonVLayout")

        self.load = QtWidgets.QPushButton(self.mainHorizontalLayoutWidget)
        self.load.setObjectName("load")
        self.configButtonVLayout.addWidget(self.load)
        self.create = QtWidgets.QPushButton(self.mainHorizontalLayoutWidget)
        self.create.setObjectName("create")
        self.configButtonVLayout.addWidget(self.create)
        self.edit = QtWidgets.QPushButton(self.mainHorizontalLayoutWidget)
        self.edit.setObjectName("edit")
        self.configButtonVLayout.addWidget(self.edit)
        self.remove = QtWidgets.QPushButton(self.mainHorizontalLayoutWidget)
        self.remove.setObjectName("remove")
        self.remove.setText("REMOVE GROUP")
        self.configButtonVLayout.addWidget(self.remove)

        
        self.firstButtonHLayout.addLayout(self.configButtonVLayout)
        self.line = QtWidgets.QFrame(self.mainHorizontalLayoutWidget)
        self.line.setFrameShape(QtWidgets.QFrame.VLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line.setObjectName("line")
        self.firstButtonHLayout.addWidget(self.line)
        self.displayLayout = QtWidgets.QVBoxLayout()
        self.displayLayout.setObjectName("displayLayout")
        self.PositionLabel = QtWidgets.QLabel(self.mainHorizontalLayoutWidget)
        self.PositionLabel.setObjectName("PositionLabel")
        self.displayLayout.addWidget(self.PositionLabel)
        self.VelocityLabel = QtWidgets.QLabel(self.mainHorizontalLayoutWidget)
        self.VelocityLabel.setObjectName("VelocityLabel")
        self.displayLayout.addWidget(self.VelocityLabel)
        self.firstButtonHLayout.addLayout(self.displayLayout)
        self.mainVerticalLayout.addLayout(self.firstButtonHLayout)
        self.hl = QtWidgets.QHBoxLayout()
        self.hl.setObjectName("hl")
        self.inputgrid = QtWidgets.QGridLayout()
        self.inputgrid.setSpacing(1)
        self.inputgrid.setObjectName("inputgrid")
        self.ycoordlabel = QtWidgets.QLabel(self.mainHorizontalLayoutWidget)
        self.ycoordlabel.setMaximumSize(QtCore.QSize(16777215, 20))
        self.ycoordlabel.setAlignment(QtCore.Qt.AlignCenter)
        self.ycoordlabel.setObjectName("ycoordlabel")
        self.inputgrid.addWidget(self.ycoordlabel, 0, 1, 1, 1)
        self.zspeedlabel = QtWidgets.QLabel(self.mainHorizontalLayoutWidget)
        self.zspeedlabel.setMaximumSize(QtCore.QSize(16777215, 20))
        self.zspeedlabel.setAlignment(QtCore.Qt.AlignCenter)
        self.zspeedlabel.setObjectName("zspeedlabel")
        self.inputgrid.addWidget(self.zspeedlabel, 2, 2, 1, 1)
        self.xspeedlabel = QtWidgets.QLabel(self.mainHorizontalLayoutWidget)
        self.xspeedlabel.setMaximumSize(QtCore.QSize(16777215, 20))
        self.xspeedlabel.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.xspeedlabel.setAlignment(QtCore.Qt.AlignCenter)
        self.xspeedlabel.setObjectName("xspeedlabel")
        self.inputgrid.addWidget(self.xspeedlabel, 2, 0, 1, 1)
        self.yspeedlabel = QtWidgets.QLabel(self.mainHorizontalLayoutWidget)
        self.yspeedlabel.setMaximumSize(QtCore.QSize(16777215, 20))
        self.yspeedlabel.setAlignment(QtCore.Qt.AlignCenter)
        self.yspeedlabel.setObjectName("yspeedlabel")
        self.inputgrid.addWidget(self.yspeedlabel, 2, 1, 1, 1)
        self.zcoord = QtWidgets.QLineEdit(self.mainHorizontalLayoutWidget)
        self.zcoord.setObjectName("zcoord")
        self.inputgrid.addWidget(self.zcoord, 1, 2, 1, 1)
        self.ycoord = QtWidgets.QLineEdit(self.mainHorizontalLayoutWidget)
        self.ycoord.setObjectName("ycoord")
        self.inputgrid.addWidget(self.ycoord, 1, 1, 1, 1)
        self.xspeed = QtWidgets.QLineEdit(self.mainHorizontalLayoutWidget)
        self.xspeed.setObjectName("xspeed")
        self.inputgrid.addWidget(self.xspeed, 3, 0, 1, 1)
        self.yspeed = QtWidgets.QLineEdit(self.mainHorizontalLayoutWidget)
        self.yspeed.setObjectName("yspeed")
        self.inputgrid.addWidget(self.yspeed, 3, 1, 1, 1)
        self.xcoord = QtWidgets.QLineEdit(self.mainHorizontalLayoutWidget)
        self.xcoord.setObjectName("xcoord")
        self.inputgrid.addWidget(self.xcoord, 1, 0, 1, 1)
        self.zspeed = QtWidgets.QLineEdit(self.mainHorizontalLayoutWidget)
        self.zspeed.setObjectName("zspeed")
        self.inputgrid.addWidget(self.zspeed, 3, 2, 1, 1)
        self.zcoordlabel = QtWidgets.QLabel(self.mainHorizontalLayoutWidget)
        self.zcoordlabel.setMaximumSize(QtCore.QSize(16777215, 20))
        self.zcoordlabel.setAlignment(QtCore.Qt.AlignCenter)
        self.zcoordlabel.setObjectName("zcoordlabel")
        self.inputgrid.addWidget(self.zcoordlabel, 0, 2, 1, 1)
        self.xcoordlabel = QtWidgets.QLabel(self.mainHorizontalLayoutWidget)
        self.xcoordlabel.setMaximumSize(QtCore.QSize(16777215, 20))
        self.xcoordlabel.setAlignment(QtCore.Qt.AlignCenter)
        self.xcoordlabel.setObjectName("xcoordlabel")
        self.inputgrid.addWidget(self.xcoordlabel, 0, 0, 1, 1)
        self.hl.addLayout(self.inputgrid)
        self.segment = QtWidgets.QFrame(self.mainHorizontalLayoutWidget)
        self.segment.setFrameShape(QtWidgets.QFrame.VLine)
        self.segment.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.segment.setObjectName("segment")
        self.hl.addWidget(self.segment)
        self.vl = QtWidgets.QVBoxLayout()
        self.vl.setObjectName("vl")
        self.move = QtWidgets.QPushButton(self.mainHorizontalLayoutWidget)
        self.move.setObjectName("move")
        self.vl.addWidget(self.move)
        self.set_speed = QtWidgets.QPushButton(self.mainHorizontalLayoutWidget)
        self.set_speed.setObjectName("set_speed")
        self.vl.addWidget(self.set_speed)
        self.zero = QtWidgets.QPushButton(self.mainHorizontalLayoutWidget)
        self.zero.setObjectName("zero")
        self.vl.addWidget(self.zero)
        self.hl.addLayout(self.vl)
        self.mainVerticalLayout.addLayout(self.hl)
        self.mainHorizontalLayout.addLayout(self.mainVerticalLayout)
        self.lin = QtWidgets.QFrame(self.mainHorizontalLayoutWidget)
        self.lin.setFrameShape(QtWidgets.QFrame.VLine)
        self.lin.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.lin.setObjectName("lin")
        self.mainHorizontalLayout.addWidget(self.lin)
        self.widget = QtWidgets.QWidget(self.groupBox)
        self.widget.setGeometry(QtCore.QRect(545, 330, 281, 211))
        self.widget.setObjectName("widget")
        self.groupTextLayout = QtWidgets.QVBoxLayout(self.widget)
        self.groupTextLayout.setContentsMargins(0, 0, 0, 0)
        self.groupTextLayout.setObjectName("groupTextLayout")
        self.GroupLabel = QtWidgets.QLabel(self.widget)
        self.GroupLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.GroupLabel.setObjectName("GroupLabel")
        self.groupTextLayout.addWidget(self.GroupLabel)
        self.GroupText = QtWidgets.QTextEdit(self.widget)
        self.GroupText.setObjectName("GroupText")
        self.GroupText.setReadOnly(True)
        self.groupTextLayout.addWidget(self.GroupText)
        
        
        
        self.runInfoLayout = QtWidgets.QWidget(self.groupBox)
        self.runInfoLayout.setGeometry(QtCore.QRect(10, 330, 371, 300))
        self.runInfoLayout.setObjectName("runInfoLayout")
        self.infovert = QtWidgets.QVBoxLayout(self.runInfoLayout)
        self.infoLayout = QtWidgets.QHBoxLayout(self.runInfoLayout)
        self.infoLayout.setContentsMargins(0, 0, 0, 0)
        self.infoLayout.setObjectName("infoLayout")
        self.label = QtWidgets.QLabel(self.runInfoLayout)
        self.label.setObjectName("label")
        self.label.setMaximumHeight(20)
        self.infoLayout.addWidget(self.label)
        self.timelabel = QtWidgets.QLabel(self.runInfoLayout)
        self.timelabel.setObjectName("timelabel")
        self.timelabel.setMaximumHeight(20)
        self.infoLayout.addWidget(self.timelabel)
        
        self.statuslabel =  QtWidgets.QLabel(self.runInfoLayout)
        self.statuslabel.setObjectName("statuslabel")
        self.statuslabel.setText("Motor Status:")
        self.statuslabel.setMaximumHeight(20)

        self.infovert.addWidget(self.statuslabel)
        self.infovert.addLayout(self.infoLayout)


        
        
        self.STOP = QtWidgets.QPushButton(self.runInfoLayout)
        self.STOP.setObjectName("STOP")
        self.STOP.setMinimumHeight(200)
        self.STOP.setText("STOP MOVEMENT")
        self.STOP.setStyleSheet(    "QPushButton"
            "{"
            "background-color : #D21404;"
            "border:5px solid #E3242B; font-size: 20px; font: Agency"
            "}"
            "QPushButton::pressed"
            "{"
            "background-color : red;"
            "}"
            
            )        
        self.infovert.addWidget(self.STOP)

        self.load.setText("LOAD GROUP CONFIGURATION")
        self.create.setText("CREATE GROUP CONFIGURATION")
        self.edit.setText("EDIT CONFIGURATION")
        self.PositionLabel.setText("CURRENT PROBE POSITION")
        self.VelocityLabel.setText("CURRENT MOTOR VELOCITY")
        self.ycoordlabel.setText("Y-COORDINATE")
        self.zspeedlabel.setText("Z-SPEED")
        self.xspeedlabel.setText("X-SPEED")
        self.yspeedlabel.setText("Y-SPEED")
        self.zcoordlabel.setText("Z-COORDINATE")
        self.xcoordlabel.setText(" X-COORDINATE")
        self.move.setText("Move")
        self.set_speed.setText("Set Speed")
        self.zero.setText("Set Zero")
        self.GroupLabel.setText("Group Information")
        self.label.setText("Number of points defined:")
        self.timelabel.setText("Estimated Time Required:")


class GroupLayout(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.groupHlayout = QtWidgets.QHBoxLayout()
        self.groupHlayout.setSizeConstraint(QtWidgets.QLayout.SetMaximumSize)
        self.groupHlayout.setObjectName("groupHlayout")
        self.GroupName = QtWidgets.QLabel()
        self.GroupName.setMaximumSize(QtCore.QSize(16777215, 30))
        self.GroupName.setAlignment(QtCore.Qt.AlignCenter)
        self.GroupName.setObjectName("GroupName")
        self.groupHlayout.addWidget(self.GroupName)
        self.Groupcoord = QtWidgets.QLabel()
        self.Groupcoord.setAlignment(QtCore.Qt.AlignCenter)
        self.Groupcoord.setObjectName("Groupcoord")
        self.groupHlayout.addWidget(self.Groupcoord)

        self.move = QtWidgets.QPushButton()
        self.move.setObjectName("move")
        self.groupHlayout.addWidget(self.move)
        self.move.setText("Move to:")
        self.move.setToolTip("Execute Movement")
        self.move.setMaximumHeight(30)

        self.x = QtWidgets.QLineEdit()
        self.x.setObjectName("x")
        self.groupHlayout.addWidget(self.x)
        self.x.setText("X")
        self.x.setMaximumHeight(30)
        self.x.setMaximumWidth(50)
        self.x.setToolTip("Set x-coordinate of desired move")

        self.y = QtWidgets.QLineEdit()
        self.y.setObjectName("y")
        self.groupHlayout.addWidget(self.y)
        self.y.setText("Y")
        self.y.setToolTip("Set y-coordinate of desired move")
        self.y.setMaximumHeight(30)
        self.y.setMaximumWidth(50)

        self.z = QtWidgets.QLineEdit()
        self.z.setObjectName("z")
        self.groupHlayout.addWidget(self.z)
        self.z.setText("Z")
        self.z.setToolTip("Set z-coordinate of desired move")
        self.z.setMaximumHeight(30)
        self.z.setMaximumWidth(50)

        self.list = QtWidgets.QComboBox()
        self.list.setObjectName("list")
        self.groupHlayout.addWidget(self.list)
        self.list.setMaximumHeight(30)
        self.list.setToolTip("Select Coordinate From Uploaded Motion List")
        self.list.setStyleSheet(
            """*    
QComboBox QAbstractItemView 
    {
    min-width: 200px;
    }
"""
        )

        self.Groupedit = QtWidgets.QPushButton()
        self.Groupedit.setObjectName("Groupedit")
        self.groupHlayout.addWidget(self.Groupedit)
        self.Groupedit.setMaximumHeight(30)

        self.GroupName.setText("GROUP NAME")
        self.Groupcoord.setText("(x,y,z)")
        self.Groupedit.setText("Edit Config")
        self.setLayout(self.groupHlayout)


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
