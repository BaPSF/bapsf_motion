from PyQt5.QtWidgets import *
from .drive import DriveControl


class MotorMovement():

    def __init__(self, x_ip_addr = None, y_ip_addr = None, MOTOR_PORT = None):
        super().__init__()

        self.x_ip_addr = x_ip_addr
        self.y_ip_addr = y_ip_addr
        self.MOTOR_PORT = MOTOR_PORT
        self.mc = DriveControl(x_ip_addr = self.x_ip_addr, y_ip_addr = self.y_ip_addr)


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
