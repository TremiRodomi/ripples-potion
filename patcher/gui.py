#!/usr/bin/env python3
"""
Ripple's Potion - graphical installer for Magical Chase (Windows 95).

    python3 gui.py [source]
    python3 gui.py --ask [source]                       text questions
    python3 gui.py <source> <output folder> [options]   command line
    --lang=ja / --lang=en                               installer language
                                                        (default: the system's)

The last two forms are the same as install_magical_chase.py; they make the
single-file builds (RipplesPotion.exe, RipplesPotion-linux-x86_64) all-in-one.

Uses tkinter, which comes with Python on Windows. On Linux it may be a
separate package (python3-tkinter on Fedora, python3-tk on Debian/Ubuntu).
Exits with code 3 if tkinter is missing or there is no display, so the
install scripts can fall back to the text questions.
"""
import glob
import os
import queue
import subprocess
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lang  # noqa: E402
from lang import t  # noqa: E402

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ImportError:
    print(t('tkinter is not installed, so the graphical installer cannot start.'))
    if sys.platform.startswith('linux'):
        print('Fedora: sudo dnf install python3-tkinter   '
              'Debian/Ubuntu: sudo apt install python3-tk')
    sys.exit(3)

import install_magical_chase as inst  # noqa: E402

TITLE = "Ripple's Potion"
SUBTITLE = 'No-CD + modern Windows patch for Magical Chase (QUEST, 1998)'
STEPS = len(inst.GAME_FILES) + 19          # files + music tracks
DEFAULT_OUT = os.path.join(os.path.expanduser('~'), 'Games', 'MagicalChase')


def cd_drives():
    """Optical drives to offer as the source."""
    if os.name == 'nt':
        import ctypes
        k = ctypes.windll.kernel32
        mask = k.GetLogicalDrives()
        return ['%s:' % chr(65 + i) for i in range(26)
                if mask >> i & 1 and k.GetDriveTypeW('%s:\\' % chr(65 + i)) == 5]
    return sorted(glob.glob('/dev/sr[0-9]*'))


class App:
    def __init__(self, root, source=''):
        self.root = root
        self.events = queue.Queue()
        self.out_dir = None
        self.done_steps = 0
        self.main = None
        root.resizable(False, False)
        drives = cd_drives()
        self.drives = drives
        self.source = tk.StringVar(value=source or (drives[0] if drives else ''))
        self.out = tk.StringVar(value=DEFAULT_OUT)
        self.music = tk.StringVar(value='cd')
        self.japanese = tk.BooleanVar(value=lang.lang == 'ja')
        self.portable = tk.BooleanVar(value=True)
        self.arrows = tk.BooleanVar(value=True)
        self.ddraw = tk.BooleanVar(value=True)
        names = dict(lang.LANGUAGES)
        self.ui_lang = tk.StringVar(value=names[lang.lang])
        self.build()

    def switch_language(self, _event=None):
        code = {name: code for code, name in lang.LANGUAGES}[self.ui_lang.get()]
        if code != lang.lang:
            lang.set_language(code)
            self.build()

    def build(self):
        """Create the window's contents in the current language."""
        root = self.root
        if self.main is not None:
            self.main.destroy()
        root.title('%s - %s' % (TITLE, t('Magical Chase installer')))
        main = self.main = ttk.Frame(root, padding=10)
        main.grid(sticky='nsew')
        main.columnconfigure(0, weight=1)

        head = ttk.Frame(main)
        head.grid(sticky='ew')
        head.columnconfigure(0, weight=1)
        ttk.Label(head, text=TITLE, font=('TkDefaultFont', 16, 'bold')).grid(
            row=0, column=0, sticky='w')
        self.lang_box = ttk.Combobox(head, textvariable=self.ui_lang, state='readonly',
                                     values=[name for _, name in lang.LANGUAGES], width=8)
        self.lang_box.grid(row=0, column=1, sticky='ne')
        self.lang_box.bind('<<ComboboxSelected>>', self.switch_language)
        ttk.Label(main, text=t(SUBTITLE)).grid(sticky='w', pady=(0, 10))

        # source
        box = ttk.LabelFrame(main, text=t('Game disc (drive, .cue or .iso)'), padding=8)
        box.grid(sticky='ew', pady=4)
        box.columnconfigure(0, weight=1)
        ttk.Combobox(box, textvariable=self.source, values=self.drives, width=50).grid(
            row=0, column=0, sticky='ew')
        ttk.Button(box, text=t('Browse...'), command=self.pick_image).grid(
            row=0, column=1, padx=(6, 0))

        # destination
        box = ttk.LabelFrame(main, text=t('Install to'), padding=8)
        box.grid(sticky='ew', pady=4)
        box.columnconfigure(0, weight=1)
        ttk.Entry(box, textvariable=self.out, width=52).grid(row=0, column=0, sticky='ew')
        ttk.Button(box, text=t('Browse...'), command=self.pick_folder).grid(
            row=0, column=1, padx=(6, 0))

        # music
        box = ttk.LabelFrame(main, text=t('Music'), padding=8)
        box.grid(sticky='ew', pady=4)
        for col, (key, label, lines) in enumerate(inst.MUSIC_CHOICES):
            box.columnconfigure(col, weight=1, uniform='music')
            ttk.Radiobutton(box, text=t(label), value=key, variable=self.music).grid(
                row=0, column=col, sticky='w')
            # each line is one point; a point that doesn't fit wraps indented
            text = '\n'.join(t(line) for line in lines)
            ttk.Label(box, text=text, justify='left', wraplength=300).grid(
                row=1, column=col, sticky='nw', padx=(24, 8))

        # options
        box = ttk.LabelFrame(main, text=t('Options'), padding=8)
        box.grid(sticky='ew', pady=4)
        row = ttk.Frame(box)
        row.grid(sticky='w')
        ttk.Label(row, text=t('Menus and in-game text:')).grid(row=0, column=0)
        ttk.Radiobutton(row, text=t('English'), value=False, variable=self.japanese).grid(
            row=0, column=1, padx=6)
        ttk.Radiobutton(row, text=t('Original Japanese (日本語)'), value=True,
                        variable=self.japanese).grid(row=0, column=2)
        ttk.Checkbutton(box, variable=self.portable,
                        text=t('Portable: save settings in the game folder (MCHASE.INI), '
                               'not the registry')).grid(sticky='w', pady=(6, 0))
        ttk.Checkbutton(box, variable=self.arrows,
                        text=t('Move with the arrow keys (untick for the original '
                               'numpad 8/2/4/6)')).grid(sticky='w')
        ttk.Checkbutton(box, variable=self.ddraw,
                        text=t('cnc-ddraw: scaled fullscreen, Alt+Enter for a window '
                               '(2.7 MB)')).grid(sticky='w')

        # install + progress
        row = ttk.Frame(main)
        row.grid(sticky='ew', pady=(10, 4))
        row.columnconfigure(0, weight=1)
        self.bar = ttk.Progressbar(row, maximum=STEPS)
        self.bar.grid(row=0, column=0, sticky='ew')
        self.open_btn = ttk.Button(row, text=t('Open folder'), command=self.open_folder,
                                   state='normal' if self.out_dir else 'disabled')
        self.open_btn.grid(row=0, column=1, padx=(6, 0))
        self.go = ttk.Button(row, text=t('Install'), command=self.start)
        self.go.grid(row=0, column=2, padx=(6, 0))
        self.status = ttk.Label(main, text='')
        self.status.grid(sticky='w')
        self.log = tk.Text(main, height=3, width=70, state='disabled')
        self.log.grid(sticky='ew', pady=(4, 0))

    # ---- pickers
    def pick_image(self):
        path = filedialog.askopenfilename(
            title=t('Magical Chase disc image'),
            filetypes=[(t('Disc images'), '*.cue *.CUE *.iso *.ISO'), (t('All files'), '*')])
        if path:
            self.source.set(path)

    def pick_folder(self):
        path = filedialog.askdirectory(title=t('Install Magical Chase to'), mustexist=False)
        if path:
            self.out.set(os.path.normpath(path))

    def open_folder(self):
        if os.name == 'nt':
            os.startfile(self.out_dir)
        else:
            subprocess.Popen(['xdg-open', self.out_dir])

    # ---- install
    def start(self):
        src, out = self.source.get().strip(), self.out.get().strip()
        if not src or not out:
            messagebox.showwarning(TITLE, t('Choose the game disc and an install folder.'))
            return
        if (self.portable.get() and os.name == 'nt' and
                'program files' in os.path.abspath(out).lower()):
            if not messagebox.askyesno(
                    TITLE, t('Portable settings need a folder the game can write to, '
                             'and Program Files usually is not.\n\nInstall there anyway?')):
                return
        self.out_dir = out
        self.done_steps = 0
        self.bar['value'] = 0
        self.bar['maximum'] = STEPS + self.ddraw.get()
        self.go['state'] = self.open_btn['state'] = 'disabled'
        self.lang_box['state'] = 'disabled'     # rebuilding would lose the progress
        self.log['state'] = 'normal'
        self.log.delete('1.0', 'end')
        self.log['state'] = 'disabled'
        opts = dict(disc_wav=self.music.get() == 'wav', japanese=self.japanese.get(),
                    arrow_keys=self.arrows.get(), portable=self.portable.get(),
                    ddraw=self.ddraw.get())
        threading.Thread(target=self.work, args=(src, out, opts), daemon=True).start()
        self.root.after(100, self.poll)

    def work(self, src, out, opts):
        try:
            inst.install(src, out, log=lambda t: self.events.put(('log', t)),
                         progress=lambda t: self.events.put(('progress', t)), **opts)
            self.events.put(('done', None))
        except SystemExit as e:
            self.events.put(('error', str(e.code)))
        except Exception as e:  # anything unexpected still ends up in the window
            self.events.put(('error', '%s: %s' % (type(e).__name__, e)))

    def poll(self):
        while True:
            try:
                kind, text = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == 'progress':
                self.status['text'] = text.strip()
            elif kind == 'log':
                if text.startswith('   '):
                    self.done_steps += 1
                    self.bar['value'] = self.done_steps
                self.status['text'] = ''
                self.write(text)
            else:
                self.go['state'] = 'normal'
                self.lang_box['state'] = 'readonly'
                if kind == 'done':
                    self.bar['value'] = self.bar['maximum']
                    self.open_btn['state'] = 'normal'
                    exe = os.path.join(self.out_dir, 'Mchase.exe')
                    run = exe if os.name == 'nt' else os.path.join(
                        self.out_dir, 'magical-chase.sh')
                    self.write(t('Installed. Start the game with %s') % run)
                    messagebox.showinfo(TITLE, t('Magical Chase is installed.\n\n'
                                                 'Start it with:\n%s') % run)
                else:
                    self.write(t('Error: ') + text)
                    messagebox.showerror(TITLE, text)
                return
        self.root.after(100, self.poll)

    def write(self, text):
        self.log['state'] = 'normal'
        self.log.insert('end', text.strip('\r') + '\n')
        self.log.see('end')
        self.log['state'] = 'disabled'


def main():
    args = sys.argv[1:]
    positional = [a for a in args if not a.startswith('--')]
    has_console = sys.stdout is not None        # not the windowed Windows exe
    if has_console and ('--ask' in args or len(positional) >= 2 or '--help' in args):
        return inst.main()
    if os.name == 'nt':
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)   # sharp text on HiDPI
        except (AttributeError, OSError):
            pass
    try:
        root = tk.Tk()
    except tk.TclError as e:
        if getattr(sys, 'frozen', False) and has_console and sys.stdin.isatty():
            print(t('Cannot open a window (%s), so asking here instead.\n') % e)
            sys.argv[1:] = ['--ask'] + positional
            return inst.main()
        print(t('Cannot open a window (%s). Use the command line installer instead.') % e)
        sys.exit(3)
    if os.name != 'nt':
        style = ttk.Style(root)
        style.theme_use('clam')                 # Tk's default Linux theme looks dated
        style.configure('TLabelframe', labeloutside=False, labelmargins=(6, 0, 6, 0))
    App(root, positional[0] if positional else '')
    root.mainloop()


if __name__ == '__main__':
    main()
