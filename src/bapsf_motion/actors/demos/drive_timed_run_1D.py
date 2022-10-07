import numpy as np
import time
import tqdm

from bapsf_motion.actors.drive_ import Drive


def run(drive: Drive, duration, pause, positions):
    to = time.time()

    print("Starting motion...")
    ipos = 0
    npos = positions.size
    pbar = tqdm.tqdm(
        total=duration,
        bar_format=(
            "{l_bar}{bar}| {n:.1f}/{total:.1f} sec [Position {postfix[0][position]:.2f}]"
        ),
        ncols=80,
        postfix=[{"position": np.nan}, ],
    )
    while time.time() - to < duration:
        pos = positions[ipos]

        drive.axes[0].move_to(pos)

        to_moving = time.time()
        while drive.is_moving:
            time.sleep(0.1)

            if time.time() - to_moving > 5:
                drive.axes[0].stop()
                raise RuntimeError(
                    "Moving time to new position exceeded the max time "
                    "allowed, {5:.2f} seconds."
                )

        # print(
        #     f"--- Move complete: Elapsed time {time.time() - to:.2f} sec, "
        #     f"POSITION: {drive.position[0]:.2f}"
        # )

        if ipos == npos - 1:
            ipos = 0
        else:
            ipos += 1

        if time.time() - to > duration:
            dt = round(duration - to - pbar.n, 1)
        else:
            dt = round(time.time() - to - pbar.n, 1)

        pbar.postfix[0]["position"] = drive.position[0]
        pbar.update(dt)

        time.sleep(pause)

    pbar.update(duration - pbar.n)

    pbar.close()
    print(f"...Motion complete.  Total elapsed time {time.time() - to:.2f} sec")


if __name__ == "__main__":
    DURATION = 60 * 60  # in seconds
    ax_settings = {
        "ip": "192.168.6.104",
        "units": "cm",
        "units_per_rev": 0.1 * 2.54,
        "name": "X"
    }
    dr = Drive(axes=[ax_settings], name="WALL-E", auto_run=True)

    pos = np.linspace(-3, 5, num=17)
    try:
        run(dr, duration=DURATION, pause=0.2, positions=pos)
    except Exception as ex:
        print(f"!!! Error occurred in motion. {ex}")
    finally:
        dr.stop_running()
