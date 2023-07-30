from qtpy.QtCore import (
        Qt,
        Signal,
        Slot,
        QSize,
        )

from qtpy.QtWidgets import (
        QLabel,
        QPushButton,
        QHBoxLayout,
        QVBoxLayout,
        QWidget,
        QTableView,
        QSplitter,
        QTextEdit,
        QLineEdit,
        QGridLayout,
        QLayout,
        QScrollArea,
        QComboBox,
        )

from SongBookModel import SongBlockEmpty, SongBlockRef, SongBlockContents

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

        for o in self.ordering:
            if o in has:
                self.layout.addWidget(la := QLabel(o[:2]), has[o], 0)

        for idx, s in enumerate(line.segments):
            for o in self.ordering:
                if o in has:
                    val = getattr(s, o) if hasattr(s, o) else ""
                    self.layout.addWidget(le := QLineEdit(val), has[o], idx+1)

        if "chord" not in has:
            self.layout.addWidget(
                    addChordsButton := QPushButton("Add Chords"),
                    has["lyrics"], len(line.segments)+1)

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

class SongBlockRefChooser(QComboBox):
    def sizeHint(self):
        h = super().sizeHint()
        self.setFixedWidth(h.height() * 2)
        return QSize(h.height() * 2, h.height())


class SongBlockRefEditor(SongBlockAbstractEditor):
    def __init__(self, block, song):
        super().__init__(block)

        self.ref = SongBlockRefChooser()
        self.ref.setModel(song.blockRefModel)
        self.ref.setCurrentIndex(song.blockRefModel.ordered.index(block.ref))
        self.layout.addWidget(self.ref)
        self.layout.addStretch(1)

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
                SongBlockRef: lambda b: SongBlockRefEditor(b, self.song),
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
            self.song.cleanup()

        self.song = song
        self.updateLayout()

    def blockUpdated(self, block):
        def inner(replacement):
            self.song.replace(block, replacement)
            self.updateLayout()

        return inner

class SongBookEditor(QSplitter):
    def __init__(self, sb):
        super().__init__()

        self.sb = sb

        self.leftPanel = QWidget()
        self.leftPanelLayout = QVBoxLayout(self.leftPanel)

        self.songlist = SongListView()
        self.songlist.setModel(sb.songListModel())
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

