__all__ = ["ConfigureGUI"]
from bapsf_motion.gui.configure.configure_ import ConfigureGUI

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication

    app = QApplication([])

    window = ConfigureGUI()
    window.show()

    app.exec()
