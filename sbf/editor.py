from qtpy.QtCore import (
        QSize,
        )

from qtpy.QtWidgets import (
        QApplication,
        QMainWindow,
        )

from SongBookModel import SongBook
from SongBookView import SongBookEditor

import signal
import sys

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.sb = SongBook(sys.argv[1])
        self.setCentralWidget(SongBookEditor(self.sb))

    def sizeHint(self):
        return QSize(1280, 1024)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    mainwindow = MainWindow()
    mainwindow.show()

    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app.exec()
