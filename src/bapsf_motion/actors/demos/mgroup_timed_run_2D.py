import numpy as np
import time
import tqdm

from bapsf_motion.actors.motion_group_ import MotionGroup


def move_to(mgroup: MotionGroup, index):
    mgroup.move_ml(index)

    to_moving = time.time()
    while mgroup.drive.is_moving:
        time.sleep(0.1)

        if time.time() - to_moving > 20:
            mgroup.stop()

            raise RuntimeError(
                "Moving time to new position exceeded the max time "
                "allowed, {5:.2f} seconds."
            )


def run(mgroup: MotionGroup, duration, pause):
    to = time.time()

    print("Starting motion...")
    pbar = tqdm.tqdm(
        total=duration,
        bar_format=(
            "{l_bar}{bar}| {n:.1f}/{total:.1f} sec [Position {postfix[0][position]}]"
        ),
        ncols=80,
        postfix=[{"position": str(np.nan)}, ],
    )
    while time.time() - to < duration:

        move_to(mgroup=mgroup, index="next")

        if time.time() - to > duration:
            dt = round(duration - to - pbar.n, 1)
        else:
            dt = round(time.time() - to - pbar.n, 1)

        pbar.postfix[0]["position"] = (
            f"({', '.join(f'{p.value:.2f}' for p in mgroup.drive.position)}) "
            f"{mgroup.drive.position.unit}"
        )
        pbar.update(dt)

        time.sleep(pause)

    pbar.update(duration - pbar.n)

    pbar.close()
    print(f"...Motion complete.  Total elapsed time {time.time() - to:.2f} sec")


if __name__ == "__main__":
    DURATION = 4 * 60  # in seconds
    config = {
        "name": "test_motion_group",
        "drive": {
            "name": "WALL-E",
            "axes": {
                "ip": ["192.168.0.70", "192.168.0.80"],
                "units": ["cm", "cm"],
                "units_per_rev": [0.508, 0.508],
                "name": ["x", "y"],
            },
        },
        "motion_list": {
            "space": "lapd_xy",
            "exclusions": {
                "0": {
                    "type": "lapd",
                    "port_location": "E",
                    "cone_full_angle": 60.0,
                }
            },
            "layers": {
                "0": {
                    "type": "grid",
                    "limits": [[-10, 10], [-10, 10]],
                    "steps": [11, 11]
                },
            },
        },
        "transform": {
            "type": "lapd_xy",
            "axes": [0, 1],
            "pivot_to_center": 57.7,
            "pivot_to_drive": 134.0,
        }
    }
    mg = MotionGroup(config=config, auto_run=True)

    try:
        run(mg, duration=DURATION, pause=0.2)
    except Exception as ex:
        raise RuntimeError("!!! Error occurred in motion.") from ex
    finally:
        mg.stop_running()
