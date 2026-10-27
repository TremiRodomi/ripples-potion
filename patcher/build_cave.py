"""Assemble the code cave used by patch_mchase.py (dev tool; needs keystone-engine).
Prints the hex blob to paste into patch_mchase.py."""
from keystone.keystone import Ks
from keystone.keystone_const import KS_ARCH_X86, KS_MODE_32

BASE   = 0x90d000          # VA of the new .mcfix section (RVA 0x50d000)
SIG    = BASE + 0x300      # "?GOPA242"
DEFSTR = BASE + 0x310      # default command line
CMDBUF = BASE + 0x320      # padded copy of the user's command line
EXEDIR = BASE + 0x340      # directory of Mchase.exe (used for mus\ path)
DESKOK = BASE + 0x2f0      # dword: 1 if the desktop was 8/16-bit at startup
WAVROOT = BASE + 0x30c     # dword: pointer used instead of the CD drive for WAV music

GetModuleFileNameA = 0x4a558c
GetModuleHandleA, GetProcAddress = 0x4a551c, 0x4a5594

# Portable settings (--portable): the registry calls in the settings load/save
# routines are pointed at these replacements, which use <exe folder>\MCHASE.INI.
PORT_CODE = BASE + 0x450   # replacement functions
PORT_STR  = BASE + 0x600   # strings, see PORT_STRINGS in patch_mchase.py
S_KERNEL, S_GETS, S_WRITES, S_SECTION, S_ININAME, S_ATTR = (
    PORT_STR, PORT_STR + 0x10, PORT_STR + 0x30, PORT_STR + 0x50, PORT_STR + 0x60,
    PORT_STR + 0x70)
INIBUF    = BASE + 0x700   # 0x110 bytes: full path of the INI file
PTR_TABLE = BASE + 0x820   # open, query, close, create, set, GetPPStruct,
                           # WritePPStruct, GetFileAttributesA
GetDC, ReleaseDC, GetDeviceCaps = 0x4a56f0, 0x4a56e8, 0x4a5490

DESKTOP_OK = BASE + 0x100
asm = f"""
; ---- cave_cmdline: replaces 'mov edi,[ebp+10h]; add esp,4; mov esi,eax' at 4214B8
cave_cmdline:
    pop ecx
    add esp, 4
    push ecx
    mov esi, eax
    mov edi, dword ptr [ebp+0x10]
    push esi
    cmp byte ptr [edi], 0
    je use_default
    mov ecx, 1
chk:
    mov al, byte ptr [edi+ecx]
    cmp al, byte ptr [ecx+{SIG:#x}]
    jne use_default
    inc ecx
    cmp ecx, 8
    jb chk
    mov esi, {CMDBUF:#x}           ; copy (max 31 chars) so edi[8]/edi[9] are always readable
    xor ecx, ecx
cpy:
    mov al, byte ptr [edi+ecx]
    mov byte ptr [esi+ecx], al
    test al, al
    jz cpy_done
    inc ecx
    cmp ecx, 31
    jb cpy
cpy_done:
    mov edi, esi
    jmp set_dir
use_default:
    mov edi, {DEFSTR:#x}
set_dir:
    push 260
    push {EXEDIR:#x}
    push 0
    call dword ptr [{GetModuleFileNameA:#x}]
    mov ecx, {EXEDIR:#x}
    xor edx, edx
scan:
    mov al, byte ptr [ecx]
    test al, al
    jz scan_end
    cmp al, 0x5c
    jne scan_next
    mov edx, ecx
scan_next:
    inc ecx
    jmp scan
scan_end:
    test edx, edx
    jz no_dir
    mov byte ptr [edx], 0
    mov dword ptr [{WAVROOT:#x}], {EXEDIR:#x}
no_dir:
    pop esi
    ret

@@desktop_ok
; ---- desktop_ok: eax=1 if desktop is 8 or 16 bpp
desktop_ok:
    push esi
    push edi
    push 0
    call dword ptr [{GetDC:#x}]
    mov esi, eax
    push 12
    push esi
    call dword ptr [{GetDeviceCaps:#x}]
    mov edi, eax
    push esi
    push 0
    call dword ptr [{ReleaseDC:#x}]
    xor eax, eax
    cmp edi, 8
    je dok
    cmp edi, 16
    jne dbad
dok:
    inc eax
dbad:
    pop edi
    pop esi
    ret

@@cave_mode
; ---- cave_mode: replaces 'mov ebx,2' at 42153D (non-'E' => windowed only if desktop allows; remembers result)
cave_mode:
    call {DESKTOP_OK:#x}
    mov dword ptr [{DESKOK:#x}], eax
    xor ebx, ebx
    test eax, eax
    jz cm_ret
    mov ebx, 2
cm_ret:
    ret

@@cave_toggle
; ---- cave_toggle: replaces 'mov eax,[4A0948h]' at 420AE5 (Alt+Enter: block fullscreen->window unless the startup desktop was 8/16-bit)
cave_toggle:
    mov eax, dword ptr [0x4a0948]
    test eax, eax
    jnz tg_skip
    cmp dword ptr [esi+0x40], 2
    je tg_go
    cmp dword ptr [{DESKOK:#x}], 0
    je tg_skip
tg_go:
    push 0x420aee
    ret
tg_skip:
    push 0x420b18
    ret

@@cave_bpp
; ---- cave_bpp: replaces 'mov [46774Ch],eax' at 4277E7 (fullscreen depth = desktop depth)
cave_bpp:
    cmp eax, 8
    je bpp_store
    cmp eax, 16
    je bpp_store
    mov eax, dword ptr [0x467750]
bpp_store:
    mov dword ptr [0x46774c], eax
    ret
"""

P_GETS, P_WRITES, P_ATTR = PTR_TABLE + 20, PTR_TABLE + 24, PTR_TABLE + 28
port_asm = f"""
; RegOpenKeyExA(hKey, sub, opts, sam, phkResult): fails while there is no INI
; yet, so the game keeps its built-in defaults (like a missing registry key)
fake_open:
    call ini_path
    push eax
    call dword ptr [{P_ATTR:#x}]
    cmp eax, -1
    je fo_fail
    mov eax, dword ptr [esp+20]
    mov dword ptr [eax], 1
    xor eax, eax
    ret 20
fo_fail:
    mov eax, 2
    ret 20
; RegCloseKey(hKey)
fake_close:
    xor eax, eax
    ret 4
; RegCreateKeyExA(hKey, sub, res, cls, opts, sam, sa, phkResult, pdisp)
fake_create:
    mov eax, dword ptr [esp+32]
    mov dword ptr [eax], 1
    mov eax, dword ptr [esp+36]
    test eax, eax
    jz fc_done
    mov dword ptr [eax], 2
fc_done:
    xor eax, eax
    ret 36
; RegQueryValueExA(hKey, name, res, ptype, data, pcb) -> GetPrivateProfileStructA
fake_query:
    call ini_path
    push eax
    mov ecx, dword ptr [esp+28]
    push dword ptr [ecx]
    push dword ptr [esp+28]
    push dword ptr [esp+20]
    push {S_SECTION:#x}
    call dword ptr [{P_GETS:#x}]
    test eax, eax
    jz fq_fail
    mov ecx, dword ptr [esp+16]
    test ecx, ecx
    jz fq_ok
    mov dword ptr [ecx], 3
fq_ok:
    xor eax, eax
    ret 24
fq_fail:
    mov eax, 2
    ret 24
; RegSetValueExA(hKey, name, res, type, data, cb) -> WritePrivateProfileStructA
fake_set:
    call ini_path
    push eax
    push dword ptr [esp+28]
    push dword ptr [esp+28]
    push dword ptr [esp+20]
    push {S_SECTION:#x}
    call dword ptr [{P_WRITES:#x}]
    test eax, eax
    jz fs_fail
    xor eax, eax
    ret 24
fs_fail:
    mov eax, 5
    ret 24
; eax = INIBUF; first call fills it and looks up the profile functions
ini_path:
    cmp byte ptr [{INIBUF:#x}], 0
    jne ip_done
    push esi
    push edi
    push 260
    push {INIBUF:#x}
    push 0
    call dword ptr [{GetModuleFileNameA:#x}]
    mov ecx, {INIBUF:#x}
    mov edx, ecx
ip_scan:
    mov al, byte ptr [ecx]
    test al, al
    jz ip_scanned
    inc ecx
    cmp al, 0x5c
    jne ip_scan
    mov edx, ecx
    jmp ip_scan
ip_scanned:
    mov esi, {S_ININAME:#x}
    mov edi, edx
ip_copy:
    mov al, byte ptr [esi]
    mov byte ptr [edi], al
    inc esi
    inc edi
    test al, al
    jnz ip_copy
    push {S_KERNEL:#x}
    call dword ptr [{GetModuleHandleA:#x}]
    mov esi, eax
    push {S_GETS:#x}
    push esi
    call dword ptr [{GetProcAddress:#x}]
    mov dword ptr [{P_GETS:#x}], eax
    push {S_WRITES:#x}
    push esi
    call dword ptr [{GetProcAddress:#x}]
    mov dword ptr [{P_WRITES:#x}], eax
    push {S_ATTR:#x}
    push esi
    call dword ptr [{GetProcAddress:#x}]
    mov dword ptr [{P_ATTR:#x}], eax
    pop edi
    pop esi
ip_done:
    mov eax, {INIBUF:#x}
    ret
"""
ks = Ks(KS_ARCH_X86, KS_MODE_32)
asm = "\n".join(l.split(";")[0].rstrip() for l in asm.splitlines())
OFFS = {'cave_cmdline': 0x000, 'desktop_ok': 0x100, 'cave_mode': 0x140, 'cave_toggle': 0x160, 'cave_bpp': 0x1a0}
parts = asm.split('@@')
names = ['cave_cmdline'] + [p.split(chr(10))[0].strip() for p in parts[1:]]
code = bytearray(b'\xcc' * 0x200)
for name, part in zip(names, parts):
    if name != 'cave_cmdline':
        part = part.split(chr(10), 1)[1]
    va = BASE + OFFS[name]
    enc, _ = ks.asm(part, va)
    o = OFFS[name]
    assert len(enc) <= (sorted([x for x in OFFS.values() if x > o] + [0x200])[0] - o), name
    code[o:o + len(enc)] = bytes(enc)
    print('%-13s %#x  %d bytes' % (name, va, len(enc)))
print('CAVE_CODE = bytes.fromhex(%r)' % bytes(code).hex())

port_asm = "\n".join(l.split(";")[0].rstrip() for l in port_asm.splitlines())
enc, _ = ks.asm(port_asm, PORT_CODE)
assert len(enc) <= PORT_STR - PORT_CODE
# entry offsets (relative to PORT_CODE) for the pointer table
labels = {}
for name in ('fake_open', 'fake_query', 'fake_close', 'fake_create', 'fake_set'):
    head = port_asm.split(name + ':')[0]
    labels[name] = len(ks.asm(head + '\nini_path:', PORT_CODE)[0] or b'')
print('PORT_CODE = bytes.fromhex(%r)' % bytes(enc).hex())
print('PORT_ENTRIES = %r' % [labels[n] for n in
      ('fake_open', 'fake_query', 'fake_close', 'fake_create', 'fake_set')])
