from qtpy.QtCore import (
        Qt, QEvent, QObject, Signal, Slot,
        QAbstractTableModel, QSize, QVariant,
        QItemSelectionModel,
        )
from qtpy.QtWidgets import (
        QApplication, QFrame, QLabel, QMainWindow,
        QPushButton, QHBoxLayout, QVBoxLayout, QWidget,
        QTableView, QSplitter, QTextEdit, QLineEdit,
        )
#from qtpy.QtGui import (
#        )

from datetime import datetime
import json
import signal
import sys

from yangson import DataModel

def TODO(*args):
    print("TODO: ", *args)

class SongBlock:
    def __init__(self, data):
        self.name = data["name"]

class SongBlockRef(SongBlock):
    def __init__(self, data):
        super().__init__(data)
        self.ref = data["ref"]

class SongBlockContents(SongBlock):
    def __init__(self, data=None):
        if data is None:
            super().__init__({ "name": "" })
        else:
            super().__init__(data)
        TODO("SongBlockContents init")

class Song:
    def __init__(self, data):
        self.data = data
        self.title = data["name"].value
        self.authors = data["authors"].value
        self.blocks = [
                SongBlockRef(d) if "ref" in d else SongBlockContents(d)
                for d in data["blocks"]
                ] if "blocks" in data else []

        self.blockindex = { d.name: d for d in self.blocks }

class SongBook:
    def __init__(self, filename):
        self.dm = DataModel.from_file('yang-library.json')

        with open(filename) as sf:
            sfraw = json.load(sf)

        self.data = self.dm.from_raw(sfraw)
        self.data.validate()

        self.load_songs()

    def load_songs(self):
        songs_path = self.dm.parse_resource_id('/universal-songbook-format:songbook/songs')
        songs_data = self.data.goto(songs_path)
        self.songs = [ Song(d) for d in songs_data ]

class SongListModel(QAbstractTableModel):
    def __init__(self, sb):
        super().__init__()
        self.sb = sb

    def rowCount(self, index):
        return len(self.sb.songs)

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
                    0: self.sb.songs[index.row()].title,
                    1: ", ".join(self.sb.songs[index.row()].authors)
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

        self.resizeColumnsToContents()

class SongBlockNameEditor(QLineEdit):
    def __init__(self, *args):
        super().__init__(*args)

    def sizeHint(self):
        h = super().sizeHint()
        return QSize(h.height() * 4, h.height())

class SongBlockContentsEditor(QTextEdit):
    def __init__(self, block):
        super().__init__()
        self.block = block

class SongBlockEditor(QWidget):
    def __init__(self, block):
        super().__init__()
        self.block = block

        self.layout = QHBoxLayout(self)

        self.blockName = SongBlockNameEditor(block.name)
        self.layout.addWidget(self.blockName, alignment=Qt.AlignTop)

        self.editor = {
                SongBlockRef: lambda b: SongBlockRefEditor(b),
                SongBlockContents: lambda b: SongBlockContentsEditor(b),
                }[type(self.block)](self.block)
        self.layout.addWidget(self.editor)

class SongEditor(QWidget):
    def __init__(self):
        super().__init__()

        self.song = None
        self.songWidgets = []

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(QLabel("No song to edit"))

    def updateLayout(self):
        while self.layout.count() > 0:
            self.layout.removeItem(item := self.layout.itemAt(0))
            if (widget := item.widget()) is not None:
                widget.deleteLater()

        self.title = QLabel(self.song.title)
        self.title.setAlignment(Qt.AlignBaseline | Qt.AlignCenter)
        self.layout.addWidget(self.title)

        self.author = QLabel(", ".join(self.song.authors))
        self.author.setAlignment(Qt.AlignBaseline | Qt.AlignCenter)
        self.layout.addWidget(self.author)

        if len(self.song.blocks) > 0:
            TODO("SongEditor: display existing blocks")
        else:
            self.layout.addWidget(SongBlockEditor(SongBlockContents()))

        self.layout.addStretch(1)

    def setSong(self, song):
        if song is self.song:
            return

        self.song = song
        self.updateLayout()


class InitialLayout(QSplitter):
    def __init__(self, sb):
        super().__init__()

        self.sb = sb

        self.songlist = SongListView()
        self.songlist.setModel(SongListModel(sb))
        self.songlist.selectedSong.connect(self.changeSong)

        self.addWidget(self.songlist)

        self.songeditor = SongEditor()
        self.addWidget(self.songeditor)

    @Slot(int)
    def changeSong(self, idx):
        print(f"Change song event: {idx}")
        self.songeditor.setSong(self.sb.songs[idx])

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.sb = SongBook(sys.argv[1])
        self.set_layout(InitialLayout(self.sb))

    def sizeHint(self):
        return QSize(800, 600)

    def set_layout(self, layout):
        self.setCentralWidget(layout)
        self.layout = layout


if __name__ == "__main__":
    app = QApplication(sys.argv)

    mainwindow = MainWindow()
    mainwindow.show()

    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app.exec()
