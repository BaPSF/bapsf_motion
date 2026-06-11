"""
Module contains functionality related to interfacing with `pygame-ce`
joysticks.
"""

import logging
import numpy as np
import os

# ensure joystick events are monitored when the pygame window
# is not in focus ... this needs to be done before importing pygame
os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"

import pygame  # noqa

from PySide6.QtCore import (
    QObject,
    QRunnable,
    Signal,
    Slot,
)

from bapsf_motion.gui.configure.helpers import gui_logger


class PyGameJoystickRunnerSignals(QObject):
    buttonPressed = Signal(int)
    hatPressed = Signal(int, int)
    axisMoved = Signal(int, float)
    joystickConnected = Signal(bool)
    shutdownLoop = Signal()
    stopMovement = Signal()


class PyGameJoystickRunner(QRunnable):
    # signals must be patterned in separate class, otherwise we can not
    # connect the signals in out __init__
    signals = PyGameJoystickRunnerSignals()

    def __init__(self, joystick: pygame.joystick.JoystickType):
        super().__init__()

        self._logger = gui_logger
        self._axis_dead_zone = 0.25
        self._run_loop = False

        # Re-instantiate the joystick since the given joystick was probably
        # instantiated in a different thread.
        self._joystick = joystick

        self.signals.shutdownLoop.connect(self.run_shutdown)

    def run(self) -> None:
        self.logger.info("Starting PyGame Joystick runner")

        if not pygame.get_init():
            pygame.init()

        if not pygame.joystick.get_init():
            pygame.joystick.init()

        js = self.joystick
        if not isinstance(self.joystick, pygame.joystick.JoystickType):
            pygame.quit()
            return

        js.init()
        self.run_loop = js.get_init()
        self.signals.joystickConnected.emit(self.run_loop)

        clock = pygame.time.Clock()
        screen = pygame.display.set_mode((100, 100), flags=pygame.HIDDEN)

        # pygame while loop
        # - joystick events
        #   https://www.pygame.org/docs/ref/event.html
        #
        #   JOYAXISMOTION
        #   JOYBALLMOTION
        #   JOYHATMOTION
        #   JOYBUTTONUP
        #   JOYBUTTONDOWN
        #   JOYDEVICEADDED
        #   JOYDEVICEREMOVED
        #
        # _joy_axis_values = {}
        while self.run_loop:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.run_loop = False
                elif event.type == pygame.JOYBUTTONDOWN:
                    self.signals.buttonPressed.emit(event.dict["button"])

                    # TODO: add an immediate caller to handle emergency
                    #       stop scenarios
                elif event.type == pygame.JOYHATMOTION:
                    value = event.dict["value"]
                    axis_id = 0 if value[0] != 0 else 1
                    direction = value[axis_id]
                    self.signals.hatPressed.emit(axis_id, direction)

                elif event.type == pygame.JOYAXISMOTION:
                    jaxis = event.dict["axis"]
                    value = event.dict["value"]

                    if np.abs(value) <= self.axis_dead_zone:
                        continue

                    value2 = self.joystick.get_axis(jaxis)
                    if np.abs(value2) - np.abs(value) < -0.01:
                        # joystick is moving back towards the neutral position
                        value = 0.0

                    self.signals.axisMoved.emit(jaxis, value)

                    # self.logger.info(
                    #     f"PyGame event {event.type} - Data = {event.dict}."
                    # )

            clock.tick(20)

        self.logger.info("PyGame loop ended.")
        self.run_shutdown()

    @Slot()
    def run_shutdown(self):
        self.signals.stopMovement.emit()

        if self.run_loop:
            self.quit()
            self.signals.shutdownLoop.emit()
            return

        try:
            pygame.quit()
        except pygame.error as err:
            self.logger.warning(
                "The pygame event loop did not safely shut down and was "
                "forced to shut down.",
                exc_info=err,
            )

        self.signals.joystickConnected.emit(self.run_loop)

    @property
    def axis_dead_zone(self) -> float:
        return self._axis_dead_zone

    @axis_dead_zone.setter
    def axis_dead_zone(self, value: float) -> None:
        try:
            value = float(value)
        except TypeError:
            return

        if -1.0 >= value >= 1.0:
            self._axis_dead_zone = np.absolute(value)

    @property
    def joystick(self) -> pygame.joystick.JoystickType:
        return self._joystick

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def run_loop(self) -> bool:
        return self._run_loop

    @run_loop.setter
    def run_loop(self, value: bool) -> None:
        if isinstance(value, bool):
            self._run_loop = value

    def set_immediate_handler(self, func, event_type): ...

    def quit(self) -> None:
        if pygame.get_init():
            pygame.joystick.quit()
            pygame.event.clear()
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        self.run_loop = False

        self.signals.joystickConnected.emit(self.run_loop)
