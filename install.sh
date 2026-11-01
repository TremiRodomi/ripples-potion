#!/bin/sh
# Ripple's Potion - Magical Chase installer for Linux/macOS.
#   ./install.sh                     opens the installer window
#   ./install.sh <source> <output folder> [--japanese] [--registry] [--disc-wav] [--numpad]
# <source>: MagicalChase.cue, MagicalChase.iso, /dev/sr0 or the mounted disc folder.
HERE="$(dirname "$0")/patcher"
if [ $# -ge 2 ]; then
  exec python3 "$HERE/install_magical_chase.py" "$@"
fi
# graphical installer; exit code 3 means no tkinter or no display: ask in text
python3 "$HERE/gui.py" "$@"
[ $? -eq 3 ] || exit
exec python3 "$HERE/install_magical_chase.py" --ask "$@"
