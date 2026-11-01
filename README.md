# Ripple's Potion

*A no-CD + modern Windows patch for Magical Chase (Windows 95, QUEST 1998)*

[日本語はこちら (Japanese)](README.ja.md)

Makes the 1998 QUEST PC port of Magical Chase run from the hard drive on
Windows 10/11 and on Linux (Wine). English menus by default, or keep the
original Japanese text.

This repository holds **only the patcher**. You need your own copy of the
game: the original CD, or a BIN/CUE image of it.

## Install

**Windows**: download `RipplesPotion.exe` from the
[Releases](https://github.com/TremiRodomi/ripples-potion/releases) page and run
it. Pick the disc drive or a `.cue`/`.iso` file, the install folder and the
options, then click **Install**. Nothing else is needed. (Some antivirus
programs distrust new, unsigned exes; if yours complains, use `install.bat`
below instead.)

**Windows, from the source**: install [Python 3](https://www.python.org/downloads/)
(tick *"Add python.exe to PATH"* during setup), then double-click
`install.bat` for the same window. You can also drag a `.cue` file onto it.

**Linux**: download `RipplesPotion-linux-x86_64` from the
[Releases](https://github.com/TremiRodomi/ripples-potion/releases) page, make
it executable (right-click › Properties › *Allow executing as program*, or
`chmod +x RipplesPotion-linux-x86_64`) and run it. Nothing else is needed to
install; to play you need Wine. Without a display it asks its questions in
the terminal instead, and it also takes the command-line options below. It
needs glibc 2.35 or newer (most distros from 2022 on).

**Linux, from the source**: run `./install.sh` for the same window. It needs
tkinter (`sudo dnf install python3-tkinter` on Fedora,
`sudo apt install python3-tk` on Debian/Ubuntu). Without it, or without a
display, the installer asks its questions in the terminal instead.

### Music

| | CD audio (recommended) | Disc WAV files |
|---|---|---|
| Quality | 44.1 kHz 16-bit stereo | 22 kHz 8-bit |
| Install | slower: reads the whole soundtrack | faster |
| Size | about 460 MB | about 115 MB |
| Needs | the disc or a BIN/CUE image | any source, including an ISO |

With CD audio, a track that can't be read (a scratched disc, a truncated
image) uses its disc WAV instead, so the install still finishes. The
installer lists which tracks fell back. If your disc is badly damaged, pick
the disc WAVs: only the data part of the disc is read.

### Options

| Option | Default | Command line |
|---|---|---|
| Menus and settings in English or the original Japanese | English | `--japanese` |
| Portable settings: `MCHASE.INI` in the game folder instead of the registry, so the folder can be moved, copied or kept on a USB stick | on | `--registry` turns it off |
| Arrow keys for movement (the original used numpad 8/2/4/6) | on | `--numpad` turns it off |
| [cnc-ddraw](https://github.com/FunkyFr3sh/cnc-ddraw) for scaled fullscreen and windowed play (downloaded from its GitHub release, 2.7 MB) | on | `--no-ddraw` turns it off |
| Disc WAV music instead of CD audio | off | `--disc-wav` |

### Command line

```
./install.sh <source> <output folder> [options]
install.bat <source> <output folder> [options]
python3 patcher/install_magical_chase.py <source> <output folder> [options]
```

| Source | Example |
|---|---|
| BIN/CUE image | `MagicalChase.cue` |
| Original disc, Linux | `/dev/sr0` or the mounted folder |
| Original disc, Windows | `D:` |
| ISO / copied disc folder | `MagicalChase.iso` (disc WAV music only) |

The output folder holds the patched `Mchase.exe`, `mus/TR01–19.WAV`, the
staff-credits viewer (`STAFF.EXE`), `magical-chase.sh` (Wine launcher) and,
unless `--no-ddraw`, cnc-ddraw (`ddraw.dll`, `ddraw.ini`, `Shaders/`,
`cnc-ddraw config.exe`).

To patch just the EXE (the original `RUN/MCHASE/SRC/Mchase.exe` from the
disc; it is checked by SHA-256):
`python3 patcher/patch_mchase.py [--japanese] [--registry] [--numpad] Mchase.exe Mchase_patched.exe`

## Running

**Windows 10/11**: run `Mchase.exe`.

**Linux (Wine)**: `./magical-chase.sh`. `--fullscreen` for Wine's own
fullscreen, `--window` for a plain unscaled 640×480 window, `--settings` for
the original AUTORUN settings screen.

**With cnc-ddraw** (the default) the game fills the screen at 4:3 with black
bars. **Alt+Enter** switches to a resizable window; the size and position
are remembered. To change how it looks, edit `ddraw.ini` (for example
`boxing=true` for sharp integer scaling) or, on Windows, run
`cnc-ddraw config.exe`. Reinstalling keeps your `ddraw.ini`.

**Without cnc-ddraw** the game switches the screen to 640×480 HiColor. You
can add cnc-ddraw later: put the `ddraw.dll` and `ddraw.ini` from its
[release zip](https://github.com/FunkyFr3sh/cnc-ddraw/releases) in the game
folder (the Linux launcher picks it up automatically).

## Controls

| Key | Action |
|---|---|
| Arrow keys | Move (numpad 8/2/4/6 with `--numpad`) |
| A | Shot |
| S | Option control |
| Enter | Start |
| Esc | Pause |
| Alt+P | Options (change keys, joystick, sound test, display) |
| Alt+Q | Quit |

**Changing keys**: press **Alt+P** (or *Settings › Options…* in the menu
bar), open the **Keyboard** tab, click a box (Up, Down, …), press the key
you want, then click **OK**. Keys are saved right away.

If you installed an earlier version of this patch, your old numpad keys are
still saved; change them with Alt+P as above. (Under Wine the boxes may say
`KP_Up` etc. for the arrow keys. That is only Wine's label: the game uses the
arrow keys.)

## What the patch changes

* **No CD check.** The game used to refuse to start unless AUTORUN.EXE passed
  it a secret `?GOPA242<drive>` argument. With no argument it now uses a
  built-in default and loads music from `<exe folder>\mus\` (the game's own
  WAV fallback), so no disc, install or `_inmm.dll` is needed.
* **32-bit desktops.** The game only draws in 8/16-bit color. It now always
  goes fullscreen at 640×480×16 (or ×8 if the `VideoMode` setting is 8)
  instead of copying the 32-bit desktop depth and quitting, and Alt+Enter
  no longer drops into a windowed mode that would crash.
* **Joystick crash** (divide by zero on some controllers): same fix as the
  official `mc_patch.exe`, so don't run that one on top.
* **Arrow keys** are the default movement keys (the original used the
  numpad, which most laptops don't have).
* **English** menus, Options pages, messages, joystick axis names and the
  music-test track names (in both resource languages, so it is English on
  Japanese Windows too). In-game story text is untouched. Skipped with
  `--japanese`.
* **Music always from the WAV files.** The CD Audio / WAV choice is gone
  (the installer already put the CD audio in `mus\`), and a CD Audio setting
  saved by the original game is ignored. The Sound page stays in
  Settings › Options as a music and sound-effect test; it used to appear only
  in AUTORUN's settings mode.
* **Portable settings** (unless `--registry`): the game's registry reads and
  writes go to `MCHASE.INI` next to `Mchase.exe` instead. Put the game in a
  folder you can write to (not `Program Files`).

Command-line options still work: `EGOPA242_` = force fullscreen,
`WGOPA242_D` = debug menu, `WGOPA242_ S` = settings screen.

Settings are stored in `MCHASE.INI` in the game folder, or in
`HKCU\Software\QUEST\MagicChase\1.0` with `--registry`.

## Files

* `install.bat` / `install.sh` – installers for Windows / Linux
* `.github/workflows/builds.yml` – builds `RipplesPotion.exe` and
  `RipplesPotion-linux-x86_64` with PyInstaller for each release
* `patcher/gui.py` – the installer window
* `patcher/install_magical_chase.py` – installer (image or disc → folder)
* `patcher/patch_mchase.py` – the EXE patcher
* `patcher/build_cave.py` – developer tool: assembles the patch code (needs
  `keystone-engine`) and prints the hex blobs used in `patch_mchase.py`

## License

The patcher is MIT licensed (see `LICENSE`). Magical Chase itself is © QUEST /
Palsoft; this project contains no game data. cnc-ddraw is © FunkyFr3sh (MIT)
and is downloaded from its own release, not included here.
