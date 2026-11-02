#!/usr/bin/env python3
"""
English in-game text for Magical Chase (Windows), taken from the US PC Engine
release (TurboGrafx-16 "Magical Chase", Quest 1993).

The Windows game is the Japanese PC Engine game ported to C: it still draws
text as PCE-style tiles, one font tile per character code. This module reads a
US PC Engine ROM supplied by the user, takes its English font and text, and
returns the changes that put them into Mchase.exe:

  * the three copies of the kana font (BMH resources BANK28 and BANK315) are
    redrawn with the US letters
  * "CRYSTAL" replaces くりすたる on the clear bonus screen (BANK3A sprites)
  * the shop dialogue, broom choice, yes/no prompt, stage results screen and
    end-of-mode messages are replaced with the US text

Character codes. The game's code draws a few characters itself (digits for
prices and scores, the cursor arrows, "C" of "Continued", the "----" marker),
so those stay where the Japanese font had them and the letters go into the
free slots. US text is re-encoded into this layout (see US_TO_WIN).

Only the Python 3 standard library is needed.
"""
import hashlib
import struct

US_ROM_SHA256 = 'c5a39c9d9b2d753244816eafd68f504a855908eebab1b1c8fea2bbf7a4a813c7'
US_ROM_SIZE = 0x80000

# --- where things are in the US ROM ----------------------------------------
US_FONT = 0x51E04            # LZ-compressed font, 0x60 tiles used
US_SHOP_TABLE = 0x7E38C      # 38 16-bit pointers (bank mapped at $A000)
US_RESULTS = 0x7FB27         # results screen text, ends with ff
US_END_MSGS = 0x7CA51        # end-of-mode messages, ends with fe
US_SPRITES_3A = 0x62637      # LZ-compressed sprites, source of BANK3A
CRYSTAL_SPRITES = range(0x800, 0xA00, 0x80)   # "CRYSTAL" (JP: くりすたる)

# --- where things are in Mchase.exe (VAs) ----------------------------------
SHOP_TABLE_VA = 0x461290     # 38 dword pointers
BROOM_TEXT_VA = 0x460BD8     # broom descriptions used by control code f4
BROOM_OFFS_VA = 0x460C10     # 4 byte offsets into BROOM_TEXT_VA
BROOM_TEXT_SITES = [0x42C89E + 6, 0x42C8AE + 2]   # imm32 / disp32 operands
YES_NO_VA = 0x460BC8         # 11 characters
YEN_TILE = 0xFF              # in BANK22
RESULTS_VA = 0x459600
RESULTS_SITES = [0x4176FA + 2, 0x417FAE + 2]       # disp32 operands
BONUS_LABELS_VA = [0x459568, 0x459580, 0x459598, 0x4595B0]   # 23 chars each
END_MSGS_VA = 0x461A08
END_MSGS_SITES = [0x437C7C + 2, 0x437D9D + 2]      # disp32 operands
# (VA, original bytes, new bytes): the difficulty menus highlight the chosen
# name 4 columns wide (the Japanese names); "Breeze" needs 6
CODE = [(0x43561F, 'b104', 'b106'), (0x4368EF, 'b104', 'b106'),
        (0x4374B8, 'b104', 'b106')]

# --- character layout of the patched font ----------------------------------
# Windows code -> US font tile. Slots not listed keep their Japanese glyph.
CAPS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
US_PUNCT = {'×': 0x40, '÷': 0x41, '~': 0x42, '▶': 0x43, '▼': 0x44, '?': 0x45,
            '!': 0x46, '…': 0x47, '-': 0x48, '.': 0x49, ',': 0x4A, "'": 0x4B,
            ':': 0x4C, '¢': 0x4D, 'x': 0x4E, '"': 0x4F}
WIN_PUNCT = {'▶': 0x0F, '▼': 0x1F, '.': 0x1C, ',': 0x1D, "'": 0x1E,
             '×': 0x32, '÷': 0x34, '?': 0x3C, '!': 0x3D, '-': 0x3E, ':': 0x3F,
             '…': 0x4A, '"': 0x4B, '~': 0x4C, '¢': 0x4D, 'x': 0x4E}
BLANK = 0x00

US_TO_WIN = {}
for i, c in enumerate(CAPS):                       # A-N 01-0e, O-Z 10-1b
    US_TO_WIN[i] = 0x01 + i if i < 14 else 0x10 + i - 14
for i in range(26):                                # a-z 55-6e
    US_TO_WIN[0x20 + i] = 0x55 + i
for c, u in US_PUNCT.items():
    US_TO_WIN[u] = WIN_PUNCT[c]
for i in range(10):                                # digits stay at 40-49
    US_TO_WIN[0x50 + i] = 0x40 + i

GLYPHS = {w: u for u, w in US_TO_WIN.items()}      # Windows code -> US tile
GLYPHS[0x54] = 0x02        # "C" drawn by the results screen for "Continued"
GLYPHS[0x74] = 0x48        # dash of the "----" marker in the broom list


def window_rows(rows, width, attr, blank):
    """Rows of a window tile map: None = empty row (one ffff word), otherwise
    text padded to the window width, one tile word per character."""
    words = []
    for r in rows:
        if r is None:
            words.append(0xFFFF)
            continue
        assert len(r) <= width, r
        words += [blank if c == ' ' else attr | encode_char(c) for c in r.ljust(width)]
    return words


def encode_char(ch):
    return encode(ch)[0]


# Window tile maps drawn by the routine at 0x406D50 (table at 0x4572D8:
# map pointer, screen address, width, rows). Same row count and positions as
# the Japanese ones, which the cursor code relies on; English from the US ROM.
WINDOWS = [
    # difficulty select, 10 x 8; choices on rows 3, 5, 7
    (0x457130, lambda: window_rows(
        [None, 'Difficulty', None, '   Breeze', None, '   Bumpy', None, '   Rough'],
        10, 0x1300, 0x1280)),
    # continue screen, 12 x 8; choices on rows 5 and 7
    (0x457270, lambda: window_rows(
        ['Continue?', None, None, None, None, '  Try again', None, '  Quit'],
        12, 0x0300, 0x0280)),
]


# In-game sound test (window 0x0E): 18 entries of 2 rows x 24 tile words at
# SOUND_TEST_VA + 0x60 * n. Row 1 is the dakuten row (its last word is the
# tens digit), row 2 the units digit, two blanks and the title in columns
# 3-21. The US release left these titles in Japanese; the ones in kana get
# short forms of the English names used on the Options > Sound page.
SOUND_TEST_VA = 0x461AC0
SOUND_TEST_TITLES = {
    1: 'Devil Comes Singing', 3: "It's Not a Bug!", 4: "It's Not Ice!",
    5: 'Whoosh~ Whoosh~', 9: 'Thank Goodness! 1', 10: 'Ra Tribe Variations',
    11: 'Meditation Waltz 1', 12: 'Meditation Waltz 2', 13: 'Thank Goodness! 2',
    15: "Ripple's Theme", 17: "Can't Sit Still?!",
}


def sound_test_patches():
    out = []
    for n, title in SOUND_TEST_TITLES.items():
        va = SOUND_TEST_VA + 0x60 * n
        out.append((va, struct.pack('<23H', *[0x0280] * 23)))   # no dakuten
        out.append((va + 2 * (24 + 3), b''.join(
            struct.pack('<H', window_rows([title], 19, 0x0300, 0x0280)[i])
            for i in range(19))))
    return out


def lz_decompress(rom, pos, n):
    """Magical Chase PCE graphics compression: 256-byte blocks, each starting
    with its escape byte. <esc> d l = copy l bytes from d back,
    <esc> 00 = the escape byte itself, anything else is a literal."""
    out = bytearray()
    while len(out) < n:
        esc = rom[pos]
        pos += 1
        stop = len(out) + 256
        while len(out) < stop:
            b = rom[pos]
            pos += 1
            if b != esc:
                out.append(b)
                continue
            d = rom[pos]
            pos += 1
            if d == 0:
                out.append(esc)
                continue
            n_copy = rom[pos]
            pos += 1
            for _ in range(n_copy):
                out.append(out[-d])
    return bytes(out[:n])


def planar_tile_pixels(b, o):
    """PCE 4bpp planar tile -> 8 rows of 8 colour indexes."""
    rows = []
    for y in range(8):
        p = (b[o + 2 * y], b[o + 2 * y + 1], b[o + 16 + 2 * y], b[o + 17 + 2 * y])
        rows.append([sum(((p[k] >> (7 - x)) & 1) << k for k in range(4)) for x in range(8)])
    return rows


def packed_tile(rows):
    """8 rows of colour indexes -> the Windows port's tile format
    (one little-endian dword per row, leftmost pixel in the top nibble)."""
    out = bytearray()
    for r in rows:
        v = 0
        for x, c in enumerate(r):
            v |= c << (28 - 4 * x)
        out += struct.pack('<I', v)
    return bytes(out)


def us_text(rom, pos, end_codes, mapping):
    """Read US text from pos up to and including the first end code."""
    out = bytearray()
    while True:
        b = rom[pos]
        pos += 1
        if b >= 0x80:
            out.append(b)
            if b in end_codes:
                return bytes(out)
        elif b in mapping:
            out.append(mapping[b])
        else:
            raise ValueError('unexpected US character %#x at %#x' % (b, pos - 1))


def encode(s):
    """Plain English -> Windows codes (for the few strings written here).
    Space is 0x80 in the shop and 0x00 on the results screen; pass it as '_'
    for 0x00."""
    out = bytearray()
    for ch in s:
        if ch == ' ':
            out.append(0x80)
        elif ch == '_':
            out.append(BLANK)
        elif ch in CAPS:
            out.append(US_TO_WIN[CAPS.index(ch)])
        elif 'a' <= ch <= 'z':
            out.append(0x55 + ord(ch) - ord('a'))
        elif ch.isdigit():
            out.append(0x40 + int(ch))
        else:
            out.append(WIN_PUNCT[ch])
    return bytes(out)


def check_rom(us_rom):
    if len(us_rom) == US_ROM_SIZE + 512:         # copier header
        us_rom = us_rom[512:]
    if hashlib.sha256(us_rom).hexdigest() != US_ROM_SHA256:
        raise ValueError('not the US Magical Chase ROM this patch was made for '
                         '(TurboGrafx-16, 512 KB, sha256 %s...)' % US_ROM_SHA256[:16])
    return us_rom


def lz_end(rom, pos, n):
    """Position just after the compressed data that decodes to n bytes."""
    done = 0
    while done < n:
        esc = rom[pos]
        pos += 1
        stop = done + 256
        while done < stop:
            b = rom[pos]
            pos += 1
            if b != esc:
                done += 1
            elif rom[pos] == 0:
                pos += 1
                done += 1
            else:
                done += rom[pos + 1]
                pos += 2
    return pos


def extract(us_rom):
    """The parts of the US ROM that build() reads, as [(offset, bytes)]."""
    us = check_rom(us_rom)
    ptrs = [0x7E000 + struct.unpack_from('<H', us, US_SHOP_TABLE + 2 * i)[0] - 0xA000
            for i in range(38)]
    ranges = [
        (US_FONT, lz_end(us, US_FONT, 0x60 * 32)),
        (US_SHOP_TABLE, US_SHOP_TABLE + 2 * 38),
        (min(ptrs), us.index(b'\xfd', max(ptrs)) + 1),
        (US_RESULTS, us.index(b'\xff', US_RESULTS) + 1),
        (US_END_MSGS, us.index(b'\xfe', US_END_MSGS) + 1),
        (US_SPRITES_3A, lz_end(us, US_SPRITES_3A, CRYSTAL_SPRITES.stop)),
    ]
    return [(a, us[a:b]) for a, b in ranges]


def bundled_rom():
    """A ROM-sized image holding only the parts in english_data.py."""
    import base64
    import english_data
    img = bytearray(US_ROM_SIZE)
    for off, b64 in english_data.CHUNKS:
        data = base64.b64decode(b64)
        img[off:off + len(data)] = data
    return bytes(img)


def write_data_module(us_rom, path):
    import base64
    lines = ['"""Generated by english_text.py from the US PC Engine ROM of Magical',
             'Chase (TurboGrafx-16, Quest 1993): its English font and in-game text,',
             'as (ROM offset, base64). Do not edit."""',
             'CHUNKS = [']
    for off, data in extract(us_rom):
        b64 = base64.b64encode(data).decode()
        lines.append('    (0x%05X,' % off)
        for i in range(0, len(b64), 68):
            lines.append("     '%s'" % b64[i:i + 68])
        lines[-1] += '),'
    lines.append(']')
    with open(path, 'w', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')


# ----------------------------------------------------------------------------
def sprite_packed(b):
    """PCE 16x16 sprite (4 planes x 16 words) -> the Windows port's format:
    per row two dwords, right 8 pixels first, leftmost pixel in the top nibble."""
    out = bytearray()
    for y in range(16):
        words = [b[p * 32 + y * 2] | b[p * 32 + y * 2 + 1] << 8 for p in range(4)]
        px = [sum(((words[p] >> (15 - x)) & 1) << p for p in range(4)) for x in range(16)]
        for half in (1, 0):
            v = 0
            for x in range(8):
                v |= px[half * 8 + x] << (28 - 4 * x)
            out += struct.pack('<I', v)
    return bytes(out)


BANKS = ('BANK28', 'BANK315', 'BANK22', 'BANK3A')


def build(us_rom, banks):
    """Return a dict:
       banks:  {'BANK28': bytes, ...}  redrawn graphics banks
       inplace: [(va, bytes)]       same-size replacements
       blobs:  {name: bytes}        new text, to be placed in the new section
       relocs: [(name, va_of_dword, offset_in_blob, expected old value or None)]
               dwords to repoint at the new text
       code:   [(va, old hex, new hex)] code patches
    us_rom: the US ROM, or None for the copy bundled in english_data.py.
    banks: {name: original BMH resource contents} for the names in BANKS."""
    us = bundled_rom() if us_rom is None else check_rom(us_rom)
    font = lz_decompress(us, US_FONT, 0x60 * 32)
    us_glyph = [planar_tile_pixels(font, i * 32) for i in range(0x60)]

    # --- fonts ---
    b28, b315, b22, b3a = (bytearray(banks[n]) for n in BANKS)
    for code in range(0x80):
        if code == BLANK:
            rows = [[0] * 8 for _ in range(8)]
        elif code in GLYPHS:
            rows = us_glyph[GLYPHS[code]]
        else:
            continue
        # BANK28 second half and BANK315 second half: black background
        for b in (b28, b315):
            b[0x1000 + code * 32:0x1000 + code * 32 + 32] = packed_tile(rows)
        # BANK315 first half: message window colours; 40/41 are window parts
        if code not in (0x40, 0x41):
            win = [[{0: 8, 14: 12}.get(c, c) for c in r] for r in rows]
            b315[code * 32:code * 32 + 32] = packed_tile(win)

    inplace, blobs, relocs = [], {}, []
    shop_map = dict(US_TO_WIN)
    shop_map[0x00] = US_TO_WIN[0x00]   # "A"

    # --- shop: one blob with every string, table repointed ---
    ptrs = [0x7E000 + struct.unpack_from('<H', us, US_SHOP_TABLE + 2 * i)[0] - 0xA000
            for i in range(38)]
    start = min(ptrs)
    end = us.index(b'\xfd', max(ptrs)) + 1
    shop = bytearray()
    pos = start
    while pos < end:
        b = us[pos]
        shop.append(b if b >= 0x80 else shop_map[b])
        pos += 1
    entry = [p - start for p in ptrs]          # string starts inside the blob

    def splice(at, end, new):
        """Replace shop[at:end] with new, keeping the string starts right."""
        shop[at:end] = new
        for i, o in enumerate(entry):
            if o >= end:
                entry[i] = o + len(new) - (end - at)

    # Broom choice page. The US layout puts letters where this game draws the
    # cursor; follow the Japanese one instead: cursor column, name, price.
    at = shop.index(encode('Pick'))
    splice(at, shop.index(b'\xf2', at) + 1,
           encode('Pick a broom:') +
           encode(' Straw  ') + b'\xf3\x01\xfe' +
           encode(' Cotton ') + b'\xf3\x02\xfe' +
           encode(' Feather') + b'\xf3\x03\xf2')

    # After the price (fc) this game starts a new row, and the yes/no line
    # (fd) is drawn over the row below it, so the question must fit in one
    # 13-column row.
    old_q = encode(' Will you take it? ')
    while old_q in shop:
        at = shop.index(old_q)
        splice(at, at + len(old_q), encode('Will you buy?'))

    blobs['shop'] = bytes(shop)
    for i, o in enumerate(entry):
        relocs.append(('shop', SHOP_TABLE_VA + 4 * i, o, None))

    # Prices are drawn after a yen sign (2-row character 0, tile 0x2FF =
    # BANK22 tile 0xFF); the shop board shows prices with a cent sign.
    b22[YEN_TILE * 32:YEN_TILE * 32 + 32] = packed_tile(us_glyph[US_PUNCT['¢']])

    # --- broom descriptions for f4 ("...for speed. Straw flies slowly.");
    # they start a 13-column row, spaced so that words are not split ---
    brooms = [encode(s) + b'\xff' for s in
              ('Straw flies  slowly', 'Cotton flies normally', 'Feather fliesfast')]
    blobs['brooms'] = b''.join(brooms)
    offs = [0, 0, len(brooms[0]), len(brooms[0]) + len(brooms[1])]
    inplace.append((BROOM_OFFS_VA, bytes(offs)))
    for site in BROOM_TEXT_SITES:
        relocs.append(('brooms', site, 0, BROOM_TEXT_VA))

    # --- yes / no (cursor at columns 1 and 7) ---
    inplace.append((YES_NO_VA, encode('  Yes   No ')))

    # --- results screen (0x00 is a space there) ---
    res_map = dict(US_TO_WIN)
    res_map[0x00] = BLANK
    blobs['results'] = us_text(us, US_RESULTS, (0xFF,), res_map)
    for site in RESULTS_SITES:
        relocs.append(('results', site, 0, RESULTS_VA))

    # "Game Clear Bonus!!!" / "Bonus Total ... 0 pts" (23 fixed columns;
    # the 1st and 3rd rows are the dakuten rows above them)
    labels = ['', '__Game_Clear_Bonus!!!', '', 'Bonus_Total________0_pt']
    for va, s in zip(BONUS_LABELS_VA, labels):
        inplace.append((va, encode(s).ljust(23, b'\0')))

    # --- end-of-mode messages (0x40 is a space in that window) ---
    end_map = dict(US_TO_WIN)
    end_map[0x40] = 0x40
    blobs['end'] = us_text(us, US_END_MSGS, (0xFE,), end_map)
    for site in END_MSGS_SITES:
        relocs.append(('end', site, 0, END_MSGS_VA))

    # --- window tile maps: difficulty select and continue screen ---
    for va, words in WINDOWS:
        inplace.append((va, b''.join(struct.pack('<H', w) for w in words())))
    inplace += sound_test_patches()

    # "CRYSTAL" instead of くりすたる on the clear bonus screen (US sprites)
    spr = lz_decompress(us, US_SPRITES_3A, CRYSTAL_SPRITES.stop)
    for o in CRYSTAL_SPRITES:
        b3a[o:o + 0x80] = sprite_packed(spr[o:o + 0x80])

    return dict(banks=dict(zip(BANKS, (bytes(b) for b in (b28, b315, b22, b3a)))),
                inplace=inplace, blobs=blobs, relocs=relocs, code=list(CODE))


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        sys.exit('Usage: python3 english_text.py <US Magical Chase .pce>\n'
                 'Regenerates english_data.py next to this file.')
    import os
    with open(sys.argv[1], 'rb') as f:
        rom = f.read()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'english_data.py')
    write_data_module(rom, out)
    print('Wrote', out)
