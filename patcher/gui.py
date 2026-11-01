#!/usr/bin/env python3
"""
Ripple's Potion - graphical installer for Magical Chase (Windows 95).

    python3 gui.py [source]

Uses tkinter, which comes with Python on Windows. On Linux it may be a
separate package (python3-tkinter on Fedora, python3-tk on Debian/Ubuntu).
Exits with code 3 if tkinter is missing, so install.bat can fall back to its
text questions.
"""
import glob
import os
import queue
import subprocess
import sys
import threading

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ImportError:
    print('tkinter is not installed, so the graphical installer cannot start.')
    if sys.platform.startswith('linux'):
        print('Fedora: sudo dnf install python3-tkinter   '
              'Debian/Ubuntu: sudo apt install python3-tk')
    sys.exit(3)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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
        root.title(TITLE + ' - Magical Chase installer')
        root.resizable(False, False)
        main = ttk.Frame(root, padding=14)
        main.grid(sticky='nsew')
        main.columnconfigure(0, weight=1)

        ttk.Label(main, text=TITLE, font=('TkDefaultFont', 16, 'bold')).grid(sticky='w')
        ttk.Label(main, text=SUBTITLE).grid(sticky='w', pady=(0, 10))

        # source
        box = ttk.LabelFrame(main, text='Game disc (drive, .cue or .iso)', padding=8)
        box.grid(sticky='ew', pady=4)
        box.columnconfigure(0, weight=1)
        drives = cd_drives()
        self.source = tk.StringVar(value=source or (drives[0] if drives else ''))
        ttk.Combobox(box, textvariable=self.source, values=drives, width=50).grid(
            row=0, column=0, sticky='ew')
        ttk.Button(box, text='Browse...', command=self.pick_image).grid(
            row=0, column=1, padx=(6, 0))

        # destination
        box = ttk.LabelFrame(main, text='Install to', padding=8)
        box.grid(sticky='ew', pady=4)
        box.columnconfigure(0, weight=1)
        self.out = tk.StringVar(value=DEFAULT_OUT)
        ttk.Entry(box, textvariable=self.out, width=52).grid(row=0, column=0, sticky='ew')
        ttk.Button(box, text='Browse...', command=self.pick_folder).grid(
            row=0, column=1, padx=(6, 0))

        # music
        box = ttk.LabelFrame(main, text='Music', padding=8)
        box.grid(sticky='ew', pady=4)
        self.music = tk.StringVar(value='cd')
        for col, (key, label, lines) in enumerate(inst.MUSIC_CHOICES):
            box.columnconfigure(col, weight=1, uniform='music')
            ttk.Radiobutton(box, text=label, value=key, variable=self.music).grid(
                row=0, column=col, sticky='w')
            # each line is one point; a point that doesn't fit wraps indented
            text = '\n'.join(lines)
            ttk.Label(box, text=text, justify='left', wraplength=300).grid(
                row=1, column=col, sticky='nw', padx=(24, 8))

        # options
        box = ttk.LabelFrame(main, text='Options', padding=8)
        box.grid(sticky='ew', pady=4)
        self.japanese = tk.BooleanVar(value=False)
        lang = ttk.Frame(box)
        lang.grid(sticky='w')
        ttk.Label(lang, text='Menus and settings:').grid(row=0, column=0)
        ttk.Radiobutton(lang, text='English', value=False, variable=self.japanese).grid(
            row=0, column=1, padx=6)
        ttk.Radiobutton(lang, text='Original Japanese (日本語)', value=True,
                        variable=self.japanese).grid(row=0, column=2)
        self.portable = tk.BooleanVar(value=True)
        ttk.Checkbutton(box, variable=self.portable,
                        text='Portable: save settings in the game folder (MCHASE.INI), '
                             'not the registry').grid(sticky='w', pady=(6, 0))
        self.arrows = tk.BooleanVar(value=True)
        ttk.Checkbutton(box, variable=self.arrows,
                        text='Move with the arrow keys (untick for the original '
                             'numpad 8/2/4/6)').grid(sticky='w')
        self.ddraw = tk.BooleanVar(value=True)
        ttk.Checkbutton(box, variable=self.ddraw,
                        text='cnc-ddraw: scaled 4:3 fullscreen, Alt+Enter for a window '
                             '(downloads 2.7 MB)').grid(sticky='w')

        # install + progress
        row = ttk.Frame(main)
        row.grid(sticky='ew', pady=(10, 4))
        row.columnconfigure(0, weight=1)
        self.bar = ttk.Progressbar(row, maximum=STEPS)
        self.bar.grid(row=0, column=0, sticky='ew')
        self.open_btn = ttk.Button(row, text='Open folder', command=self.open_folder,
                                   state='disabled')
        self.open_btn.grid(row=0, column=1, padx=(6, 0))
        self.go = ttk.Button(row, text='Install', command=self.start)
        self.go.grid(row=0, column=2, padx=(6, 0))
        self.status = ttk.Label(main, text='')
        self.status.grid(sticky='w')
        self.log = tk.Text(main, height=4, width=70, state='disabled')
        self.log.grid(sticky='ew', pady=(4, 0))

    # ---- pickers
    def pick_image(self):
        path = filedialog.askopenfilename(
            title='Magical Chase disc image',
            filetypes=[('Disc images', '*.cue *.CUE *.iso *.ISO'), ('All files', '*')])
        if path:
            self.source.set(path)

    def pick_folder(self):
        path = filedialog.askdirectory(title='Install Magical Chase to', mustexist=False)
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
            messagebox.showwarning(TITLE, 'Choose the game disc and an install folder.')
            return
        if (self.portable.get() and os.name == 'nt' and
                'program files' in os.path.abspath(out).lower()):
            if not messagebox.askyesno(
                    TITLE, 'Portable settings need a folder the game can write to, and '
                           'Program Files usually is not.\n\nInstall there anyway?'):
                return
        self.out_dir = out
        self.done_steps = 0
        self.bar['value'] = 0
        self.bar['maximum'] = STEPS + self.ddraw.get()
        self.go['state'] = self.open_btn['state'] = 'disabled'
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
                if kind == 'done':
                    self.bar['value'] = self.bar['maximum']
                    self.open_btn['state'] = 'normal'
                    exe = os.path.join(self.out_dir, 'Mchase.exe')
                    run = exe if os.name == 'nt' else os.path.join(
                        self.out_dir, 'magical-chase.sh')
                    self.write('Installed. Start the game with %s' % run)
                    messagebox.showinfo(TITLE, 'Magical Chase is installed.\n\n'
                                               'Start it with:\n%s' % run)
                else:
                    self.write('Error: ' + text)
                    messagebox.showerror(TITLE, text)
                return
        self.root.after(100, self.poll)

    def write(self, text):
        self.log['state'] = 'normal'
        self.log.insert('end', text.strip('\r') + '\n')
        self.log.see('end')
        self.log['state'] = 'disabled'


def main():
    if os.name == 'nt':
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)   # sharp text on HiDPI
        except (AttributeError, OSError):
            pass
    try:
        root = tk.Tk()
    except tk.TclError as e:
        print('Cannot open a window (%s). Use the command line installer instead.' % e)
        sys.exit(3)
    App(root, sys.argv[1] if len(sys.argv) > 1 else '')
    root.mainloop()


if __name__ == '__main__':
    main()
