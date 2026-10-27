#!/bin/sh
# Magical Chase installer for Linux/macOS.
#   ./install.sh <source> <output folder> [--japanese] [--portable] [--disc-wav] [--numpad]
# <source>: MagicalChase.cue, MagicalChase.iso, /dev/sr0 or the mounted disc folder.
exec python3 "$(dirname "$0")/patcher/install_magical_chase.py" "$@"
