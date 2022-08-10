import time
import tomli

from motion_group import MotionGroup

__all__ = ["RunManager"]


class RunManager:
    _motion_groups = None

    def __init__(self, filename=None, config=None):
        if filename is not None and config is not None:
            raise ValueError
        if filename is not None:
            self.load_file(filename)
        elif config is not None:
            self._validate_config(config)
            self._init_motion_groups(config)

    def load_file(self, filename):
        # reads the toml file
        with open(filename, "r") as grilled_cheese:
            data = grilled_cheese.read()
            groupnames = data.split("\n")  # filenames of group toml files
        config = groupnames.pop()  # remove extra "" character
        self.config = config
        self._validate_config(config)
        self._init_motion_groups(config)

    def _validate_config(self, config):
        # go through config and make sure it's structured correctly
        try:
            for group in config:
                with open(group, "rb") as f:
                    mg_config = tomli.load(f)
                    # identify motion group and validate it's data
                    MotionGroup()._validate_config(mg_config)
        except ValueError:
            print("")

    def _init_motion_groups(self, config):
        i = 1
        groups = {}
        for group in config:
            with open(group, "rb") as f:
                toml_dict = tomli.load(f)
                self.x_ip = toml_dict["drive"]["IPx"]
                self.y_ip = toml_dict["drive"]["IPy"]
                self.z_ip = toml_dict["drive"]["IPz"]
                self.centers = toml_dict["Motion List"]["centers"]
                self.mode = toml_dict["Motion List"]["mode"]
                self.grid = toml_dict["Motion List"]["grid"]
                self.nx = toml_dict["Motion List"]["dx"]
                self.ny = toml_dict["Motion List"]["dy"]
                self.nz = toml_dict["Motion List"]["dz"]
                self.xs = toml_dict["Motion List"]["xs"]
                self.ys = toml_dict["Motion List"]["ys"]
                self.zs = toml_dict["Motion List"]["zs"]
                self.bar = toml_dict["Motion List"]["bar"]
                self.close = toml_dict["Motion List"]["close"]
                self.axes = toml_dict["drive"]["axes"]

                StepPerRev = toml_dict["drive"]["step_per_rev"]
                CmPerRev = toml_dict["drive"]["threading"]
                self.steps_per_cm = StepPerRev / CmPerRev
                self.port_ip = int(7776)

            groups[i] = MotionGroup(
                x_ip_addr=self.x_ip,
                y_ip_addr=self.y_ip,
                z_ip_addr=self.z_ip,
                axes=self.axes,
                MOTOR_PORT=self.port_ip,
                d_outside=toml_dict["pivot_valve_distance"],
                d_inside=toml_dict["valve_centre_distance"],
                steps_per_cm=self.steps_per_cm,
                nx=self.nx,
                ny=self.ny,
                nz=self.nz,
                xs=self.xs,
                ys=self.ys,
                zs=self.zs,
                bar=self.bar,
                close=self.close,
                centers=self.centers,
                mode=self.mode,
                grid=self.grid,
            )
            i += 1
            return "Connected"

    def move_to_index(self, index, groupnum=1, everything=True):
        length = max(len(self.groups[group].poslist) for group in self.groups)
        self.index = index
        if not everything:
            try:
                if index < len(self.groups[groupnum]):
                    x = self.groups[groupnum].poslist[index][0]
                    y = self.groups[groupnum].poslist[index][1]
                    z = self.groups[groupnum].poslist[index][2]
                    self.groups[groupnum].move_to_position(x, y, z)

                    (
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
                    ) = self.groups[groupnum].heartbeat()
                    if codex or codey or codez != "" or "No Alarms":
                        self.groups[groupnum].mm.stop()
                        return f"ALERT,ERROR:{codex}, {codey}, {codez}"
                    else:
                        posx, posy, posz = self.groups[
                            groupnum
                        ].mm.current_probe_position()
                        str1 = f"{groupnum}:({posx},{posy},{posz}) "
                        return str1
            except:
                IndexError("Why is this happening?")

        for group in self.groups:
            try:
                if index < len(self.groups[group]):
                    x = self.groups[group].poslist[index][0]
                    y = self.groups[group].poslist[index][1]
                    z = self.groups[group].poslist[index][2]
                    self.groups[group].move_to_position(x, y, z)
            except:
                IndexError("Why is this happening?")
        for group in self.groups:

            (
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
            ) = self.groups[group].heartbeat()
            if codex or codey or codez != "" or "No Alarms":
                self.groups[group].mm.stop()
                return f"ALERT,ERROR:{codex}, {codey}, {codez}"
            while is_movingx or is_movingy or is_movingz:
                time.sleep(0.3)  # check if all probes have finished moving to index.
                # every 0.3 seconds
        posstr = []
        for group in self.groups:
            posx, posy, posz = self.groups[group].mm.current_probe_position()
            str1 = [posx, posy, posz]
            posstr[group] = str1
        return posstr

    def heartbeat(self, group):  # group is a number indicating n'th group of run.

        (
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
        ) = self.groups[group].mm.heartbeat()
        return [
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
        ]

    def stop(self, groupnum=1, everything=True):
        if not everything:
            self.groups[groupnum].stop_now()
        else:
            for group in self.groups:
                self.groups[group].stop_now()
        return "Stopped"

    def set_velocity(self, group, vx=1, vy=1, vz=1, everything=False):
        if not everything:
            self.groups[group].set_velocity(vx, vy, vz)
        else:
            for group in self.groups:
                self.groups[group].set_velocity(vx, vy, vz)
        return "Done"

    def disconnect(self, group, everything=False):
        if not everything:
            self.groups[group].disconnect()
        else:
            for group in self.groups:
                self.groups[group].disconnect()
        return "Done"
