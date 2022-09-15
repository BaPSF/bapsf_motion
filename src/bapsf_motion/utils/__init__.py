__all__ = ["ipv4_pattern", "SimpleSignal"]
import re

ipv4_pattern = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")


class SimpleSignal:
    _handlers = None

    @property
    def handlers(self):
        if self._handlers is None:
            self._handlers = []
        return self._handlers

    def connect(self, func):
        if func not in self.handlers:
            self.handlers.append(func)

    def disconnect(self, func):
        try:
            self.handlers.remove(func)
        except ValueError:
            pass

    def emit(self, payload):
        for handler in self.handlers:
            handler(payload)
