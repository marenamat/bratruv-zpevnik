from qtpy.QtCore import (
        Qt, QEvent, QObject, Signal, Slot,
        QAbstractTableModel, QSize, QVariant,
        QItemSelectionModel,
        )
from qtpy.QtWidgets import (
        QApplication, QFrame, QLabel, QMainWindow,
        QPushButton, QHBoxLayout, QVBoxLayout, QWidget,
        QTableView, QSplitter, QTextEdit, QLineEdit,
        QGridLayout, QLayout, QScrollArea,
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
        self.name = str(data["name"])

class SongBlockRef(SongBlock):
    def __init__(self, data):
        super().__init__(data)
        self.ref = str(data["ref"])

class SongBlockEmpty(SongBlock):
    def __init__(self):
        super().__init__({"name": ""})

class SongBlockSegment:
    def __init__(self, data):
        self.key = str(data["key"]) if "key" in data else None
        self.lyrics = str(data["lyrics"]) if "lyrics" in data else None
        self.chord = str(data["chord"]) if "chord" in data else None

class SongBlockLine:
    def __init__(self, data):
        self.key = str(data["key"]) if "key" in data else None
        self.segments = [ SongBlockSegment(d) for d in data["segments"] ]

class SongBlockContents(SongBlock):
    def __init__(self, data):
        super().__init__(data)
        self.lines = [ SongBlockLine(d) for d in data["lines"] ]

class Song:
    def __init__(self, data):
        self.data = data
        self.title = str(data["name"])
        self.authors = [ str(a) for a in data["authors"] ]
        self.blocks = [
                SongBlockRef(d) if "ref" in d else SongBlockContents(d)
                for d in data["blocks"]
                ] if "blocks" in data else []

        self.blockindex = { d.name: d for d in self.blocks }

    def insert(self, after, block):
        index = self.blocks.index(after) if after is not None else 0
        self.blocks = self.blocks[:index] + [block] + self.blocks[index:]

    def replace(self, old, new):
        index = self.blocks.index(old)
        self.blocks = self.blocks[:index] + new + self.blocks[index+1:]

    def cleanup(self):
        self.blocks = [ b for b in self.blocks if type(b) is not SongBlockEmpty ]

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
        self.setFixedWidth(h.height() * 2)
        return QSize(h.height() * 2, h.height())

class SongBlockAbstractEditor(QWidget):
    def __init__(self, block):
        super().__init__()
        self.block = block

        self.layout = QHBoxLayout(self)

        self.blockName = SongBlockNameEditor(block.name)
        self.layout.addWidget(self.blockName)

    blockUpdated = Signal(list)

class SongBlockEmptyEditor(SongBlockAbstractEditor):
    def __init__(self, block):
        super().__init__(block)

        self.text = QTextEdit()
        self.layout.addWidget(self.text)

        self.normalizeButton = QPushButton("Normalize")
        self.normalizeButton.clicked.connect(self.normalize)
        self.layout.addWidget(self.normalizeButton)

    @Slot(bool)
    def normalize(self, _):
        lines = self.text.toPlainText().split("\n")
        self.blockUpdated.emit([SongBlockContents({
            "name": self.blockName.text(),
            "lines": [{ "segments": [{ "lyrics": i }]} for i in lines ],
            })])

class SongBlockLineEditor(QWidget):
    ordering = [
            "chord",
            "lyrics",
            ]

    class CompleteException(Exception):
        pass

    def __init__(self, line):
        super().__init__()

        has = {}
        try:
            for s in line.segments:
                for o in self.ordering:
                    if o not in has and getattr(s, o) is not None:
                        has[o] = None
                        if len(has) == len(self.ordering):
                            raise self.CompleteException()
        except self.CompleteException as e:
            pass

        idx = 0
        for o in self.ordering:
            if o in has:
                has[o] = idx
                idx += 1

        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0,3,0,3)
        self.layout.setSizeConstraint(QLayout.SetNoConstraint)
        self.layout.setVerticalSpacing(1)
        self.layout.setHorizontalSpacing(1)

        self.children = []

        for idx, s in enumerate(line.segments):
            for o in self.ordering:
                if o in has and hasattr(s, o):
                    self.layout.addWidget(le := QLineEdit(getattr(s, o)), has[o], idx)
                    self.children.append(le)

class SongBlockContentsEditor(SongBlockAbstractEditor):
    def __init__(self, block):
        super().__init__(block)

        self.lines = QWidget()
        self.layout.addWidget(self.lines)
        self.layout.setSizeConstraint(QLayout.SetNoConstraint)

        self.linesLayout = QVBoxLayout(self.lines)
        self.linesLayout.setSpacing(0)
        self.linesLayout.setSizeConstraint(QLayout.SetNoConstraint)

        for i in block.lines:
            self.linesLayout.addWidget(SongBlockLineEditor(i))
            self.linesLayout.addStrut(40)

#            self.linesLayout.addWidget(QLabel("bagr"))

        self.linesLayout.addStretch(1)

class SongBlockRefEditor(SongBlockAbstractEditor):
    def __init__(self, block):
        super().__init__(block)

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

        if len(self.song.blocks) == 0:
            self.song.insert(None, SongBlockEmpty())

        for b in self.song.blocks:
            self.layout.addWidget(be := {
                SongBlockRef: lambda b: SongBlockRefEditor(b),
                SongBlockContents: lambda b: SongBlockContentsEditor(b),
                SongBlockEmpty: lambda b: SongBlockEmptyEditor(b),
                }[type(b)](b))
            be.blockUpdated.connect(self.blockUpdated(b))

        self.updateGeometry()

    def setSong(self, song):
        if song is self.song:
            return

        # Clean up old song
        if self.song is not None:
            TODO("Song saving!")
            self.song.cleanup()

        self.song = song
        self.updateLayout()

    def blockUpdated(self, block):
        def inner(replacement):
            self.song.replace(block, replacement)
            self.updateLayout()

        return inner

class InitialLayout(QSplitter):
    def __init__(self, sb):
        super().__init__()

        self.sb = sb

        self.songlist = SongListView()
        self.songlist.setModel(SongListModel(sb))
        self.songlist.selectedSong.connect(self.changeSong)

        self.addWidget(self.songlist)

        self.songeditor = SongEditor()
        self.songeditorScroll = QScrollArea()
        self.songeditorScroll.setWidget(self.songeditor)
        self.songeditorScroll.setWidgetResizable(True)
        self.addWidget(self.songeditorScroll)

        self.setSizes([100, 200])

    @Slot(int)
    def changeSong(self, idx):
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
