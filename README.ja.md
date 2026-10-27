# マジカルチェイス（Windows 95版）ノーCD・最新Windows対応パッチ

[English](README.md)

1998年にクエストから発売されたPC版『マジカルチェイス』を、CDなしで
Windows 10/11 や Linux（Wine）で遊べるようにするパッチです。
`--japanese` を付けると、オリジナルの日本語メニュー・ダイアログのまま
修正だけを適用します。

このリポジトリに含まれているのは**パッチツールだけ**です。ゲーム本体
（オリジナルCD、またはそのBIN/CUEイメージ）はご自身でご用意ください。

## インストール

[Python 3](https://www.python.org/downloads/) が必要です（他には何も要りません）。
Windowsではインストール時に「Add python.exe to PATH」にチェックを入れてください。

**Windows**: `install.bat` をダブルクリックして質問に答えます。
「Keep the original Japanese menus?」には `y` と答えると日本語のままになります。
`.cue` ファイルを `install.bat` にドラッグ＆ドロップしてもOKです。
CDから直接インストールする場合はドライブ名（例: `D:`）を入力します。

**コマンドライン**:

```
py -3 patcher\install_magical_chase.py D: C:\Games\MagicalChase --japanese
python3 patcher/install_magical_chase.py MagicalChase.cue ~/Games/MagicalChase --japanese
```

| オプション | 内容 |
|---|---|
| `--japanese` | オリジナルの日本語テキストのまま（修正はすべて適用） |
| `--portable` | 設定をレジストリではなくゲームフォルダの `MCHASE.INI` に保存（フォルダごと移動・コピー可能） |
| `--numpad` | 移動キーを元のテンキー（8/2/4/6）のままにする（標準は矢印キー） |
| `--disc-wav` | CD音源を取り込まず、ディスク内の22kHz WAVを使う |

## 遊び方

`Mchase.exe` を実行します。画面は640×480 HiColorに切り替わります。
ウィンドウ表示や拡大表示をしたい場合は
[cnc-ddraw](https://github.com/FunkyFr3sh/cnc-ddraw/releases) の
`ddraw.dll` と `ddraw.ini` をゲームフォルダに置いてください
（`ddraw.ini` で `windowed=true`、`width=1920`、`height=1440`、`maintas=true` など）。

## 操作

| キー | 操作 |
|---|---|
| 矢印キー | 移動（`--numpad` の場合はテンキー 8/2/4/6） |
| A | ショット |
| S | オプション操作 |
| Enter | スタート |
| Esc | ポーズ |
| Alt+P | オプション（キー・ジョイスティック・サウンド設定） |
| Alt+Q | 終了 |

**キー設定の変更**: **Alt+P**（またはメニューの「設定 › オプション」）→
「キーボード」タブ → 変更したい欄をクリック → 割り当てたいキーを押す → **OK**。

## パッチの内容

* **CDチェックの解除**: AUTORUN.EXEなしで起動し、音楽は `<ゲームフォルダ>\mus\` から読み込みます。
* **32ビットカラーのデスクトップ対応**: 640×480×16ビットのフルスクリーンで起動します。
* **ジョイスティックのクラッシュ修正**（公式 `mc_patch.exe` と同じ修正。重ねて当てないでください）。
* **移動キーを矢印キーに**（テンキーのないノートPC向け）。
* **サウンド設定ページ**（CD-DA / WAV切替、音楽・効果音テスト）を常に表示。
* **英語化**（`--japanese` の場合は行いません）。
* **ポータブル設定**（`--portable` の場合のみ）。

## 注意

* `--japanese` 版は日本語版Windowsを想定しています。日本語以外のWindowsや、
  「ベータ: ワールドワイド言語サポートで Unicode UTF-8 を使用」を有効にした
  環境では、ジョイスティックの軸名が文字化けすることがあります
  （ゲームの動作には影響しません）。
* `--portable` の場合は、書き込み可能なフォルダ（`Program Files` 以外）に
  インストールしてください。
