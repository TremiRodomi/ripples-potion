#!/usr/bin/env python3
"""
Install Magical Chase (Windows 95) to a folder - no CD needed afterwards, no
AUTORUN.EXE, no InstallShield - and apply patch_mchase.py.

Usage:
    python3 install_magical_chase.py <source> <output folder> [options]
    python3 install_magical_chase.py --ask [source]     asks the questions
    python3 gui.py [source]                             graphical installer

<source> can be any of:
    MagicalChase.cue        a BIN/CUE image (single or one-file-per-track)
    /dev/sr0                Linux: the original disc in a drive
    D:                      Windows: the original disc in a drive
    /run/media/you/MCHASE   a mounted disc (Linux: its drive is found automatically)
    MagicalChase.iso        data-only image (no CD audio, so disc WAVs are used)

    --disc-wav   use the 22 kHz 8-bit MUS\\*.WAV files from the disc instead of
                 the 44.1 kHz CD audio tracks (smaller, lower quality, faster;
                 also handy for a scratched disc). Without it, any CD audio
                 track that can't be read falls back to its disc WAV anyway.
    --japanese   keep the original Japanese menus, dialogs and in-game text
                 (only the compatibility fixes are applied)
    --numpad     keep the original default keys (numpad 8/2/4/6) instead of
                 the arrow keys
    --no-ddraw   don't download cnc-ddraw (by default it is downloaded from
                 its GitHub release and set up for scaled 4:3 fullscreen;
                 Alt+Enter switches to a window)
    --registry   save settings in the Windows registry like the original game,
                 instead of MCHASE.INI in the game folder (the default, which
                 lets the folder be moved or copied)

Result:
    <output>/Mchase.exe         patched game
    <output>/mus/TR01-19.WAV    music (CD quality by default)
    <output>/STAFF.EXE + BMPs   staff-credits viewer from the disc
    <output>/magical-chase.sh   Linux/Wine launcher (not written on Windows)
    <output>/ddraw.dll, ddraw.ini, Shaders/, cnc-ddraw config.exe   (cnc-ddraw)

Only the Python 3 standard library is needed.
"""
import ctypes
import hashlib
import io
import os
import re
import struct
import sys
import textwrap
import urllib.request
import wave
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import patch_mchase  # noqa: E402

GAME_FILES = ['Mchase.exe', 'STAFF.EXE', 'STAFF.BMP', 'STAFF8C.BMP']
CDDA_SECTOR = 2352            # bytes of 44.1 kHz 16-bit stereo per CD sector
CDDA_FRAMES = CDDA_SECTOR // 4


# --------------------------------------------------------------------------
# Sources. Each source offers:
#   read_file(path) -> bytes      file from the data track
#   audio_tracks                  list of (read(offset, n) -> raw CDDA bytes,
#                                          length in sectors), one per audio track
# --------------------------------------------------------------------------
class ISO9660:
    """Read files from an ISO 9660 filesystem given a sector reader."""

    def __init__(self, sector):
        self.sector = sector
        pvd = sector(16)
        if pvd[1:6] != b'CD001':
            raise ValueError('data track is not ISO 9660')
        self.root = self._rec(pvd, 156)

    def _read(self, lba, size):
        out = bytearray()
        for i in range((size + 2047) // 2048):
            out += self.sector(lba + i)
        return bytes(out[:size])

    @staticmethod
    def _rec(b, o):
        nlen = b[o + 32]
        return dict(len=b[o], lba=struct.unpack_from('<I', b, o + 2)[0],
                    size=struct.unpack_from('<I', b, o + 10)[0],
                    name=b[o + 33:o + 33 + nlen].decode('latin-1').split(';')[0])

    def _listdir(self, d):
        data = self._read(d['lba'], d['size'])
        o, out = 0, []
        while o < len(data):
            if data[o] == 0:
                o = (o // 2048 + 1) * 2048
                continue
            r = self._rec(data, o)
            if r['name'] not in ('\x00', '\x01'):
                out.append(r)
            o += r['len']
        return out

    def read_file(self, path):
        cur = self.root
        for part in path.split('/'):
            for r in self._listdir(cur):
                if r['name'].upper() == part.upper():
                    cur = r
                    break
            else:
                raise FileNotFoundError(path)
        return self._read(cur['lba'], cur['size'])


class CueSource:
    def __init__(self, path):
        self.tracks = self._parse(path)
        data = self.tracks[0]
        self.iso = ISO9660(lambda lba: self._sector(data, lba))
        self.read_file = self.iso.read_file
        self.audio_tracks = [(lambda off, n, t=t: self._audio(t, off, n), t['length'])
                             for t in self.tracks if t['mode'] == 'AUDIO']

    @staticmethod
    def _parse(path):
        base = os.path.dirname(os.path.abspath(path))
        tracks, cur_file = [], None
        for line in open(path, encoding='latin-1'):
            line = line.strip()
            m = (re.match(r'FILE\s+"(.*)"\s+(\S+)', line) or
                 re.match(r'FILE\s+(\S+)\s+(\S+)', line))
            if m:
                cur_file = os.path.join(base, m.group(1))
                continue
            m = re.match(r'TRACK\s+(\d+)\s+(\S+)', line)
            if m:
                tracks.append(dict(mode=m.group(2).upper(), file=cur_file, idx={}))
                continue
            m = re.match(r'INDEX\s+(\d+)\s+(\d+):(\d+):(\d+)', line)
            if m:
                i, mm, ss, ff = map(int, m.groups())
                tracks[-1]['idx'][i] = (mm * 60 + ss) * 75 + ff
        for i, t in enumerate(tracks):
            t['ssize'] = 2048 if t['mode'] == 'MODE1/2048' else CDDA_SECTOR
            nxt = tracks[i + 1] if i + 1 < len(tracks) else None
            if nxt and nxt['file'] == t['file']:
                end = min(nxt['idx'].values())
            else:
                end = os.path.getsize(t['file']) // t['ssize']
            t['start'], t['length'] = t['idx'][1], end - t['idx'][1]
        return tracks

    @staticmethod
    def _sector(t, lba):
        with open(t['file'], 'rb') as f:
            f.seek((t['start'] + lba) * t['ssize'])
            raw = f.read(t['ssize'])
        if t['ssize'] == 2048:
            return raw
        return raw[24:24 + 2048] if t['mode'] == 'MODE2/2352' else raw[16:16 + 2048]

    @staticmethod
    def _audio(t, off, n):
        with open(t['file'], 'rb') as f:
            f.seek((t['start'] + off) * CDDA_SECTOR)
            return f.read(n * CDDA_SECTOR)


class IsoFileSource:
    def __init__(self, path):
        self.f = open(path, 'rb')
        self.iso = ISO9660(self._sector)
        self.read_file = self.iso.read_file
        self.audio_tracks = []

    def _sector(self, lba):
        self.f.seek(lba * 2048)
        return self.f.read(2048)


class FolderSource:
    """A mounted disc where the drive itself can't be opened: files only."""

    def __init__(self, root):
        self.root = root
        self.audio_tracks = []

    def read_file(self, path):
        cur = self.root
        for part in path.split('/'):
            names = {n.upper(): n for n in os.listdir(cur)}
            cur = os.path.join(cur, names[part.upper()])
        return open(cur, 'rb').read()


class LinuxDrive:
    CDROMREADTOCHDR, CDROMREADTOCENTRY, CDROMREADAUDIO = 0x5305, 0x5306, 0x530E
    CDROM_LBA, CDROM_LEADOUT = 0x01, 0xAA

    class TocEntry(ctypes.Structure):
        _fields_ = [('track', ctypes.c_ubyte), ('adr_ctrl', ctypes.c_ubyte),
                    ('format', ctypes.c_ubyte), ('lba', ctypes.c_int),
                    ('datamode', ctypes.c_ubyte)]

    class ReadAudio(ctypes.Structure):
        _fields_ = [('lba', ctypes.c_int), ('addr_format', ctypes.c_ubyte),
                    ('nframes', ctypes.c_int), ('buf', ctypes.c_void_p)]

    def __init__(self, dev):
        import fcntl
        self.ioctl = fcntl.ioctl
        self.fd = os.open(dev, os.O_RDONLY | os.O_NONBLOCK)
        hdr = bytearray(2)
        self.ioctl(self.fd, self.CDROMREADTOCHDR, hdr)
        toc = []
        for trk in list(range(hdr[0], hdr[1] + 1)) + [self.CDROM_LEADOUT]:
            e = self.TocEntry(track=trk, format=self.CDROM_LBA)
            self.ioctl(self.fd, self.CDROMREADTOCENTRY, e)
            toc.append((e.lba, bool((e.adr_ctrl >> 4) & 4)))
        setup_toc(self, toc)

    def raw_data(self, lba):
        return os.pread(self.fd, 2048, lba * 2048)

    def raw_audio(self, lba, n):
        buf = ctypes.create_string_buffer(n * CDDA_SECTOR)
        ra = self.ReadAudio(lba=lba, addr_format=self.CDROM_LBA, nframes=n,
                            buf=ctypes.addressof(buf))
        self.ioctl(self.fd, self.CDROMREADAUDIO, ra)
        return buf.raw


class WindowsDrive:
    IOCTL_CDROM_READ_TOC, IOCTL_CDROM_RAW_READ = 0x24000, 0x2403E

    def __init__(self, letter):
        from ctypes import wintypes
        k = ctypes.WinDLL('kernel32', use_last_error=True)
        k.CreateFileW.restype = wintypes.HANDLE
        k.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                  ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
                                  wintypes.HANDLE]
        k.DeviceIoControl.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p,
                                      wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
                                      ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
        k.ReadFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                               ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
        k.SetFilePointerEx.argtypes = [wintypes.HANDLE, ctypes.c_longlong,
                                       ctypes.c_void_p, wintypes.DWORD]
        self.k, self.DWORD = k, wintypes.DWORD
        self.h = k.CreateFileW('\\\\.\\%s:' % letter, 0x80000000, 3, None, 3, 0, None)
        if self.h in (None, ctypes.c_void_p(-1).value):
            raise OSError(ctypes.get_last_error(), 'cannot open drive %s:' % letter)
        out = ctypes.create_string_buffer(804)
        self._ioctl(self.IOCTL_CDROM_READ_TOC, None, 0, out)
        b = out.raw
        first, last = b[2], b[3]
        toc = []
        for i in range(last - first + 2):          # tracks + lead-out
            e = b[4 + 8 * i:12 + 8 * i]
            lba = (e[5] * 60 + e[6]) * 75 + e[7] - 150
            toc.append((lba, bool(e[1] & 4)))
        setup_toc(self, toc)

    def _ioctl(self, code, inbuf, inlen, out):
        n = self.DWORD()
        if not self.k.DeviceIoControl(self.h, code, inbuf, inlen, out, len(out),
                                      ctypes.byref(n), None):
            raise OSError(ctypes.get_last_error(), 'DeviceIoControl %#x failed' % code)
        return n.value

    def raw_data(self, lba):
        buf = ctypes.create_string_buffer(2048)
        n = self.DWORD()
        self.k.SetFilePointerEx(self.h, lba * 2048, None, 0)
        if not self.k.ReadFile(self.h, buf, 2048, ctypes.byref(n), None):
            raise OSError(ctypes.get_last_error(), 'ReadFile failed')
        return buf.raw

    def raw_audio(self, lba, n):
        info = ctypes.create_string_buffer(struct.pack('<qII', lba * 2048, n, 2), 16)
        out = ctypes.create_string_buffer(n * CDDA_SECTOR)
        self._ioctl(self.IOCTL_CDROM_RAW_READ, info, 16, out)
        return out.raw


def setup_toc(drive, toc):
    """toc: [(start_lba, is_data)] for every track plus the lead-out."""
    data_start = next(lba for lba, is_data in toc[:-1] if is_data)
    drive.iso = ISO9660(lambda lba: drive.raw_data(data_start + lba))
    drive.read_file = drive.iso.read_file
    def read_audio(lba, n):
        for attempt in range(4):
            try:
                return drive.raw_audio(lba, n)
            except OSError:
                if attempt == 3:
                    raise
    drive.audio_tracks = [(lambda off, n, s=lba: read_audio(s + off, n), toc[i + 1][0] - lba)
                          for i, (lba, is_data) in enumerate(toc[:-1]) if not is_data]


def mount_to_device(path):
    """Linux: the optical drive a mounted CD folder lives on, or None."""
    try:
        path = os.path.realpath(path)
        best = None
        for line in open('/proc/mounts'):
            dev, mnt, fstype = line.split()[:3]
            mnt = mnt.replace('\\040', ' ')
            if fstype not in ('iso9660', 'udf'):
                continue
            if (path == mnt or path.startswith(mnt.rstrip('/') + '/')) and \
                    (best is None or len(mnt) > len(best[1])):
                best = (dev, mnt)
        if best and best[0].startswith('/dev/'):
            return best[0]
    except OSError:
        pass
    return None


def open_source(src):
    low = src.lower()
    if low.endswith('.cue'):
        return CueSource(src)
    if low.endswith('.iso'):
        return IsoFileSource(src)
    if os.name == 'nt':
        m = re.match(r'^(?:\\\\\.\\)?([A-Za-z]):\\?$', src)
        if m:
            try:
                return WindowsDrive(m.group(1).upper())
            except OSError as e:
                print('Could not read the drive directly (%s); copying files only.' % e)
                return FolderSource(m.group(1) + ':\\')
    if os.path.isdir(src):
        dev = mount_to_device(src) if os.name != 'nt' else None
        if dev:
            try:
                return LinuxDrive(dev)
            except OSError as e:
                print('Could not read %s directly (%s); copying files only.' % (dev, e))
        return FolderSource(src)
    if os.name != 'nt':
        try:
            return LinuxDrive(src)
        except OSError as e:
            raise SystemExit('Cannot read %s: %s (is the disc inserted?)' % (src, e.strerror or e))
    raise SystemExit('Unrecognised source: %s' % src)


# --------------------------------------------------------------------------
# cnc-ddraw (MIT licence, https://github.com/FunkyFr3sh/cnc-ddraw): a DirectDraw
# replacement that scales the 640x480 game to any window or screen size.
# A fixed release is downloaded and checked, so nothing unexpected is installed.
DDRAW_URL = ('https://github.com/FunkyFr3sh/cnc-ddraw/releases/download/'
             'v7.1.0.0/cnc-ddraw.zip')
DDRAW_SHA256 = '0b13ab89a64c9918189b1dadd449ef6ed3cb3b7b19cabd96d8adbd95505bb908'
# Scaled borderless fullscreen keeping 4:3 (fits any screen); Alt+Enter
# switches to a resizable window. devmode=true leaves the cursor free
# ("Lock cursor" off in cnc-ddraw config.exe), so the game's own settings
# menu can be reached in fullscreen.
DDRAW_SETTINGS = dict(fullscreen='true', windowed='true', maintas='true',
                      aspect_ratio='4:3', devmode='true')


def add_cnc_ddraw(out, log):
    """Download cnc-ddraw into <out>. An existing ddraw.ini is kept. Failure
    is only a warning: the game runs without it."""
    try:
        with urllib.request.urlopen(DDRAW_URL, timeout=60) as r:
            blob = r.read()
        if hashlib.sha256(blob).hexdigest() != DDRAW_SHA256:
            raise ValueError('the download does not match the expected file')
        z = zipfile.ZipFile(io.BytesIO(blob))
    except (OSError, ValueError, zipfile.BadZipFile) as e:
        log('cnc-ddraw not installed (%s). The game still works; see the README to '
            'add it by hand.' % e)
        return
    keep_ini = os.path.exists(os.path.join(out, 'ddraw.ini'))
    for info in z.infolist():
        parts = info.filename.replace('\\', '/').split('/')
        if info.is_dir() or '..' in parts or info.filename.startswith('/'):
            continue
        if parts == ['ddraw.ini'] and keep_ini:
            continue
        dst = os.path.join(out, *parts)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        data = z.read(info)
        if parts == ['ddraw.ini']:
            data = ddraw_ini(data)
        open(dst, 'wb').write(data)
    log('   cnc-ddraw (scaled fullscreen, Alt+Enter for a window)' +
        ('; kept your ddraw.ini' if keep_ini else ''))


def ddraw_ini(data):
    """Apply DDRAW_SETTINGS to the global [ddraw] section of ddraw.ini."""
    text = data.decode('latin-1')
    m = re.search(r'^\[(?!ddraw\])', text, re.M)    # first game-specific section
    head, rest = (text[:m.start()], text[m.start():]) if m else (text, '')
    for key, value in DDRAW_SETTINGS.items():
        head, n = re.subn(r'(?m)^%s=.*?(\r?)$' % key, r'%s=%s\1' % (key, value), head)
        if not n:
            head = head.replace('[ddraw]', '[ddraw]\r\n%s=%s' % (key, value), 1)
    return (head + rest).encode('latin-1')


# --------------------------------------------------------------------------
# The music choice as the installers (GUI and install.bat) explain it.
MUSIC_CHOICES = [
    ('cd', 'CD audio (recommended)', [
        '+ Best quality: 44.1 kHz 16-bit stereo',
        '- Slower install: reads the whole soundtrack',
        '- Takes more space: about 460 MB',
        'A track that can\'t be read (scratched disc) uses its disc WAV '
        'instead, so the install still finishes.',
    ]),
    ('wav', 'Disc WAV files', [
        '+ Faster install, and smaller: about 115 MB',
        '+ Good for a damaged disc or an ISO',
        '- Lower quality: 22 kHz 8-bit',
    ]),
]

LAUNCHER = r'''#!/bin/sh
# Magical Chase launcher for Wine.
#   ./magical-chase.sh               normal start (see below)
#   ./magical-chase.sh --fullscreen  real fullscreen (Wine/the desktop scales 640x480)
#   ./magical-chase.sh --window      plain 640x480 Wine window (no scaling)
#   ./magical-chase.sh --settings    AUTORUN's original settings screen
# If cnc-ddraw's ddraw.dll is in this folder, the normal start uses it, so the
# game is scaled to whatever window/fullscreen size ddraw.ini asks for.
# Otherwise the normal start is the same as --window.
# WINEPREFIX is respected; set it to keep the game's settings separate.
cd "$(dirname "$0")" || exit 1
EXE="$(winepath -w "$PWD/Mchase.exe")"
VDESK="explorer /desktop=MagicalChase,640x480"
if [ -f ddraw.dll ] || [ -f DDRAW.DLL ]; then
  export WINEDLLOVERRIDES="ddraw=n,b${WINEDLLOVERRIDES:+;$WINEDLLOVERRIDES}"
  VDESK=""
fi
case "$1" in
  --fullscreen) exec wine "$EXE" ;;
  --window)     exec wine explorer /desktop=MagicalChase,640x480 "$EXE" ;;
  --settings)   exec wine $VDESK "$EXE" WGOPA242_ S ;;
  *)            exec wine $VDESK "$EXE" ;;
esac
'''


def wav_frames(disc_wav):
    ch, rate = struct.unpack_from('<HI', disc_wav, 22)
    bits = struct.unpack_from('<H', disc_wav, 34)[0]
    m = disc_wav.find(b'data', 12)
    return struct.unpack_from('<I', disc_wav, m + 4)[0] // (ch * bits // 8), rate


def install(src, out, disc_wav=False, japanese=False, arrow_keys=True,
            portable=True, ddraw=True, log=print, progress=None):
    """Copy, patch and rip everything into <out>. log(text) reports each
    step; progress(text) (optional) reports a step still running."""
    progress = progress or (lambda text: print('\r' + text.ljust(70), end='', flush=True))
    source = open_source(src)
    os.makedirs(os.path.join(out, 'mus'), exist_ok=True)

    for name in GAME_FILES:
        blob = source.read_file('RUN/MCHASE/SRC/' + name)
        if name == 'Mchase.exe':
            h = hashlib.sha256(blob).hexdigest()
            if h not in patch_mchase.ORIGINAL_SHA256:
                raise SystemExit('Unexpected Mchase.exe on this disc (sha256 %s)' % h)
            blob = patch_mchase.patch(blob, japanese=japanese, arrow_keys=arrow_keys,
                                      portable=portable)
        open(os.path.join(out, name), 'wb').write(blob)
        log('   ' + name)

    audio = source.audio_tracks
    use_cd = not disc_wav and len(audio) >= 19
    if not disc_wav and not use_cd:
        log('No CD audio tracks available from this source; using the disc WAV files.')
    fallbacks = []
    for n in range(1, 20):
        disc = source.read_file('MUS/TR%02d.WAV' % n)
        dst = os.path.join(out, 'mus', 'TR%02d.WAV' % n)
        if use_cd:
            try:
                rip_track(audio[n - 1], disc, dst, n, progress)
                log('   mus/TR%02d.WAV' % n)
                continue
            except (OSError, ValueError) as e:
                fallbacks.append(n)
                log('   mus/TR%02d.WAV: CD audio unreadable (%s), using the disc WAV' % (n, e))
        else:
            log('   mus/TR%02d.WAV (disc WAV)' % n)
        open(dst, 'wb').write(disc)
    if fallbacks:
        log('%d track(s) use the lower quality disc WAV: %s' % (
            len(fallbacks), ', '.join('TR%02d' % n for n in fallbacks)))

    if ddraw:
        add_cnc_ddraw(out, log)

    if os.name != 'nt':                 # the Wine launcher is useless on Windows
        sh = os.path.join(out, 'magical-chase.sh')
        open(sh, 'w', newline='\n').write(LAUNCHER)
        os.chmod(sh, 0o755)


def rip_track(track, disc, dst, n, progress):
    """Rip CD audio track for disc WAV n to dst. Disc WAV n == CD audio track
    n+1; the CD track is cut to the WAV's exact length (each CD track ends
    with a few seconds of silence/pregap)."""
    frames, rate = wav_frames(disc)
    read, length = track
    want = min(round(frames * 44100 / rate), length * CDDA_FRAMES)
    sectors = (want + CDDA_FRAMES - 1) // CDDA_FRAMES
    pcm = bytearray()
    for off in range(0, sectors, 20):
        cnt = min(20, sectors - off)
        chunk = read(off, cnt)
        if len(chunk) < cnt * CDDA_SECTOR:       # truncated image file
            raise ValueError('image file ends early')
        pcm += chunk
        progress('   mus/TR%02d.WAV  %3d%%' % (n, 100 * (off + cnt) // sectors))
    progress('')
    w = wave.open(dst, 'wb')
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(44100)
    w.writeframes(bytes(pcm[:want * 4]))
    w.close()


def ask(src=''):
    """Text-mode questions, for when the graphical installer can't run."""
    def yes(question, default):
        ans = input('%s (%s): ' % (question, 'Y/n' if default else 'y/N')).strip().lower()
        return default if not ans else ans.startswith('y')

    src = src or input('Disc drive (e.g. D: or /dev/sr0) or .cue / .iso file: ').strip('" ')
    default_out = os.path.join(os.path.expanduser('~'), 'Games', 'MagicalChase')
    out = input('Install folder [%s]: ' % default_out).strip('" ') or default_out
    print('\nMusic:')
    for i, (_, label, lines) in enumerate(MUSIC_CHOICES, 1):
        print('  %d. %s' % (i, label))
        for line in lines:
            print(textwrap.fill(line, 76, initial_indent='       ',
                                subsequent_indent='         '))
    disc_wav = input('Choose 1 or 2 [1]: ').strip() == '2'
    print()
    japanese = yes('Keep the original Japanese menus, dialogs and in-game text?', False)
    portable = yes('Save settings in the game folder (portable)?', True)
    ddraw = yes('Download cnc-ddraw for scaled fullscreen / bigger window?', True)
    print()
    log = lambda text: print('\r' + text.ljust(70))  # noqa: E731
    install(src, out, disc_wav=disc_wav, japanese=japanese, portable=portable,
            ddraw=ddraw, log=log)
    print('\nStart the game with "%s"' % os.path.join(
        out, 'Mchase.exe' if os.name == 'nt' else 'magical-chase.sh'))


def main():
    flags = {a for a in sys.argv[1:] if a.startswith('--')}
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if '--ask' in flags:
        try:
            return ask(args[0] if args else '')
        except (KeyboardInterrupt, EOFError):
            sys.exit('\nCancelled.')
    known = {'--disc-wav', '--japanese', '--numpad', '--registry', '--portable',
             '--no-ddraw'}
    if len(args) != 2 or flags - known:
        print(__doc__)
        sys.exit(1)
    log = lambda text: print('\r' + text.ljust(70))  # noqa: E731  (overwrites a progress line)
    install(args[0], args[1], disc_wav='--disc-wav' in flags,
            japanese='--japanese' in flags, arrow_keys='--numpad' not in flags,
            portable='--registry' not in flags, ddraw='--no-ddraw' not in flags,
            log=log)
    print('Done. Windows: run Mchase.exe   Linux: run %s' %
          os.path.join(args[1], 'magical-chase.sh'))


if __name__ == '__main__':
    main()
