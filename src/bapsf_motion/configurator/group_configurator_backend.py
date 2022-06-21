__all__ = ["MotionGroup", "ProbeConfig", "ProbeDriveConfig"]

import datetime
import os
import tomli
import tomli_w

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import *


class MotionGroup:
    def getdrive(self, arg, filename=None):
        """
        Opens FileExplorer to allow loading drive config files from
        database.  Or, preexisting config file is preloaded from
        dropdown box selection, if file name is provided. Also
        populates contents of the config file into 'Drive Contents'
        textbox in gui.
        """
        check = True
        if filename is None:
            filename, check = QFileDialog.getOpenFileName(
                None,
                "QFileDialog.getOpenFileName()",
                "Probe Drives",
                "toml files (*.toml)",
            )
        self.drivefile = filename

        if check:
            with open(filename, "r") as f:
                data = f.read()
                arg.DriveContents.setText(data)

    def getprobe(self, arg, filename=None):
        """
        Opens FileExplorer to allow loading probe config files from
        database.  Or, preexisting config file is preloaded from
        dropdown box selection, if file name is provided. Also
        populates contents of the config file into 'Probe Contents'
        textbox in gui.
        """
        check = True

        if filename is None:
            filename, check = QFileDialog.getOpenFileName(
                None,
                "QFileDialog.getOpenFileName()",
                "Probes",
                "toml files (*.toml)",
            )
        self.probefile = filename

        if check:
            with open(filename, "r") as f:
                data = f.read()
                arg.ProbeContents.setText(data)

    def getAttributes(self, arg):
        """
        Saves text inputs provided by user defining meta-data
        pertaining to group.
        """
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
            QMessageBox.about(None, "Error", "Missing Information.")

    def save(self, arg):
        """Saves group config details."""
        Dict = {
            "group.id": self.id,
            "name": self.name,
            "pivot_valve_distance": self.d1,
            "valve_centre_distance": self.d2,
            "port_number": self.portnumber,
            "port_location": self.portloc,
        }
        tomli_string = tomli_w.dumps(Dict)  # Output to a string
        dirname = os.path.dirname(__file__)
        save_path = os.path.join(dirname, "Groups")
        output_file_name = str(self.name)
        completeName = os.path.join(save_path, output_file_name + ".toml")

        if os.path.exists(completeName):
            qm = QtWidgets.QMessageBox
            ret = qm.warning(
                arg.centralwidget,
                "WARNING",
                "A Motion Group with the same name already exists. "
                "Are you sure you want to overwrite it?",
                qm.Yes | qm.No,
            )
            if ret == qm.Yes:
                modifiedTime = os.path.getmtime(completeName)

                timestamp = datetime.datetime.fromtimestamp(modifiedTime).strftime(
                    "%b-%d-%Y_%H.%M.%S"
                )

                newName = save_path + "\\Backup\\" + output_file_name

                os.rename(completeName, newName + "_" + timestamp + ".toml")

                with open(completeName, "wb") as tomli_file:
                    tomli_w.dump(Dict, tomli_file)
            else:
                pass
        else:
            qm = QtWidgets.QMessageBox
            ret = qm.question(
                arg.centralwidget,
                "",
                "Are you sure you want to save this configuration?",
                qm.Yes | qm.No,
            )
            if ret == qm.Yes:
                with open(completeName, "wb") as tomli_file:
                    tomli_w.dump(Dict, tomli_file)

    def moveon(self, arg):
        """
        Combines configs of drive, probe, and group, saves the config
        file, and enables motion list generator tab.
        """

        Dict = {
            "group.id": self.id,
            "name": self.name,
            "pivot_valve_distance": self.d1,
            "valve_centre_distance": self.d2,
            "port_number": self.portnumber,
            "port_location": self.portloc,
        }

        def Merge(dict1, dict2, dict3):
            # res = {**dict1, **dict2, **dict3}
            res = dict1
            res["probe"] = dict2
            res["drive"] = dict3
            return res

        try:

            with open(self.probefile, "rb") as f:
                Dict2 = tomli.load(f)
            with open(self.drivefile, "rb") as f:
                Dict3 = tomli.load(f)
            Dict = Merge(Dict, Dict2, Dict3)
        except AttributeError:
            QMessageBox.about(None, "Error", "Please Choose associated configurations.")
        if Dict["port_number"] == "0":
            self.hand = 0
        elif Dict["port_number"] == "1":
            self.hand = 1
        arg.canvas.set_hand(self.hand)
        arg.canvas.set_name(self.name)
        tomli_string = tomli_w.dumps(Dict)  # Output to a string
        dirname = os.path.dirname(__file__)
        save_path = os.path.join(dirname, "Groups")
        output_file_name = str(self.name)
        completeName = os.path.join(save_path, f"{output_file_name}.toml")
        qm = QtWidgets.QMessageBox
        ret = qm.question(
            arg.centralwidget, "", "Are you sure you want to proceed?", qm.Yes | qm.No
        )

        if ret == qm.Yes:
            with open(completeName, "wb") as tomli_file:
                tomli_w.dump(Dict, tomli_file)
            arg.tabWidget.setCurrentIndex(3)
            arg.tabWidget.setTabEnabled(0, False)
            arg.tabWidget.setTabEnabled(1, False)
            arg.tabWidget.setTabEnabled(2, False)
            arg.tabWidget.setTabEnabled(3, True)


class ProbeConfig:
    def getAttributes(self, arg):
        """
        Saves text inputs provided by user defining meta-data
        pertaining to probe.
        """
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

    def probeBoxSetter(self, arg):
        """
        Parameters
        ----------
        arg : main gui window
            Necessary as this function updates the gui to display
            the parameters of the probe chosen from drop-down.
        """
        # TODO:- create list of standard probes, with their properties
        # being listed here, just like pdBoxSetter
        index = arg.probeDriveBox.currentIndex()
        if index is None:
            pass
        elif index == 0:
            pass
        elif index == 1:
            arg.group.getprobe(
                arg,
                "Probes\\Langmuir.toml",
            )

    def save(self, arg):
        """Save defined config file to database.
        Saves a timestamped backup in case filename is overwritten
        """
        Dict = {
            "id": self.id,
            "name": self.name,
            "made": self.datefabricated,
            "serviced": self.dateserviced,
            "type": self.type,
            "units": self.units,
            "diameter": self.diameter,
            "thickness": self.thickness,
            "length": self.length,
            "material": self.material,
        }
        tomli_string = tomli_w.dumps(Dict)  # Output to a string
        dirname = os.path.dirname(__file__)
        save_path = os.path.join(dirname, "Probes")
        output_file_name = str(self.name)
        completeName = os.path.join(save_path, output_file_name + ".toml")
        if os.path.exists(completeName):
            qm = QtWidgets.QMessageBox
            ret = qm.warning(
                arg.centralwidget,
                "WARNING",
                "A Probe configuration with the same name already exists."
                " Are you sure you want to overwrite it?",
                qm.Yes | qm.No,
            )
            if ret == qm.Yes:
                modifiedTime = os.path.getmtime(completeName)

                timestamp = datetime.datetime.fromtimestamp(modifiedTime).strftime(
                    "%b-%d-%Y_%H.%M.%S"
                )

                newName = save_path + "\\Backup\\" + output_file_name
                os.rename(completeName, newName + "_" + timestamp + ".toml")
                with open(completeName, "wb") as tomli_file:
                    tomli_w.dump(Dict, tomli_file)
            else:
                pass
        else:
            qm = QtWidgets.QMessageBox
            ret = qm.question(
                arg.centralwidget,
                "",
                "Are you sure you want to save this configuration?",
                qm.Yes | qm.No,
            )
            if ret == qm.Yes:
                with open(completeName, "wb") as tomli_file:
                    tomli_w.dump(Dict, tomli_file)


class ProbeDriveConfig:
    def IPBoxsetter(self, arg):
        """Disables third motor ip address input for < 3 axes drives"""
        index = arg.AxesBox.currentIndex()
        if index is None:
            pass
        if index == 0:

            arg.ipz.setEnabled(False)
            arg.ymotorLabel.setText("Y-motor")
        if index == 1:
            arg.ipz.setEnabled(True)
            arg.ymotorLabel.setText("Y-motor")
        if index == 2:
            arg.ipz.setEnabled(False)
            arg.ymotorLabel.setText("ϴ-motor")

    def getAttributes(self, arg):
        """
        Saves text inputs provided by user defining meta-data
        pertaining to probe drive.
        """

        self.name = arg.templatename.text()
        self.id = self.name.replace(" ", "_").lower()
        self.axes = arg.AxesBox.currentText()
        self.IPx = arg.ipx.text()
        self.IPy = arg.ipy.text()
        self.IPz = arg.ipz.text()
        self.Countperstep = float(arg.countStep.text())
        self.Stepperrev = float(arg.stepRev.text())
        self.Threading = float(arg.customThreading.text())
        self.save(arg)

    def TPIsetter(self, arg):
        """
        Updates threading parameter as per the threading chosen from
        drop down box.

        Parameters
        ----------
        arg : gui main window
        """
        index = arg.TPIBox.currentIndex()
        if index == 0:
            arg.customThreading.setText("0.0508")
        elif index == 1:
            arg.customThreading.setText("0.254")
        elif index == 2:
            arg.customThreading.setText("0.508")
        elif index == 3:
            arg.customThreading.setText("0.02")

    def pdBoxsetter(self, arg):
        """
        Preset probe drive configurations are saved here. This function
        automatically fills out the configuration details as per the
        presets.
        """
        index = arg.probeDriveBox.currentIndex()
        if index is None or index == 0:
            pass
        elif index == 1:
            arg.templatename.setText("Standard XY")
            arg.AxesBox.setCurrentIndex(0)
            arg.ipx.setText("2")
            arg.ipy.setText("1")
            arg.ipz.setText("1")
            arg.countStep.setText("5")
            arg.stepRev.setText("1")
            arg.TPIBox.setCurrentIndex(1)  # in order to trigger threading label update
            arg.TPIBox.setCurrentIndex(0)
            arg.group.getdrive(
                arg,
                "Probe Drives\\Standard XY.toml",
            )

        elif index == 2:
            arg.templatename.setText("Standard XYZ")
            arg.AxesBox.setCurrentIndex(1)
            arg.ipx.setText("2")
            arg.ipy.setText("1")
            arg.ipz.setText("1")
            arg.countStep.setText("5")
            arg.stepRev.setText("1")
            arg.TPIBox.setCurrentIndex(1)  # in order to trigger threading label update
            arg.TPIBox.setCurrentIndex(0)
            arg.group.getdrive(
                arg,
                "Probe Drives\\Standard XYZ.toml",
            )

        elif index == 3:
            arg.templatename.setText("Standard X-ϴ")
            arg.AxesBox.setCurrentIndex(2)
            arg.ipx.setText("2")
            arg.ipy.setText("1")
            arg.ipz.setText("1")
            arg.countStep.setText("5")
            arg.stepRev.setText("1")
            arg.TPIBox.setCurrentIndex(1)  # in order to trigger threading label update
            arg.TPIBox.setCurrentIndex(0)
            arg.group.getdrive(
                arg,
                "Probe Drives\\Standard X-ϴ.toml",
            )

    def getStepCm(self, arg):
        """
        Uses defined parameters of threading, step per rev, etc. to
        calculate and update the steps per cm value of configuration.
        """
        try:
            StepPerRev = float(arg.stepRev.text())
            CmPerRev = float(arg.customThreading.text())
            StepPerCm = StepPerRev / CmPerRev
            arg.StepPerCmLabel.setText(f"Calculated Steps/cm : {StepPerCm}")
        except ValueError:
            pass

    def save(self, arg):
        """
        Save defined config file to database.  Saves a timestamped
        backup in case filename is overwritten.
        """
        Dict = {
            "id": self.id,
            "name": self.name,
            "axes": self.axes,
            "IPx": self.IPx,
            "IPy": self.IPy,
            "IPz": self.IPz,
            "count_per_step": self.Countperstep,
            "step_per_rev": self.Stepperrev,
            "threading": self.Threading,
        }

        tomli_string = tomli_w.dumps(Dict)  # Output to a string
        dirname = os.path.dirname(__file__)
        save_path = os.path.join(dirname, "Probe Drives")
        output_file_name = str(self.name)
        completeName = os.path.join(save_path, output_file_name + ".toml")
        if os.path.exists(completeName):
            qm = QtWidgets.QMessageBox
            ret = qm.warning(
                arg.centralwidget,
                "WARNING",
                "A Probe Drive configuration with the same name already exists."
                " Are you sure you want to overwrite it?",
                qm.Yes | qm.No,
            )
            if ret == qm.Yes:

                modifiedTime = os.path.getmtime(completeName)

                timestamp = datetime.datetime.fromtimestamp(modifiedTime).strftime(
                    "%b-%d-%Y_%H.%M.%S"
                )

                newName = f"{save_path}\\Backup\\{output_file_name}"

                os.rename(completeName, f"{newName}_{timestamp}.toml")

                with open(completeName, "wb") as tomli_file:
                    tomli_w.dump(Dict, tomli_file)
            else:
                pass
        else:
            qm = QtWidgets.QMessageBox
            ret = qm.question(
                arg.centralwidget,
                "",
                "Are you sure you want to save this configuration?",
                qm.Yes | qm.No,
            )
            if ret == qm.Yes:
                with open(completeName, "wb") as tomli_file:
                    tomli_w.dump(Dict, tomli_file)
            else:
                pass
