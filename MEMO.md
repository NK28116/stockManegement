# 株式投資分析・運用システム

## 今後の予定や実装内容

### `python/analysis/portfolio_analyzer.py`

このファイルは、ポートフォリオの取得、株価データの取得（`DB`または`yfinance`）、テクニカル指標の計算（ボリンジャーバンド、MACD）、分析結果の保存、およびチャートのプロット機能を提供しています。

**実装状況の評価:**

- **ポートフォリオ取得 (`get_portfolio`)**: SQLiteデータベースから、またはCSVファイルから保有株式情報を取得する機能があります。
- **株価取得 (`get_stock_prices`, `fetch_stock_data`)**: データベースから株価を取得する機能と、`yfinance`を使って外部から株価データを取得する機能があります。`get_stock_prices`はDBから取得し、`fetch_stock_data`は`yfinance`から取得します。`analyze_portfolio`では`get_stock_prices`が使われているため、DBに最新の株価データが格納されていることが前提となります。
- **株価分析 (`analyze_stock`)**: `++`, `+-`, `--` のパターンに基づいて売買シグナルを生成するロジックがあります。これはシンプルなロジックですが、スイングトレードの基本的な判断材料となり得ます。
- **テクニカル指標計算 (`calculate_technical_indicators`)**: ボリンジャーバンドとMACDを計算する機能があります。
- **分析結果保存 (`save_results`, `save_analysis`)**: 分析結果をテキストファイルに保存する機能があります。
- **チャート描画 (`plot_indicators`)**: 株価とテクニカル指標をプロットし、表示または画像ファイルとして保存する機能があります。
- **ポートフォリオ全体分析 (`analyze_portfolio`)**: 保有銘柄ごとに株価を取得し、テクニカル指標を計算し、プロットして分析結果を保存する一連の処理を実行します。

**未実装または改善が必要な点:**

1. **株価データの更新メカニズム**
   - `analyze_portfolio`はDBから株価データを取得しますが、このDBが常に最新のデータで更新されている保証がありません。`python/watch/dailyAggregator.py`のコメントにあったように、「分足から日足への自動集計機能が未実装」であるため、日々の株価データをDBに自動的に取り込む仕組みが必要です。`fetch_stock_data`は`yfinance`からデータを取得できますが、これを定期的に実行し、DBに保存するロジックが不足しています。
2. **`analyze_stock`のロジックの強化**
   - 現在の`analyze_stock`は非常にシンプルなパターン認識に基づいています。より高度なスイングトレード戦略（例: 複数のテクニカル指標の組み合わせ、機械学習ベースのシグナル生成など）を導入することで、分析の精度を高めることができます。
3. **ポートフォリオ管理の機能拡張**
   - `get_portfolio`は保有銘柄を取得しますが、売買履歴の管理、損益計算、ポートフォリオのリバランス提案など、より高度なポートフォリオ管理機能は不足しています。
4. **アラート機能との連携**
   - `python/utils/alert.py`が存在しますが、`PortfolioAnalyzer`の分析結果（特に売買シグナル）をアラート機能と連携させる仕組みが明示されていません。

### `python/trading/every_stock_BuySell_timing.py`

このファイルは、CSVファイルから銘柄コードを読み込み、各銘柄の株価データを`yfinance`から取得し、`ImprovedTradingRules`クラス（このファイルには定義されていませんが、`trading_rules`モジュールからインポートされています）を使用して売買タイミングを分析し、サマリーレポートと詳細レポートを生成・保存する機能を提供しています。

**実装状況の評価:**

- **銘柄コードの読み込み (`load_codes_from_csv`)**: CSVファイルから銘柄コードを読み込み、`.T`形式に変換する機能があります。
- **単一銘柄の分析 (`analyze_single_stock`)**: `yfinance`から株価データを取得し、`ImprovedTradingRules`を使って売買ルール分析とパフォーマンス指標の計算を行います。
- **全銘柄の分析 (`analyze_all_stocks`)**: 読み込んだ全銘柄に対して`analyze_single_stock`を実行します。
- **レポート生成・保存 (`generate_summary_report`, `generate_detailed_report`, `save_reports`)**: 分析結果をまとめたサマリーレポートと、損益詳細観察形式の詳細レポートを生成し、指定されたディレクトリに保存します。
- **購入情報取得 (`get_purchase_info`)**: `my_stock.csv`から購入情報を取得する機能があります。
- **月次リターン計算 (`calculate_monthly_returns`)**: 月次リターンを計算します。
- **日次ステータス取得 (`get_daily_status`)**: 直近N日間の毎日のステータスと判断を取得します。
- **ストップ値計算 (`calculate_daily_stop_price`)**: その日のストップ値を計算します。

**未実装または改善が必要な点:**

1. **`ImprovedTradingRules`の実装詳細**: このファイルでは`from trading_rules import ImprovedTradingRules`とインポートされていますが、その具体的な実装（どのような売買ルールが適用されているか）は不明です。このルールの妥当性や改善の余地を評価するためには、`python/trading/trading_rules.py`の内容を確認する必要があります。
2. **データソースの一貫性**: `PortfolioAnalyzer`はDBから株価データを取得するのに対し、このモジュールは`yfinance`から直接データを取得しています。データソースが異なることで、データの一貫性や処理速度に影響が出る可能性があります。理想的には、一元化されたデータ収集・保存メカニズム（DB）からデータを取得するように統一すべきです。
3. **レポートの活用**: 生成されたレポートがどのように活用されるか（例: 自動通知、ダッシュボード表示など）が明確ではありません。レポートを単にファイルとして保存するだけでなく、ユーザーがよりアクセスしやすい形で情報を提供する仕組みがあると良いでしょう。
4. **リアルタイム性**: `yfinance`からのデータ取得はリアルタイムに近いですが、日次タスクとして実行される場合、市場が開いている間に最新のデータを取得し、分析に反映させるためのスケジューリングや実行方法を考慮する必要があります。

### `python/visualization/generate_all_charts.py`

このファイルは、`StockChartVisualizer`クラスを使用して、`my_stock.csv`に記載されている全銘柄のチャートを一括で生成する機能を提供しています。期間はデフォルトで3ヶ月に設定されています。

**実装状況の評価:**

- **チャート生成の実行**: `StockChartVisualizer`をインスタンス化し、`visualize_all_stocks`メソッドを呼び出すことで、チャート生成プロセスを開始します。
- **対象銘柄**: `my_stock.csv`から銘柄を読み込むようです。
- **出力先**: チャートファイルは`data/chartImg`フォルダに保存されると記載されています。

**未実装または改善が必要な点:**

1. **`StockChartVisualizer`の実装詳細**: このファイルでは`StockChartVisualizer`クラスがインポートされていますが、その具体的な実装（どのようなチャートが生成されるか、どのようなテクニカル指標がプロットされるか、データソースは何かなど）は不明です。このクラスの妥当性や改善の余地を評価するためには、`python/visualization/stock_chart_visualizer.py`の内容を確認する必要があります。
2. **データソースの一貫性**: `every_stock_BuySell_timing.py`と同様に、`StockChartVisualizer`がどのようなデータソースから株価データを取得しているかを確認する必要があります。理想的には、一元化されたデータ収集・保存メカニズム（DB）からデータを取得するように統一すべきです。
3. **柔軟性**: 現在は`my_stock.csv`と期間`3mo`がハードコードされています。コマンドライン引数などでこれらを変更できるようにすると、より柔軟な運用が可能になります。

次に、データ収集とデータベースの準備状況を確認します。これには、`python/init_database.py`と、`python/analysis/data_collector.py`、そして`python/db/dump_csv.py`が関連している可能性があります。まず

### `python/init_database.py`

このファイルは、SQLiteデータベース`my_stock.db`を初期化し、複数のテーブル（`intraday`, `daily`, `pre_buy_daily`, `portfolio`, `stock_data`, `stocks`, `portfolio_holdings`）を作成する機能を提供しています。また、重複ディレクトリの削除やデータベースの状態確認機能も含まれています。

**実装状況の評価:**

- **データベース構造**: スイングトレードに必要な様々な情報を格納するためのテーブルが定義されています。特に`intraday`（分足）、`daily`（日足）、`stock_data`（株価データ）、`portfolio_holdings`（ポートフォリオ保有銘柄）などは重要です。
- **初期化機能**: データベースが存在しない場合にテーブルを作成し、インデックスを設定する機能があります。

**未実装または改善が必要な点:**

1. **`stock_data`テーブルの利用**: `stock_data`テーブルは`date`, `open`, `high`, `low`, `close`というカラムを持っていますが、`code`カラムがありません。これは、このテーブルが単一の銘柄の日足データを格納することを意図しているのか、あるいは設計上の問題があるのか不明です。複数の銘柄の株価データを格納するためには、`code`カラムが必要です。
2. **データ投入メカニズム**: データベースの初期化は行われますが、これらのテーブルに実際に株価データや銘柄情報を投入するメカニズムが不足しています。特に、`intraday`や`daily`、`stock_data`テーブルに最新の株価データを継続的に取り込む機能が必要です。これは、以前に指摘した「株価データの更新メカニズム」と密接に関連しています。
3. **`daily`テーブルと`portfolio_holdings`テーブルの重複**: `daily`テーブルと`portfolio_holdings`テーブルは、保有銘柄に関する情報を格納する点で重複しているように見えます。`daily`テーブルには`name`, `quantity`, `purchase_price`, `purchase_date`, `sector`, `status`といった情報があり、`portfolio_holdings`テーブルにも`portfolio_name`, `code`, `quantity`, `purchase_price`, `purchase_date`といった情報があります。これらのテーブルの役割を明確にし、冗長性を排除するか、連携方法を定義する必要があります。
4. **`pre_buy_daily`テーブルの活用**: 購入予定の銘柄を管理する`pre_buy_daily`テーブルがありますが、このテーブルにデータを追加・更新するロジックや、そのデータがどのように売買タイミング分析に活用されるかが不明です。

### `python/analysis/data_collector.py`

このファイルは、前四半期の株価データを`yfinance`から取得し、テクニカル指標（日次リターン、SMA_20、ボラティリティ）を計算し、パフォーマンス分析を行い、その結果をCSVファイルに保存する機能を提供しています。また、`stocks`テーブルから銘柄コードリストを取得し、取得した株価データをDBの`stock_prices`テーブルに保存する機能も含まれています。

**実装状況の評価:**

- **データ収集 (`collect_stock_data`, `fetch_and_store_stock_prices_quarter`)**: `yfinance`から指定期間（前四半期）の株価データを取得し、DBの`stock_prices`テーブルに保存する機能があります。これは、以前に指摘した「株価データの更新メカニズム」の一部を担う可能性があります。
- **テクニカル指標計算 (`_calculate_indicators`)**: 日次リターン、20日移動平均線、ボラティリティを計算します。
- **パフォーマンス分析 (`_analyze_performance`)**: 始値、終値、価格変化率、最高値、最安値、出来高平均、ボラティリティ、データポイント数などのパフォーマンス指標を計算します。
- **銘柄リスト取得 (`get_stock_list_from_db`)**: `stocks`テーブルから銘柄コードを取得します。
- **結果保存**: 分析結果を`quarterly_analysis.csv`として保存します。

**未実装または改善が必要な点:**

1. ~~**`stock_prices`テーブルの定義**: `fetch_and_store_stock_prices_quarter`関数は`stock_prices`テーブルにデータを挿入していますが、`python/init_database.py`で定義されているテーブルには`stock_prices`という名前のテーブルがありません。`init_database.py`の`stock_data`テーブルがこれに相当する可能性がありますが、その場合、`stock_data`テーブルには`code`カラムがないため、複数の銘柄の株価データを格納できません。この不整合を解消する必要があります。~~
   - **修正案**: `init_database.py`の`stock_data`テーブルに`code TEXT`カラムを追加し、`PRIMARY KEY (code, date)`とする。または、`stock_prices`という新しいテーブルを`init_database.py`で定義する。
2. **日次データの継続的な更新**: このスクリプトは前四半期のデータを取得・保存しますが、日々の最新データを継続的に取得し、DBに保存するメカニズムがまだ不足しています。`main.py`の日次タスクでこの機能を呼び出すか、別途スケジューリングされたタスクとして実行する必要があります。
3. **データ収集の対象銘柄**: `get_stock_list_from_db`は`stocks`テーブルから銘柄コードを取得しますが、`stocks`テーブルにどのように銘柄が登録されるかが不明です。また、`main`関数内では`config.codes_path`からも銘柄一覧を読み込んでおり、データソースが複数存在します。銘柄リストの管理方法を統一する必要があります。
4. ~~**エラーハンドリングとロギング**: `print`文が多く使われていますが、`python/utils/logger.py`で定義されているロギングシステムを統一的に使用することで、ログの管理と分析が容易になります。~~

### `python/db/dump_csv.py`

このファイルは、SQLiteデータベースから指定されたテーブルの指定年分のデータをCSVファイルにダンプし、その後データベースからそのデータを削除する機能を提供しています。これは、データのアーカイブとデータベースの肥大化防止に役立ちます。

**実装状況の評価:**

- **データダンプと削除 (`dump_and_delete_table_by_year`)**: 指定されたテーブルと日付カラム、対象年を基にデータを抽出し、CSVとして保存後、DBから削除します。
- **対象テーブル**: `main`関数では`stock_prices`と`trading_signals`テーブルを対象としています。

**未実装または改善が必要な点:**

1. **`stock_prices`テーブルの定義**: 再度になりますが、`python/init_database.py`で定義されているテーブルには`stock_prices`という名前のテーブルがありません。`python/analysis/data_collector.py`と同様に、この不整合を解消する必要があります。
    - **修正案**: `init_database.py`の`stock_data`テーブルに`code TEXT`カラムを追加し、`PRIMARY KEY (code, date)`とする。または、`stock_prices`という新しいテーブルを`init_database.py`で定義する。
2. **`trading_signals`テーブルの定義**: `trading_signals`テーブルも`init_database.py`で定義されていません。売買シグナルを保存するテーブルが必要であれば、これも`init_database.py`に追加する必要があります。
3. **自動化**: 現在、対象年はユーザーからの入力に依存しています。年次タスクとして自動実行されるためには、対象年を自動的に決定するロジック（例: 前年）が必要です。
4. **ロギング**: `print`文が多く使われていますが、`python/utils/logger.py`で定義されているロギングシステムを統一的に使用することで、ログの管理と分析が容易になります。

これまでのファイル確認で、データ収集とデータベースの準備に関する主要な課題が明らかになりました。

### `python/utils/alert.py`

このファイルは、SlackとLINEを通じてアラートメッセージを送信する機能を提供しています。`AlertManager`クラスが通知のロジックをカプセル化し、`send_alert`関数が簡易的なインターフェースを提供しています。通知の有効/無効や`Webhook URL/トークン`は`config.py`から取得されます。

**実装状況の評価:**

- **通知機能**: Slackと主要な通知チャネルに対応しています。
- **設定連携**: `config.py`から設定を読み込むため、柔軟な設定が可能です。
- **ロギング**: 適切なロギングが行われています。

**未実装または改善が必要な点:**

1. **アラートトリガーとの連携**: アラート機能自体は実装されていますが、どのイベント（例: 売買シグナル発生、ポートフォリオの異常、データ取得エラーなど）でアラートをトリガーするか、そのロジックが他のモジュール（`PortfolioAnalyzer`, `every_stock_BuySell_timing`など）に実装されている必要があります。現在、この連携は明示されていません。
2. **アラート内容のカスタマイズ**: 現在の`send_alert`はシンプルなメッセージを送信しますが、より詳細な情報（例: 銘柄コード、現在の価格、シグナルの種類、推奨アクションなど）を含む、構造化されたアラートメッセージを生成する機能があると、ユーザーにとってより有用です。

### `python/config.py`

このファイルは、プロジェクト全体で使用される様々な設定（パス、DB接続、分析パラメータ、リスク管理、監視、ポートフォリオ分析、アラート設定）を一元的に管理する`Config`クラスを提供しています。環境変数からの読み込みもサポートしています。

**実装状況の評価:**

- **一元管理**: 多くの設定が一箇所にまとめられており、管理しやすい構造です。
- **パス設定**: ルートディレクトリからの相対パスで各種ディレクトリやファイルパスが定義されています。
- **環境変数対応**: `Slack Webhook`などの機密情報や動的な設定は環境変数から読み込むことができます。
- **パラメータ**: 分析やリスク管理、監視に関する様々なパラメータが定義されています。

**未実装または改善が必要な点:**

1. **LINE通知トークンの欠落**: 
   - ~~`python/utils/alert.py`ではLINE通知機能が実装されていますが、`config.py`には`line_token`の設定がありません。LINE通知を有効にするためには、この設定を追加する必要があります。~~
2. **DBパスの不整合**: 
   - ~~`self.db_path = self.root_dir / "python" / "db" / "my_stock.db"`と定義されていますが、`python/init_database.py`では`main_db_path = os.path.join(os.path.dirname(__file__), "db/my_stock.db")`となっており、これは`python/db/my_stock.db`を指します。`config.py`のパスは`python/python/db/my_stock.db`を指すことになり、不整合が生じています。これを修正する必要があります~~。
   - **修正案**: `self.db_path = self.root_dir / "db" / "my_stock.db"` に変更するか、`init_database.py`のパス定義を`config.db_path`を使用するように変更する。
3. ~~**`get_alert_config`の`enabled`ロジック**: 現在、`enabled`は`bool(self.slack_webhook)`に依存しています。LINE通知を追加する場合、`slack_webhook`または`line_token`のいずれかが設定されていれば`enabled`となるようにロジックを修正する必要があります。~~
4. ~~**`trading_rules.py`のパラメータ**: `every_stock_BuySell_timing.py`で使われている`ImprovedTradingRules`クラスのパラメータ（もしあれば）が`config.py`で管理されていない可能性があります。もしあれば、ここに追加することで一元管理できます。~~
これまでのファイル確認で、実装すべき点がかなり明確になりました。

### 実装すべき点のまとめ

1. **データベース構造の修正と統一**:
   - `python/init_database.py`の`stock_data`テーブルに`code TEXT`カラムを追加し、`PRIMARY KEY (code, date)`とする。これにより、複数の銘柄の日足データを格納できるようにする。
   - または、`stock_prices`という新しいテーブルを`init_database.py`で定義し、`code TEXT`カラムを含める。
   - `trading_signals`テーブルが`python/db/dump_csv.py`で参照されているため、必要であれば`init_database.py`に追加する。
   - `daily`テーブルと`portfolio_holdings`テーブルの役割を明確にし、冗長性を排除するか、連携方法を定義する。
2. **株価データの継続的な更新メカニズムの実装**:
   - `python/analysis/data_collector.py`の`fetch_and_store_stock_prices_quarter`関数を拡張し、日々の最新データを取得してDBに保存する機能（例: `fetch_and_store_daily_prices`）を実装する。
   - この新しい関数を`main.py`の日次タスク（`run_daily_task`）内で呼び出すようにする。
   - `stocks`テーブルに銘柄を登録するメカニズムを確立する（例: CSVから一括登録、手動登録など）。
3. **`python/trading/trading_rules.py`の実装詳細の確認と強化**:
   - `python/trading/trading_rules.py`の内容を読み、`ImprovedTradingRules`クラスの具体的な売買ロジックを理解する。
   - 必要に応じて、より高度なスイングトレード戦略（複数のテクニカル指標の組み合わせ、リスク管理ルールなど）を導入し、ロジックを強化する。
4. **アラート機能の連携と強化**:
   - `python/analysis/portfolio_analyzer.py`や`python/trading/every_stock_BuySell_timing.py`の分析結果（特に売買シグナルやポートフォリオの異常）をトリガーとして、`python/utils/alert.py`の`send_alert`関数を呼び出すロジックを実装する。
   - アラートメッセージに銘柄コード、価格、シグナルの種類などの詳細情報を含めるようにカスタマイズする。
5. **設定ファイル（`python/config.py`）の修正**:
   - LINE通知を有効にするために`line_token`設定を追加する。
   - `self.db_path`のパス定義を修正し、実際のデータベースファイルパスと一致させる。
   - `get_alert_config`の`enabled`ロジックを、SlackまたはLINEのいずれかが有効であればTrueとなるように修正する。
   - `trading_rules.py`のパラメータがあれば、ここに追加する。
6. **ロギングの統一**:
   - `print`文が使われている箇所を`python/utils/logger.py`で定義されているロギングシステムに置き換える。
7. **`python/visualization/stock_chart_visualizer.py`の実装詳細の確認**:
   - `python/visualization/stock_chart_visualizer.py`の内容を読み、チャート生成の詳細（データソース、プロットされる指標など）を理解する。必要に応じて、データソースをDBに統一するなどの改善を行う。
8. **年次タスクの自動化**:
   - `python/db/dump_csv.py`の`main`関数を修正し、ユーザー入力ではなく、自動的に対象年（例: 前年）を決定して実行するようにする。

