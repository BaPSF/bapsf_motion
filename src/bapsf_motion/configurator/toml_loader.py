__all__ = ["Loader"]

import math
import numpy as np
import tomli

from PyQt5.QtWidgets import *

from bapsf_motion.controllers.motion_group import MotionGroup


class Loader:
    def getgroup(self, arg, arg2, index, filename=None):

        if filename is None:
            filename, check = QFileDialog.getOpenFileName(
                None,
                "QFileDialog.getOpenFileName()",
                "configurator\\Groups",
                "toml files (*.toml)",
            )
            self.drivefile = filename
            if check:

                with open(filename, "r") as f:
                    data = f.read()
                    arg.GroupText.setText(data)

                with open(filename, "rb") as f:
                    self.toml_dict = tomli.load(f)
                    self.x_ip = self.toml_dict["drive"]["IPx"]
                    self.y_ip = self.toml_dict["drive"]["IPy"]
                    self.z_ip = self.toml_dict["drive"]["IPz"]
                    self.centers = self.toml_dict["Motion List"]["centers"]
                    self.mode = self.toml_dict["Motion List"]["mode"]
                    self.grid = self.toml_dict["Motion List"]["grid"]
                    self.nx = self.toml_dict["Motion List"]["dx"]
                    self.ny = self.toml_dict["Motion List"]["dy"]
                    self.nz = self.toml_dict["Motion List"]["dz"]
                    self.xs = self.toml_dict["Motion List"]["xs"]
                    self.ys = self.toml_dict["Motion List"]["ys"]
                    self.zs = self.toml_dict["Motion List"]["zs"]
                    self.bar = self.toml_dict["Motion List"]["bar"]
                    self.close = self.toml_dict["Motion List"]["close"]
                    self.axes = self.toml_dict["drive"]["axes"]
                    self.string1 = list(zip(self.xs, self.ys, self.zs))
                    self.string1 = str(self.string1).strip("[]")

        if self.axes != "X-Y-Z":
            arg2.groups[index].z.setEnabled(False)
            arg2.tabs[index].zcoord.setEnabled(False)
            arg2.tabs[index].zspeed.setEnabled(False)
        arg2.tabWidget.setTabText(
            index,
            f"{self.toml_dict['port_number']}-{self.toml_dict['port_location']}",
        )
        arg2.groups[index].GroupName.setText(
            f"{self.toml_dict['port_number']}-{self.toml_dict['port_location']}"
        )
        self.create_list(arg)
        self.update_list(arg2, index)

        StepPerRev = self.toml_dict["drive"]["step_per_rev"]
        CmPerRev = self.toml_dict["drive"]["threading"]
        self.steps_per_cm = StepPerRev / CmPerRev

        self.ConnectMotor(arg2)

    # set tab name to port location

    def update_list(self, arg, index):
        for coordinate in self.poslist:
            arg.groups[index].list.insertItem(0, str(coordinate))

    def ConnectMotor(self, arg2):
        self.port_ip = int(7776)
        self.mm = MotionGroup(
            x_ip_addr=self.x_ip,
            y_ip_addr=self.y_ip,
            z_ip_addr=self.z_ip,
            axes=self.axes,
            MOTOR_PORT=self.port_ip,
            d_outside=self.toml_dict["pivot_valve_distance"],
            d_inside=self.toml_dict["valve_centre_distance"],
            steps_per_cm=self.steps_per_cm,
        )
        arg2.ConnectMotor()

    def create_list(self, arg):

        str1 = self.string1
        str1 = np.array(
            str1.replace("(", "").replace(")", "").split(","), dtype=float
        ).reshape(-1, 3)

        if self.mode == "polyline":

            try:

                xs = [x[0] for x in str1]
                ys = [x[1] for x in str1]
                zs = [x[2] for x in str1]
                xpos = [xs[0]]
                ypos = [ys[0]]
                zpos = [zs[0]]

                index = -1 if self.closeit else 0
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
                        xpos = np.append(xpos, np.round(xval, 3))
                        ypos = np.append(ypos, np.round(yval, 3))
                        zpos = np.append(zpos, np.round(zval, 3))
                positions = list(zip(xpos, ypos, zpos))
                self.poslist = positions
            except ValueError:
                QMessageBox.about(self, "Error", "Position should be valid numbers.")
        elif self.mode == "line":

            try:

                xs = [x[0] for x in str1]
                ys = [x[1] for x in str1]
                zs = [x[2] for x in str1]
                xpos = [xs[0]]
                ypos = [ys[0]]
                zpos = [zs[0]]

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
                        xpos = np.append(xpos, np.round(xval, 3))
                        ypos = np.append(ypos, np.round(yval, 3))
                        zpos = np.append(zpos, np.round(zval, 3))
                positions = list(zip(xpos, ypos, zpos))
                self.poslist = positions
            except ValueError:
                QMessageBox.about(self, "Error", "Position should be valid numbers.")

        elif self.mode == "rect":

            if self.grid == "rect":

                try:

                    xs = [x[0] for x in str1]
                    ys = [x[1] for x in str1]
                    zs = [x[2] for x in str1]

                    poslist = []
                    for i in range(0, len(xs) - 1, 2):
                        nx = self.nx[i // 2]
                        ny = self.ny[i // 2]
                        nz = self.nz[i // 2]
                        xmax = xs[i + 1]
                        xmin = xs[i]
                        ymax = ys[i + 1]
                        ymin = ys[i]
                        zmax = zs[i + 1]
                        zmin = zs[i]
                        cx = (xmax + xmin) / 2
                        cy = (ymax + ymin) / 2
                        cz = (zmax + zmin) / 2
                        linvalz = abs(math.floor((zmax - zmin) / nz))
                        linvalx = abs(math.floor((xmax - xmin) / nx))
                        linvaly = abs(math.floor((ymax - ymin) / ny))
                        zvals = np.linspace(zmin, zmax, linvalz + 1)
                        xvals = np.linspace(xmin, xmax, linvalx + 1)
                        yvals = np.linspace(ymin, ymax, linvaly + 1)

                        positions = []
                        for z in zvals:
                            for x in xvals:
                                for y in yvals:
                                    positions.append(
                                        [np.round(x, 3), np.round(y, 3), np.round(z, 3)]
                                    )
                        poslist.extend(positions)
                        # print(poslist)
                    self.poslist = poslist
                except ValueError:
                    QMessageBox.about(
                        self, "Error", "Position should be valid numbers."
                    )
            if self.grid == "circle":

                try:

                    xs = [x[0] for x in str1]
                    ys = [x[1] for x in str1]
                    zs = [x[2] for x in str1]

                    xpos = []
                    ypos = []
                    poslist = []
                    for i in range(0, len(xs) - 1, 2):
                        dr = self.nx[i // 2]
                        dtheta = self.ny[i // 2]
                        nz = self.nz[i // 2]
                        xmax = max([xs[i + 1], xs[i]])
                        xmin = min([xs[i + 1], xs[i]])
                        ymax = max([ys[i + 1], ys[i]])
                        ymin = min([ys[i + 1], ys[i]])
                        zmax = max([zs[i + 1], zs[i]])
                        zmin = min([zs[i + 1], zs[i]])

                        linvalz = abs(math.floor((zmax - zmin) / nz))
                        cx = (xmax + xmin) / 2
                        cy = (ymax + ymin) / 2
                        cz = (zmax + zmin) / 2

                        zvals = np.linspace(zmin, zmax, linvalz + 1)

                        r = 0.5 * (np.sqrt((xmax - xmin) ** 2 + (ymax - ymin) ** 2))

                        linval = math.floor(r / dr)

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
                                    xpos = np.append(xpos, np.round(xval, 3))
                                    ypos = np.append(ypos, np.round(yval, 3))
                        for z in zvals:
                            zpos = np.round(z * np.ones(len(xpos)), 3)
                            positions = list(zip(xpos, ypos, zpos))
                            poslist = poslist + positions
                        self.poslist = poslist
                except ValueError:
                    QMessageBox.about(
                        self, "Error", "Position should be valid numbers."
                    )
            if self.grid == "ellipse":

                try:

                    xs = [x[0] for x in str1]
                    ys = [x[1] for x in str1]
                    zs = [x[2] for x in str1]

                    e = self.eccentricity
                    xpos = []
                    ypos = []
                    poslist = []
                    for i in range(0, len(self.xpos) - 1, 2):
                        dr = self.nx[i // 2]
                        dtheta = self.ny[i // 2]
                        dz = self.nz[i // 2]
                        xmax = max([xs[i + 1], xs[i]])
                        xmin = min([xs[i + 1], xs[i]])
                        ymax = max([ys[i + 1], ys[i]])
                        ymin = min([ys[i + 1], ys[i]])
                        zmax = max([zs[i + 1], zs[i]])
                        zmin = min([zs[i + 1], zs[i]])

                        cx = (xmax + xmin) / 2
                        cy = (ymax + ymin) / 2
                        cz = (zmax + zmin) / 2

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
                                if (
                                    (xval > xmax)
                                    or xval < xmin
                                    or yval > ymax
                                    or yval < ymin
                                ):
                                    pass
                                else:
                                    xpos = np.append(xpos, np.round(xval, 3))
                                    ypos = np.append(ypos, np.round(yval, 3))
                        for z in zvals:
                            zpos = np.round(z * np.ones(len(xpos)), 3)
                            positions = list(zip(xpos, ypos, zpos))
                            poslist = poslist + positions
                    self.poslist = poslist
                except ValueError:
                    QMessageBox.about(
                        self, "Error", "Position should be valid numbers."
                    )
            if self.grid == "sphere":

                try:

                    xs = [x[0] for x in str1]
                    ys = [x[1] for x in str1]
                    zs = [x[2] for x in str1]

                    poslist = []
                    for i in range(0, len(xs) - 1, 2):
                        dr = self.nx[i // 2]
                        dtheta = self.ny[i // 2]
                        dphi = self.nz[i // 2]

                        xmax = max([xs[i + 1], xs[i]])
                        xmin = min([xs[i + 1], xs[i]])
                        ymax = max([ys[i + 1], ys[i]])
                        ymin = min([ys[i + 1], ys[i]])
                        zmax = max([zs[i + 1], zs[i]])
                        zmin = min([zs[i + 1], zs[i]])

                        # NEED TO RECALCULATE POINT GENERATING PARAMETERS TO GET
                        # APPROPRIATE ONES WITHIN THE REGION.
                        cx = (xmax + xmin) / 2
                        cy = (ymax + ymin) / 2
                        cz = (zmax + zmin) / 2
                        r = np.sqrt(
                            (xmax - xmin) ** 2 + (ymax - ymin) ** 2 + (zmax - zmin) ** 2
                        )

                        linval = math.floor(r / dr)

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
                                        positions.append(
                                            [
                                                np.round(xval, 3),
                                                np.round(yval, 3),
                                                np.round(zval, 3),
                                            ]
                                        )
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

                    xs = [x[0] for x in str1]
                    ys = [x[1] for x in str1]
                    zs = [x[2] for x in str1]

                    poslist = []

                    for i in range(0, len(xs) - 1, 2):
                        dr = self.nx[i // 2]
                        dtheta = self.ny[i // 2]
                        nz = self.nz[i // 2]

                        xpos = []
                        ypos = []
                        xposi = xs[i]
                        xposi2 = xs[i + 1]

                        yposi = ys[i]
                        yposi2 = ys[i + 1]

                        zmax = zs[i + 1]
                        zmin = zs[i]
                        linvalz = abs(math.floor((zmax - zmin) / nz))

                        xpos = np.append(xpos, xposi)
                        ypos = np.append(ypos, yposi)
                        zvals = np.linspace(zmin, zmax, linvalz + 1)
                        r = np.sqrt((xposi - xposi2) ** 2 + (yposi - yposi2) ** 2)

                        linval = math.floor(r / dr)

                        thetavals = np.linspace(0, 1, math.floor(360 / dtheta) + 1)
                        parvals = np.linspace(0, 1, linval + 1)

                        for t in parvals[1:]:
                            for th in thetavals[1:]:
                                xval = xposi + t * r * np.cos(th * 2 * np.pi)
                                yval = yposi + t * r * np.sin(th * 2 * np.pi)

                                xpos = np.append(xpos, np.round(xval, 3))
                                ypos = np.append(ypos, np.round(yval, 3))
                        for z in zvals:
                            zpos = np.round(z * np.ones(len(xpos)), 3)
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

                    xs = [x[0] for x in str1]
                    ys = [x[1] for x in str1]
                    zs = [x[2] for x in str1]

                    poslist = []
                    xpos = []
                    ypos = []
                    zpos = []

                    for i in range(0, len(xs) - 1, 2):
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

                        r = np.sqrt((xposi - xposi2) ** 2 + (yposi - yposi2) ** 2)
                        xmax = cx + r
                        xmin = cx - r
                        ymax = cy + r
                        ymin = cy - r

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
                                        positions.append(
                                            [
                                                np.round(xvals[x], 3),
                                                np.round(yvals[y], 3),
                                                np.round(zvals[z], 3),
                                            ]
                                        )
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

                    xs = [x[0] for x in str1]
                    ys = [x[1] for x in str1]
                    zs = [x[2] for x in str1]

                    poslist = []

                    for i in range(0, len(xs) - 1, 2):
                        dr = self.nx[i // 2]
                        dtheta = self.ny[i // 2]
                        dphi = self.nz[i // 2]
                        xposi = xs[i]
                        xposi2 = xs[i + 1]

                        yposi = ys[i]
                        yposi2 = ys[i + 1]

                        zmax = zs[i + 1]
                        zmin = zs[i]
                        cx = xposi
                        cy = yposi
                        cz = (zmax + zmin) / 2

                        rc = np.sqrt((xposi - xposi2) ** 2 + (yposi - yposi2) ** 2)
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
                            # Other start points are incorporated as the end
                            # points of previous segment.
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
                                    positions.append(
                                        [
                                            np.round(xval, 3),
                                            np.round(yval, 3),
                                            np.round(zval, 3),
                                        ]
                                    )
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

                    xs = [x[0] for x in str1]
                    ys = [x[1] for x in str1]
                    zs = [x[2] for x in str1]

                    e = self.eccentricity
                    poslist = []
                    xpos = []
                    ypos = []
                    for i in range(0, len(xs) - 1, 2):
                        dr = self.nx[i // 2]
                        dtheta = self.ny[i // 2]
                        dz = self.nz[i // 2]
                        xposi = xs[i]
                        xposi2 = xs[i + 1]

                        yposi = ys[i]
                        yposi2 = ys[i + 1]

                        zmax = zs[i + 1]
                        zmin = zs[i]
                        linvalz = abs(math.floor((zmax - zmin) / (dz)))

                        zvals = np.linspace(zmin, zmax, linvalz + 1)
                        b = np.sqrt((xposi - xposi2) ** 2 + (yposi - yposi2) ** 2)
                        a = b / np.sqrt(1 - e**2)
                        # zposi = zs[i]
                        # zposi2 =zs[i+1]

                        cx = xposi
                        cy = yposi
                        cz = (zmax + zmin) / 2
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
                                    xpos = np.append(xpos, np.round(xval, 3))
                                    ypos = np.append(ypos, np.round(yval, 3))
                        for z in zvals:
                            zpos = np.round(z * np.ones(len(xpos)), 3)
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

                    xs = [x[0] for x in str1]
                    ys = [x[1] for x in str1]
                    zs = [x[2] for x in str1]

                    poslist = []

                    for i in range(0, len(xs) - 1, 2):
                        dr = self.nx[i // 2]
                        dtheta = self.ny[i // 2]
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

                        linval = math.floor((min([a, b])) / (dr))

                        thetavals = np.linspace(0, 1, math.floor(360 / dtheta) + 1)
                        parvals = np.linspace(0, 1, linval + 1)

                        for t in parvals[1:]:
                            for z in thetavals[1:]:
                                xval = cx + t * a * np.cos(z * 2 * np.pi)
                                yval = cy + t * b * np.sin(z * 2 * np.pi)
                                xpos = np.append(xpos, np.round(xval, 3))
                                ypos = np.append(ypos, np.round(yval, 3))
                        for z in zvals:
                            zpos = np.round(z * np.ones(len(xpos)), 3)
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

                    xs = [x[0] for x in str1]
                    ys = [x[1] for x in str1]
                    zs = [x[2] for x in str1]

                    poslist = []

                    for i in range(0, len(xs) - 1, 2):
                        nx = self.nx[i // 2]
                        ny = self.ny[i // 2]
                        nz = self.nz[i // 2]
                        xmax = xs[i + 1]
                        xmin = xs[i]
                        ymax = ys[i + 1]
                        ymin = ys[i]
                        zmax = zs[i + 1]
                        zmin = zs[i]
                        linvalz = abs(math.floor((zmax - zmin) / nz))

                        zvals = np.linspace(zmin, zmax, linvalz + 1)

                        cx = (xposi + xposi2) / 2
                        cy = (yposi + yposi2) / 2
                        cz = (zmax + zmin) / 2

                        a = np.abs(xmax - xmin) / 2
                        b = np.abs(ymax - ymin) / 2

                        linvalx = abs(math.floor((xmax - xmin) / nx))
                        linvaly = abs(math.floor((ymax - ymin) / ny))
                        xpos = np.linspace(xmin, xmax, linvalx + 1)
                        ypos = np.linspace(ymin, ymax, linvaly + 1)
                        positions = []
                        for z in range(0, len(zvals)):
                            for x in range(0, len(xpos)):
                                for y in range(0, len(ypos)):
                                    if ((xpos[x] - cx) / a) ** 2 + (
                                        (ypos[y] - cy) / b
                                    ) ** 2 <= 1:
                                        positions.append(
                                            [
                                                np.round(xpos[x], 3),
                                                np.round(ypos[y], 3),
                                                np.round(zvals[z], 3),
                                            ]
                                        )
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

                    xs = [x[0] for x in str1]
                    ys = [x[1] for x in str1]
                    zs = [x[2] for x in str1]

                    poslist = []

                    for i in range(0, len(xs) - 1, 2):

                        nx = self.nx[i // 2]
                        ny = self.ny[i // 2]
                        nz = self.nz[i // 2]
                        xmax = xs[i + 1]
                        xmin = xs[i]
                        ymax = ys[i + 1]
                        ymin = ys[i]
                        zmax = zs[i + 1]
                        zmin = zs[i]
                        linvalz = abs(math.floor((zmax - zmin) / nz))

                        zvals = np.linspace(zmin, zmax, linvalz + 1)

                        cx = (xposi + xposi2) / 2
                        cy = (yposi + yposi2) / 2
                        cz = (zmax + zmin) / 2

                        a = np.abs(xmax - xmin) / 2
                        b = np.abs(ymax - ymin) / 2
                        r = np.sqrt((xposi2 - xposi) ** 2 + (yposi - yposi2) ** 2) * 0.5

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
                                    xpos = np.append(np.round(xpos, 3), xval)
                                    ypos = np.append(np.round(ypos, 3), yval)
                    for z in range(0, len(zvals)):
                        zpos = np.round(z * np.ones(len(xpos)), 3)
                        positions = list(zip(xpos, ypos, zpos))
                        poslist = poslist + positions
                    self.poslist = poslist
                except ValueError:
                    QMessageBox.about(
                        self, "Error", "Position should be valid numbers."
                    )
        arg.canvas.update_graph(
            self.poslist, self.nx, self.ny, self.nz, self.bar, self.mode
        )
