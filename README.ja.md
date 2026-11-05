# Ripple's Potion（リップルのポーション）

*マジカルチェイス（Windows 95版）ノーCD・最新Windows対応パッチ*

[English](README.md)

1998年にクエストから発売されたPC版『マジカルチェイス』を、CDなしで
Windows 10/11 や Linux（Wine）で遊べるようにするパッチです。
インストール時に「オリジナルの日本語」を選ぶと、オリジナルの日本語メニュー・
ダイアログのまま修正だけを適用します。

このリポジトリに含まれているのは**パッチツールだけ**です。ゲーム本体
（オリジナルCD、またはそのBIN/CUEイメージ）はご自身でご用意ください。

## インストール

**Windows（かんたん）**: [Releases](https://github.com/TremiRodomi/ripples-potion/releases)
ページから `RipplesPotion.exe` をダウンロードして実行します。他には何も要りません
（新しい署名なしのexeをウイルス対策ソフトが警告する場合は、下の `install.bat` を使ってください）。

**Windows（ソースから）**: [Python 3](https://www.python.org/downloads/) をインストールし
（「Add python.exe to PATH」にチェック）、`install.bat` をダブルクリックするとインストーラーの画面が開きます。
CDドライブまたは `.cue` / `.iso` ファイル、インストール先、オプションを選んで
**インストール** を押します。`.cue` ファイルを `install.bat` にドラッグ＆ドロップしてもOKです。

**Linux（かんたん）**: [Releases](https://github.com/TremiRodomi/ripples-potion/releases)
ページから `RipplesPotion-linux-x86_64` をダウンロードし、実行可能にして
（`chmod +x RipplesPotion-linux-x86_64`）実行します。インストールには他に何も要りません
（遊ぶにはWineが必要です。glibc 2.35以降のディストリビューションに対応）。

**Linux（ソースから）**: `./install.sh` で同じ画面が開きます（tkinterが必要です。Fedora:
`sudo dnf install python3-tkinter`、Debian/Ubuntu: `sudo apt install python3-tk`）。
tkinterや画面がない場合は、ターミナルで質問に答える形式になります。

インストーラーの表示は、システムの言語に合わせて日本語または英語になります。
画面右上のメニューで切り替えるか、`--lang=ja` / `--lang=en` を指定してください。

### 音楽

| | CD音源（おすすめ） | ディスク内のWAV |
|---|---|---|
| 音質 | 44.1kHz 16ビット ステレオ | 22kHz 8ビット |
| インストール | 遅め（サウンドトラック全体を読み込み） | 速い |
| 容量 | 約460MB | 約115MB |
| 必要なもの | ディスクまたはBIN/CUEイメージ | どれでも可（ISOも可） |

CD音源を選んだ場合でも、読めない曲（ディスクの傷など）はその曲だけディスク内の
WAVを使うので、インストールは最後まで完了します。ディスクの傷がひどい場合は
「ディスク内のWAV」を選んでください（データ部分しか読みません）。

### オプション

| オプション | 標準 | コマンドライン |
|---|---|---|
| メニュー・設定画面・ゲーム内の文章を英語またはオリジナルの日本語に | 英語（インストーラーが日本語のときは日本語） | `--japanese` |
| ポータブル設定：設定をレジストリではなくゲームフォルダの `MCHASE.INI` に保存（フォルダごと移動・コピー可能） | オン | `--registry` でオフ |
| 移動キーを矢印キーに（元はテンキー 8/2/4/6） | オン | `--numpad` でオフ |
| [cnc-ddraw](https://github.com/FunkyFr3sh/cnc-ddraw)（拡大フルスクリーン・ウィンドウ表示。GitHubのリリースからダウンロード、2.7MB） | オン | `--no-ddraw` でオフ |
| CD音源ではなくディスク内のWAVを使う | オフ | `--disc-wav` |

**コマンドライン**:

```
py -3 patcher\install_magical_chase.py D: C:\Games\MagicalChase --japanese
python3 patcher/install_magical_chase.py MagicalChase.cue ~/Games/MagicalChase --japanese
```

## 遊び方

`Mchase.exe`（Linuxでは `./magical-chase.sh`）を実行します。

cnc-ddraw（標準でオン）を使うと、画面いっぱいに4:3で表示されます。
**Alt+Enter** でサイズ変更できるウィンドウ表示に切り替わります（大きさと位置は
記憶されます）。見た目は `ddraw.ini`（例：`boxing=true` で整数倍拡大）か、
Windowsでは `cnc-ddraw config.exe` で変更できます。再インストールしても
`ddraw.ini` はそのまま残ります。

cnc-ddrawなしの場合は、画面が640×480 HiColorに切り替わります。

## 操作

| キー | 操作 |
|---|---|
| 矢印キー | 移動（`--numpad` の場合はテンキー 8/2/4/6） |
| A | ショット |
| S | オプション操作 |
| Enter | スタート |
| Esc | ポーズ |
| Alt+P | オプション（キー・ジョイスティック・サウンドテスト設定） |
| Alt+Q | 終了 |

**キー設定の変更**: **Alt+P**（またはメニューの「設定 › オプション」）→
「キーボード」タブ → 変更したい欄をクリック → 割り当てたいキーを押す → **OK**。

## パッチの内容

* **CDチェックの解除**: AUTORUN.EXEなしで起動し、音楽は `<ゲームフォルダ>\mus\` から読み込みます。
* **32ビットカラーのデスクトップ対応**: 640×480×16ビットのフルスクリーンで起動します。
* **ジョイスティックのクラッシュ修正**（公式 `mc_patch.exe` と同じ修正。重ねて当てないでください）。
* **移動キーを矢印キーに**（テンキーのないノートPC向け）。
* **音楽は常にWAVから再生**: CD-DA / WAVの切替はなくなりました（CD音源はインストール時に
  `mus\` に取り込み済み）。サウンド設定ページは音楽・効果音テストとして常に表示されます。
* **英語化**: メニュー・設定画面に加え、ゲーム内の文章（ショップ、難易度選択、コンティニュー、
  リザルト画面、モード終了メッセージ、クリアボーナスの「CRYSTAL」）も北米版PCエンジン（TurboGrafx-16）版の英語とフォントに
  なります（`--japanese` の場合は行いません）。
* **ポータブル設定**（`--registry` の場合を除く）。

## 注意

* `--japanese` 版は日本語版Windowsを想定しています。日本語以外のWindowsや、
  「ベータ: ワールドワイド言語サポートで Unicode UTF-8 を使用」を有効にした
  環境では、ジョイスティックの軸名が文字化けすることがあります
  （ゲームの動作には影響しません）。
* ポータブル設定の場合は、書き込み可能なフォルダ（`Program Files` 以外）に
  インストールしてください。
