import math
import numpy as np

from PyQt5.QtWidgets import *

from .drive import DriveControl


class MotorMovement:
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
    ):
        super().__init__()

        self.x_ip_addr = x_ip_addr
        self.y_ip_addr = y_ip_addr
        self.z_ip_addr = z_ip_addr
        self.MOTOR_PORT = MOTOR_PORT
        self.axes = axes
        self.mc = DriveControl(
            x_ip_addr=self.x_ip_addr,
            y_ip_addr=self.y_ip_addr,
            z_ip_addr=self.z_ip_addr,
        )

        self.d_outside = d_outside
        # measured dec 14, 2metre stick
        self.d_inside = d_inside  # cm distance from the ball valve to the center of the chamber (0,0) point
        self.d_offset = d_offset  # cm
        self.alpha = alpha  # rad

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
        self.velocityInput.setText(
            f"({self.speedx}, {self.speedy}, {self.speedz})"
        )

    def get_alarm_code(self):
        return self.mc.get_alarm_code()

    def heartbeat(self):
        return self.mc.heartbeat()
