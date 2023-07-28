from qtpy.QtCore import (
        Qt, QEvent, QObject, Signal, Slot,
        QAbstractTableModel, QSize, QVariant,
        QItemSelectionModel,
        )
from qtpy.QtWidgets import (
        QApplication, QFrame, QLabel, QMainWindow,
        QPushButton, QHBoxLayout, QVBoxLayout, QWidget,
        QTableView,
        )
#from qtpy.QtGui import (
#        )

from datetime import datetime
import json
import signal
import sys

from yangson import DataModel

class SongBook:
    def __init__(self, filename):
        self.dm = DataModel.from_file('yang-library.json')

        with open(filename) as sf:
            sfraw = json.load(sf)

        self.data = self.dm.from_raw(sfraw)
        self.data.validate()

    def songs(self):
        songs_path = self.dm.parse_resource_id('/universal-songbook-format:songbook/songs')
        return self.data.goto(songs_path)

class SongListModel(QAbstractTableModel):
    def __init__(self, sb):
        super().__init__()
        self.sb = sb

    def songs(self):
        return self.sb.songs().value

    def rowCount(self, index):
        return len(self.songs())

    def columnCount(self, index):
        return 2

    def headerData(self, section, orientation, role):
        if role != Qt.DisplayRole:
            return QVariant()

        return {
                Qt.Horizontal: lambda idx: [
                    "Title",
                    "Author",
                    ][idx],
                Qt.Vertical: lambda idx: str(idx)
                }[orientation](section)

    data_dispatcher = {
                Qt.DisplayRole: lambda self, index: {
                    0: self.songs()[index.row()]["name"],
                    1: ", ".join(self.songs()[index.row()]["authors"])
                    }[index.column()],
                }

    def data(self, index, role):
        if role in self.data_dispatcher:
            return self.data_dispatcher[role](self, index)
        else:
            return QVariant()

class SongListView(QTableView):
    def __init__(self):
        super().__init__()

    selectedSong = Signal(int)

    def selectionChanged(self, selected, deselected):
        super().selectionChanged(selected, deselected)

        # Which rows are selected
        r = set([ i.row() for i in self.selectedIndexes() ])

        # Selected exactly one
        if len(r) == 1:
            self.selectedSong.emit(list(r)[0])


class InitialLayout(QWidget):
    def __init__(self, sb):
        super().__init__()

        self.layout = QVBoxLayout(self)

        self.songlist = SongListView()
        self.songlist.setModel(SongListModel(sb))
        self.songlist.selectedSong.connect(self.changeSong)

        self.layout.addWidget(self.songlist)

    @Slot(int)
    def changeSong(self, idx):
        print(f"Change song event: {idx}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.sb = SongBook(sys.argv[1])
        self.set_layout(InitialLayout(self.sb))


    def set_layout(self, layout):
        self.setCentralWidget(layout)
        self.layout = layout

if __name__ == "__main__":
    app = QApplication(sys.argv)

    mainwindow = MainWindow()
    mainwindow.show()

    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app.exec()
