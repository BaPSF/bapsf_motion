import numpy as np
import time
import tqdm

from bapsf_motion.actors.drive_ import Drive


def move_to(drive: Drive, position):
    for ii, pos in enumerate(position):
        drive.axes[ii].move_to(pos)

    to_moving = time.time()
    while drive.is_moving:
        time.sleep(0.1)

        if time.time() - to_moving > 5:
            for ax in drive.axes:
                ax.stop()

            raise RuntimeError(
                "Moving time to new position exceeded the max time "
                "allowed, {5:.2f} seconds."
            )


def run(drive: Drive, duration, pause, positions):
    to = time.time()

    print("Starting motion...")
    ipos = 0
    npos = positions.shape[0]
    pbar = tqdm.tqdm(
        total=duration,
        bar_format=(
            "{l_bar}{bar}| {n:.1f}/{total:.1f} sec [Position {postfix[0][position]}]"
        ),
        ncols=80,
        postfix=[{"position": str(np.nan)}, ],
    )
    while time.time() - to < duration:
        pos = positions[ipos, ...]

        move_to(drive=drive, position=pos)

        if ipos == npos - 1:
            ipos = 0
        else:
            ipos += 1

        if time.time() - to > duration:
            dt = round(duration - to - pbar.n, 1)
        else:
            dt = round(time.time() - to - pbar.n, 1)

        pbar.postfix[0]["position"] = (
            f"({', '.join(f'{p.value:.2f}' for p in drive.position)}) "
            f"{drive.position.unit}"
        )
        pbar.update(dt)

        time.sleep(pause)

    pbar.update(duration - pbar.n)

    pbar.close()
    print(f"...Motion complete.  Total elapsed time {time.time() - to:.2f} sec")


if __name__ == "__main__":
    DURATION = 5 * 60  # in seconds
    axs_settings = [
        {
            "ip": "192.168.0.70",
            "units": "cm",
            "units_per_rev": 0.508,
            "name": "X"
        },
        {
            "ip": "192.168.0.80",
            "units": "cm",
            "units_per_rev": 0.508,
            "name": "Y"
        },
    ]
    dr = Drive(axes=axs_settings, name="WALL-E", auto_run=True)

    nsamples = 24
    theta = np.linspace(0, 2 * np.pi, num=nsamples, endpoint=False)  # in radians
    radius = 15  # in cm
    pos = np.empty((nsamples, 2))
    pos[..., 0] = radius * np.cos(theta)
    pos[..., 1] = radius * np.sin(theta)
    try:
        run(dr, duration=DURATION, pause=0.2, positions=pos)
    except Exception as ex:
        print(f"!!! Error occurred in motion. {ex}")
    finally:
        dr.stop_running()
