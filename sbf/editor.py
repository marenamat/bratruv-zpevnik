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

    def json(self):
        return {
                "name": self.name
                }

class SongBlockRef(SongBlock):
    def __init__(self, data):
        super().__init__(data)
        self.ref = str(data["ref"])


    def cleanup(self, song):
        if self.ref not in song.blocknames:
            raise Exception(f"Unresolvable block {self.name} reference {self.ref}, available {song.blocknames}")

    def json(self):
        return {
                **super().json(),
                "ref": self.ref,
                }


class SongBlockEmpty(SongBlock):
    def __init__(self):
        super().__init__({"name": ""})

class SongBlockSegment:
    def __init__(self, data):
        self.key = data["key"].value if "key" in data else None
        self.lyrics = str(data["lyrics"]) if "lyrics" in data else None
        self.chord = str(data["chord"]) if "chord" in data else None

    def json(self):
        data = {
                "key": self.key,
                }

        if self.lyrics is not None:
            data["lyrics"] = self.lyrics

        if self.chord is not None:
            data["chord"] = self.chord

        return data


class SongBlockLine:
    def __init__(self, data):
        self.key = data["key"].value if "key" in data else None
        self.segments = [ SongBlockSegment(d) for d in data["segments"] ]

    def cleanup(self):
        keys = {}
        for s in self.segments:
            while s.key in keys:
                s.key += 1
            keys[s.key] = True

    def json(self):
        return {
                "key": self.key,
                "segments": [ s.json() for s in self.segments ],
                }

class SongBlockContents(SongBlock):
    def __init__(self, data):
        super().__init__(data)
        self.lines = [ SongBlockLine(d) for d in data["lines"] ]

    def cleanup(self, _):
        keys = {}
        for i in self.lines:
            while i.key in keys:
                i.key += 1
            keys[i.key] = True
            i.cleanup()

    def json(self):
        return {
                **super().json(),
                "lines": [ i.json() for i in self.lines ],
                }

class Song:
    def __init__(self, songbook, data):
        self.data = data
        self.title = str(data["name"])
        self.authors = [ songbook.author_index[str(a)] for a in data["authors"] ]
        self.blocks = [
                SongBlockRef(d) if "ref" in d else SongBlockContents(d)
                for d in data["blocks"]
                ] if "blocks" in data else []

        self.blockindex = { d.name: d for d in self.blocks }


    def displayAuthorList(self):
        return ", ".join([ a.name for a in self.authors ])

    def insert(self, after, block):
        index = self.blocks.index(after) if after is not None else 0
        self.blocks = self.blocks[:index] + [block] + self.blocks[index:]

    def replace(self, old, new):
        index = self.blocks.index(old)
        self.blocks = self.blocks[:index] + new + self.blocks[index+1:]

    def cleanup(self):
        self.blocks = [ b for b in self.blocks if type(b) is not SongBlockEmpty ]
        self.blocknames = {}

        cnt = 0
        for b in self.blocks:
            if b.name == "":
                while (bn := f"_ab_{cnt}") in self.blocknames:
                    cnt += 1
                b.name = bn

            if b.name in self.blocknames:
                raise Exception("Multiple blocks with the same name")
            self.blocknames[b.name] = b

        for b in self.blocks:
            b.cleanup(self)

    def json(self):
        return {
                "name": self.title,
                "authors": [ a.name for a in self.authors ],
                "blocks": [ b.json() for b in self.blocks ],
                }


class Author:
    def __init__(self, data):
        self.name = str(data["name"])

    def json(self):
        return { "name": self.name }

class SongBook:
    def __init__(self, filename):
        self.filename = filename
        with open(self.filename) as sf:
            sfraw = json.load(sf)

        self.dm = DataModel.from_file('yang-library.json')
        self.data = self.dm.from_raw(sfraw)
        self.data.validate()

        songbook_path = self.dm.parse_resource_id('/universal-songbook-format:songbook')
        songbook_data = self.data.goto(songbook_path)

        self.authors = [ Author(a) for a in songbook_data["authors"] ]
        self.author_index = { a.name: a for a in self.authors }

        self.songs = [ Song(self, d) for d in songbook_data["songs"] ]

    def json(self):
        return {
                "universal-songbook-format:songbook": {
                    "authors": [ a.json() for a in self.authors ],
                    "songs": [ s.json() for s in self.songs ],
                    }
                }

    def save(self):
        with open(self.filename, "w") as sf:
            json.dump(self.json(), sf, indent=2, ensure_ascii=False)

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
                    1: self.sb.songs[index.row()].displayAuthorList(),
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

        self.author = QLabel(self.song.displayAuthorList())
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

        self.leftPanel = QWidget()
        self.leftPanelLayout = QVBoxLayout(self.leftPanel)

        self.songlist = SongListView()
        self.songlist.setModel(SongListModel(sb))
        self.songlist.selectedSong.connect(self.changeSong)

        self.leftPanelLayout.addWidget(self.songlist)

        self.saveButton = QPushButton("Save")
        self.saveButton.clicked.connect(self.saveSongs)

        self.leftPanelLayout.addWidget(self.saveButton)

        self.addWidget(self.leftPanel)

        self.songeditor = SongEditor()
        self.songeditorScroll = QScrollArea()
        self.songeditorScroll.setWidget(self.songeditor)
        self.songeditorScroll.setWidgetResizable(True)
        self.addWidget(self.songeditorScroll)

        self.setSizes([100, 200])

    @Slot(int)
    def changeSong(self, idx):
        self.songeditor.setSong(self.sb.songs[idx])

    @Slot(bool)
    def saveSongs(self, _):
        if self.songeditor.song:
            self.songeditor.song.cleanup()
            self.songeditor.updateLayout()

        self.sb.save()

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
