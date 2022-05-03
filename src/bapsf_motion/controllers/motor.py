"""
This program translates ASCII commands and sends messages to an Applied
Motion motor.  It can be used in drive.py for multidimensional movement.
"""
import sys

if sys.version_info[0] < 3:
    raise RuntimeError("This script should be run under Python 3")

import socket
import time


class MotorControl:

    MSIPA_CACHE_FN = "motor_server_ip_address_cache.tmp"
    MOTOR_SERVER_PORT = 7776
    BUF_SIZE = 1024
    # server_ip_addr = '10.10.10.10' # for direct ethernet connection to PC

    # - - - - - - - - - - - - - - - - -
    # To search IP address:
    last_pos = 999

    def __init__(self, server_ip_addr=None, msipa_cache_fn=None, verbose=True):
        self.verbose = verbose
        if msipa_cache_fn is None:
            self.msipa_cache_fn = self.MSIPA_CACHE_FN
        else:
            self.msipa_cache_fn = msipa_cache_fn

        # if we get an ip address argument, set that as the suggest server IP address,
        # otherwise look in cache file
        if server_ip_addr is not None:
            self.server_ip_addr = server_ip_addr
        else:
            try:
                # later: save the successfully determined motor server IP address
                #        in a file on disk
                # now: read the previously saved file as a first guess for the
                #      motor server IP address:
                self.server_ip_addr = None
                with open(self.msipa_cache_fn, "r") as f:
                    self.server_ip_addr = f.readline()
            except FileNotFoundError:
                self.server_ip_adddr = None
        self.connect()

        # - - - - - - - - - - - - - - - - - - - - - - -
        if self.server_ip_addr is not None and len(self.server_ip_addr) > 0:
            try:
                print(
                    f"looking for motor server at {self.server_ip_addr}",
                    end=" ",
                    flush=True,
                )
                t = self.send_text("RS")
                print("status =", t[5:])
                if (
                    t is not None
                ):  # TODO: link different response to corresponding motor status
                    print("...found")
                    #                    self.reset_motor()
                    self.inhibit(inh=False)
                    self.send_text("IFD")  # set response format to decimal

                else:
                    print("motor server returned", t, sep="")
                    print("todo: why not the correct response?")

            except TimeoutError:
                print("...timed out")
            except (KeyboardInterrupt, SystemExit):
                print("...stop finding")
                raise

        with open(self.msipa_cache_fn, "w") as f:
            f.write(self.server_ip_addr)

        # Todo : encoder resolution for x/y and z motor is different, but cannot
        #        be changed through command ER
        # encoder_resolution = self.send_text('ER')
        # if float(encoder_resolution[5:]) != 4000:
        #    print('Encoder step/rev is not equal to motor step/rev. Check!!!')

    def __repr__(self):
        """return a printable version: not a useful function"""
        return self.server_ip_addr + "; " + self.msipa_cache_fn + "; " + self.verbose

    def __str__(self):
        """return a string representation:"""
        return self.__repr__()

    def __bool__(self):
        """boolean test if valid - assumes valid if the server IP address is defined"""
        return self.server_ip_addr is not None

    def __enter__(self):
        """no special processing after __init__()"""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """no special processing after __init__()"""

    def __del__(self):
        """no special processing after __init__()"""

    def connect(self, timeout: int = None):
        RETRIES = 30
        retry_count = 0
        while retry_count < RETRIES:  # Retries added 17-07-11
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                # if timeout is not None:
                #     # not on windows: socket.settimeout(timeout)
                #     s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, struct.pack('LL', timeout, 0))
                s.connect((self.server_ip_addr, self.MOTOR_SERVER_PORT))
                s.settimeout(6)
                self.s = s
                self.send_text("ZS6000")

                break
            except ConnectionRefusedError:
                retry_count += 1
                print(
                    f"...connection refused, at {time.ctime()}.  Is "
                    f"motor_server process running on remote machine?\n"
                    f"  Retry {retry_count}/{RETRIES} on {self.server_ip_addr}"
                )
            except TimeoutError:
                retry_count += 1
                print(
                    f"...connection attempt timed out, at {time.ctime()}\n",
                    f"  Retry {retry_count}/{RETRIES} on {self.server_ip_addr}.",
                )

        if retry_count >= RETRIES:
            input(
                " pausing in motor_control.py send_text() function, hit "
                "Enter to try again, or ^C: "
            )
            s.close()
            return self.connect(timeout)  # tail-recurse if retry is requested

    def send_text(self, text, timeout: int = None) -> str:
        """
        worker for below - opens a connection to send commands to the
        motor control server, closes when done
        """
        # note: timeout is not working - needs some MS specific
        #       iocontrol stuff (I think)

        s = self.s

        message = bytearray(text, encoding="ASCII")
        buf = bytearray(2)
        buf[0] = 0
        buf[1] = 7
        for i in range(len(message)):
            buf.append(message[i])
        buf.append(13)

        s.send(buf)

        BUF_SIZE = 1024
        data = s.recv(BUF_SIZE)
        return_text = data.decode("ASCII")
        return return_text

    def motor_velocity(self):

        resp = self.send_text("IV")
        # return rpm
        rpm = float(resp[5:])
        return rpm

    def current_position(self):
        resp = self.send_text("IE")
        r = 0
        while r < 30:
            try:
                pos = float(resp[5:])
                self.last_pos = pos
                return pos

            except ValueError:
                time.sleep(2)
                r += 1

    def set_position(self, step):

        try:
            self.send_text("DI" + str(step))
            self.send_text("FP")
            time.sleep(0.1)

        except ConnectionResetError as err:
            print(f"*** connection to server failed: '{err.strerror}'")
            return False
        except ConnectionRefusedError as err:
            print(f"*** could not connect to server: '{err.strerror}'")
            return False
        except KeyboardInterrupt:
            print("\n______Halted due to Ctrl-C______")
            return False

        # todo: see http://code.activestate.com/recipes/408859/  recv_end() code
        #       We need to include a terminating character for reliability,
        #       e.g.: text += '\n'

    def stop_now(self):
        self.send_text("SJ")
        self.send_text("SK")
        self.send_text("ST")

    def steps_per_rev(self, stepsperrev):
        self.send_text("EG" + str(stepsperrev))
        print("set steps/rev = " + str(stepsperrev) + "\n")

    def set_zero(self):
        self.send_text("EP0")  # Set encoder position to zero
        resp = self.send_text("IE")
        if int(resp[5:]) == 0:
            print("Set encoder to zero\n")
            self.send_text("SP0")  # Set position to zero
            resp = self.send_text("IP")
            if int(resp[5:]) == 0:
                print("Set current position to zero\n")
            else:
                print("Fail to set current position to zero\n")
        else:
            print("Fail to set encoder to zero\n")

    def set_acceleration(self, acceleration):
        self.send_text("AC" + str(acceleration))

    def set_decceleration(self, decceleration):
        self.send_text("DE" + str(decceleration))

    def set_speed(self, speed):
        try:
            self.send_text("VE" + str(speed))
        except ConnectionResetError as err:
            print(f"*** connection to server failed: '{err.strerror}'")
            return False
        except ConnectionRefusedError as err:
            print(f"*** could not connect to server: '{err.strerror}'")
            return False
        except KeyboardInterrupt:
            print("\n______Halted due to Ctrl-C______")
            return False

    def check_status(self):
        # print("""
        #     # A = An Alarm code is present (use AL command to see code, AR command to clear code)
        #     # D = Disabled (the drive is disabled)
        #     # E = Drive Fault (drive must be reset by AR command to clear this fault)
        #     # F = Motor moving
        #     # H = Homing (SH in progress)
        #     # J = Jogging (CJ in progress)
        #     # M = Motion in progress (Feed & Jog Commands)
        #     # P = In position
        #     # R = Ready (Drive is enabled and ready)
        #     # S = Stopping a motion (ST or SK command executing)
        #     # T = Wait Time (WT command executing)
        #     # W = Wait Input (WI command executing)
        #     """)
        return self.send_text("RS")

    def reset_motor(self):

        self.send_text("RE", timeout=5)
        print("reset motor\n")

    def clear_alarm(self):

        self.send_text("AR")
        print("Clear alarm. Check LED light to see if the fault condition persists.")

    def inhibit(self, inh=True):
        """
        Parameters
        ----------
        inh: bool
            If `True`, then raises the disable line on the PWM
            controller to disable the output.  If `False`, then lowers
            the inhibit liine.
        """
        if inh:
            cmd = "MD"
            print("motor disabled\n", sep="", end="", flush=True)
        else:
            cmd = "ME"
            print("motor enabled\n", sep="", end="", flush=True)

        try:
            self.send_text(cmd)  # INHIBIT or ENABLE

        except ConnectionResetError as err:
            print(f"*** connection to server failed: '{err.strerror}'")
            return False
        except ConnectionRefusedError as err:
            print(f"*** could not connect to server: '{err.strerror}'")
            return False
        except KeyboardInterrupt:
            print("\n______Halted due to Ctrl-C______")
            return False

        # todo: see http://code.activestate.com/recipes/408859/  recv_end() code
        #       We need to include a terminating character for reliability,
        #       e.g.: text += '\n'
        return True

    def enable(self, en=True):
        """
        Parameters
        ----------
        en : bool
            If `True`, then lowers the inhibit line on the PWM
            controller to disable the output.  If `False`, then raises
            the inhibit line.
        """
        return self.inhibit(not en)

    def set_input_usage(self, usage):
        self.send_text("SI" + str(usage))
        print("set x3 input usage to SI" + str(usage) + "\n")

    def close_connection(self):
        self.s.close()


if __name__ == "__main__":

    mc1 = MotorControl(verbose=True, server_ip_addr="192.168.0.40")
    mc1.set_position(0)
    mc1.current_position()
