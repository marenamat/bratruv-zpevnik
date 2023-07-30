# Universal SongBook Format

The need for a versatile song-along and play-along songbook brings a need for
an universal format, available for simple machine processing allowing more features
than a simple songbook display.

## Planned features

* keep TeX output possibility
* unfolding chorus portions to avoid upscrolling
* autoscroll based on rhythm
* metronome and song position auto-indication
* synchronized song-along with multiple instances
* inline display of tabulatures, melody lines or intermezzos

## Structure

Universal SongBook Format is a container described by YANG, thus freely
convertible between JSON, XML and CBOR. See `universal-songbook-format.yang`.

## Editor

Needs `yangson` to run, install by `pip`.

## TODO

### Critical
- TeX import

### High
- Webapp: read JSON directly
- Webapp: chorus unfolding
- Editor: split segment, delete segment
- TeX export

### Mid
- More automatics in TeX
- Time signature, tempo, segment timing
- Webapp: run, autoscroll, show current segment
- Tabulatures
- Melodies

### Low
- Webapp: favourites
- Webapp: create PDF from my favourites
- Webapp: synchronized play-sing-along between multiple sessions
- Editor: undo feature
- Editor: File open / save-as dialog
