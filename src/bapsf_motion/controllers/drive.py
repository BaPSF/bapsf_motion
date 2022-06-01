"""
DriveControl controls upto 3 motors (x , y , z), using Motor.py

Modified by: Yuchen Qian
Oct 2017
Modified by: Rishabh Singh
Nov 2021
"""
__all__ = ["DriveControl"]

import numpy as np
import time

from scipy.optimize import fsolve

from bapsf_motion.controllers.motor import MotorControl


class DriveControl:
    def __init__(
        self, x_ip_addr=None, y_ip_addr=None, z_ip_addr=None, steps_per_cm=39370.0787402
    ):

        self.x_mc = None
        self.y_mc = None
        self.z_mc = None
        if x_ip_addr is not None:
            self.x_mc = MotorControl(verbose=True, server_ip_addr=x_ip_addr)

            self.x_mc.send_text("MT")
        if y_ip_addr is not None:
            self.y_mc = MotorControl(verbose=True, server_ip_addr=y_ip_addr)

            self.y_mc.send_text("MT")
        if z_ip_addr is not None:
            self.z_mc = MotorControl(verbose=True, server_ip_addr=y_ip_addr)

            self.z_mc.send_text("MT")
        self.steps_per_cm = steps_per_cm

        self.motor_moving = False

    def move_to_position(self, x, y=None, z=None):
        """Coordinate transformation for 3 axes"""
        # Directly move the motor to their absolute position

        x_step = self.cm_to_steps(x)
        if y is not None:
            y_step = self.cm_to_steps(y)
        if z is not None:
            z_step = self.cm_to_steps(z)

        if self.x_mc is not None:
            self.x_mc.set_position(x_step)
        if self.y_mc is not None:
            self.y_mc.set_position(y_step)
        if self.z_mc is not None:
            self.z_mc.set_position(z_step)

        self.motor_moving = True
        # self.wait_for_motion_complete()

    def stop_now(self):
        # Stop motor movement now
        if self.x_mc is not None:
            self.x_mc.stop_now()
        if self.y_mc is not None:
            self.y_mc.stop_now()
        if self.z_mc is not None:
            self.z_mc.stop_now()

    def set_zero(self):
        if self.x_mc is not None:
            self.x_mc.set_zero()
        if self.y_mc is not None:
            self.y_mc.set_zero()
        if self.z_mc is not None:
            self.z_mc.set_zero()

    def reset_motor(self):
        if self.x_mc is not None:
            self.x_mc.reset_motor()
        if self.y_mc is not None:
            self.y_mc.reset_motor()
        if self.z_mc is not None:
            self.z_mc.reset_motor()

    def ask_velocity(self):
        self.speedx = None
        self.speedy = None
        self.speedz = None

        if self.x_mc is not None:
            self.speedx = self.x_mc.motor_velocity()
        if self.y_mc is not None:
            self.speedy = self.y_mc.motor_velocity()
        if self.z_mc is not None:
            self.speedz = self.z_mc.motor_velocity()
        return self.speedx, self.speedy, self.speedz

    def set_velocity(self, vx=1, vy=1, vz=1):
        if self.x_mc is not None:
            self.x_mc.set_speed(vx)
        if self.y_mc is not None:
            self.y_mc.set_speed(vy)
        if self.z_mc is not None:
            self.z_mc.set_speed(vz)

    def cm_to_steps(self, d: float) -> int:
        # convert distance d in cm to motor position
        return int(d * self.steps_per_cm)

    def degree_to_steps(
        self, d: float
    ) -> int:  # This feature applies to Z-Th probe drive
        # convert angle d in degree to motor position
        return int(d * self.steps_per_degree)

    def current_probe_position2D(self):
        """Might need a encoder_unit_per_step, if encoder feedback != input step"""
        # Obtain encoder feedback and calculate probe position
        timeout = time.time() + 300
        x_stat = self.x_mc.check_status()
        y_stat = self.y_mc.check_status()
        # time.sleep(0.2)

        x_not_moving = x_stat.find("M") == -1
        y_not_moving = y_stat.find("M") == -1

        #                print ('x:', x_stat)
        #                print ('y:', y_stat)
        #                print ('z:', z_stat)
        #                print (x_not_moving, y_not_moving, z_not_moving)

        if x_not_moving and y_not_moving:
            self.motor_moving = False
        elif time.time() > timeout:
            raise TimeoutError("Motor has been moving for over 5min???")

        mx_pos = self.x_mc.current_position() / self.steps_per_cm * 5
        my_pos = (
            self.y_mc.current_position() / self.steps_per_cm * 5
        )  # Seems that 1 encoder unit = 5 motor step unit
        a = self.d_outside
        b = self.d_inside

        if my_pos < 0:
            C = (
                np.abs(my_pos)
                - a * np.tan(self.alpha)
                - self.d_offset / np.cos(self.alpha)
            )

            def func(x):
                return a * np.tan(x) + self.d_offset / np.cos(x) - 50

            theta = fsolve(func, 0)
            x = (b + mx_pos) * np.cos(theta)
            y = (b + mx_pos) * np.sin(theta)

            return mx_pos, my_pos
        else:
            C = (
                np.abs(my_pos)
                + a * np.tan(self.alpha)
                + self.d_offset / np.cos(self.alpha)
            )

            def func(x):
                return a * np.tan(x) - self.d_offset / np.cos(x) - 50

            theta = fsolve(func, 0)
            x = (b + mx_pos) * np.cos(theta)
            y = (b + mx_pos) * np.sin(theta)

            return mx_pos, my_pos

    def current_probe_position1D(self):
        # Obtain encoder feedback and calculate probe position
        """Might need a encoder_unit_per_step, if encoder feedback != input step"""
        mx_pos = self.x_mc.current_position() / self.steps_per_cm * 5
        # my_pos = self.y_mc.current_position() / self.steps_per_cm * 5  # Seems that 1 encoder unit = 5 motor step unit

        return mx_pos

    def current_probe_position3D(self):
        pass

    def current_probe_positionZTh(self):
        pass

    def get_alarm_code(self):
        if self.x_mc is not None:
            alarmx = self.x_mc.get_alarm_code()
        else:
            alarmx = None

        if self.y_mc is not None:
            alarmy = self.y_mc.get_alarm_code()
        else:
            alarmy = None

        if self.z_mc is not None:
            alarmz = self.z_mc.get_alarm_code()
        else:
            alarmz = None

        return alarmx, alarmy, alarmz

    def set_jog_speed(self, vx=None, vy=None, vz=None):
        if self.x_mc is not None:
            self.x_mc.set_jog_velocity(vx)
        if self.y_mc is not None:
            self.y_mc.set_jog_velocity(vy)
        if self.z_mc is not None:
            self.z_mc.set_jog_velocity(vz)

    def set_jog_acceleration(self, ax=None, ay=None, az=None):
        if self.x_mc is not None:
            self.x_mc.set_jog_acceleration(ax)
        if self.y_mc is not None:
            self.y_mc.set_jog_acceleration(ay)
        if self.z_mc is not None:
            self.z_mc.set_jog_acceleration(az)

    def initiate_jog(self):
        if self.x_mc is not None:
            self.x_mc.commence_jogging()
        if self.y_mc is not None:
            self.y_mc.commence_jogging()
        if self.z_mc is not None:
            self.z_mc.commence_jogging()

    def stop_jog(self):
        if self.x_mc is not None:
            self.x_mc.stop_jogging()
        if self.y_mc is not None:
            self.y_mc.stop_jogging()
        if self.z_mc is not None:
            self.z_mc.stop_jogging()

    def disable(self):
        if self.x_mc is not None:
            self.x_mc.inhibit()
        if self.y_mc is not None:
            self.y_mc.inhibit()
        if self.z_mc is not None:
            self.z_mc.inhibit()

    def enable(self):
        if self.x_mc is not None:
            self.x_mc.enable()
        if self.y_mc is not None:
            self.y_mc.enable()
        if self.z_mc is not None:
            self.z_mc.enable()

    def set_input_usage(self, usage):
        if self.x_mc is not None:
            self.x_mc.set_input_usage(usage)
        if self.y_mc is not None:
            self.y_mc.set_input_usage(usage)
        if self.z_mc is not None:
            self.z_mc.set_input_usage(usage)

    def close_connection(self):
        if self.x_mc is not None:
            self.x_mc.close_connection()
        if self.y_mc is not None:
            self.y_mc.close_connection()
        if self.z_mc is not None:
            self.z_mc.close_connection()

    def heartbeat(self):
        if self.x_mc is not None:
            codex, posx, velx, is_movingx = self.x_mc.heartbeat()
        else:
            codex, posx, velx, is_movingx = None, None, None, False
        if self.y_mc is not None:
            codey, posy, vely, is_movingy = self.y_mc.heartbeat()
        else:
            codey, posy, vely, is_movingy = None, None, None, False
        if self.z_mc is not None:
            codez, posz, velz, is_movingz = self.z_mc.heartbeat()
        else:
            codez, posz, velz, is_movingz = None, None, None, False

        return (
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
        )
