#!/usr/bin/env python3
"""
Magical Chase (Windows 95, QUEST 1998) - compatibility + English settings patch.

Usage:  python3 patch_mchase.py [options] <original Mchase.exe> <output Mchase.exe>

    --japanese   keep the original Japanese menus/dialogs/messages; only the
                 compatibility fixes are applied
    --numpad     keep the original default keys (numpad 8/2/4/6) instead of
                 the arrow keys
    --portable   store settings in MCHASE.INI next to the EXE instead of the
                 registry (HKCU\\Software\\QUEST\\MagicChase\\1.0)

What it changes (the original file is never modified):
  * No CD / AUTORUN.EXE needed: if the "?GOPA242" launch token is missing the
    game uses a built-in default, and looks for music in "<exe folder>\\mus\\".
  * Never quits with "only works in 256 / 64K color modes" on 32-bit desktops:
    windowed mode is only used when the desktop is 8/16-bit, otherwise the
    game starts fullscreen and Alt+Enter is ignored. Fullscreen uses 16-bit
    HiColor by default (8-bit if the VideoMode registry value is 8) instead
    of copying the 32-bit desktop depth.
  * Sound page (CD Audio / WAV choice, music & SE test) always present in
    Settings > Options, not only in AUTORUN's settings mode.
  * Joystick divide-by-zero crash fix (same bytes as the official mc_patch.exe).
  * Default movement keys are the arrow keys instead of numpad 8/2/4/6
    (laptops often have no numpad). Saved key settings are not touched.
  * Menus, settings dialogs, messages, joystick axis names and BGM track names
    translated to English (both the 0x409 and 0x411 resource languages).
    Skipped with --japanese.
  * Optional (--portable): settings saved in MCHASE.INI next to the EXE.

Only the Python 3 standard library is needed.
"""
import hashlib
import struct
import sys

ORIGINAL_SHA256 = {
    'c91a4a808c34db5f5d45162d8a3a2567ffc35a956af2388315673f6c80940256': 'retail 1998',
}

IMAGE_BASE = 0x400000
SEC_VA = 0x90D000           # new section ".mcfix"
SIG_VA = SEC_VA + 0x300
DEFSTR_VA = SEC_VA + 0x310
RES_OFF = 0x900             # resource blobs start here inside the section

# Default command line: W = windowed if the desktop allows it (else fullscreen),
# GOPA242 = launch token, _ = no CD drive (music from <exe>\mus\).
DEFAULT_CMDLINE = b'WGOPA242_'

# Assembled by build_cave.py (keystone). Entry points: +0x000 cave_cmdline,
# +0x100 desktop_ok, +0x140 cave_mode, +0x160 cave_toggle, +0x1a0 cave_bpp.
CAVE_CODE = bytes.fromhex(
    '5983c4045189c68b7d1056803f007431b9010000008a040f3a8100d3900075214183f908'
    '72efbe20d3900031c98a040f88040e84c074064183f91f72f089f7eb05bf10d390006804'
    '0100006840d390006a00ff158c554a00b940d3900031d28a0184c074093c5c750289ca41'
    'ebf185d2740dc60200c7050cd3900040d390005ec3cccccccccccccccccccccccccccccc'
    'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc'
    'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc'
    'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc'
    'cccccccc56576a00ff15f0564a0089c66a0c56ff1590544a0089c7566a00ff15e8564a00'
    '31c083ff08740583ff107501405f5ec3cccccccccccccccccccccccccccccccce8bbffff'
    'ffa3f0d2900031db85c07405bb02000000c3cccccccccccccccccccca148094a0085c075'
    '15837e40027409833df0d2900000740668ee0a4200c368180b4200c3cccccccccccccccc'
    'cccccccccccccccccccccccccccccccccccccccc83f808740a83f8107405a150774600a3'
    '4c774600c3')

# Portable settings (build_cave.py): stand-ins for the registry functions that
# store settings in <exe folder>\MCHASE.INI instead of HKCU\Software\QUEST.
PORT_OFF, PORT_STR_OFF, PTR_TABLE_OFF = 0x450, 0x600, 0x820
PORT_CODE = bytes.fromhex(
    'e8b100000050ff153cd8900083f8ff740f8b442414c7000100000031c0c21400b8020000'
    '00c2140031c0c204008b442420c700010000008b44242485c07406c7000200000031c0c2'
    '2400e867000000508b4c241cff31ff74241cff7424146850d69000ff1534d8900085c074'
    '138b4c241085c97406c7010300000031c0c21800b802000000c21800e82900000050ff74'
    '241cff74241cff7424146850d69000ff1538d8900085c0740531c0c21800b805000000c2'
    '1800803d00d7900000757d565768040100006800d790006a00ff158c554a00b900d79000'
    '89ca8a0184c07409413c5c75f589caebf1be60d6900089d78a068807464784c075f66800'
    'd69000ff151c554a0089c66810d6900056ff1594554a00a334d890006830d6900056ff15'
    '94554a00a338d890006870d6900056ff1594554a00a33cd890005f5eb800d79000c3')
PORT_ENTRIES = [0, 74, 40, 45, 136]   # open, query, close, create, set
PORT_STRINGS = [(0x00, b'kernel32.dll'), (0x10, b'GetPrivateProfileStructA'),
                (0x30, b'WritePrivateProfileStructA'), (0x50, b'MagicalChase'),
                (0x60, b'MCHASE.INI'), (0x70, b'GetFileAttributesA')]
# (VA, original instruction, IAT slot replaced by pointer-table index)
PORTABLE_SITES = [
    (0x427674, 'ff155c544a00', 0),   # call [RegOpenKeyExA]
    (0x427682, '8b1d60544a00', 1),   # mov ebx,[RegQueryValueExA]
    (0x427832, 'ff1564544a00', 2),   # call [RegCloseKey]
    (0x427887, 'ff1558544a00', 3),   # call [RegCreateKeyExA]
    (0x427899, '8b3554544a00', 4),   # mov esi,[RegSetValueExA]
    (0x42794D, 'ff1564544a00', 2),   # call [RegCloseKey]
]

# (VA, original bytes, new bytes)
CODE_PATCHES = [
    # mov edi,[ebp+10h]; add esp,4; mov esi,eax  ->  call cave_cmdline; nop x3
    (0x4214B8, '8b7d1083c4048bf0', None),
    # mov ebx,2 (windowed)  ->  call cave_mode
    (0x42153D, 'bb02000000', None),
    # mov eax,[4A0948h] (Alt+Enter handler)  ->  jmp cave_toggle
    (0x420AE5, 'a148094a00', None),
    # joystick axis range: sub esi,edi -> inc esi ; sub ecx,eax -> inc ecx
    (0x4210C4, '2bf7', '4690'),
    (0x421117, '2bc8', '4190'),
    # Options sheet: always include the Sound page (originally only when
    # AUTORUN started the game in its "settings" mode with the S argument)
    (0x427D9C, '750f', 'eb0f'),
]


def rel32(src_after, dst):
    return struct.pack('<i', dst - src_after)


CODE_PATCHES[0] = (0x4214B8, '8b7d1083c4048bf0',
                   (b'\xe8' + rel32(0x4214B8 + 5, SEC_VA + 0x000) + b'\x90' * 3).hex())
CODE_PATCHES[1] = (0x42153D, 'bb02000000',
                   (b'\xe8' + rel32(0x42153D + 5, SEC_VA + 0x140)).hex())
# default fullscreen depth 16-bit (HiColor) instead of 8-bit: registry
# default + the two static defaults used when no settings key exists yet
CODE_PATCHES.append((0x4277AD, 'b808000000', 'b810000000'))
CODE_PATCHES.append((0x46774C, '0800000008000000', '1000000010000000'))
# WAV music path root: read our exe-folder pointer instead of the CD drive
CODE_PATCHES.append((0x42E0E9, '8b0d74094a00',
                     (b'\x8b\x0d' + struct.pack('<I', SEC_VA + 0x30C)).hex()))
CODE_PATCHES.append((0x4277E7, 'a34c774600',
                     (b'\xe8' + rel32(0x4277E7 + 5, SEC_VA + 0x1A0)).hex()))
CODE_PATCHES[2] = (0x420AE5, 'a148094a00',
                   (b'\xe9' + rel32(0x420AE5 + 5, SEC_VA + 0x160)).hex())

# Default keyboard bindings (Up, Down, Left, Right, Shot, Option control) used
# when the registry has no "Keyboard" value. Each is a hotkey-control word:
# low byte = virtual key, high byte 0x08 = extended key (the real arrow keys,
# not the numpad ones). The game only polls the low byte.
DEFAULT_KEYS_VA = 0x45F278
DEFAULT_KEYS_NUMPAD = '680062006400660041005300'
DEFAULT_KEYS_ARROWS = '260828082508270841005300'

# Shift-JIS joystick axis names in .data (VA, slot size, English)
DATA_STRINGS = [
    (0x4677AC, 8, 'Axis 0'), (0x4677B4, 8, 'Axis 9'), (0x4677BC, 8, 'Axis 8'),
    (0x4677C4, 8, 'Axis 7'), (0x4677CC, 8, 'Axis 6'), (0x4677D4, 8, 'Axis 5'),
    (0x4677DC, 8, 'Axis 4'), (0x4677E4, 8, 'Axis 3'),
    (0x4677EC, 16, 'Y Axis (Axis 2)'), (0x4677FC, 16, 'X Axis (Axis 1)'),
]

# ----------------------------------------------------------------------------
# English resources
# ----------------------------------------------------------------------------
FONT = (8, 'MS Sans Serif')

MENU_TEXT = {
    'ゲーム': '&Game',
    'ポーズ\tEsc': '&Pause\tEsc',
    '終了\tAlt-Q': 'E&xit\tAlt-Q',
    '設定': '&Settings',
    'フルスクリーン\t Alt-Enter': '&Full Screen\tAlt-Enter',
    'オプション\tAlt-P': '&Options...\tAlt-P',
    'デバッグ': '&Debug',
}

DIALOG_TEXT = {
    'Full screen': 'Full screen color depth',
    '256 Colors ': '256 Colors',
    'キーボード': 'Keyboard',
    '上': 'Up', '下': 'Down', '左': 'Left', '右': 'Right',
    'ショット': 'Shot',
    'オプション操作': 'Option control',
    'Too or more funstion setted on same key':
        'Two or more functions are assigned to the same key.',
    '方向キー': 'Direction',
    '縦移動': 'Vertical move',
    '横移動': 'Horizontal move',
    'ボタン': 'Buttons',
    '音楽': 'Music',
    'ＣＤ－ＤＡ': 'CD Audio',
    'ＷＡＶ': 'WAV files',
    '再生': 'Play',
    '停止': 'Stop',
    '効果音': 'Sound effects',
}

STRINGS = {
    1: 'Magical Chase for Windows 95',
    3: 'Options',
    4: 'Sound',
    5: 'Joystick',
    6: 'Keyboard',
    7: 'Joystick %u',
    8: 'Direction %u',
    9: 'Button %u',
    10: 'Not connected',
    11: 'Could not save settings to the registry.',
    12: 'Display',
    13: 'SE %u',
    50018: "EXE file damaged. Can't load resource.",
    50019: 'To start the program, run autorun.exe.',
    50020: 'This program only works in 256-color or 65536-color (HiColor) display modes.',
    50021: 'Azure Way',
    50022: 'Here Comes the Devil, Singing a Song',
    50023: 'Gizmo Dancing',
    50024: "It's Not a Bug!",
    50025: "It's Not Ice!",
    50026: 'Whoosh~ Whoosh~',
    50027: 'Gizmo March',
    50028: 'Uncle Pumpkin',
    50029: "Can't You Sit Still?!",
    50030: 'Rampish Chase',
    50031: 'Phew, Thank Goodness...! Part 1',
    50032: 'Variations on a Melody of the Ra Tribe',
    50033: 'Meditation Waltz Part 1 (unused)',
    50034: 'Meditation Waltz Part 2',
    50035: 'Phew, Thank Goodness...! Part 2',
    50036: 'Termination',
    50037: "Ripple's Theme",
    50038: 'Ending',
    50039: 'Awakening',
}


# ----------------------------------------------------------------------------
# Small PE helpers
# ----------------------------------------------------------------------------
class PE:
    def __init__(self, data):
        self.d = bytearray(data)
        self.pe = struct.unpack_from('<I', self.d, 0x3C)[0]
        assert self.d[self.pe:self.pe + 4] == b'PE\0\0'
        self.nsec = struct.unpack_from('<H', self.d, self.pe + 6)[0]
        self.optsz = struct.unpack_from('<H', self.d, self.pe + 20)[0]
        self.opt = self.pe + 24
        self.sectab = self.opt + self.optsz

    def sections(self):
        for i in range(self.nsec):
            o = self.sectab + 40 * i
            name = bytes(self.d[o:o + 8]).rstrip(b'\0')
            vsz, va, rsz, rptr = struct.unpack_from('<IIII', self.d, o + 8)
            yield o, name, va, vsz, rptr, rsz

    def off(self, rva):
        for _, _, va, vsz, rptr, rsz in self.sections():
            if va <= rva < va + max(vsz, rsz):
                return rptr + rva - va
        raise ValueError(hex(rva))

    def datadir(self, i):
        return struct.unpack_from('<II', self.d, self.opt + 96 + 8 * i)


def u16z(b, o):
    e = o
    while b[e:e + 2] != b'\0\0':
        e += 2
    return b[o:e].decode('utf-16le'), e + 2


def sz_or_ord(b, o):
    if b[o:o + 2] == b'\xff\xff':
        return struct.unpack_from('<H', b, o + 2)[0], o + 4
    return u16z(b, o)


def w_sz_or_ord(v):
    if isinstance(v, int):
        return struct.pack('<HH', 0xFFFF, v)
    return v.encode('utf-16le') + b'\0\0'


def walk_resources(pe):
    """Yield (type, name, lang, data_entry_file_offset)."""
    rva, _ = pe.datadir(2)
    base = pe.off(rva)
    d = pe.d

    def entries(o):
        nn, ni = struct.unpack_from('<HH', d, base + o + 12)
        for i in range(nn + ni):
            name, ptr = struct.unpack_from('<II', d, base + o + 16 + 8 * i)
            if name & 0x80000000:
                so = base + (name & 0x7FFFFFFF)
                ln = struct.unpack_from('<H', d, so)[0]
                name = bytes(d[so + 2:so + 2 + 2 * ln]).decode('utf-16le')
            yield name, ptr

    for t, tp in entries(0):
        for n, np_ in entries(tp & 0x7FFFFFFF):
            for lang, lp in entries(np_ & 0x7FFFFFFF):
                yield t, n, lang, base + lp

# ----------------------------------------------------------------------------
# Resource (de)serialisers
# ----------------------------------------------------------------------------
def parse_menu(b):
    items, o = [], 4
    while o < len(b):
        fl = struct.unpack_from('<H', b, o)[0]
        o += 2
        mid = None
        if not fl & 0x10:
            mid = struct.unpack_from('<H', b, o)[0]
            o += 2
        txt, o = u16z(b, o)
        items.append((fl, mid, txt))
    return items


def build_menu(items):
    out = bytearray(4)
    for fl, mid, txt in items:
        out += struct.pack('<H', fl)
        if mid is not None:
            out += struct.pack('<H', mid)
        out += MENU_TEXT.get(txt, txt).encode('utf-16le') + b'\0\0'
    return bytes(out)


def parse_dialog(b):
    style, ex, n, x, y, cx, cy = struct.unpack_from('<IIHhhhh', b, 0)
    o = 18
    menu, o = sz_or_ord(b, o)
    cls, o = sz_or_ord(b, o)
    title, o = u16z(b, o)
    if style & 0x40:
        o += 2
        _, o = u16z(b, o)
    items = []
    for _ in range(n):
        o = (o + 3) & ~3
        st, exs, ix, iy, icx, icy, iid = struct.unpack_from('<IIhhhhH', b, o)
        o += 18
        c, o = sz_or_ord(b, o)
        t, o = sz_or_ord(b, o)
        el = struct.unpack_from('<H', b, o)[0]
        extra = b[o + 2:o + 2 + el]
        o += 2 + el
        items.append([st, exs, ix, iy, icx, icy, iid, c, t, extra])
    return dict(style=style, ex=ex, rect=[x, y, cx, cy], menu=menu, cls=cls,
                title=title, items=items)


def build_dialog(dlg):
    out = bytearray(struct.pack('<IIH', dlg['style'] | 0x40, dlg['ex'], len(dlg['items'])))
    out += struct.pack('<hhhh', *dlg['rect'])
    out += w_sz_or_ord(dlg['menu']) + w_sz_or_ord(dlg['cls'])
    out += dlg['title'].encode('utf-16le') + b'\0\0'
    out += struct.pack('<H', FONT[0]) + FONT[1].encode('utf-16le') + b'\0\0'
    for st, exs, x, y, cx, cy, iid, c, t, extra in dlg['items']:
        while len(out) % 4:
            out += b'\0'
        if isinstance(t, str):
            t = DIALOG_TEXT.get(t, t)
        out += struct.pack('<IIhhhhH', st, exs, x, y, cx, cy, iid)
        out += w_sz_or_ord(c) + w_sz_or_ord(t)
        out += struct.pack('<H', len(extra)) + extra
    return bytes(out)


def adjust_dialog(name, dlg):
    it = dlg['items']
    if name == 101:  # keyboard page: wider labels for "Option control"
        for i in it:
            if i[7] == 0x82 and i[6] == 0xFFFF:
                i[4] = 60
            if i[7] == 'msctls_hotkey32':
                i[2], i[4] = 84, 82
        it[-1][3], it[-1][5] = 111, 16
    if name == 102:  # joystick page: labels a bit wider, combos moved right
        for i in it:
            if i[7] == 0x82:
                i[4] = 78
            if i[7] == 0x85 and i[6] != 1013:
                i[2], i[4] = 104, 61


def build_string_block(block_id, existing):
    out = bytearray()
    for i in range(16):
        sid = (block_id - 1) * 16 + i
        s = STRINGS.get(sid, existing[i])
        out += struct.pack('<H', len(s)) + s.encode('utf-16le')
    return bytes(out)


def parse_string_block(b):
    o, res = 0, []
    for _ in range(16):
        n = struct.unpack_from('<H', b, o)[0]
        res.append(b[o + 2:o + 2 + 2 * n].decode('utf-16le'))
        o += 2 + 2 * n
    return res

# ----------------------------------------------------------------------------
def patch(src, japanese=False, arrow_keys=True, portable=False):
    """Return the patched EXE.
    japanese:   keep the original Japanese text
    arrow_keys: default movement keys are the arrow keys (not numpad 8/2/4/6)
    portable:   settings go to MCHASE.INI next to the EXE, not the registry"""
    pe = PE(src)
    code = list(CODE_PATCHES)
    if arrow_keys:
        code.append((DEFAULT_KEYS_VA, DEFAULT_KEYS_NUMPAD, DEFAULT_KEYS_ARROWS))
    if portable:
        for va, old, idx in PORTABLE_SITES:
            ptr = SEC_VA + PTR_TABLE_OFF + 4 * idx
            code.append((va, old, old[:4] + struct.pack('<I', ptr).hex()))

    # 1. code patches
    for va, old, new in code:
        o = pe.off(va - IMAGE_BASE)
        old, new = bytes.fromhex(old), bytes.fromhex(new)
        assert pe.d[o:o + len(old)] == old, 'unexpected bytes at %#x' % va
        pe.d[o:o + len(new)] = new

    # 2. Shift-JIS axis names -> English
    for va, size, txt in ([] if japanese else DATA_STRINGS):
        o = pe.off(va - IMAGE_BASE)
        assert pe.d[o] >= 0x81, 'unexpected data at %#x' % va
        enc = txt.encode('ascii')
        assert len(enc) < size
        pe.d[o:o + size] = enc + b'\0' * (size - len(enc))

    # 3. new section contents
    sec = bytearray(RES_OFF)
    sec[0:len(CAVE_CODE)] = CAVE_CODE
    sec[0x300:0x309] = b'?GOPA242\0'
    sec[0x310:0x310 + len(DEFAULT_CMDLINE)] = DEFAULT_CMDLINE
    sec[PORT_OFF:PORT_OFF + len(PORT_CODE)] = PORT_CODE
    for off, txt in PORT_STRINGS:
        sec[PORT_STR_OFF + off:PORT_STR_OFF + off + len(txt) + 1] = txt + b'\0'
    for i, entry in enumerate(PORT_ENTRIES):
        struct.pack_into('<I', sec, PTR_TABLE_OFF + 4 * i, SEC_VA + PORT_OFF + entry)

    # 4. resources: collect the Japanese (0x411) originals, build English blobs
    res = {}
    for t, n, lang, entry in walk_resources(pe):
        if t in (4, 5, 6):
            rva, size = struct.unpack_from('<II', pe.d, entry)
            res[(t, n, lang)] = (entry, bytes(pe.d[pe.off(rva):pe.off(rva) + size]))
    if japanese:
        res = {}
    blobs = {}
    for (t, n, lang), (entry, data) in res.items():
        if lang != 0x411:
            continue
        if t == 4:
            blobs[(t, n)] = build_menu(parse_menu(data))
        elif t == 5:
            dlg = parse_dialog(data)
            adjust_dialog(n, dlg)
            blobs[(t, n)] = build_dialog(dlg)
        elif t == 6:
            blobs[(t, n)] = build_string_block(n, parse_string_block(data))
    for (t, n, lang), (entry, _) in res.items():
        blob = blobs[(t, n)]
        while len(sec) % 16:
            sec.append(0)
        rva = SEC_VA - IMAGE_BASE + len(sec)
        sec += blob
        struct.pack_into('<II', pe.d, entry, rva, len(blob))

    # 5. append the section (after any overlay, file-aligned)
    falign = struct.unpack_from('<I', pe.d, pe.opt + 36)[0]
    salign = struct.unpack_from('<I', pe.d, pe.opt + 32)[0]
    last = list(pe.sections())[-1]
    assert last[2] + ((last[3] + salign - 1) // salign) * salign == SEC_VA - IMAGE_BASE
    while len(pe.d) % falign:
        pe.d.append(0)
    raw_ptr = len(pe.d)
    vsize = len(sec)
    while len(sec) % falign:
        sec.append(0)
    pe.d += sec
    hdr = pe.sectab + 40 * pe.nsec
    assert hdr + 40 <= struct.unpack_from('<I', pe.d, pe.opt + 60)[0]
    assert not any(pe.d[hdr:hdr + 40])
    struct.pack_into('<8sIIIIIIHHI', pe.d, hdr, b'.mcfix', vsize, SEC_VA - IMAGE_BASE,
                     len(sec), raw_ptr, 0, 0, 0, 0, 0xE0000060)  # code|data|RWX
    struct.pack_into('<H', pe.d, pe.pe + 6, pe.nsec + 1)
    size_of_image = SEC_VA - IMAGE_BASE + ((vsize + salign - 1) // salign) * salign
    struct.pack_into('<I', pe.d, pe.opt + 56, size_of_image)
    return bytes(pe.d)


def main():
    flags = {a for a in sys.argv[1:] if a.startswith('--')}
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    unknown = flags - {'--japanese', '--numpad', '--portable'}
    if len(args) != 2 or unknown:
        print(__doc__)
        sys.exit(1)
    with open(args[0], 'rb') as f:
        data = f.read()
    h = hashlib.sha256(data).hexdigest()
    if h not in ORIGINAL_SHA256:
        sys.exit('Unrecognised Mchase.exe (sha256 %s). Use the unmodified file from '
                 'RUN\\MCHASE\\SRC on the CD.' % h)
    out = patch(data, japanese='--japanese' in flags, arrow_keys='--numpad' not in flags,
                portable='--portable' in flags)
    with open(args[1], 'wb') as f:
        f.write(out)
    print('Patched %s -> %s' % (args[0], args[1]))


if __name__ == '__main__':
    main()
