__all__ = ["MotionGroup"]

import math
import numpy as np

from PyQt5.QtWidgets import *

from bapsf_motion.controllers.drive import DriveControl


class MotionGroup:
    def __init__(
        self,
        x_ip_addr=None,
        y_ip_addr=None,
        z_ip_addr=None,
        axes=None,
        MOTOR_PORT=None,
        d_outside=124.4,
        d_inside=64.0,
        d_offset=20.7,
        alpha=-0.9 * np.pi / 180,  # rad
        steps_per_cm=39370.0787402,
        # motion list stuff
        nx=None,
        ny=None,
        nz=None,
        xs=None,
        ys=None,
        zs=None,
        bar=None,
        close=None,
        centers=None,
        mode=None,
        grid=None,
    ):
        super().__init__()

        self.x_ip_addr = x_ip_addr
        self.y_ip_addr = y_ip_addr
        self.z_ip_addr = z_ip_addr
        self.MOTOR_PORT = MOTOR_PORT
        self.axes = axes

        self.d_outside = d_outside
        # measured dec 14, 2metre stick
        self.d_inside = d_inside  # cm distance from the ball valve to the center of the chamber (0,0) point
        self.d_offset = d_offset  # cm
        self.alpha = alpha  # rad
        # motion list stuff

        self.centers = centers
        self.mode = mode
        self.grid = grid
        self.nx = nx
        self.ny = ny
        self.nz = nz
        self.xs = xs
        self.ys = ys
        self.zs = zs
        self.bar = bar
        self.close = close
        self.create_list()
        self._validate_config()
        # connect the drives
        self.mc = DriveControl(
            x_ip_addr=self.x_ip_addr,
            y_ip_addr=self.y_ip_addr,
            z_ip_addr=self.z_ip_addr,
        )

    def _validate_config(self, mg_config=None):

        """
        Final verification routine to check no point is in a no-go
        region or an unreachable region.
        """

        if mg_config is None:
            xs = [x[0] for x in self.poslist]
            ys = [x[1] for x in self.poslist]
            barlist = self.barlist * 5
        else:
            self.centers = mg_config["Motion List"]["centers"]
            self.mode = mg_config["Motion List"]["mode"]
            self.grid = mg_config["Motion List"]["grid"]
            self.nx = mg_config["Motion List"]["dx"]
            self.ny = mg_config["Motion List"]["dy"]
            self.nz = mg_config["Motion List"]["dz"]
            self.xs = mg_config["Motion List"]["xs"]
            self.ys = mg_config["Motion List"]["ys"]
            self.zs = mg_config["Motion List"]["zs"]
            self.bar = mg_config["Motion List"]["bar"]
            self.close = mg_config["Motion List"]["close"]
            self.axes = mg_config["drive"]["axes"]

            # create coordinate list
            self.create_list()
            # now run same verification routine
            xs = [x[0] for x in self.poslist]
            ys = [x[1] for x in self.poslist]
            barlist = self.barlist * 5

        # theta is the angular position of port.
        # alpha is the angular reach of probe.
        # must map port location with theta (hand), and make some
        # formula to get alpha.
        alpha = np.pi / 4
        self.hand = 0
        if self.hand == 0:
            theta = 0.0
        else:  # self.hand == 1:
            theta = np.pi

        for i in range(0, len(xs)):
            dist = ((xs[i]) ** 2 + (ys[i]) ** 2) ** 0.5

            if dist > 250:

                # msg = QMessageBox()
                # msg.setIcon(QMessageBox.Critical)
                # msg.setText("Error")
                # msg.setInformativeText(
                #     "Some designated points are outside of the machine!"
                # )
                # msg.setWindowTitle("Error")
                # msg.exec_()

                raise ValueError("Some designated points are outside of the machine!")

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
                    # msg = QMessageBox()
                    # msg.setIcon(QMessageBox.Critical)
                    # msg.setText("Error")
                    # msg.setInformativeText(
                    #     "Some designated points are outside of reach!!"
                    # )
                    # msg.setWindowTitle("Error")
                    # msg.exec_()
                    # return
                    raise ValueError("Some designated points are outside of reach!!")

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
                    raise ValueError("Some designated points are outside of reach!!")

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
                    raise ValueError("Some designated points are outside of reach!!")

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
                    raise ValueError("Some designated points are outside of reach!!")

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

                        raise ValueError("Some designated points are in No-go zone!!")

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
                        raise ValueError("Some designated points are in No-go zone!!")

    def move_to_position(self, x, y, z=None):
        # Directly move the motor to their absolute position
        if self.axes == "X-Y":

            a = self.d_outside
            b = self.d_inside

            alpha = self.alpha
            # dy = P * L^3 / (E * 3 / 2 * pi * r^4) for load (castigliano's method)
            # P, = KL^4 / (E * 8/2 * pi * r^4) for self weight.
            # K = density * A * g
            # self-weight deflection from
            # cns.gatech.edu/~predrag/GTcourses/PHYS-4421-04/lautrup/2.8/rods.pdf [pg 166]
            #
            # r =1.9cm E = 195*10^9 Pa, density = 7970 kg/m^3
            c = np.sqrt(x**2 + y**2)
            # deflection differential from
            # cns.gatech.edu/~predrag/GTcourses/PHYS-4421-04/lautrup/2.8/rods.pdf [pg 166]
            #
            # E = 205*10^9 Pa, density = 7970 kg/m^3
            P = 0.040 * 9.81  # kg load at end
            E = 190 * (10**9)  # Pa
            r = 0.0046625  # m
            r2 = 0.00394
            density = 7990  # kg/m^3
            g = 9.81  # m/s^2
            K = density * np.pi * (r**2) * g
            I = np.pi * (r**4 - r2**4) / 2

            if x == 0:
                phi = np.pi / 2
            elif x < 0:
                phi = math.atan(y / x) + np.pi
            else:
                phi = math.atan(y / x)
            l2 = (b**2 + c**2 + 2 * b * c * math.cos(phi)) ** 0.5
            L = l2 / 100

            # dy_selfweight = 100 * K * (L**4) / (E * 8 * I) - 100 * K * (
            #     (b / 100) ** 4
            # ) / (E * 8 * I)
            # dy_weight = 100 * P * (L**3) / (
            #     E * 1.5 * np.pi * (r**4 - r2**4)
            # ) - 100 * P * ((b / 100) ** 3) / (E * 1.5 * np.pi * (r**4 - r2**4))

            if y >= 0:
                theta = math.atan(np.abs(y) / (b + x))
            else:
                theta = math.atan(np.abs(y) / (b + x))
            L = L * np.cos(theta)

            dy_total = 100 * (
                ((L**3) / (4 * E * I)) * (2 * P + K * L)
                + (L**3 / (6 * E * I)) * (-P - K * L)
                + K * (L**4) / (24 * E * I)
                - (
                    (((b / 100) ** 3) / (4 * E * I)) * (2 * P + K * ((b / 100)))
                    + ((b / 100) ** 3 / (6 * E * I)) * (-P - K * (b / 100))
                    + K * ((b / 100) ** 4) / (24 * E * I)
                )
            )

            # y-corr.
            y = y + 1 * dy_total

            if x == 0:
                phi = np.pi / 2
            elif x < 0:
                phi = math.atan(y / x) + np.pi
            else:
                phi = math.atan(y / x)
            c = np.sqrt(x**2 + y**2)
            if y >= 0:
                theta = (
                    math.atan(np.abs(y) / (b + x)) + alpha
                )  # + math.atan(0.005*(np.abs(y)**0.9)/184.4)
            else:
                theta = (
                    math.atan(np.abs(y) / (b + x)) - alpha
                )  # + math.atan(0.051*(np.abs(y)**0.8)/184.4)
            l2 = (b**2 + c**2 + 2 * b * c * math.cos(phi)) ** 0.5

            l1 = a / math.cos(theta)

            if y >= 0:
                y_new = -1 * (
                    l1 * math.sin(theta)
                    - self.d_offset * (1 / math.cos(alpha) - 1 / math.cos(theta))
                    - a * math.tan(alpha)
                )
                x_new = (
                    l1
                    + l2
                    - a / math.cos(alpha)
                    - b
                    - a * (1 / math.cos(theta) - 1 / math.cos(alpha))
                )  # + 0.7*(math.tan(theta -alpha))
            else:
                y_new = (
                    l1 * math.sin(theta)
                    + self.d_offset * (1 / math.cos(alpha) - 1 / math.cos(theta))
                    + a * math.tan(alpha)
                )
                x_new = (
                    l1
                    + l2
                    - a / math.cos(alpha)
                    - b
                    - (a) * (1 / math.cos(theta) - 1 / math.cos(alpha))
                    - 0.7 * (math.tan(theta - alpha))
                )
            self.mc.move_to_position(x_new, y_new)
        if self.axes == "X-Y-Z":
            self.mc.move_to_position(x, y, z)
        if self.axes == "X-ϴ":
            self.mc.move_to_position(x, y)

    def stop_now(self):
        # Stop motor movement now
        self.mc.stop_now()

    def zero(self):
        zeroreply = QMessageBox.question(
            self,
            "Set Zero",
            "You are about to set the current probe position to (0,0). Are you sure?",
            QMessageBox.Yes,
            QMessageBox.No,
        )
        if zeroreply == QMessageBox.Yes:
            QMessageBox.about(self, "Set Zero", "Probe position is now (0,0).")
            self.mc.set_zero()

    def ask_velocity(self):
        return self.mc.ask_velocity()

    def set_velocity(self, xv=1, yv=1, zv=1):
        self.mc.set_velocity(xv, yv, zv)

    def current_probe_position(self):

        if self.axes == "X-Y":
            return self.mc.current_probe_position2D()
        if self.axes == "X-Y-Z":
            return self.mc.current_probe_position3D()
        if self.axes == "X-ϴ":
            return self.mc.current_probe_positionZTh()

    def update_current_speed(self):
        self.speedx, self.speedy, self.speedz = self.ask_velocity()
        if self.speedx is None:
            self.speedx = "None"
        if self.speedy is None:
            self.speedy = "None"
        if self.speedz is None:
            self.speedz = "None"
        self.velocityInput.setText(f"({self.speedx}, {self.speedy}, {self.speedz})")

    def get_alarm_code(self):
        return self.mc.get_alarm_code()

    def heartbeat(self):
        return self.mc.heartbeat()

    def disconnect(self):
        return self.mc.close_connection()

    def create_list(self):

        str1 = list(zip(self.xs, self.ys, self.zs))
        str1 = str(str1).strip("[]")
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

                if self.closeit == True:
                    index = -1
                elif self.closeit == False:
                    index = 0
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
                    linval = math.floor(length / (res))

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
                pass
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
                    linval = math.floor(length / (res))

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
                pass
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
                                    positions.append(
                                        [np.round(x, 3), np.round(y, 3), np.round(z, 3)]
                                    )
                        poslist.extend(positions)
                        # print(poslist)
                    self.poslist = poslist
                except ValueError:
                    pass
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

                        linvalz = abs(math.floor((zmax - zmin) / (nz)))
                        cx = (xmax + xmin) / 2
                        cy = (ymax + ymin) / 2
                        cz = (zmax + zmin) / 2

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
                                    xpos = np.append(xpos, np.round(xval, 3))
                                    ypos = np.append(ypos, np.round(yval, 3))
                        for z in zvals:
                            zpos = np.round(z * np.ones(len(xpos)), 3)
                            positions = list(zip(xpos, ypos, zpos))
                            poslist = poslist + positions
                        self.poslist = poslist
                except ValueError:
                    pass
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
                                    xpos = np.append(xpos, np.round(xval, 3))
                                    ypos = np.append(ypos, np.round(yval, 3))
                        for z in zvals:
                            zpos = np.round(z * np.ones(len(xpos)), 3)
                            positions = list(zip(xpos, ypos, zpos))
                            poslist = poslist + positions
                    self.poslist = poslist
                except ValueError:
                    pass
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
                    pass
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
                        linvalz = abs(math.floor((zmax - zmin) / (nz)))

                        xpos = np.append(xpos, xposi)
                        ypos = np.append(ypos, yposi)
                        zvals = np.linspace(zmin, zmax, linvalz + 1)
                        r = np.sqrt((xposi - xposi2) ** 2 + (yposi - yposi2) ** 2)

                        linval = math.floor(r / (dr))

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
                    pass
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
                    pass
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

                        linval = math.floor(r / (dr))

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
                    pass
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
                    pass
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
                    pass
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
                        linvalz = abs(math.floor((zmax - zmin) / (nz)))

                        zvals = np.linspace(zmin, zmax, linvalz + 1)

                        cx = (xposi + xposi2) / 2
                        cy = (yposi + yposi2) / 2
                        cz = (zmax + zmin) / 2

                        a = np.abs(xmax - xmin) / 2
                        b = np.abs(ymax - ymin) / 2

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
                    pass
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
                        linvalz = abs(math.floor((zmax - zmin) / (nz)))

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
                    pass
