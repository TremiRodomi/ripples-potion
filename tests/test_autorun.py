"""Regression tests using a locally supplied original disc (never bundled)."""
from pathlib import Path
import struct
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'patcher'))
import install_magical_chase as installer
import patch_autorun as patcher
from patch_mchase import PE, walk_resources, sz_or_ord


def dialog_controls(data):
    """Read IDs and bounds from the resulting extended dialog resource."""
    o = 26
    for _ in range(3):
        _, o = sz_or_ord(data, o)
    if struct.unpack_from('<I', data, 12)[0] & 0x40:
        _, o = sz_or_ord(data, o + 6)
    controls = {}
    for _ in range(struct.unpack_from('<H', data, 16)[0]):
        o = (o + 3) & ~3
        rect = struct.unpack_from('<hhhh', data, o + 12)
        ident = struct.unpack_from('<I', data, o + 20)[0]
        o += 24
        _, o = sz_or_ord(data, o)
        _, o = sz_or_ord(data, o)
        size = struct.unpack_from('<H', data, o)[0]
        o += 2 + size
        controls[ident] = rect
    return controls

class OriginalLauncherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cue=Path(__file__).resolve().parents[1]/'MagicalChase.cue'
        if not cue.exists():
            raise unittest.SkipTest('Requires a local original MagicalChase.cue')
        source=installer.open_source(str(cue))
        cls.autorun=source.read_file('RUN/AUTORUN.EXE')
        cls.staff=source.read_file('RUN/MCHASE/SRC/STAFF.EXE')

    def test_original_code_is_retained(self):
        for japanese in (False,True):
            original=PE(self.autorun)
            result=PE(patcher.patch(self.autorun,japanese))
            self.assertEqual(original.d[original.opt+16:original.opt+20],
                             result.d[result.opt+16:result.opt+20])
            text=next(s for s in original.sections() if s[1]==b'.text')
            start,size=text[4],text[5]
            changed=sum(a!=b for a,b in zip(original.d[start:start+size],result.d[start:start+size]))
            self.assertLess(changed,100)
            # Original artwork renderer and process creation/wait handlers.
            for a,b in [(0x1c00,0x1e31),(0x1348,0x13db),(0x1b94,0x1bc9)]:
                self.assertEqual(original.d[original.off(a):original.off(b)],
                                 result.d[result.off(a):result.off(b)])

    def test_staff_original_renderer_retained(self):
        a,b=PE(self.staff),PE(patcher.patch_staff(self.staff))
        self.assertEqual(a.d[a.off(0x1250):a.off(0x1272)],b.d[b.off(0x1250):b.off(0x1272)])
        self.assertEqual(a.d[a.off(0x1281):a.off(0x1499)],b.d[b.off(0x1281):b.off(0x1499)])

    def test_installer_buttons_removed_in_both_languages(self):
        for japanese in (False, True):
            pe = PE(patcher.patch(self.autorun, japanese))
            for typ, name, _, entry in walk_resources(pe):
                if typ != 5 or name != 102:
                    continue
                rva, size = struct.unpack_from('<II', pe.d, entry)
                data = pe.d[pe.off(rva):pe.off(rva) + size]
                controls = dialog_controls(data)
                self.assertEqual(set(controls), {2, 1002, 1003, 1006, 1007})
                # Exit is full width, and the visible buttons don't overlap.
                self.assertEqual(controls[2][::2], controls[1002][::2])
                height = struct.unpack_from('<h', data, 24)[0]
                previous_bottom = 0
                for ident in (1002, 1006, 1007, 2):
                    x, y, width, h = controls[ident]
                    self.assertGreaterEqual(y, previous_bottom)
                    self.assertLess(y + h, height)
                    previous_bottom = y + h

    def test_wrong_sources_rejected(self):
        for fn,data in [(patcher.patch,self.autorun),(patcher.patch_staff,self.staff)]:
            with self.assertRaises(ValueError):fn(data[:-1]+bytes([data[-1]^1]))

if __name__=='__main__':unittest.main()
