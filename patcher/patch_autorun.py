"""Patch the original QUEST AUTORUN.EXE and STAFF.EXE in place.
Original entry points, MFC dialog, painting and launch handlers are retained.
Only disc/OS/install assumptions, paths, imports and translated resources change.
"""
import hashlib
import struct
from patch_mchase import PE, walk_resources, sz_or_ord, w_sz_or_ord
from autorun_hooks import ROOT, PATHS, REPAINT, STAFF_PATHS

ORIGINAL_SHA256 = '1c19a97d73dd7fd799c72619ae9fedddd919d27955f985485623f62fd7fd9694'
STAFF_SHA256 = 'de4bd5ab75f11c3576fbc28bc6d8f3e4a3e8b45a365ccc1b792f360954bbf3ff'


def edit(pe, va, expected, replacement):
    expected, replacement = bytes.fromhex(expected), bytes.fromhex(replacement)
    at = pe.off(va - 0x400000)
    if bytes(pe.d[at:at+len(expected)]) != expected:
        raise ValueError('Unexpected instruction at %#x' % va)
    if len(replacement) != len(expected):
        raise ValueError('Patch length mismatch')
    pe.d[at:at+len(expected)] = replacement


def branch(va, target, size=5, call=False):
    return ((b'\xe8' if call else b'\xe9') + struct.pack('<i', target-va-5)
            + b'\x90'*(size-5)).hex()


def add_section(pe, payload, rva):
    d=pe.d
    sa,fa=struct.unpack_from('<II',d,pe.opt+32)
    align=lambda n,a:(n+a-1)//a*a
    raw=align(len(d),fa)
    tab=pe.sectab+40*pe.nsec
    if tab+40>min(s[4] for s in pe.sections() if s[5]):
        raise ValueError('No section header space')
    struct.pack_into('<8sIIIIIIHHI',d,tab,b'.mcfix\0\0',len(payload),rva,
                     align(len(payload),fa),raw,0,0,0,0,0xe0000060)
    struct.pack_into('<H',d,pe.pe+6,pe.nsec+1)
    struct.pack_into('<I',d,pe.opt+56,align(rva+len(payload),sa))
    struct.pack_into('<I',d,pe.opt+64,0)
    d.extend(b'\0'*(raw-len(d)));d.extend(payload)
    d.extend(b'\0'*(align(len(d),fa)-len(d)))


def portable_dialog(b, japanese=False):
    """Edit the original DLGTEMPLATEEX; remove obsolete installer controls."""
    fixed = bytearray(b[:26])
    o = 26
    fields = []
    for _ in range(3):
        value, o = sz_or_ord(b, o)
        fields.append(value)
    style = struct.unpack_from('<I', b, 12)[0]
    title = fields[2] if japanese else 'Magical Chase for Windows95'
    out = fixed + w_sz_or_ord(fields[0]) + w_sz_or_ord(fields[1]) + w_sz_or_ord(title)
    if style & 0x40:
        start = o
        o += 6
        _, o = sz_or_ord(b, o)
        out += (b[start:o] if japanese else
                struct.pack('<HHBB', 9, 400, 0, 1) + w_sz_or_ord('MS Shell Dlg'))
    titles = {2: 'Exit', 1002: 'Game Start', 1003: 'Game Start (from CD)',
              1006: 'Options', 1007: 'STAFF'}
    count = struct.unpack_from('<H', b, 16)[0]
    items = []
    for _ in range(count):
        o = (o + 3) & ~3
        header = bytearray(b[o:o + 24])
        ident = struct.unpack_from('<I', header, 20)[0]
        o += 24
        cls, o = sz_or_ord(b, o)
        caption, o = sz_or_ord(b, o)
        n = struct.unpack_from('<H', b, o)[0]
        extra = b[o:o + 2 + n]
        o += 2 + n
        items.append((ident, header, cls, caption, extra))
    # Close the Install row's gap and let Exit span the former bottom pair.
    by_id = {i[0]: i[1] for i in items}
    row = (struct.unpack_from('<h', by_id[1006], 14)[0] -
           struct.unpack_from('<h', by_id[1004], 14)[0])
    kept = 0
    for ident, header, cls, caption, extra in items:
        if ident in (1000, 1004):
            continue
        if ident in (2, 1006, 1007):
            y = struct.unpack_from('<h', header, 14)[0]
            struct.pack_into('<h', header, 14, y - row)
        if ident == 2:
            header[12:14] = by_id[1002][12:14]  # Game Start's x and width
            header[16:18] = by_id[1002][16:18]
        out += b'\0' * ((-len(out)) % 4)
        out += header + w_sz_or_ord(cls)
        out += w_sz_or_ord(caption if japanese else titles.get(ident, caption)) + extra
        kept += 1
    struct.pack_into('<H', out, 16, kept)
    height = struct.unpack_from('<h', out, 24)[0]
    struct.pack_into('<h', out, 24, height - row)
    return out


def patch(data, japanese=False):
    if hashlib.sha256(data).hexdigest()!=ORIGINAL_SHA256:
        raise ValueError('Unexpected AUTORUN.EXE on this disc')
    pe=PE(data)
    # Windows NT is supported; skip the Win95-only refusal and CD drive test.
    edit(pe,0x40218b,'7318','eb18')
    edit(pe,0x40224d,'741e','eb1e')
    # Treat this portable installation as installed. Obsolete installer
    # controls are removed from the dialog below.
    edit(pe,0x401800,'518d442400','b801000000')
    edit(pe,0x401805,'56','c3')
    edit(pe,0x4018cb,'6a01','6a00')
    # Repaint after the original ShowWindow/suppression-flag sequence.
    edit(pe,0x4015dd,'a378754200',branch(0x4015dd,0x439200,call=True))
    # Module path (not process command line) determines the portable root.
    edit(pe,0x402390,'ff1534c74200',branch(0x402390,0x439000,6))
    # Replace only registry path lookup; ORIGINAL command builder,
    # CreateProcess, process wait, menu disable/enable and return remain.
    edit(pe,0x4012c4,'8d54240852',branch(0x4012c4,0x439100,call=True))
    edit(pe,0x4012c9,'6a016a0068',branch(0x4012c9,0x40133b))
    # STAFF is beside AUTORUN, not under the disc's MCHASE/SRC directory.
    edit(pe,0x4234b8,'5c6d63686173655c737263','00'*11)
    # Use an explicit application name, so STAFF paths with spaces work.
    edit(pe,0x401b8c,'6a00','5090')
    # Remove only the obsolete DSETUP import descriptor. Remaining original
    # imports/IAT addresses stay intact; installer actions are disabled.
    imp,_=pe.datadir(1);at=pe.off(imp);end=at
    while any(pe.d[end:end+20]):end+=20
    pe.d[at:end+20]=pe.d[at+20:end+20]+bytes(20)
    payload=bytearray(0x400)
    payload[:len(ROOT)]=ROOT
    payload[0x100:0x100+len(PATHS)]=PATHS
    payload[0x200:0x200+len(REPAINT)]=REPAINT
    payload[0x300:0x30d]=b'\\Mchase.exe"\0'
    if japanese:
        # MFC's post-paint sanity check used FindWindowA with a CP932
        # caption. Use its existing HWND so Japanese captions work even
        # when Wine's ANSI code page is not Japanese.
        edit(pe,0x4011e3,'68f43042006a00ff1528ca4200',
             '8b461c'+'90'*10)
    for typ,name,_,entry in walk_resources(pe):
        if typ==5 and name==102:
            rva,n=struct.unpack_from('<II',pe.d,entry)
            b=portable_dialog(bytes(pe.d[pe.off(rva):pe.off(rva)+n]), japanese)
            struct.pack_into('<II',pe.d,entry,0x39000+len(payload),len(b))
            payload.extend(b)
    if not japanese:
        # MFC checks FindWindow against this exact caption after painting.
        at=pe.off(0x230f4)
        old=bytes(pe.d[at:]).split(b'\0')[0]
        title=b'Magical Chase for Windows95'
        pe.d[at:at+len(old)+1]=title+bytes(len(old)+1-len(title))
    add_section(pe,payload,0x39000)
    return bytes(pe.d)


def patch_staff(data):
    if hashlib.sha256(data).hexdigest()!=STAFF_SHA256:
        raise ValueError('Unexpected STAFF.EXE on this disc')
    pe=PE(data)
    # The original WS_POPUP + CW_USEDEFAULT creates a zero-size window
    # under Wine. An ordinary overlapped window honors ShowWindow(MAXIMIZE).
    edit(pe,0x401091,'6800000080','680000cf00')
    edit(pe,0x401096,'6828504000','6820504000')
    edit(pe,0x401000,'83ec445356',branch(0x401000,0x40a100))
    edit(pe,0x401272,'bd38504000','bd00a64000')
    edit(pe,0x40127c,'bd2c504000','bd00a44000')
    payload=bytearray(0x800)
    payload[:len(STAFF_PATHS)]=STAFF_PATHS
    # Call the path helper, replay displaced instructions, resume original.
    payload[0x100:0x10f]=bytes.fromhex(branch(0x40a100,0x40a000,call=True)+'83ec445356'+branch(0x40a10a,0x401005))
    add_section(pe,payload,0xa000)
    return bytes(pe.d)


if __name__=='__main__':
    import argparse
    from pathlib import Path
    from install_magical_chase import open_source
    parser=argparse.ArgumentParser(description='Patch the original disc AUTORUN.EXE for portable use.')
    parser.add_argument('source')
    parser.add_argument('output')
    parser.add_argument('--japanese',action='store_true')
    args=parser.parse_args()
    source=open_source(args.source)
    Path(args.output).write_bytes(patch(source.read_file('RUN/AUTORUN.EXE'),args.japanese))
    print('Patched original autorun: '+args.output)
