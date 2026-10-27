# Magical Chase (Windows 95) – no-CD + modern Windows patch

[日本語はこちら (Japanese)](README.ja.md)

Makes the 1998 QUEST PC port of Magical Chase run from the hard drive on
Windows 10/11 and on Linux (Wine). English menus by default, or keep the
original Japanese text with `--japanese`.

This repository holds **only the patcher**. You need your own copy of the
game: the original CD, or a BIN/CUE image of it.

## Install

You need [Python 3](https://www.python.org/downloads/) (nothing else; on
Windows tick *"Add python.exe to PATH"* during setup).

**Windows**: double-click `install.bat` and answer the questions, or drag
the `.cue` file onto it. It can read the disc directly too: enter its drive
letter, e.g. `D:`.

**Linux / command line**:

```
./install.sh <source> <output folder> [options]
python3 patcher/install_magical_chase.py <source> <output folder> [options]
```

| Source | Example | Music |
|---|---|---|
| BIN/CUE image | `MagicalChase.cue` | CD quality (ripped from the audio tracks) |
| Original disc, Linux | `/dev/sr0` or the mounted folder | CD quality |
| Original disc, Windows | `D:` | CD quality |
| ISO / copied disc folder | `MagicalChase.iso` | disc WAVs (22 kHz 8-bit) |

| Option | Effect |
|---|---|
| `--japanese` | Keep the original Japanese menus, dialogs and messages. All fixes are still applied. |
| `--portable` | Save settings in `MCHASE.INI` in the game folder instead of the Windows registry, so the folder can be moved, copied or kept on a USB stick. |
| `--numpad` | Keep the original default keys (numpad 8/2/4/6) instead of the arrow keys. |
| `--disc-wav` | Use the disc's smaller 22 kHz WAVs instead of ripping the CD audio. |

The output folder holds the patched `Mchase.exe`, `mus/TR01–19.WAV`, the
staff-credits viewer (`STAFF.EXE`) and `magical-chase.sh` (Wine launcher).

To patch just the EXE (the original `RUN/MCHASE/SRC/Mchase.exe` from the
disc; it is checked by SHA-256):
`python3 patcher/patch_mchase.py [options] Mchase.exe Mchase_patched.exe`

## Running

**Windows 10/11**: run `Mchase.exe`. It switches the screen to 640×480
HiColor. For a window or scaling, see cnc-ddraw below.

**Linux (Wine)**: `./magical-chase.sh`. `--fullscreen` for fullscreen,
`--window` for a plain unscaled 640×480 window, `--settings` for the
original AUTORUN settings screen.

**Bigger window / scaling (recommended)**: download the latest
[cnc-ddraw](https://github.com/FunkyFr3sh/cnc-ddraw/releases) zip and put its
`ddraw.dll` and `ddraw.ini` in the game folder (the Linux launcher picks it
up automatically). In `ddraw.ini` set for example `windowed=true`,
`width=1920`, `height=1440`, `maintas=true` (keep 4:3), and optionally
`boxing=true` for sharp integer scaling. Use `fullscreen=true` instead for
scaled borderless fullscreen.

## Controls

| Key | Action |
|---|---|
| Arrow keys | Move (numpad 8/2/4/6 with `--numpad`) |
| A | Shot |
| S | Option control |
| Enter | Start |
| Esc | Pause |
| Alt+P | Options (change keys, joystick, sound, display) |
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
* **Sound page always available** in Settings › Options (CD Audio vs WAV,
  music/SE test). It used to appear only in AUTORUN's settings mode.
  "CD Audio" plays from the first CD drive like the original did.
* **Portable settings** (optional, `--portable`): the game's registry reads
  and writes go to `MCHASE.INI` next to `Mchase.exe` instead. Put the game in
  a folder you can write to (not `Program Files`).

Command-line options still work: `EGOPA242_` = force fullscreen,
`WGOPA242_D` = debug menu, `WGOPA242_ S` = settings screen,
`WGOPA242Q` = play CD audio from drive Q:.

Settings are stored in `HKCU\Software\QUEST\MagicChase\1.0` (or in
`MCHASE.INI` with `--portable`).

## Files

* `install.bat` / `install.sh` – installers for Windows / Linux
* `patcher/install_magical_chase.py` – installer (image or disc → folder)
* `patcher/patch_mchase.py` – the EXE patcher
* `patcher/build_cave.py` – developer tool: assembles the patch code (needs
  `keystone-engine`) and prints the hex blobs used in `patch_mchase.py`

## License

The patcher is MIT licensed (see `LICENSE`). Magical Chase itself is © QUEST /
Palsoft; this project contains no game data.
