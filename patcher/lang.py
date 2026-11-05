"""
The installer's own text in English and Japanese.

    from lang import t
    print(t('Install to'))

The language comes from --lang=ja / --lang=en on the command line, or else
the system's language. Text without a Japanese entry stays English.
"""
import os
import sys

LANGUAGES = [('en', 'English'), ('ja', '日本語')]


def detect():
    for arg in sys.argv[1:]:
        if arg.startswith('--lang='):
            return 'ja' if arg[7:].lower().startswith('ja') else 'en'
    if os.name == 'nt':
        try:
            import ctypes
            ui = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            return 'ja' if ui & 0x3FF == 0x11 else 'en'      # LANG_JAPANESE
        except (AttributeError, OSError):
            return 'en'
    for var in ('LC_ALL', 'LC_MESSAGES', 'LANG', 'LANGUAGE'):
        value = os.environ.get(var)
        if value:
            return 'ja' if value.lower().startswith('ja') else 'en'
    return 'en'


lang = detect()


def set_language(code):
    global lang
    lang = code


def t(text):
    return JA.get(text, text) if lang == 'ja' else text


JA = {
    # gui.py
    'tkinter is not installed, so the graphical installer cannot start.':
        'tkinterがインストールされていないため、インストーラーの画面を開けません。',
    'No-CD + modern Windows patch for Magical Chase (QUEST, 1998)':
        'マジカルチェイス（クエスト、1998年）ノーCD・最新Windows対応パッチ',
    'Magical Chase installer': 'マジカルチェイス インストーラー',
    'Game disc (drive, .cue or .iso)': 'ゲームディスク（ドライブ、.cue または .iso）',
    'Browse...': '参照...',
    'Install to': 'インストール先',
    'Music': '音楽',
    'Options': 'オプション',
    'Menus and in-game text:': 'メニュー・ゲーム内の文章：',
    'English': '英語',
    'Original Japanese (日本語)': 'オリジナルの日本語',
    'Portable: save settings in the game folder (MCHASE.INI), not the registry':
        'ポータブル：設定をレジストリではなくゲームフォルダの MCHASE.INI に保存',
    'Move with the arrow keys (untick for the original numpad 8/2/4/6)':
        '矢印キーで移動（チェックを外すと元のテンキー 8/2/4/6）',
    'cnc-ddraw: scaled fullscreen, Alt+Enter for a window (2.7 MB)':
        'cnc-ddraw：拡大フルスクリーン、Alt+Enterでウィンドウ表示（2.7MB）',
    'Open folder': 'フォルダを開く',
    'Install': 'インストール',
    'Magical Chase disc image': 'マジカルチェイスのディスクイメージ',
    'Disc images': 'ディスクイメージ',
    'All files': 'すべてのファイル',
    'Install Magical Chase to': 'マジカルチェイスのインストール先',
    'Choose the game disc and an install folder.':
        'ゲームディスクとインストール先を選んでください。',
    'Portable settings need a folder the game can write to, and Program Files '
    'usually is not.\n\nInstall there anyway?':
        'ポータブル設定にはゲームが書き込めるフォルダが必要ですが、Program Files '
        'は通常書き込めません。\n\nそれでもインストールしますか？',
    'Installed. Start the game with %s': 'インストール完了。ゲームの起動：%s',
    'Magical Chase is installed.\n\nStart it with:\n%s':
        'マジカルチェイスをインストールしました。\n\n起動するには：\n%s',
    'Error: ': 'エラー：',
    'Cannot open a window (%s), so asking here instead.\n':
        '画面を開けないため（%s）、ここで質問します。\n',
    'Cannot open a window (%s). Use the command line installer instead.':
        '画面を開けません（%s）。コマンドライン版のインストーラーを使ってください。',

    # install_magical_chase.py: sources
    'Could not read the drive directly (%s); copying files only.':
        'ドライブを直接読めませんでした（%s）。ファイルだけをコピーします。',
    'Could not read %s directly (%s); copying files only.':
        '%s を直接読めませんでした（%s）。ファイルだけをコピーします。',
    'Cannot read %s: %s (is the disc inserted?)':
        '%s を読めません：%s（ディスクは入っていますか？）',
    'Unrecognised source: %s': '認識できないソースです：%s',

    # cnc-ddraw
    'the download does not match the expected file':
        'ダウンロードしたファイルが想定と一致しません',
    'cnc-ddraw not installed (%s). The game still works; see the README to add it by hand.':
        'cnc-ddrawはインストールされませんでした（%s）。ゲームはそのまま遊べます。'
        '手動で追加する方法はREADMEを参照してください。',
    '   cnc-ddraw (scaled fullscreen, Alt+Enter for a window)':
        '   cnc-ddraw（拡大フルスクリーン、Alt+Enterでウィンドウ表示）',
    '; kept your ddraw.ini': '、今までの ddraw.ini はそのまま',

    # music choice (\u00a0, a no-break space, keeps a window from wrapping
    # the line right after its + or -)
    'CD audio (recommended)': 'CD音源（おすすめ）',
    '+ Best quality: 44.1 kHz 16-bit stereo': '+\u00a0最高音質：44.1kHz 16ビット ステレオ',
    '- Slower install: reads the whole soundtrack':
        '-\u00a0インストールが遅め：全曲を読み込むため',
    '- Takes more space: about 460 MB': '-\u00a0容量が大きい：約460MB',
    'A track that can\'t be read (scratched disc) uses its disc WAV instead, '
    'so the install still finishes.':
        '読めない曲（ディスクの傷など）はその曲だけディスク内のWAVを使うので、'
        'インストールは最後まで完了します。',
    'Disc WAV files': 'ディスク内のWAV',
    '+ Faster install, and smaller: about 115 MB': '+\u00a0速くて省スペース：約115MB',
    '+ Good for a damaged disc or an ISO': '+\u00a0傷のあるディスクやISOに向いています',
    '- Lower quality: 22 kHz 8-bit': '-\u00a0音質は低め：22kHz 8ビット',

    # install
    'Unexpected Mchase.exe on this disc (sha256 %s)':
        'このディスクの Mchase.exe は想定外のものです（sha256 %s）',
    'No CD audio tracks available from this source; using the disc WAV files.':
        'このソースにはCD音源がないため、ディスク内のWAVを使います。',
    '   mus/TR%02d.WAV: CD audio unreadable (%s), using the disc WAV':
        '   mus/TR%02d.WAV：CD音源を読めないため（%s）、ディスク内のWAVを使います',
    '   mus/TR%02d.WAV (disc WAV)': '   mus/TR%02d.WAV（ディスク内のWAV）',
    '%d track(s) use the lower quality disc WAV: %s':
        '%d曲は音質の低いディスク内のWAVを使っています：%s',
    'image file ends early': 'イメージファイルが途中で終わっています',

    # text-mode questions
    'Disc drive (e.g. D: or /dev/sr0) or .cue / .iso file: ':
        'ディスクドライブ（例：D: や /dev/sr0）または .cue / .iso ファイル：',
    'Install folder [%s]: ': 'インストール先 [%s]：',
    '\nMusic:': '\n音楽：',
    'Choose 1 or 2 [1]: ': '1 か 2 を選んでください [1]：',
    'Keep the original Japanese menus, dialogs and in-game text?':
        'メニュー・ダイアログ・ゲーム内の文章をオリジナルの日本語のままにしますか？',
    'Save settings in the game folder (portable)?':
        '設定をゲームフォルダに保存しますか（ポータブル）？',
    'Download cnc-ddraw for scaled fullscreen / bigger window?':
        '拡大フルスクリーン・大きなウィンドウ用に cnc-ddraw をダウンロードしますか？',
    '\nStart the game with "%s"': '\nゲームの起動：「%s」',
    '\nCancelled.': '\nキャンセルしました。',
    'Done. Windows: run Mchase.exe   Linux: run %s':
        '完了。Windows：Mchase.exe を実行   Linux：%s を実行',
}
