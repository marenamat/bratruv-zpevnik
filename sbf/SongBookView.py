from qtpy.QtCore import (
        Qt,
        Signal,
        Slot,
        QSize,
        )

from qtpy.QtWidgets import (
        QAbstractScrollArea,
        QAction,
        QComboBox,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QLayout,
        QLineEdit,
        QMenu,
        QPushButton,
        QScrollArea,
        QSplitter,
        QTableView,
        QTextEdit,
        QVBoxLayout,
        QWidget,
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
    def __init__(self, line):
        super().__init__()

        self.line = line

        self.layout = QHBoxLayout(self)
#        self.layout.setContentsMargins(0,3,0,3)
#        self.layout.setSizeConstraint(QLayout.SetNoConstraint)
#        self.layout.setVerticalSpacing(1)
#        self.layout.setHorizontalSpacing(1)

        self.editor = QTableView()
        self.editor.setModel(line.model())
        self.editor.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.editor.horizontalHeader().hide()
        self.editor.model().modelReset.connect(self.resetSizes)
        self.editor.model().dataChanged.connect(self.resetSizes)
        self.editor.model().columnsInserted.connect(self.resetSizes)
        self.editor.model().columnsRemoved.connect(self.resetSizes)

        self.editor.setContextMenuPolicy(Qt.CustomContextMenu)
        self.editor.customContextMenuRequested.connect(self.showContextMenu)

        self.layout.addWidget(self.editor)

        self.resetSizes()

        if "chord" not in self.editor.model().has:
            self.addChordsButton = QPushButton("Add Chords")
            self.addChordsButton.setFixedWidth(int(self.addChordsButton.sizeHint().height() * 4.5))
            self.addChordsButton.clicked.connect(self.addChordsButtonClicked)
            self.layout.addWidget(self.addChordsButton)

    def addChordsButtonClicked(self, _):
        self.editor.model().addChords()
        self.layout.removeWidget(self.addChordsButton)
        self.addChordsButton.deleteLater()

    def resetSizes(self, *args):
        ehsbsz = self.editor.horizontalScrollBar().sizeHint()
        self.editor.resizeColumnsToContents()
        self.editor.resizeRowsToContents()
        self.editor.setFixedHeight(self.editor.sizeHint().height() - ehsbsz.height())

    def showContextMenu(self, pos):
        print("scm", pos)
        menu = QMenu()

        acPrep = QAction("Prepend segment")
        acPrep.triggered.connect(lambda _: self.editor.model().insertColumn(self.editor.indexAt(pos).column()))
        menu.addAction(acPrep)

        acApp = QAction("Append segment")
        acApp.triggered.connect(lambda _: self.editor.model().insertColumn(self.editor.indexAt(pos).column()+1))
        menu.addAction(acApp)

        acDel = QAction("Delete segment")
        acDel.triggered.connect(lambda _: self.editor.model().removeColumn(self.editor.indexAt(pos).column()))
        menu.addAction(acDel)
        menu.exec(self.editor.mapToGlobal(pos))

class SongBlockContentsEditor(SongBlockAbstractEditor):
    def __init__(self, block):
        super().__init__(block)
        self.createEditor()

    def createEditor(self):
        if hasattr(self, "linesLayout"):
            while self.linesLayout.count() > 0:
                self.linesLayout.removeItem(item := self.linesLayout.itemAt(0))
                if (widget := item.widget()) is not None:
                    widget.deleteLater()

            self.layout.removeWidget(self.lines)
            self.lines.deleteLater()

        self.lines = QWidget()
        self.layout.addWidget(self.lines)
        self.layout.setSizeConstraint(QLayout.SetNoConstraint)

        self.linesLayout = QVBoxLayout(self.lines)
        self.linesLayout.setSpacing(0)
        self.linesLayout.setSizeConstraint(QLayout.SetNoConstraint)

        self.lineEditors = [ SongBlockLineEditor(i) for i in self.block.lines ]
        self.lineMaxWidth = max([ le.sizeHint().width() for le in self.lineEditors ])

        ple = None
        for le in self.lineEditors:
            self.linesLayout.addWidget(le)
            le.editor.setFixedWidth(self.lineMaxWidth)

            deleteButton = QPushButton("Delete line")
            deleteButton.setFixedWidth(int(deleteButton.sizeHint().height() * 4.5))
            deleteButton.clicked.connect(self.deleteLine(le.line))

            le.layout.addWidget(deleteButton)

            if ple is not None and ple.editor.model().isLyricsOnly() and le.editor.model().isLyricsOnly():
                ple.layout.addWidget(mergeChordsButton := QPushButton("Is Chords ↓"))
                mergeChordsButton.setFixedWidth(int(mergeChordsButton.sizeHint().height() * 4.5))
                mergeChordsButton.clicked.connect(self.mergeLinesAsChords(lyrics=le.line, chords=ple.line))

            ple = le

        self.linesLayout.addStretch(1)

        self.lines.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lines.customContextMenuRequested.connect(self.showContextMenu)

    def showContextMenu(self, pos):
        print("pos", pos)
        prevheight = self.lineEditors[0].size().height()

        for le in self.lineEditors[1:]:
            y = le.pos().y()
            h = le.size().height()
            if y + h / 3 >= pos.y() >= y - prevheight / 3:
                print("before line ", le.line)
                menu = QMenu()

                # This action destroys this view
                acSplit = QAction("Split block")
                acSplit.triggered.connect(self.splitBlock(le.line))
                menu.addAction(acSplit)

                menu.exec(self.lines.mapToGlobal(pos))
                return

            else:
                prevheight = h

    def deleteLine(self, line):
        def inner():
            self.block.deleteLine(line)
            self.createEditor()
        return inner

    def mergeLinesAsChords(self, lyrics, chords):
        def inner():
            self.block.mergeLinesAsChords(lyrics, chords)
            self.createEditor()
        return inner

    def splitBlock(self, before):
        def inner():
            self.blockUpdated.emit(self.block.split(before))
        return inner

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

