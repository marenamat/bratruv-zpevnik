from qtpy.QtCore import (
        Qt,
        QAbstractListModel,
        QAbstractTableModel,
        QModelIndex,
        QVariant,
        )

from yangson import DataModel
import json

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

class SongBlockIndex(QAbstractListModel):
    def __init__(self, song):
        super().__init__()

        self.blocks = { d.name: d for d in song.blocks }
        self.ordered = sorted(self.blocks)

    def __contains__(self, what):
        return what in self.blocks

    def add(self, what):
        assert(what.name not in self.blocks)
        self.blocks[what.name] = what

        nord = sorted(self.blocks)
        ni = nord.index(what.name)

        self.beginInsertRows(QModelIndex(), ni, ni)
        self.ordered = nord
        self.endInsertRows()

    def remove(self, what):
        assert(what.name in self.blocks)
        oi = self.ordered.index(what.name)
        del self.blocks[what.name]

        self.beginRemoveRows(QModelIndex(), oi, oi)
        self.ordered = sorted(self.blocks)
        self.endRemoveRows()

    def rowCount(self, index):
        return len(self.ordered)

    data_dispatcher = {
            Qt.DisplayRole: lambda self, index: self.ordered[index.row()],
            }

    def data(self, index, role):
        if role in self.data_dispatcher:
            return self.data_dispatcher[role](self, index)
        else:
            return QVariant()

class Song:
    def __init__(self, songbook, data):
        self.data = data
        self.title = str(data["name"])
        self.authors = [ songbook.author_index[str(a)] for a in data["authors"] ]
        self.blocks = [
                SongBlockRef(d) if "ref" in d else SongBlockContents(d)
                for d in data["blocks"]
                ] if "blocks" in data else []

        self.blockRefModel = SongBlockIndex(self)

    def displayAuthorList(self):
        return ", ".join([ a.name for a in self.authors ])

    def blockAutoName(self):
        cnt = 0
        while (bn := f"_ab_{cnt}") in self.blockRefModel:
            cnt += 1

        return bn

    def refBlocks(self, blocks):
        for b in blocks:
            if b.name == "":
                b.name = self.blockAutoName()
            elif b.name in self.blockRefModel:
                raise Exception("Multiple blocks with the same index")

            self.blockRefModel.add(b)

    def unrefBlocks(self, blocks):
        for b in blocks:
            self.blockRefModel.remove(b)

    def insert(self, after, block):
        self.refBlocks([block])

        index = self.blocks.index(after) if after is not None else 0
        self.blocks = self.blocks[:index] + [block] + self.blocks[index:]

    def replace(self, old, new):
        self.unrefBlocks([old])
        self.refBlocks(new)

        index = self.blocks.index(old)
        self.blocks = self.blocks[:index] + new + self.blocks[index+1:]

        self.cleanup()

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

    def songListModel(self):
        return SongListModel(self)

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
