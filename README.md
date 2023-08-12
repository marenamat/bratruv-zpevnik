# Universal SongBook

This is an attempt to create a versatile song-along and play-along electronic
songbook with some cool features. The base for this project is Bratrův zpěvník
which I forked and did some file format updates to allow for implementation of
these features.

## Planned features

* keep TeX output possibility
* autotranspose / capo
* unfolding chorus portions to avoid upscrolling
* autoscroll based on rhythm
* metronome and song position auto-indication
* synchronized song-along with multiple instances
* inline display of tabulatures, melody lines or intermezzos

## File Format

Universal SongBook Format is a container described by YANG. The songs are split
to named blocks (verses, chori, etc.), then to lines and these to segments.
Every segment has its lyrics part and chorus part. In future, these segments
will have assigned time duration to enable for autoscroll and current segment
highlighting.

Blocks with names beginning with an underscore `_` are considered *technical*
and are shown without these names.

The description of this format is in `sbf/universal-songbook-format.yang`.

I dropped the LaTeX parser from the web app and it's now using the JSON
directly. However, I broke some features on my way so fixes are needed.

## Editor

Needs `yangson` to run, install by `pip`. Use on your risks, pull requests for
verbesserungen deeply appreciated.

## Text-Friendly SongBook Format

To allow editing songs in plain text editors, there is also a special `tfsbf` format
intended to be easily converted from/to the JSON format by a script. Now only
the `tfsbf` generator exists; the back-convertor is to be done soon.

This format begins each line with a 4-letter signature and a space (which may be omitted
if the whole line is just the signature).

- `SONG`: begin of song
- `TITL (text)`: name of song
- `AUTH (text)`: author of song (may be repeated)
- `BLCK (id)`: block begin with a given ID
- `REFR (id)`: a reference to another block
- `LYRI (text)`: lyrics; fill with `~` to match the chord line in length
- `CHRD (chords)`: chords matched with the lyrics *under* them
- `ENDS`: end of song

*(list to be updated as new features come by)*

## TODO

### Critical
- fix TeX import to properly import references
- check that the TeX import works correctly
- Webapp: fix in-word hyphens in segments where the chord is too long
- Webapp: fix now-broken

### High
- Webapp: fix capo display
- Webapp: fix chord display to show 7's and others as superscripts
- Webapp: read JSON directly
- Webapp: chorus unfolding
- Editor: join blocks, save block names
- TeX export

### Medium
- File Format: more systematic chord storage than just a string
- Time signature, tempo, segment timing
- Webapp: run, autoscroll, show current segment
- Webapp: auto key transpose
- Tabulatures
- Melodies for singing, vocals or other instruments (Lilypond integration!)
- Editor: fix trailing focus by unselecting segment edit fields
  by inheriting QTableView() and implementing focusOutEvent()

### Low
- Webapp: favourites
- Webapp: create PDF from my favourites
- Webapp: synchronized play-sing-along between multiple sessions
- Editor: undo feature
- Editor: File open / save-as dialog
