# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'paint.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!
__all__ = ["Ui_MainWindow"]

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")

        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        # set big size to fit screen + not break auto maximize..
        self.centralwidget.setMinimumHeight(3000)
        self.centralwidget.setMinimumWidth(3000)

        self.tabWidget = QtWidgets.QTabWidget(self.centralwidget)
        self.tabWidget.setGeometry(QtCore.QRect(0, 0, 1550, 2550))
        self.tabWidget.setObjectName("tabWidget")
        self.showMaximized()

        ##################### Probe Drive stuff
        self.PD = QtWidgets.QWidget()
        self.PD.setObjectName("PD")
        self.label_12 = QtWidgets.QLabel(self.PD)
        self.label_12.setGeometry(QtCore.QRect(30, 30, 131, 21))
        self.label_12.setObjectName("label_12")
        self.probeDriveBox = QtWidgets.QComboBox(self.PD)
        self.probeDriveBox.setGeometry(QtCore.QRect(30, 70, 101, 22))
        self.probeDriveBox.setObjectName("probeDriveBox")
        self.probeDriveBox.addItem("")
        self.probeDriveBox.addItem("Standard XY")
        self.probeDriveBox.addItem("Standard XYZ")
        self.probeDriveBox.addItem("Standard X-ϴ")
        self.line = QtWidgets.QFrame(self.PD)
        self.line.setGeometry(QtCore.QRect(173, 30, 20, 491))
        self.line.setFrameShape(QtWidgets.QFrame.VLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line.setObjectName("line")
        self.label_13 = QtWidgets.QLabel(self.PD)
        self.label_13.setGeometry(QtCore.QRect(190, 30, 181, 20))
        self.label_13.setObjectName("label_13")
        self.templatename = QtWidgets.QLineEdit(self.PD)
        self.templatename.setGeometry(QtCore.QRect(190, 70, 113, 20))
        self.templatename.setObjectName("templatename")
        self.AxesBox = QtWidgets.QComboBox(self.PD)
        self.AxesBox.setGeometry(QtCore.QRect(190, 120, 69, 22))
        self.AxesBox.setObjectName("AxesBox")
        self.AxesBox.addItem("")
        self.AxesBox.addItem("")
        self.AxesBox.addItem("")
        self.label_14 = QtWidgets.QLabel(self.PD)
        self.label_14.setGeometry(QtCore.QRect(190, 100, 121, 16))
        self.label_14.setObjectName("label_14")
        self.label_15 = QtWidgets.QLabel(self.PD)
        self.label_15.setGeometry(QtCore.QRect(190, 150, 211, 20))
        self.label_15.setObjectName("label_15")

        self.IPBox = QtWidgets.QGroupBox(self.PD)
        self.IPBox.setGeometry(QtCore.QRect(190, 180, 301, 110))
        self.IPBox.setObjectName("IPBox")
        self.ipx = QtWidgets.QLineEdit(self.IPBox)
        self.ipx.setGeometry(QtCore.QRect(120, 20, 113, 20))
        self.ipx.setObjectName("ipx")
        self.xmotorLabel = QtWidgets.QLabel(self.IPBox)
        self.xmotorLabel.setGeometry(QtCore.QRect(20, 20, 47, 13))
        self.xmotorLabel.setObjectName("xmotorLabel")
        self.ymotorLabel = QtWidgets.QLabel(self.IPBox)
        self.ymotorLabel.setGeometry(QtCore.QRect(20, 50, 47, 13))
        self.ymotorLabel.setObjectName("ymotorLabel")
        self.ipy = QtWidgets.QLineEdit(self.IPBox)
        self.ipy.setGeometry(QtCore.QRect(120, 50, 113, 20))
        self.ipy.setObjectName("ipy")

        self.zmotorLabel = QtWidgets.QLabel(self.IPBox)
        self.zmotorLabel.setGeometry(QtCore.QRect(20, 80, 47, 13))
        self.zmotorLabel.setObjectName("zmotorLabel")

        self.ipz = QtWidgets.QLineEdit(self.IPBox)
        self.ipz.setGeometry(QtCore.QRect(120, 80, 113, 20))
        self.ipz.setObjectName("ipz")
        self.ipz.setEnabled(False)

        self.CountPerStepLabel = QtWidgets.QLabel(self.PD)
        self.CountPerStepLabel.setGeometry(QtCore.QRect(190, 300, 171, 20))
        self.CountPerStepLabel.setObjectName("CountPerStepLabel")
        self.StepPerRevLabel = QtWidgets.QLabel(self.PD)
        self.StepPerRevLabel.setGeometry(QtCore.QRect(190, 350, 161, 16))
        self.StepPerRevLabel.setObjectName("StepPerRevLabel")
        self.SelectThreadingLabel = QtWidgets.QLabel(self.PD)
        self.SelectThreadingLabel.setGeometry(QtCore.QRect(190, 400, 121, 16))
        self.SelectThreadingLabel.setObjectName("SelectThreadingLabel")
        self.countStep = QtWidgets.QLineEdit(self.PD)
        self.countStep.setGeometry(QtCore.QRect(190, 320, 113, 20))
        self.countStep.setObjectName("countStep")
        self.countStep.setText("5")

        self.stepRev = QtWidgets.QLineEdit(self.PD)
        self.stepRev.setGeometry(QtCore.QRect(190, 370, 113, 20))
        self.stepRev.setObjectName("stepRev")
        self.TPIBox = QtWidgets.QComboBox(self.PD)
        self.TPIBox.setGeometry(QtCore.QRect(190, 420, 81, 22))
        self.TPIBox.setObjectName("TPIBox")
        self.TPIBox.addItem("0.02 in/rev")
        self.TPIBox.addItem("0.1 in/rev")
        self.TPIBox.addItem("0.4 in/rev")
        self.TPIBox.addItem("2 mm/rev")

        self.IsCustomLabel = QtWidgets.QLabel(self.PD)
        self.IsCustomLabel.setGeometry(QtCore.QRect(190, 450, 160, 16))
        self.IsCustomLabel.setObjectName("IsCustomLabel")
        self.customThreading = QtWidgets.QLineEdit(self.PD)
        self.customThreading.setGeometry(QtCore.QRect(190, 470, 113, 20))
        self.customThreading.setObjectName("customThreading")
        self.StepPerCmLabel = QtWidgets.QLabel(self.PD)
        self.StepPerCmLabel.setGeometry(QtCore.QRect(190, 510, 131, 16))
        self.StepPerCmLabel.setObjectName("StepPerCmLabel")

        self.SaveDriveButton = QtWidgets.QPushButton(self.PD)
        self.SaveDriveButton.setGeometry(QtCore.QRect(190, 570, 100, 22))
        self.SaveDriveButton.setText("Save")

        self.tabWidget.addTab(self.PD, "")
        ############################################ Probe config stuff##############################

        self.PC = QtWidgets.QWidget()
        self.PC.setObjectName("PC")

        self.probeBoxLabel = QtWidgets.QLabel(self.PC)
        self.probeBoxLabel.setGeometry(QtCore.QRect(50, 40, 121, 16))
        self.probeBoxLabel.setObjectName("probeBoxLabel")

        self.probeBox = QtWidgets.QComboBox(self.PC)
        self.probeBox.setGeometry(QtCore.QRect(50, 70, 129, 22))
        self.probeBox.setObjectName("probeBox")
        self.probeBox.addItem("")
        self.probeBox.addItem("Langmuir 1")

        self.line_2 = QtWidgets.QFrame(self.PC)
        self.line_2.setGeometry(QtCore.QRect(223, 40, 20, 481))
        self.line_2.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_2.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_2.setObjectName("line_2")
        self.ConfigProbeLabel = QtWidgets.QLabel(self.PC)
        self.ConfigProbeLabel.setGeometry(QtCore.QRect(250, 40, 201, 16))
        self.ConfigProbeLabel.setObjectName("ConfigProbeLabel")

        self.ProbeName = QtWidgets.QLineEdit((self.PC))
        self.ProbeName.setGeometry(QtCore.QRect(250, 70, 150, 22))
        self.ProbeName.setText("Probe Name")

        self.DateFabricatedLabel = QtWidgets.QLabel(self.PC)
        self.DateFabricatedLabel.setGeometry(QtCore.QRect(250, 100, 100, 22))
        self.DateFabricatedLabel.setObjectName("DateFabricatedLabel")
        self.DateFabricatedLabel.setText("Date Fabricated:")
        self.dateedit = QtWidgets.QDateEdit(self.PC, calendarPopup=True)
        self.dateedit.setGeometry(QtCore.QRect(350, 100, 80, 28))
        self.dateedit.setDateTime(QtCore.QDateTime.currentDateTime())

        self.DateServicedLabel = QtWidgets.QLabel(self.PC)
        self.DateServicedLabel.setGeometry(QtCore.QRect(250, 130, 100, 22))
        self.DateServicedLabel.setObjectName("DateServicedLabel")
        self.DateServicedLabel.setText("Last Date Serviced:")
        self.dateedit2 = QtWidgets.QDateEdit(self.PC, calendarPopup=True)
        self.dateedit2.setGeometry(QtCore.QRect(350, 130, 80, 28))
        self.dateedit2.setDateTime(QtCore.QDateTime.currentDateTime())

        self.ProbeTypeLabel = QtWidgets.QLabel(self.PC)
        self.ProbeTypeLabel.setGeometry(QtCore.QRect(250, 160, 100, 22))
        self.ProbeTypeLabel.setObjectName("ProbeTypeLabel")
        self.ProbeTypeLabel.setText("Probe Type:")
        self.ProbeType = QtWidgets.QComboBox(self.PC)
        self.ProbeType.setGeometry(QtCore.QRect(350, 160, 80, 28))
        self.ProbeType.addItem("Langmuir")
        self.ProbeType.addItem("Langmuir2")
        self.ProbeType.addItem("Bdot")

        self.UnitLabel = QtWidgets.QLabel(self.PC)
        self.UnitLabel.setGeometry(QtCore.QRect(250, 190, 100, 22))
        self.UnitLabel.setObjectName("UnitLabel")
        self.UnitLabel.setText("Units:")
        self.UnitType = QtWidgets.QComboBox(self.PC)
        self.UnitType.setGeometry(QtCore.QRect(350, 190, 80, 28))
        self.UnitType.addItem("SI")
        self.UnitType.addItem("IPS")
        self.UnitType.addItem("CGS")

        self.DiameterLabel = QtWidgets.QLabel(self.PC)
        self.DiameterLabel.setGeometry(QtCore.QRect(250, 220, 100, 22))
        self.DiameterLabel.setObjectName("DiameterLabel")
        self.DiameterLabel.setText("Shaft Diameter:")
        self.Diameter = QtWidgets.QLineEdit(self.PC)
        self.Diameter.setGeometry(QtCore.QRect(350, 220, 80, 28))
        self.Diameter.setText("2")

        self.ThicknessLabel = QtWidgets.QLabel(self.PC)
        self.ThicknessLabel.setGeometry(QtCore.QRect(250, 250, 100, 22))
        self.ThicknessLabel.setObjectName("ThicknessLabel")
        self.ThicknessLabel.setText("Shaft Thickness:")
        self.Thickness = QtWidgets.QLineEdit(self.PC)
        self.Thickness.setGeometry(QtCore.QRect(350, 250, 80, 28))
        self.Thickness.setText("2")

        self.LengthLabel = QtWidgets.QLabel(self.PC)
        self.LengthLabel.setGeometry(QtCore.QRect(250, 280, 100, 22))
        self.LengthLabel.setObjectName("LengthLabel")
        self.LengthLabel.setText("Shaft Length:")
        self.Length = QtWidgets.QLineEdit(self.PC)
        self.Length.setGeometry(QtCore.QRect(350, 280, 80, 28))
        self.Length.setText("2")

        self.MaterialLabel = QtWidgets.QLabel(self.PC)
        self.MaterialLabel.setGeometry(QtCore.QRect(250, 310, 100, 22))
        self.MaterialLabel.setObjectName("MaterialLabel")
        self.MaterialLabel.setText("Shaft Material:")
        self.Material = QtWidgets.QComboBox(self.PC)
        self.Material.setGeometry(QtCore.QRect(350, 310, 80, 28))
        self.Material.addItem("Stainess Steel")
        self.Material.addItem("Brass")
        self.Material.addItem("Copper")

        self.SaveProbeButton = QtWidgets.QPushButton(self.PC)
        self.SaveProbeButton.setGeometry(QtCore.QRect(250, 390, 100, 22))
        self.SaveProbeButton.setText("Save")

        self.tabWidget.addTab(self.PC, "")

        ## group config stuff
        ######################################################################
        self.GD = QtWidgets.QWidget()
        self.GD.setObjectName("GD")

        self.MgroupBoxLabel = QtWidgets.QLabel(self.GD)
        self.MgroupBoxLabel.setGeometry(QtCore.QRect(10, 40, 121, 16))
        self.MgroupBoxLabel.setObjectName("MgroupBoxLabel")

        self.MgroupBox = QtWidgets.QComboBox(self.GD)
        self.MgroupBox.setGeometry(QtCore.QRect(10, 70, 129, 22))
        self.MgroupBox.setObjectName("MgroupBox")
        self.MgroupBox.addItem("Port 1 Standard")
        self.MgroupBox.addItem("Port 2 Standard")
        self.MgroupBox.addItem("Port 3 Standard")

        self.DriveChoose = QtWidgets.QPushButton(self.GD)
        self.DriveChoose.setGeometry(QtCore.QRect(10, 150, 200, 20))
        self.DriveChoose.setObjectName("DriveChoose")
        self.DriveChoose.setText("Choose Drive Configuration:")
        self.DriveContents = QtWidgets.QTextEdit(self.GD)
        self.DriveContents.setGeometry(QtCore.QRect(10, 182, 200, 200))
        self.DriveContents.setEnabled(False)
        self.ProbeChoose = QtWidgets.QPushButton(self.GD)
        self.ProbeChoose.setGeometry(QtCore.QRect(10, 390, 200, 22))
        self.ProbeChoose.setObjectName("Probe Choose")
        self.ProbeChoose.setText("Choose Probe Configuration:")
        self.ProbeContents = QtWidgets.QTextEdit(self.GD)
        self.ProbeContents.setGeometry(QtCore.QRect(10, 420, 200, 200))
        self.ProbeContents.setEnabled(False)
        self.line_3 = QtWidgets.QFrame(self.GD)
        self.line_3.setGeometry(QtCore.QRect(223, 40, 20, 640))
        self.line_3.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_3.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_3.setObjectName("line_3")

        self.ConfigGroupLabel = QtWidgets.QLabel(self.GD)
        self.ConfigGroupLabel.setGeometry(QtCore.QRect(250, 40, 201, 16))
        self.ConfigGroupLabel.setObjectName("ConfigGroupLabel")

        self.GroupName = QtWidgets.QLineEdit((self.GD))
        self.GroupName.setGeometry(QtCore.QRect(250, 70, 150, 22))
        self.GroupName.setText("Group Name")

        self.Dist1Label = QtWidgets.QLabel(self.GD)
        self.Dist1Label.setGeometry(QtCore.QRect(250, 130, 220, 22))
        self.Dist1Label.setObjectName("Dist1Label")
        self.Dist1Label.setText("Distance from drive pivot to valve pivot (cm)")
        self.Dist1 = QtWidgets.QLineEdit(self.GD)
        self.Dist1.setGeometry(QtCore.QRect(500, 130, 200, 28))
        self.Dist1.setText("125")

        self.Dist2Label = QtWidgets.QLabel(self.GD)
        self.Dist2Label.setGeometry(QtCore.QRect(250, 160, 220, 22))
        self.Dist2Label.setObjectName("Dist1Label")
        self.Dist2Label.setText("Distance from valve pivot to LAPD centre (cm)")
        self.Dist2 = QtWidgets.QLineEdit(self.GD)
        self.Dist2.setGeometry(QtCore.QRect(500, 160, 200, 28))
        self.Dist2.setText("57.7")

        self.PortNumberLabel = QtWidgets.QLabel(self.GD)
        self.PortNumberLabel.setGeometry(QtCore.QRect(250, 190, 100, 22))
        self.PortNumberLabel.setObjectName("PortNumberLabel")
        self.PortNumberLabel.setText("Port Number:")
        self.PortNumber = QtWidgets.QLineEdit(self.GD)
        self.PortNumber.setGeometry(QtCore.QRect(350, 190, 100, 28))
        self.PortNumber.setText("0")

        self.PortLocationLabel = QtWidgets.QLabel(self.GD)
        self.PortLocationLabel.setGeometry(QtCore.QRect(250, 220, 100, 22))
        self.PortLocationLabel.setObjectName("PortLocationLabel")
        self.PortLocationLabel.setText("Port Location:")
        self.PortLocation = QtWidgets.QLineEdit(self.GD)
        self.PortLocation.setGeometry(QtCore.QRect(350, 220, 100, 28))
        self.PortLocation.setText("0")

        self.SaveGroupButton = QtWidgets.QPushButton(self.GD)
        self.SaveGroupButton.setGeometry(QtCore.QRect(250, 290, 100, 22))
        self.SaveGroupButton.setText("Save")

        self.ConfirmButton = QtWidgets.QPushButton(self.GD)
        self.ConfirmButton.setGeometry(QtCore.QRect(250, 320, 100, 22))
        self.ConfirmButton.setText("Confirm")

        self.tabWidget.addTab(self.GD, "")

        ######################################## MOTION LIST STUFF##########################
        self.ML = QtWidgets.QWidget()
        self.ML.setObjectName("ML")

        self.widget = QtWidgets.QWidget(self.ML)
        self.widget.setGeometry(QtCore.QRect(0, 0, 1240, 675))
        self.widget.setSizePolicy(
            QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
            )
        )
        self.widget.setObjectName("widget")

        # overall layout
        self.verticalLayout = QtWidgets.QVBoxLayout(self.widget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")

        # layout with canvases and mode stuff
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.widget)
        self.horizontalLayout.setObjectName("horizontalLayout")

        self.groupBox = QtWidgets.QGroupBox(self.widget)
        self.groupBox.setObjectName("groupBox")
        self.groupBox.setGeometry(QtCore.QRect(10, 20, 160, 160))

        # groupBox mode stuff
        self.widget1 = QtWidgets.QWidget(self.groupBox)
        self.widget1.setGeometry(QtCore.QRect(10, 20, 160, 160))
        self.widget1.setObjectName("widget1")

        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.groupBox)
        self.verticalLayout_2.setContentsMargins(2, 0, 2, 0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        # label = choose mode label
        self.label = QtWidgets.QLabel(self.groupBox)
        self.label.setMaximumSize(QtCore.QSize(150, 20))
        self.label.setObjectName("label")
        self.verticalLayout_2.addWidget(self.label)

        # Mode style box

        self.vl = QtWidgets.QVBoxLayout(self.groupBox)

        self.modeBox = QtWidgets.QComboBox(self.groupBox)
        self.modeBox.setObjectName("modeBox")
        self.modeBox.addItem("")
        self.modeBox.addItem("")
        self.modeBox.addItem("")
        self.modeBox.addItem("")
        self.modeBox.addItem("")
        self.modeBox.addItem("")
        self.modeBox.setMaximumWidth(150)
        self.modeBox.SelectedIndex = 0
        self.vl.addWidget(self.modeBox)
        self.verticalLayout_2.addLayout(self.vl)

        self.gridV = QtWidgets.QVBoxLayout(self.groupBox)
        self.gridL = QtWidgets.QHBoxLayout(self.groupBox)

        self.generatorlabel = QtWidgets.QLabel(self.groupBox)
        self.generatorlabel.setMaximumWidth(150)
        self.gridL.addWidget(self.generatorlabel)

        self.generateBox = QtWidgets.QCheckBox(self.groupBox)
        self.generateBox.setObjectName("generateBox")
        self.generateBox.setMaximumWidth(80)
        self.gridL.addWidget(self.generateBox)
        self.gridV.addLayout(self.gridL)

        self.gridL0 = QtWidgets.QHBoxLayout(self.groupBox)
        self.Num = QtWidgets.QLabel(self.groupBox)
        self.Num.setMaximumWidth(150)
        self.Num.setMaximumHeight(30)
        self.gridL0.addWidget(self.Num)

        self.Dim = QtWidgets.QLabel(self.groupBox)
        self.Dim.setMaximumWidth(150)
        self.Dim.setMaximumHeight(30)
        self.gridL0.addWidget(self.Dim)

        self.gridL1 = QtWidgets.QHBoxLayout(self.groupBox)
        self.gridL2 = QtWidgets.QHBoxLayout(self.groupBox)
        self.gridL3 = QtWidgets.QHBoxLayout(self.groupBox)

        self.ea = QtWidgets.QLineEdit(self.groupBox)
        self.ea.setMaximumWidth(80)
        self.ea.setObjectName("ea")
        self.ea.setText("No. of points: X")
        self.ea.setToolTip(
            "Enter the number of data points you wish to define.\n Enter multiple integers separated by commas (i.e '1,2,3') for disjoint regions"
        )
        self.gridL1.addWidget(self.ea)

        self.la = QtWidgets.QLineEdit(self.groupBox)
        self.la.setMaximumWidth(80)
        self.la.setObjectName("la")
        self.la.setText("Length- X")
        self.gridL1.addWidget(self.la)

        self.eb = QtWidgets.QLineEdit(self.groupBox)
        self.eb.setMaximumWidth(80)
        self.eb.setObjectName("eb")
        self.eb.setText("No. of points: Y")
        self.eb.setToolTip(
            "Enter the number of data points you wish to define.\n Enter multiple integers separated by commas (i.e '1,2,3') for disjoint regions"
        )
        self.gridL2.addWidget(self.eb)

        self.lb = QtWidgets.QLineEdit(self.groupBox)
        self.lb.setMaximumWidth(80)
        self.lb.setObjectName("lb")
        self.lb.setText("Length- Y")
        self.gridL2.addWidget(self.lb)

        self.ec = QtWidgets.QLineEdit(self.groupBox)
        self.ec.setMaximumWidth(80)
        self.ec.setObjectName("ec")
        self.ec.setText("No. of points: Z")
        self.ec.setToolTip(
            "Enter the number of data points you wish to define.\n Enter multiple integers separated by commas (i.e '1,2,3') for disjoint regions"
        )
        self.gridL3.addWidget(self.ec)

        self.lc = QtWidgets.QLineEdit(self.groupBox)
        self.lc.setMaximumWidth(80)
        self.lc.setObjectName("lc")
        self.lc.setText("Length- Z")
        self.gridL3.addWidget(self.lc)

        self.ea.setEnabled(False)
        self.eb.setEnabled(False)
        self.ec.setEnabled(False)

        self.gridV.addLayout(self.gridL0)
        self.gridV.addLayout(self.gridL1)
        self.gridV.addLayout(self.gridL2)
        self.gridV.addLayout(self.gridL3)

        self.verticalLayout_2.addLayout(self.gridV)

        self.gridCentreLabel = QtWidgets.QLabel(self.groupBox)
        self.gridCentreLabel.setMaximumSize(QtCore.QSize(150, 20))
        self.gridCentreLabel.setObjectName("gridCentreLabel")
        self.verticalLayout_2.addWidget(self.gridCentreLabel)

        self.gridCentre = QtWidgets.QLineEdit(self.groupBox)
        self.gridCentre.setObjectName("gridCentre")
        self.gridCentre.setMaximumWidth(150)
        self.verticalLayout_2.addWidget(self.gridCentre)

        # grid box stuff
        # label_7 - choose grid style
        self.label_7 = QtWidgets.QLabel(self.groupBox)
        self.label_7.setMaximumSize(QtCore.QSize(150, 20))
        self.label_7.setObjectName("label_7")
        self.verticalLayout_2.addWidget(self.label_7)
        self.gridBox = QtWidgets.QComboBox(self.groupBox)
        self.gridBox.setObjectName("gridBox")
        self.gridBox.addItem("")
        self.gridBox.addItem("")
        self.gridBox.addItem("")
        self.gridBox.addItem("")
        self.gridBox.setMaximumWidth(150)
        self.verticalLayout_2.addWidget(self.gridBox)
        self.gridResLabel = QtWidgets.QLabel(self.groupBox)
        self.gridResLabel.setMaximumSize(QtCore.QSize(150, 40))
        self.gridResLabel.setObjectName("gridResLabel")
        self.verticalLayout_2.addWidget(self.gridResLabel)

        self.hl = QtWidgets.QHBoxLayout(self.groupBox)
        self.xreslabel = QtWidgets.QLabel(self.groupBox)
        self.xreslabel.setMaximumSize(QtCore.QSize(150, 40))
        self.xreslabel.setObjectName("gridResLabel")
        self.hl.addWidget(self.xreslabel)

        self.xres = QtWidgets.QLineEdit(self.groupBox)
        self.xres.setObjectName("xres")
        self.xres.setMaximumWidth(150)
        self.hl.addWidget(self.xres)

        self.hl2 = QtWidgets.QHBoxLayout(self.groupBox)
        self.yreslabel = QtWidgets.QLabel(self.groupBox)
        self.yreslabel.setMaximumSize(QtCore.QSize(150, 40))
        self.yreslabel.setObjectName("gridResLabel")
        self.hl2.addWidget(self.yreslabel)

        self.yres = QtWidgets.QLineEdit(self.groupBox)
        self.yres.setObjectName("yres")
        self.yres.setMaximumWidth(150)
        self.hl2.addWidget(self.yres)

        self.hl3 = QtWidgets.QHBoxLayout(self.groupBox)
        self.zreslabel = QtWidgets.QLabel(self.groupBox)
        self.zreslabel.setMaximumSize(QtCore.QSize(150, 40))
        self.zreslabel.setObjectName("gridResLabel")
        self.hl3.addWidget(self.zreslabel)

        self.zres = QtWidgets.QLineEdit(self.groupBox)
        self.zres.setObjectName("xres")
        self.zres.setMaximumWidth(150)
        self.hl3.addWidget(self.zres)

        self.verticalLayout_2.addLayout(self.hl)
        self.verticalLayout_2.addLayout(self.hl2)
        self.verticalLayout_2.addLayout(self.hl3)

        self.zH = QtWidgets.QHBoxLayout(self.groupBox)

        self.zrangelabel = QtWidgets.QLabel(self.groupBox)
        self.zrangelabel.setMaximumSize(QtCore.QSize(50, 20))
        self.zrangelabel.setObjectName("zrangelabel")
        self.zH.addWidget(self.zrangelabel)

        self.z1 = QtWidgets.QLineEdit(self.groupBox)
        self.z1.setObjectName("z1")
        self.z1.setMaximumWidth(20)
        self.z1.setValidator(QDoubleValidator())
        self.zH.addWidget(self.z1)

        self.label_11 = QtWidgets.QLabel(self.groupBox)
        self.label_11.setMaximumSize(QtCore.QSize(20, 20))
        self.label_11.setObjectName("label_11")
        self.zH.addWidget(self.label_11)
        self.z2 = QtWidgets.QLineEdit(self.groupBox)
        self.z2.setMaximumWidth(20)
        self.z2.setObjectName("z2")
        self.z2.setValidator(QDoubleValidator())
        self.zH.addWidget(self.z2)
        self.verticalLayout_2.addLayout(self.zH)

        self.printButton = QtWidgets.QPushButton(self.groupBox)
        self.printButton.setObjectName("printButton")
        self.printButton.setMaximumWidth(150)

        self.verticalLayout_2.addWidget(self.printButton)
        self.clearButton = QtWidgets.QPushButton(self.groupBox)
        self.clearButton.setObjectName("clearButton")
        self.clearButton.setMaximumWidth(150)
        self.verticalLayout_2.addWidget(self.clearButton)
        self.verifyButton = QtWidgets.QPushButton(self.groupBox)
        self.verifyButton.setObjectName("verifyButton")
        self.verifyButton.setMaximumWidth(150)
        self.verticalLayout_2.addWidget(self.verifyButton)
        self.saveButton = QtWidgets.QPushButton(self.groupBox)
        self.saveButton.setObjectName("saveButton")
        self.saveButton.setMaximumWidth(150)
        self.verticalLayout_2.addWidget(self.saveButton)

        self.horizontalLayout.addWidget(self.groupBox)

        self.verticalLayout.addLayout(self.horizontalLayout)

        self.groupBox_2 = QtWidgets.QGroupBox(self.widget)
        self.groupBox_2.setMinimumSize(QtCore.QSize(0, 70))
        self.groupBox_2.setMaximumSize(QtCore.QSize(2100, 130))
        # self.groupBox_2.addStretch()
        self.groupBox_2.setObjectName("groupBox_2")

        # coordinate entering + other info stuff.
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.groupBox_2)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")

        self.cursorLabel = QtWidgets.QLabel(self.groupBox_2)
        self.cursorLabel.setObjectName("cursorLabel")
        self.horizontalLayout_2.addWidget(self.cursorLabel)

        self.line_4 = QtWidgets.QFrame(self.groupBox_2)
        self.line_4.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_4.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_4.setObjectName("line_4")
        self.horizontalLayout_2.addWidget(self.line_4)

        self.timelayout = QtWidgets.QVBoxLayout(self.groupBox_2)

        self.pointnumberLabel = QtWidgets.QLabel(self.groupBox_2)
        self.pointnumberLabel.setObjectName("pointnumberLabel")
        self.timelayout.addWidget(self.pointnumberLabel)
        self.timeLabel = QtWidgets.QLabel(self.groupBox_2)
        self.timeLabel.setObjectName("timeLabel")
        self.timelayout.addWidget(self.timeLabel)

        self.horizontalLayout_2.addLayout(self.timelayout)

        self.line_5 = QtWidgets.QFrame(self.groupBox_2)
        self.line_5.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_5.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_5.setObjectName("line_5")
        self.horizontalLayout_2.addWidget(self.line_5)

        self.coordinatesVert = QtWidgets.QVBoxLayout(self.groupBox_2)

        self.coordEnterLabel = QtWidgets.QLabel(self.groupBox_2)
        self.coordEnterLabel.setObjectName("coordEnterLabel")
        self.coordEnterLabel.setMaximumWidth(60)
        self.coordEnterLabel.setMaximumHeight(80)
        self.horizontalLayout_2.addWidget(self.coordEnterLabel)

        self.coordinates = QtWidgets.QLineEdit(self.groupBox_2)
        self.coordinates.setObjectName("coordinates")
        self.coordinates.setText(
            "Enter points separated by commas and space. For eg. - (0,0,0), (10,0,0), (0,20,10)"
        )
        self.coordinatesVert.addWidget(self.coordinates)

        self.barcord = QtWidgets.QLineEdit(self.groupBox_2)
        self.barcord.setObjectName("barcord")
        self.barcord.setText("Enter coordinates for the barrier. Same format.")
        self.coordinatesVert.addWidget(self.barcord)

        self.horizontalLayout_2.addLayout(self.coordinatesVert)

        self.EntButton = QtWidgets.QPushButton(self.groupBox_2)
        self.EntButton.setObjectName("Enter")
        self.horizontalLayout_2.addWidget(self.EntButton)

        self.line_6 = QtWidgets.QFrame(self.groupBox_2)
        self.line_6.setFrameShape(QtWidgets.QFrame.VLine)
        self.line_6.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_6.setObjectName("line_6")
        self.horizontalLayout_2.addWidget(self.line_6)

        self.spacinglabel = QtWidgets.QLabel(self.groupBox_2)
        self.spacinglabel.setObjectName("spacinglabel")
        self.spacinglabel.setText("Grid Spacing")
        self.horizontalLayout_2.addWidget(self.spacinglabel)

        self.sl = QSlider(Qt.Horizontal)
        self.sl.setMinimum(1)
        self.sl.setMaximum(10)
        self.sl.setValue(2)
        self.sl.setTickPosition(QSlider.TicksBelow)
        self.sl.setTickInterval(1)

        self.slider_vbox = QtWidgets.QVBoxLayout()
        self.slider_hbox = QtWidgets.QHBoxLayout()
        self.slider_hbox.setContentsMargins(0, 0, 0, 0)
        self.slider_vbox.setContentsMargins(0, 0, 0, 0)
        self.slider_vbox.setSpacing(0)
        self.label_minimum = QtWidgets.QLabel(alignment=QtCore.Qt.AlignLeft)
        self.label_minimum.setText("1cm")
        self.label_maximum = QtWidgets.QLabel(alignment=QtCore.Qt.AlignRight)
        self.label_maximum.setText("10cm")
        self.slider_vbox.addWidget(self.sl)
        self.slider_vbox.addLayout(self.slider_hbox)
        self.slider_hbox.addWidget(self.label_minimum, QtCore.Qt.AlignLeft)
        self.slider_hbox.addWidget(self.label_maximum, QtCore.Qt.AlignRight)
        self.slider_vbox.addStretch()

        self.horizontalLayout_2.addLayout(self.slider_vbox)

        self.ToggleEm = QtWidgets.QVBoxLayout()

        self.PlasmaColumnH = QtWidgets.QHBoxLayout()
        self.PlasmaColumn = QtWidgets.QCheckBox(self.groupBox_2)
        self.PlasmaColumnLabel = QtWidgets.QLabel(self.groupBox_2)
        self.PlasmaColumnLabel.setText("Plasma Column       ")

        self.PlasmaColumnH.addWidget(self.PlasmaColumnLabel)
        self.PlasmaColumnH.addWidget(self.PlasmaColumn)
        self.PlasmaColumn.setChecked(True)
        self.ToggleEm.addLayout(self.PlasmaColumnH)

        self.MainCathodeH = QtWidgets.QHBoxLayout()
        self.MainCathode = QtWidgets.QCheckBox(self.groupBox_2)
        self.MainCathodeLabel = QtWidgets.QLabel(self.groupBox_2)
        self.MainCathodeLabel.setText("Main Cathode         ")

        self.MainCathodeH.addWidget(self.MainCathodeLabel)
        self.MainCathodeH.addWidget(self.MainCathode)
        self.ToggleEm.addLayout(self.MainCathodeH)

        self.SecondaryCathodeH = QtWidgets.QHBoxLayout()
        self.SecondaryCathode = QtWidgets.QCheckBox(self.groupBox_2)
        self.SecondaryCathodeLabel = QtWidgets.QLabel(self.groupBox_2)
        self.SecondaryCathodeLabel.setText("Secondary Cathode")

        self.SecondaryCathodeH.addWidget(self.SecondaryCathodeLabel)
        self.SecondaryCathodeH.addWidget(self.SecondaryCathode)
        self.ToggleEm.addLayout(self.SecondaryCathodeH)

        self.horizontalLayout_2.addLayout(self.ToggleEm)

        self.verticalLayout.addWidget(self.groupBox_2)
        ################################################################

        ############################################################################
        self.tabWidget.addTab(self.ML, "")
        self.tabWidget.setTabEnabled(3, False)

        ##################################################################################
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 21))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.label_12.setText(_translate("MainWindow", "SELECT PROBE DRIVE:"))
        self.label_13.setText(_translate("MainWindow", "DEFINE NEW PROBE DRIVE SETUP:"))
        self.templatename.setText(_translate("MainWindow", "Template Name"))
        self.AxesBox.setItemText(0, _translate("MainWindow", "X-Y"))
        self.AxesBox.setItemText(1, _translate("MainWindow", "X-Y-Z"))
        self.AxesBox.setItemText(2, _translate("MainWindow", "X-ϴ"))
        self.label_14.setText(_translate("MainWindow", "Select Probe Axes:"))
        self.label_15.setText(
            _translate("MainWindow", "Enter IP-addresses of axis motors:")
        )
        self.IPBox.setTitle(_translate("MainWindow", "IP-addresses:"))

        self.xmotorLabel.setText(_translate("MainWindow", "X-motor"))
        self.ymotorLabel.setText(_translate("MainWindow", "Y-motor"))
        self.zmotorLabel.setText(_translate("MainWindow", "Z-motor"))

        self.CountPerStepLabel.setText(
            _translate("MainWindow", "Enter Encoder-Motor Counts/Step:")
        )
        self.StepPerRevLabel.setText(
            _translate("MainWindow", "Enter Steps/Revolution: ")
        )
        self.SelectThreadingLabel.setText(
            _translate("MainWindow", "Select Rod Threading:")
        )
        self.IsCustomLabel.setText(
            _translate("MainWindow", "If custom, please specify (cm/rev)-")
        )
        self.StepPerCmLabel.setText(_translate("MainWindow", "Calculated Steps/cm :"))
        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.PD),
            _translate("MainWindow", "Probe Drive Config"),
        )
        self.probeBoxLabel.setText(_translate("MainWindow", "SELECT PROBE:"))
        self.ConfigProbeLabel.setText(_translate("MainWindow", "CONFIGURE NEW PROBE:"))

        self.MgroupBoxLabel.setText(_translate("MainWindow", "SELECT GROUP CONFIG:"))
        self.ConfigGroupLabel.setText(
            _translate("MainWindow", "CONFIGURE NEW MOTION GROUP:")
        )

        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.PC), _translate("MainWindow", "Probe Config")
        )
        self.groupBox.setTitle(_translate("MainWindow", ""))
        self.label.setText(_translate("MainWindow", "Choose Bounding Shape"))
        self.Num.setText(_translate("MainWindow", "Point Numbers"))
        self.Dim.setText(_translate("MainWindow", "Shape Dimensions"))

        self.modeBox.setItemText(0, _translate("MainWindow", "Rectangle"))
        self.modeBox.setItemText(1, _translate("MainWindow", "Circle"))
        self.modeBox.setItemText(2, _translate("MainWindow", "Line"))
        self.modeBox.setItemText(3, _translate("MainWindow", "Polygon"))
        self.modeBox.setItemText(4, _translate("MainWindow", "Ellipse"))
        self.modeBox.setItemText(5, _translate("MainWindow", "Barrier"))
        self.modeBox.setToolTip(
            _translate(
                "MainWindow",
                "RECTANGLE: Click and Drag to define a rectangular area\n\
                                           CIRCLE: Click and Drag to define a circular area\n\
                                           ELLIPSE: Click and Drag to define a rectangle in which the ellipse will be inscribed.\n\
                                           LINE: Click, Hold and Drag to define a line path\n\
                                           POLYLINE: Click and Drag to define line path. Click again to start second line. Double click to end.\n\
                                           BARRIER: Click, Hold and Drag to define a barrier for the probe.\n\
                                               ",
            )
        )

        self.gridBox.setToolTip(
            _translate(
                "MainWindow",
                "RECTANGLE: Select for Rectangular gridding\n\
                                           CIRCLE: Select for Circular (or cylindrical) gridding\n\
                                           ELLIPSE: Select for Elliptical gridding\n\
                                           SPHERE: Select for Spherical gridding",
            )
        )
        self.label_7.setText(_translate("MainWindow", "Choose Grid-Style"))
        self.gridBox.setItemText(0, _translate("MainWindow", "Rectangle"))
        self.gridBox.setItemText(1, _translate("MainWindow", "Circular"))
        self.gridBox.setItemText(2, _translate("MainWindow", "Spherical"))
        self.gridBox.setItemText(3, _translate("MainWindow", "Elliptical"))
        self.gridCentreLabel.setText(_translate("MainWindow", "Shape-Centre(s):"))
        self.gridCentre.setToolTip(
            _translate(
                "MainWindow",
                "Enter custom-center(s) in the format (x,y,z), (x1,y1,z1,) , or leave empty for default gridding (Centers of defined regions). Must specify centers for auto-shape generation.",
            )
        )

        self.generatorlabel.setText(
            _translate("MainWindow", "Auto-generate Bounding shape?")
        )

        self.gridResLabel.setText(_translate("MainWindow", "Step-Size:"))
        self.zrangelabel.setText(_translate("MainWindow", "Z-range:"))
        self.label_11.setText(_translate("MainWindow", "to:"))

        self.z1.setText(_translate("MainWindow", "1"))
        self.z2.setText(_translate("MainWindow", "1"))
        self.xreslabel.setText(_translate("MainWindow", "dx (cm)"))
        self.yreslabel.setText(_translate("MainWindow", "dy (cm)"))
        self.zreslabel.setText(_translate("MainWindow", "dz (cm)"))
        self.xres.setText(_translate("MainWindow", "2"))
        self.yres.setText(_translate("MainWindow", "2"))
        self.zres.setText(_translate("MainWindow", "2"))

        self.printButton.setText(_translate("MainWindow", "Print"))
        self.printButton.setToolTip(
            _translate("MainWindow", "Display Data Aquisition Points")
        )
        self.clearButton.setText(_translate("MainWindow", "Clear"))
        self.verifyButton.setText(_translate("MainWindow", "Verify Motion List"))
        self.verifyButton.setToolTip(
            _translate("MainWindow", "You must print positions before verifying.")
        )

        self.saveButton.setText(_translate("MainWindow", "Save"))
        self.saveButton.setToolTip(
            _translate(
                "MainWindow", "You must verify the motion list before saving it."
            )
        )

        self.EntButton.setText(_translate("MainWindow", "Enter"))
        self.EntButton.setToolTip(
            _translate(
                "MainWindow",
                "Enter endpoints of desired geometry to denote probe-area.",
            )
        )

        self.groupBox_2.setTitle(_translate("MainWindow", ""))
        self.cursorLabel.setText(_translate("MainWindow", "Cursor Coordinates:"))
        self.pointnumberLabel.setText(
            _translate("MainWindow", "Number of points defined: 0")
        )
        self.timeLabel.setText(_translate("MainWindow", "Estimated Time Required: 0s"))

        self.coordEnterLabel.setText(_translate("MainWindow", "Input \nCoordinates:"))
        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.ML),
            _translate("MainWindow", "Motion List Generator"),
        )

        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.GD),
            _translate("MainWindow", "Motion Group Configuration"),
        )
