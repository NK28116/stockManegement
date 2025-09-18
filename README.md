# 株式投資分析・運用システム

## 概要

このシステムは、個人投資家向けの包括的な株式投資分析・運用ツールです。Pythonをベースに開発されており、データ収集から分析、レポート作成までを一貫してサポートします。

## 主な機能

### ポートフォリオ管理

- **複数銘柄の一括管理**: `data/my_stock.csv` を編集することで、保有銘柄の追加、数量変更、購入価格変更が可能です。
- **平均取得価格・含み益の自動計算**: 保有銘柄の現在の評価額と損益を自動で計算します。
- **セクター別・資産クラス別の分散管理**: ポートフォリオの分散状況を可視化し、リスクを低減します。

### テクニカル分析

- **主要なテクニカル指標の自動計算**: MACD、ボリンジャーバンド、RSIなどの指標を自動で計算し、チャートに表示します。
- **カスタマイズ可能な売買シグナル生成**: 買い・売りシグナル（ゴールデンクロス、デッドクロス、RSI過買い/過売りなど）を生成します。
- **マルチタイムフレーム分析**: 日足、週足などの異なる時間軸での分析をサポートします。

### リスク管理

- **ボラティリティ分析**: 株価の変動率を分析し、リスクを評価します。
- **バリュエーションモデル**: 企業の価値評価モデルを用いて、割安・割高を判断します。
- **ドローダウン分析**: 過去の最大損失幅を分析し、リスク許容度を評価します。
- **ストップロス・利確設定**: `config.py` でストップロス幅や利確幅を設定し、自動売買の判断基準とします。

### レポート機能

- **自動レポート生成（日次/週次/月次）**: ポートフォリオのパフォーマンスや分析結果を定期的にレポートとして出力します。
- **カスタマイズ可能なダッシュボード**: 主要な指標やチャートを一覧で確認できるダッシュボードを提供します。
- **PDF/Excel形式でのエクスポート**: レポートをPDFやExcel形式で出力し、共有や保存を容易にします。

### アラート機能

- **価格アラート**: 設定した価格に達した場合に通知します。
- **テクニカルシグナルアラート**: 特定のテクニカルシグナル（例: ゴールデンクロス）が発生した場合に通知します。
- **ニュースアラート**: 関連ニュースを監視し、重要な情報があった場合に通知します。
- **暴落アラート**: `config.py` で設定した閾値（例: -3%）以上の下落があった場合に、ログやSlackに通知します。

## サポート市場

- 東京証券取引所（一部上場・マザーズ・JASDAQ）
- 米国主要市場（NYSE, NASDAQ）

## 運用

このシステムは、主に`Makefile`を通じて操作されます。以下に、各OSでの運用方法と、ログ・アラートの活用について説明します。

### Windowsでの運用方法

Windows環境での詳細な運用方法については、このセクションで詳しく説明します。

#### 1. バックグラウンド運用

##### a. PowerShellスクリプトと `Start-Process` コマンドレットの使用

PowerShellはWindowsの強力なシェルであり、`Start-Process`コマンドレットを使ってプログラムをバックグラウンドで起動できます。

- **使い方**:
    1. **PowerShellスクリプトの作成**:
        プロジェクトのルートディレクトリに、例えば `start_watch.ps1` という名前で以下の内容のファイルを作成します。

        ```powershell
        # start_watch.ps1
        $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
        Set-Location $scriptDir

        # 仮想環境のPythonを使用する場合
        # $pythonPath = ".\venv\Scripts\python.exe" # 仮想環境のパスに合わせて修正
        # $scriptPath = ".\python\watch\watch.py" # watch.pyへのパス

        # make watch コマンドを実行する場合 (makeがPATHにあるか、フルパスを指定)
        $command = "make"
        $arguments = "watch"

        # バックグラウンドで実行し、新しいウィンドウを表示しない
        Start-Process -FilePath $command -ArgumentList $arguments -NoNewWindow -Wait:$false -PassThru | Out-Null
        ```

        **注意**:
        - `$pythonPath`と`$scriptPath`は、ご自身の環境に合わせて正確なパスに修正してください。
        - `make watch`を実行する場合、`make`コマンドがシステム環境変数`PATH`に登録されている必要があります。登録されていない場合は、`make.exe`へのフルパスを`$command`に指定してください。
        - `Start-Process`の`-NoNewWindow`は新しいウィンドウを表示しないオプションです。`-Wait:$false`はプロセスが終了するのを待たずにすぐに制御を返すオプションです。`-PassThru | Out-Null`は、起動したプロセスの情報を表示しないようにします。
    2. **スクリプトの実行**:
        PowerShellを開き、作成したスクリプトを実行します。

        ```powershell
        .\start_watch.ps1
        ```

        または、コマンドプロンプトから実行する場合:

        ```cmd
        powershell -File ".\start_watch.ps1"
        ```

- **メリット**:
  - Windowsネイティブな方法で、比較的モダンです。
  - 新しいウィンドウを表示せずにバックグラウンドで実行できます。
  - ログ出力などをスクリプト内で柔軟に制御できます。
- **デメリット**:
  - 実行中のプロセスを直接操作することはできません。
  - プロセスの停止には、タスクマネージャーやPowerShellコマンド（`Get-Process | Where-Object {$_.CommandLine -like "*make watch*"} | Stop-Process`など）を使用する必要があります。

##### b. VBScript (Visual Basic Script) の使用

VBScriptは、Windowsでスクリプトを実行するための古い方法ですが、シンプルにプログラムをバックグラウンドで起動するのに使われることがあります。

- **使い方**:
    1. **VBScriptファイルの作成**:
        プロジェクトのルートディレクトリに、例えば `run_watch_hidden.vbs` という名前で以下の内容のファイルを作成します。

        ```vbs
        ' run_watch_hidden.vbs
        Set WshShell = CreateObject("WScript.Shell")
        ' プロジェクトのルートディレクトリに移動
        WshShell.CurrentDirectory = "C:\Users\YourUser\Documents\PrivateDevelop\stockManegement" ' プロジェクトのフルパスに修正

        ' make watch コマンドを実行
        ' makeがPATHにあるか、フルパスを指定
        WshShell.Run "cmd.exe /c make watch", 0, False
        ' または、Pythonスクリプトを直接実行する場合
        ' WshShell.Run "C:\Users\YourUser\AppData\Local\Programs\Python\Python39\python.exe python\watch\watch.py", 0, False
        ```

        **注意**:
        - `WshShell.CurrentDirectory`はプロジェクトのフルパスに修正してください。
        - `WshShell.Run`の第2引数`0`はウィンドウを非表示にする設定です。`False`はプロセスが終了するのを待たない設定です。
    2. **スクリプトの実行**:
        このVBScriptファイルをダブルクリックするか、コマンドプロンプトから実行します。

        ```cmd
        wscript.exe ".\run_watch_hidden.vbs"
        ```

- **メリット**:
  - 非常にシンプルで、新しいウィンドウを表示せずにバックグラウンドで実行できます。
- **デメリット**:
  - PowerShellに比べて機能が限定的です。
  - プロセスの停止には、タスクマネージャーを使用する必要があります。

##### c. Windows Subsystem for Linux (WSL) の使用

もしWindowsにWSLを導入している場合、Linux環境で`nohup`や`screen`/`tmux`といったコマンドをそのまま利用できます。これは、Linux環境での運用経験がある場合に非常に強力な選択肢となります。

- **WSLの概要**:
    WSLは、Windows上でLinuxディストリビューション（Ubuntuなど）を直接実行できる機能です。これにより、LinuxのコマンドラインツールやアプリケーションをWindows上で利用できます。
- **使い方**:
    1. **WSLのインストールと設定**:
        まだWSLをインストールしていない場合は、Microsoftのドキュメントに従ってインストールし、好みのLinuxディストリビューションを設定します。
    2. **プロジェクトファイルの配置**:
        プロジェクトファイルをWSLのファイルシステム内（例: `/home/youruser/stockManegement`）に配置するか、WindowsのファイルシステムをWSLからマウントしてアクセスします（例: `/mnt/c/Users/YourUser/Documents/PrivateDevelop/stockManegement`）。WSLのファイルシステム内に配置する方がパフォーマンスが良いことが多いです。
    3. **Linuxコマンドの利用**:
        WSLのターミナルを開き、Linux環境で`nohup`や`screen`/`tmux`コマンドを上記Linux/macOSの説明と同じように使用できます。

        ```bash
        # WSLターミナル内で
        nohup make watch > watch.log 2>&1 &
        # または
        screen -S stock_watch
        make watch
        # Ctrl+A, D でデタッチ
        ```

- **メリット**:
  - Linux環境で慣れ親しんだツール（`nohup`, `screen`, `tmux`）をWindows上で利用できます。
  - Linuxの強力なスクリプト機能や自動化ツールを活用できます。
- **デメリット**:
  - WSLのセットアップが必要になります。
  - WindowsとWSL間のファイルアクセスや環境設定に慣れが必要です。

#### 2. 定期実行 (タスクスケジューラ)

Windowsには「タスクスケジューラ」という機能があり、指定した時間にプログラムやスクリプトを自動実行できます。これはLinux/macOSの`cron`に相当する機能です。

- **タスクスケジューラの設定方法**:
    1. **タスクスケジューラを開く**:
        スタートメニューから「タスクスケジューラ」と検索して開きます。
    2. **新しいタスクの作成**:
        右側の「操作」ペインから「タスクの作成...」を選択します。
    3. **「全般」タブ**:
        - 「名前」: `StockManagement_DailyTask` のように分かりやすい名前を付けます。
        - 「説明」: タスクの内容を記述します（例: 「株式投資分析システムの日次データ更新とレポート生成」）。
        - 「ユーザーがログオンしているかどうかにかかわらず実行する」を選択し、「パスワードを保存しない」のチェックを外します。これにより、ログオフ状態でもタスクが実行されます。
        - 「最上位の特権で実行する」にチェックを入れると、管理者権限で実行されます。
    4. **「トリガー」タブ**:
        - 「新規」をクリックします。
        - 「タスクの開始」: 「スケジュールに従って」を選択します。
        - 「設定」: 「毎日」を選択し、開始日時と繰り返し間隔（例: 毎日午前9時）を設定します。
        - 「有効」にチェックが入っていることを確認します。
        - 「OK」をクリックします。
    5. **「操作」タブ**:
        - 「新規」をクリックします。
        - 「操作」: 「プログラムの開始」を選択します。
        - 「プログラム/スクリプト」: Pythonの実行ファイルへのパスを指定します。
            例: `C:\Users\YourUser\AppData\Local\Programs\Python\Python39\python.exe`
            （ご自身のPythonインストールパスに合わせてください。仮想環境を使用している場合は、その仮想環境の`python.exe`を指定します。）
        - 「引数の追加(オプション)」: 実行したいPythonスクリプトのパスと引数を指定します。
            例: `C:\Users\YourUser\Documents\PrivateDevelop\stockManegement\main.py run-daily`
            （`main.py`が`run-daily`というサブコマンドを持つ場合。または、`C:\Users\YourUser\Documents\PrivateDevelop\stockManegement\makefile`と指定し、「開始(オプション)」に`make run-daily`と指定することも可能ですが、Pythonスクリプトを直接指定する方がシンプルです。）
            **Makefileを使用する場合**:
            「プログラム/スクリプト」に`C:\Windows\System32\cmd.exe`または`C:\Windows\System32\bash.exe` (WSLの場合) を指定し、
            「引数の追加(オプション)」に`/c "cd /d C:\Users\YourUser\Documents\PrivateDevelop\stockManegement && make run-daily"` のように指定します。
            （`make`コマンドがWindowsの環境変数`PATH`に登録されているか、`make.exe`へのフルパスを指定する必要があります。）
        - 「開始(オプション)」: プロジェクトのルートディレクトリを指定します。
            例: `C:\Users\YourUser\Documents\PrivateDevelop\stockManegement`
        - 「OK」をクリックします。
    6. **「条件」タブと「設定」タブ**:
        必要に応じて、電源やネットワーク接続の条件、タスクの動作設定などを調整します。
    7. **タスクの完了**:
        「OK」をクリックすると、ユーザーアカウントのパスワードを求められる場合があります。入力してタスクを保存します。

- **メリット**:
  - Windows環境で完全に自動化された定期実行が可能です。
  - GUIで設定できるため、比較的容易に設定できます。
- **注意点**:
  - Pythonの実行パスやスクリプトのパス、作業ディレクトリを正確に指定する必要があります。
  - 仮想環境を使用している場合は、その仮想環境の`python.exe`を指定しないと、依存関係が解決されない可能性があります。

#### 3. Windowsでの自動起動設定

本システムは常時監視 (`watch.py`) を前提とします。Windows 環境では以下の手順で自動起動を設定できます。

##### 手順

1. バッチファイルを作成する

   ```bat
   @echo off
   cd /d C:\Users\<USERNAME>\your_project\watch
   python watch.py
   ```

   プロジェクトルートで `make create-win-batch` を実行すると、`run_watch.bat` が作成されます。
   - 作成される `run_watch.bat` が Windows 起動時に自動で `watch.py` を実行します。
   - ログは `log/watch/` に出力されます。
   - シャットダウンするまで2分ごとのリアルタイム監視が継続します。

##### GitHub Actions 連携による自動反映

- `main` ブランチへの `push` により、自動的に `runWindow` ブランチに反映されます。
- これにより、手動で Windows にログインして操作しなくても、最新のコードが常に Windows 環境に反映されます。
- 反映後、`run_watch.bat` による自動実行で最新状態が即座に監視・分析に反映されます。

##### 補足

- 開発や編集は主に macOS で行い、`push` で Windows 側に反映。
- Windows 側は起動したら自動で `watch.py` が動作するのみで操作不要。
- 実運用では `watch.py` が常駐し、株価取得・分析・アラート出力を継続。

### Linux/macOSでの運用方法

#### 1. バックグラウンド運用

LinuxやmacOS環境では、`nohup`や`screen`/`tmux`を使用してバックグラウンドでプロセスを実行できます。

```bash
# nohup を使用してバックグラウンドで実行し、ログをファイルに出力
nohup make watch > watch.log 2>&1 &

# screen を使用してセッションをデタッチ
screen -S stock_watch
make watch
# Ctrl+A, D でデタッチ

# tmux を使用してセッションをデタッチ
tmux new -s stock_watch
make watch
# Ctrl+B, D でデタッチ
```

#### 2. 定期実行 (cron)

日次、週次、月次などの定期的なタスクは、`cron`を使用して自動実行できます。
`make install-cron` コマンドで、必要なcronジョブを設定できます。

### ログとアラート

メイン運用マシンでの操作を最小限に抑えるためには、システムが適切に動作しているか、あるいは問題が発生していないかをリモートで確認できる仕組みが重要です。このシステムでは、ログファイルとSlackアラートがその役割を担います。

#### a. ログファイルの活用

システムは実行中に様々な情報をログファイルに記録します。これにより、システムの動作状況、エラー、警告などを後から確認できます。

- **ログファイルの場所**:
    プロジェクトのルートディレクトリにある`log/`ディレクトリに、各モジュールやタスクごとのログファイルが出力されます。ログファイル名は通常、`YYYY-MM-DD.log`形式です。
    主なログ出力先は以下の通りです。
  - `log/analysis/`: 分析関連のログ
  - `log/task/Daily/`: 日次タスクのログ
  - `log/task/Error/`: エラーログ
  - `log/trading/`: 取引関連のログ
  - `log/watch/`: 監視関連のログ

- **ログの確認方法**:
    運用マシンに直接ログインしなくても、リモートデスクトップ接続やSSH（Windowsの場合はPowerShellのSSHクライアントやWSL経由）で接続し、ログファイルを確認できます。
  - **リアルタイムでログを監視**:
    例えば、日次タスクの最新ログを監視する場合:

   ```cmd
   # コマンドプロンプトまたはPowerShellで
   Get-Content -Path ".\log\task\Daily\$(Get-Date -Format 'yyyy-MM-dd').log" -Wait -Tail 10
   ```

   （Linux/macOSの`tail -f`に相当します。`-Tail 10`は最新の10行を表示し、`-Wait`で新しい行が追加されるたびに表示します。）
  - **特定のキーワードで検索**:
    例えば、エラーログから「ERROR」という文字列を含む行を検索する場合:

   ```cmd
   # コマンドプロンプトまたはPowerShellで
   Select-String -Path ".\log\task\Error\*.log" -Pattern "ERROR"
   ```

   （ログファイルから「ERROR」という文字列を含む行を検索します。）

- **メリット**:
  - システムの詳細な動作履歴を確認できます。
  - 問題発生時の原因究明に役立ちます。
  - リモートからでも状況を把握できます。

#### b. Slackアラートの活用

システムは、特定の重要なイベント（例: 株価の急落）が発生した場合に、Slackに通知を送る機能を備えています。これにより、運用マシンを常に監視していなくても、重要な情報を見逃すことなく把握できます。

- **設定方法**:
    `python/config.py`ファイル（または`config/settings.yaml`）でSlack通知の設定を行います。
    通常、SlackのWebhook URLを設定することで、システムからメッセージを送信できるようになります。

    ```python
    # python/config.py (例)
    class Config:
        # ... その他の設定 ...
        SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
        CRASH_THRESHOLD = -3.0 # 暴落アラートの閾値
        # ...
    ```

    または、`config/settings.yaml`に設定項目がある場合:

    ```yaml
    alert:
      slack:
        enabled: true
        webhook_url: your_slack_webhook_url_here
      email:
        enabled: false
        recipients: []
    ```

    **注意**: SlackのWebhook URLは機密情報なので、公開リポジトリに直接コミットしないように注意してください。環境変数で管理するか、`.gitignore`で除外された設定ファイルに記述するのが安全です。

- **アラートの条件**:
    README.mdの「アラート条件表」に記載されているように、以下のような条件でアラートが発動します。
  - 価格下落 ≥ -3% (暴落アラート)
  - ストップロス達成
  - 利確達成
    これらのアラートは、`python/utils/alert.py`モジュールによって処理され、設定に応じてSlackに通知されます。

- **メリット**:
  - 運用マシンにログインしていなくても、重要なイベントをリアルタイムで受け取れます。
  - 緊急性の高い情報に素早く対応できます。
  - チームでの情報共有にも役立ちます。

---

## プロジェクト構成

```bash
stockManegement//
├── data
│   ├── analyze_my_stock
│   ├── API
│   │   └── kabu_STATION_API.yaml
│   ├── archive
│   ├── chartImg
│   ├── my_stock.csv
│   ├── plots
│   ├── practice
│   │   ├── charts
│   │   │   ├── 4503_T_アステラス製薬.png
│   │   │   ├── 6367_T_ダイキン工業.png
│   │   │   ├── 6752_T_パナソニック.png
│   │   │   ├── 6758_T_ソニーグループ.png
│   │   │   ├── 6861_T_キーエンス.png
│   │   │   ├── 7203_T_トヨタ自動車.png
│   │   │   ├── 7974_T_任天堂.png
│   │   │   ├── 8306_T_三菱UFJフィナンシャル・グループ.png
│   │   │   ├── 9433_T_KDDI.png
│   │   │   ├── 9984_T_ソフトバンクグループ.png
│   │   │   ├── demo_7203_T_トヨタ自動車.png
│   │   │   └── trading_summary_portfolio_practice.txt
│   │   ├── portfolio_beginner.csv
│   │   ├── portfolio_diversified.csv
│   │   ├── portfolio_growth.csv
│   │   ├── portfolio_practice.csv
│   │   ├── portfolio_stable.csv
│   │   ├── portfolio_template.csv
│   │   └── portfolio_with_notes.csv
│   ├── quarterly_analysis.csv
│   ├── README.md
│   └── report
│       ├── detailed
│       └── summary
├── Detail.md
├── log
│   ├── analysis
│   │   ├── analyze_my_stock
│   │   │   ├── 2025-09-08.log
│   │   │   └── 2025-09-09.log
│   │   ├── data_collector
│   │   │   └── {datetime.now().strftime('%Y-%m-%d')}.log
│   │   ├── every_stock_analysis
│   │   │   ├── {datetime.now().strftime('%Y-%m-%d')}.log
│   │   │   ├── 2025-09-08.log
│   │   │   └── 2025-09-09.log
│   │   └── PortfolioAnalyzer
│   │       ├── {datetime.now().strftime('%Y-%m-%d')}.log
│   │       ├── 2025-09-08.log
│   │       └── 2025-09-09.log
│   ├── db
│   ├── README.md
│   ├── report
│   │   └── report
│   │       └── {datetime.now().strftime('%Y-%m-%d')}.log
│   ├── task
│   │   ├── Daily
│   │   │   ├── 2025-09-08.log
│   │   │   └── 2025-09-09.log
│   │   ├── Error
│   │   │   ├── 2025-09-08.log
│   │   │   └── 2025-09-09.log
│   │   ├── main_task
│   │   │   └── {datetime.now().strftime('%Y-%m-%d')}.log
│   │   ├── Monthly
│   │   │   ├── 2025-09-08.log
│   │   │   └── 2025-09-09.log
│   │   ├── Weekly
│   │   │   ├── 2025-09-08.log
│   │   │   └── 2025-09-09.log
│   │   └── Yearly
│   │       ├── 2025-09-08.log
│   │       └── 2025-09-09.log
│   ├── trading
│   │   └── every_stock_BuySell_timing
│   │       ├── {datetime.now().strftime('%Y-%m-%d')}.log
│   │       ├── 2025-09-08.log
│   │       └── 2025-09-09.log
│   ├── utils
│   ├── visualization
│   └── watch
│       ├── alert
│       │   ├── {datetime.now().strftime('%Y-%m-%d')}.log
│       │   ├── 2025-09-08.log
│       │   └── 2025-09-09.log
│       ├── analyze
│       │   └── {datetime.now().strftime('%Y-%m-%d')}.log
│       ├── dailyAggregator
│       │   └── {datetime.now().strftime('%Y-%m-%d')}.log
│       └── watch
│           └── {datetime.now().strftime('%Y-%m-%d')}.log
├── main.py
├── makefile
├── python
│   ├── __init__.py
│   ├── analysis
│   │   ├── __init__.py
│   │   ├── data_collector.py
│   │   ├── formula_for_analyzer.py
│   │   ├── portfolio_analyzer.py
│   │   └── README.md
│   ├── config.py
│   ├── db
│   │   ├── dump_csv.py
│   │   ├── my_stock.db
│   │   └── README.md
│   ├── init_database.py
│   ├── trading
│   │   ├── __init__.py
│   │   ├── buy_and_sell_stock.py
│   │   ├── every_stock_buy_and_sell_timing.py
│   │   ├── README.md
│   │   └── trading_rules.py
│   ├── utils
│   │   ├── __init__.py
│   │   ├── alert.py
│   │   ├── indicators.py
│   │   ├── logger.py
│   │   ├── README.md
│   │   └── report.py
│   ├── visualization
│   │   ├── __init__.py
│   │   ├── generate_all_charts.py
│   │   ├── plot_indicators.py
│   │   ├── README.md
│   │   ├── stock_chart_visualizer.py
│   │   └── view_charts.py
│   └── watch
│       ├── __init__.py
│       ├── analyze.py
│       ├── dailyAggregator.py
│       ├── README.md
│       └── watch.py
├── README.md
├── README.md.bak
└── requirements.txt

```

## Makefile による操作

このプロジェクトでは、様々なタスクを簡単に実行するためのMakefileを提供しています。

### 基本的なコマンド

```bash
# ヘルプを表示
make help

# 依存関係のインストール
make install

# コードのフォーマット
make format

# コードのリントチェック
make lint

# テストの実行
make test
```

### 監視・分析コマンド

```bash
# リアルタイム監視モードで実行
make watch

# 全銘柄の分析を実行
make analyze-all

# 特定の銘柄を分析（例：7203はトヨタ自動車）
make analyze-stock CODE=7203

# 日次データの集計を実行
make aggregate
```

### データベース操作

```bash
# データベースの初期化
make init-db

# データベースのバックアップ作成
make backup-db
```

### 定期実行タスク

```bash
# 日次タスク（データ集計、日次レポート）
make run-daily

# 週次タスク（週次レポート生成）
make run-weekly

# 月次タスク（月次レポート、ポートフォリオ見直し）
make run-monthly

# 年次タスク（年次レポート、税務計算）
make run-yearly

# 定期実行用のcronジョブを設定
make install-cron
```

### メンテナンス

```bash
# 一時ファイルの削除
make clean
```

### その他の操作

このシステムは主にMakefileを通じて操作します。以下に、主要な操作コマンドをまとめます。

#### データ取得・更新

| コマンド | 説明 |
|---------|------|
| `make update-prices` | 株価データを更新します。 |
| `make update-fundamentals` | 財務データを更新します。 |

#### 分析・レポート生成

| コマンド | 説明 |
|---------|------|
| `make analyze-all` | 全銘柄のテクニカル分析を実行します。 |
| `make analyze-stock CODE=XXXX` | 特定銘柄（例：`CODE=7203`はトヨタ自動車）の分析を実行します。 |
| `make analyze-my-stock` | 保有株式の売買タイミングやパフォーマンスを分析します。 |
| `make analyze-my-stock PERIOD=6mo` | 分析期間を指定して保有株式の売買タイミングを分析します（例：6ヶ月）。 |
| `make generate-my-charts` | 保有株式のテクニカル指標チャートを作成します。 |
| `make view-my-charts` | 作成されたチャートを確認します。 |
| `make analyze-portfolio` | ポートフォリオ全体の健全性を評価します。 |
| `make validate-trading-rules` | 売買ルールの検証を実行します。 |
| `make backtest` | バックテストを実行します。 |
| `make optimize` | パラメータ最適化を実行します。 |

#### リアルタイム監視

| コマンド | 説明 |
|---------|------|
| `make watch` | リアルタイム監視モードで実行します（推奨）。 |

#### テスト

```bash
# すべてのテストを実行
make test

# カバレッジレポート付きでテストを実行
pytest --cov=python --cov-report=html

# 特定のテストを実行
pytest tests/unit/test_analysis.py -v
```

### コーディング規約

- PEP 8 に準拠
- 型ヒントを使用
- ドキュメント文字列（docstring）を記述
- ユニットテストを記述

## 売買タイミングの理解

システムが生成する買い・売りシグナルの主な条件です。

### 買いシグナル

- **++パターン**: 連続上昇（ゴールデンクロス）
- **RSI過売り**: RSI 30以下からの反転
- **価格安値圏**: 長期移動平均線の90%以下

### 売りシグナル

- **--パターン**: 連続下降（デッドクロス）
- **RSI過買い**: RSI 70以上からの反転
- **利確**: 10%利益達成での自動売却
- **ストップロス**: 5%損失での自動売却

## 分析結果の読み方

### 重要な指標

| 指標 | 良い値 | 悪い値 | 説明 |
|------|--------|--------|------|
| **総リターン** | +5%以上 | -5%以下 | 期間中の収益率 |
| **年率リターン** | +10%以上 | -10%以下 | 年間換算の収益率 |
| **ボラティリティ** | 20%以下 | 40%以上 | 価格変動の激しさ |
| **シャープレシオ** | 1.0以上 | 0.5以下 | リスク調整後リターン |
| **最大ドローダウン** | -10%以内 | -20%以下 | 最大の損失幅 |
| **勝率** | 60%以上 | 40%以下 | 利益が出る取引の割合 |

### 分散効果の評価

- **平均相関係数**: ポートフォリオ内の各銘柄間の平均的な相関関係を示します。値が低いほど分散効果が高いと判断できます。
  - 0.3未満 → ✅ 良好な分散効果
  - 0.3-0.6 → ⚠️ 中程度の分散効果
  - 0.6以上 → ❌ 分散効果が限定的

## カスタマイズ方法

### 保有株式管理

保有株は `data/my_stock.csv` で管理します。このCSVファイルを編集することで、銘柄の追加、数量変更、購入価格変更が可能です。システムはCSVの内容を読み込んで自動的に分析・監視を行います。

`data/my_stock.csv` の例:

```csv
code,name,quantity,purchase_price,purchase_date,sector
7974.T,任天堂,30,8000,2024-06-01,ゲーム
1878.T,大東建託,50,2000,2024-06-01,不動産
7203.T,トヨタ自動車,100,2500,2024-06-01,自動車
```

### リスク管理パラメータ（`python/config.py`）

リスク管理に関するパラメータは `python/config.py` で設定できます。

- ストップロス幅（%）: `self.max_loss_percent = 3.0`
- 利確幅（%）: `self.take_profit_percent = 8.0`
- 暴落アラート閾値（%）: `self.crash_threshold = -3.0`

## リアルタイム監視・分析フロー

システムは以下のフローでリアルタイム監視と分析を行います。

```mermaid
flowchart TD
    A[CSV 読み込み: my_stock.csv] --> B[株価取得: 2分周期 ex:Yahoo Financeなど]
    B --> C{価格変動確認}
    C -->|下落 >= 3%| D[アラート出力: ログ, Slack]
    C -->|正常| E[データ保存: SQLite > my_stock.db]
    E --> F[MACD / ボリンジャーバンド計算]
    F --> G[ポートフォリオ指標計算]
    G --> H[レポート生成 & 保存]
    H --> I[テクニカル指標グラフ生成 & 保存]
```

- 2分ごとに株価を取得して SQLite に保存します。
- 下落が閾値以上の場合、アラートを出力します。
- ポートフォリオ分析やテクニカル指標の計算も自動実行されます。

## アラート条件表

| 条件 | 内容 | 出力形式 |
|---|---|---|
| 価格下落 ≥ -3% | 暴落アラート | ログ / Slack |
| 連続2本下落 | 短期的な下落トレンドの開始を示唆し、ダマシを回避するための条件 | ログ |
| ストップロス達成（-max_loss%） | 許容損失を超えた場合の強制売却候補 | ログ / レポート |
| 利確達成（+take_profit%） | 目標利益に達した場合の利益確定候補 | ログ / レポート |

## 閾値一覧表（`python/config.py` 設定例）

| パラメータ | 値 | 説明 |
|---|---|---|
| max_loss_percent | 3.0 | 許容損失の最大割合（%） |
| take_profit_percent | 8.0 | 利確の目標割合（%） |
| crash_threshold | -3.0 | 暴落アラート発生割合（%） |
| risk_free_rate | 0.1% | シャープレシオ計算に用いる無リスク金利（年率） |

### 定期実行タスク

このセクションでは、定期的に実行するタスクとそれに対応する`Makefile`コマンドを説明します。

| コマンド | 説明 |
|---------|------|
| `make run-daily` | 日次タスク（データ集計、日次レポート生成）を実行します。 |
| `make run-weekly` | 週次タスク（週次レポート生成）を実行します。 |
| `make run-monthly` | 月次タスク（月次レポート、ポートフォリオ見直し）を実行します。 |
| `make run-yearly` | 年次タスク（年次レポート、税務計算）を実行します。 |
| `make install-cron` | 定期実行用のcronジョブを設定します（Linux/macOSのみ）。 |

#### 定期的な確認タスク

- **日常チェック（5分）**:
  - 保有株状況確認: `make analyze-my-stock`
  - 重要シグナル確認: `make watch`
- **週次分析（30分）**:
  - 売買タイミング分析: `make analyze-my-stock`
  - 分析結果確認: `cat data/report/summary/summary_report_*.txt`
- **月次評価（1時間）**:
  - 長期パフォーマンス分析: `make analyze-my-stock PERIOD=6mo`
  - ポートフォリオ再構築検討: 分析結果を基に銘柄入れ替えを検討します。
- **年次タスク(毎年12/31に実施)**:
  - `my_stock.db`を`data/archive/YYYY_myStock.csv` にbumpします。

### メンテナンス

```bash
# 一時ファイルの削除
make clean
```

### その他の操作

このシステムは主にMakefileを通じて操作します。以下に、主要な操作コマンドをまとめます。

#### データ取得・更新

| コマンド | 説明 |
|---------|------|
| `make update-prices` | 株価データを更新します。 |
| `make update-fundamentals` | 財務データを更新します。 |

#### 分析・レポート生成

| コマンド | 説明 |
|---------|------|
| `make analyze-all` | 全銘柄のテクニカル分析を実行します。 |
| `make analyze-stock CODE=XXXX` | 特定銘柄（例：`CODE=7203`はトヨタ自動車）の分析を実行します。 |
| `make analyze-my-stock` | 保有株式の売買タイミングやパフォーマンスを分析します。 |
| `make analyze-my-stock PERIOD=6mo` | 分析期間を指定して保有株式の売買タイミングを分析します（例：6ヶ月）。 |
| `make generate-my-charts` | 保有株式のテクニカル指標チャートを作成します。 |
| `make view-my-charts` | 作成されたチャートを確認します。 |
| `make analyze-portfolio` | ポートフォリオ全体の健全性を評価します。 |
| `make validate-trading-rules` | 売買ルールの検証を実行します。 |
| `make backtest` | バックテストを実行します。 |
| `make optimize` | パラメータ最適化を実行します。 |
| `make portfolio-analysis` | ポートフォリオ総合分析を実行し、レポートとグラフを生成します。 |

#### リアルタイム監視

| コマンド | 説明 |
|---------|------|
| `make watch` | リアルタイム監視モードで実行します（推奨）。 |

#### テスト

```bash
# すべてのテストを実行
make test

# カバレッジレポート付きでテストを実行
pytest --cov=python --cov-report=html

# 特定のテストを実行
pytest tests/unit/test_analysis.py -v
```

### コーディング規約

- PEP 8 に準拠
- 型ヒントを使用
- ドキュメント文字列（docstring）を記述
- ユニットテストを記述

## 売買タイミングの理解

システムが生成する買い・売りシグナルの主な条件です。

### 買いシグナル

- **++パターン**: 連続上昇（ゴールデンクロス）
- **RSI過売り**: RSI 30以下からの反転
- **価格安値圏**: 長期移動平均線の90%以下

### 売りシグナル

- **--パターン**: 連続下降（デッドクロス）
- **RSI過買い**: RSI 70以上からの反転
- **利確**: 10%利益達成での自動売却
- **ストップロス**: 5%損失での自動売却

## 分析結果の読み方

### 重要な指標

| 指標 | 良い値 | 悪い値 | 説明 |
|------|--------|--------|------|
| **総リターン** | +5%以上 | -5%以下 | 期間中の収益率 |
| **年率リターン** | +10%以上 | -10%以下 | 年間換算の収益率 |
| **ボラティリティ** | 20%以下 | 40%以上 | 価格変動の激しさ |
| **シャープレシオ** | 1.0以上 | 0.5以下 | リスク調整後リターン |
| **最大ドローダウン** | -10%以内 | -20%以下 | 最大の損失幅 |
| **勝率** | 60%以上 | 40%以下 | 利益が出る取引の割合 |

### 分散効果の評価

- **平均相関係数**: ポートフォリオ内の各銘柄間の平均的な相関関係を示します。値が低いほど分散効果が高いと判断できます。
  - 0.3未満 → ✅ 良好な分散効果
  - 0.3-0.6 → ⚠️ 中程度の分散効果
  - 0.6以上 → ❌ 分散効果が限定的

## カスタマイズ方法

### 保有株式管理

保有株は `data/my_stock.csv` で管理します。このCSVファイルを編集することで、銘柄の追加、数量変更、購入価格変更が可能です。システムはCSVの内容を読み込んで自動的に分析・監視を行います。

`data/my_stock.csv` の例:

```csv
code,name,quantity,purchase_price,purchase_date,sector
7974.T,任天堂,30,8000,2024-06-01,ゲーム
1878.T,大東建託,50,2000,2024-06-01,不動産
7203.T,トヨタ自動車,100,2500,2024-06-01,自動車
```

### リスク管理パラメータ（`python/config.py`）

リスク管理に関するパラメータは `python/config.py` で設定できます。

- ストップロス幅（%）: `self.max_loss_percent = 3.0`
- 利確幅（%）: `self.take_profit_percent = 8.0`
- 暴落アラート閾値（%）: `self.crash_threshold = -3.0`

## リアルタイム監視・分析フロー

システムは以下のフローでリアルタイム監視と分析を行います。

```mermaid
flowchart TD
    A[CSV 読み込み: my_stock.csv] --> B[株価取得: 2分周期 ex:Yahoo Financeなど]
    B --> C{価格変動確認}
    C -->|下落 >= 3%| D[アラート出力: ログ, Slack]
    C -->|正常| E[データ保存: SQLite > my_stock.db]
    E --> F[MACD / ボリンジャーバンド計算]
    F --> G[ポートフォリオ指標計算]
    G --> H[レポート生成 & 保存]
    H --> I[テクニカル指標グラフ生成 & 保存]
```

- 2分ごとに株価を取得して SQLite に保存します。
- 下落が閾値以上の場合、アラートを出力します。
- ポートフォリオ分析やテクニカル指標の計算も自動実行されます。

## アラート条件表

| 条件 | 内容 | 出力形式 |
|---|---|---|
| 価格下落 ≥ -3% | 暴落アラート | ログ / Slack |
| 連続2本下落 | 短期的な下落トレンドの開始を示唆し、ダマシを回避するための条件 | ログ |
| ストップロス達成（-max_loss%） | 許容損失を超えた場合の強制売却候補 | ログ / レポート |
| 利確達成（+take_profit%） | 目標利益に達した場合の利益確定候補 | ログ / レポート |

## 閾値一覧表（`python/config.py` 設定例）

| パラメータ | 値 | 説明 |
|---|---|---|
| max_loss_percent | 3.0 | 許容損失の最大割合（%） |
| take_profit_percent | 8.0 | 利確の目標割合（%） |
| crash_threshold | -3.0 | 暴落アラート発生割合（%） |
| risk_free_rate | 0.1% | シャープレシオ計算に用いる無リスク金利（年率） |

## 分析フローまとめ

1. CSV 読み込み → 保有株一覧取得 (`data/my_stock.csv`)
2. 株価取得（Yahoo Financeなど / 2分周期）
3. リアルタイム監視（暴落・ダマシ回避）
4. 売買タイミング分析（ストップロス / 利確 / MACD・ボリンジャーバンド）
5. ポートフォリオ指標計算（リターン・ボラティリティ・シャープレシオ・ドローダウン・VaR）
6. レポート生成 & 保存 (`data/report/`)
7. テクニカル指標グラフ生成 & 保存 (`data/plots/`)

## Windows での自動起動設定

本システムは常時監視 (`watch.py`) を前提とします。Windows 環境では以下の手順で自動起動を設定できます。

### 手順

1. バッチファイルを作成する

   ```bat
   @echo off
   cd /d C:\Users\<USERNAME>\your_project\watch
   python watch.py
   ```

# プロジェクトルートで

make create-win-batch

 • 作成される run_watch.bat が Windows 起動時に自動で watch.py を実行します。
 • ログは log/watch/ に出力されます。
 • シャットダウンするまで2分ごとのリアルタイム監視が継続します。

GitHub Actions 連携による自動反映
 • main ブランチへの push により、自動的に runWindow ブランチに反映されます。
 • これにより、手動で Windows にログインして操作しなくても、最新のコードが常に Windows 環境に反映されます。
 • 反映後、run_watch.bat による自動実行で最新状態が即座に監視・分析に反映されます。

補足:
 • 開発や編集は主に macOS で行い、push で Windows 側に反映。
 • Windows 側は起動したら自動で watch.py が動作するのみで操作不要。
 • 実運用では watch.py が常駐し、株価取得・分析・アラート出力を継続。
