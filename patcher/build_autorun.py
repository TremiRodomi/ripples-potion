"""Developer tool: assemble small hooks for the ORIGINAL autorun/staff EXEs.
Requires keystone-engine. No executable replacement or original assets bundled.
"""
from pathlib import Path
from keystone.keystone import Ks
from keystone.keystone_const import KS_ARCH_X86, KS_MODE_32
ks = Ks(KS_ARCH_X86, KS_MODE_32)
def asm(code, va):
    return bytes(ks.asm(code, va)[0]).hex()
# Autorun's original path globals and IAT are reused.
root = asm('''
 pushad
 push 240
 push 0x427640
 push 0
 call dword ptr [0x42c78c]
 mov ecx, 0x427640
 xor edx, edx
 scan:
 mov al, byte ptr [ecx]
 test al, al
 jz done
 cmp al, 0x5c
 jne next
 mov edx, ecx
 next:
 inc ecx
 jmp scan
 done:
 test edx, edx
 jz end
 mov byte ptr [edx], 0
 end:
 mov byte ptr [0x427748], 0x5f
 popad
 ret
''',0x439000)
# Called after GetCurrentDirectory in the ORIGINAL game launch handler.
paths = asm('''
 pushad
 mov esi, 0x427640
 lea edi, [esp+0x194]
 cpdir:
 lodsb
 stosb
 test al, al
 jnz cpdir
 mov esi, 0x427640
 lea edi, [esp+0x90]
 mov al, 0x22
 stosb
 cpcmd:
 lodsb
 test al, al
 jz tail
 stosb
 jmp cpcmd
 tail:
 mov esi, 0x439300
 copytail:
 lodsb
 stosb
 test al, al
 jnz copytail
 popad
 mov dword ptr [esp+0xc], 0
 ret
''',0x439100)
# ShowWindow paints synchronously while the original suppression flag is
# still set. Once it is cleared, invalidate the original dialog to repaint.
repaint = asm('''
 mov dword ptr [0x427578], eax
 test eax, eax
 jnz done
 pushad
 call 0x4152bc
 test eax, eax
 jz finish
 mov edx, dword ptr [eax]
 mov ecx, eax
 call dword ptr [edx+0x7c]
 test eax, eax
 jz finish
 push 0
 push 0
 push dword ptr [eax+0x1c]
 call dword ptr [0x42c9d4]
 finish:
 popad
 done:
 ret
''',0x439200)
# STAFF resolves both bitmap names relative to its own executable.
staff = asm('''
 pushad
 push 240
 push 0x40a400
 push 0
 call dword ptr [0x407238]
 mov esi, 0x40a400
 xor edx, edx
 scan:
 mov al, byte ptr [esi]
 test al, al
 jz done
 cmp al, 0x5c
 jne next
 mov edx, esi
 next:
 inc esi
 jmp scan
 done:
 inc edx
 mov byte ptr [edx], 0
 mov esi, 0x40a400
 mov edi, 0x40a600
 copy:
 lodsb
 stosb
 test al, al
 jnz copy
 mov edi, edx
 mov esi, 0x40502c
 low:
 lodsb
 stosb
 test al, al
 jnz low
 mov edi, 0x40a600
 scan2:
 cmp byte ptr [edi], 0
 je high
 inc edi
 jmp scan2
 high:
 mov esi, 0x405038
 highcopy:
 lodsb
 stosb
 test al, al
 jnz highcopy
 popad
 ret
''',0x40a000)
Path(__file__).with_name('autorun_hooks.py').write_text(
    '"""Small hooks assembled by build_autorun.py; no game code or assets."""\n'
    + '\n'.join(name+' = bytes.fromhex('+repr(value)+')' for name,value in
                [('ROOT',root),('PATHS',paths),('REPAINT',repaint),('STAFF_PATHS',staff)])+'\n')
