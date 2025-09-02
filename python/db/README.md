
# データベース管理ガイド

## 📁 **ディレクトリ概要**
`python/db/`は、株式投資分析システムのデータベースファイルとスキーマを管理するディレクトリです。

## 🗄️ **データベースファイル**

### **stock.db**
- **形式**: SQLite3データベース
- **用途**: 株価データ、分析結果、ポートフォリオ情報の保存
- **サイズ**: 動的に変化（データ量に応じて）

## ��️ **データベース構造**

### **主要テーブル**

#### **stocks（株式基本情報）**
```sql
CREATE TABLE stocks (
    code TEXT PRIMARY KEY,           -- 証券コード
    name TEXT,                       -- 銘柄名
    sector TEXT,                     -- 業種
    created_at TIMESTAMP,            -- 作成日時
    updated_at TIMESTAMP             -- 更新日時
);
```

#### **stock_prices（株価データ）**
```sql
CREATE TABLE stock_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT,                       -- 証券コード
    date DATE,                       -- 日付
    open REAL,                       -- 始値
    high REAL,                       -- 高値
    low REAL,                        -- 安値
    close REAL,                      -- 終値
    volume INTEGER,                  -- 出来高
    created_at TIMESTAMP,            -- 作成日時
    FOREIGN KEY (code) REFERENCES stocks(code)
);
```

#### **portfolio_holdings（ポートフォリオ保有情報）**
```sql
CREATE TABLE portfolio_holdings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT,                       -- 証券コード
    quantity INTEGER,                -- 保有数量
    purchase_price REAL,             -- 購入価格
    purchase_date DATE,              -- 購入日
    portfolio_name TEXT,             -- ポートフォリオ名
    created_at TIMESTAMP,            -- 作成日時
    FOREIGN KEY (code) REFERENCES stocks(code)
);
```

#### **trading_signals（売買シグナル）**
```sql
CREATE TABLE trading_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT,                       -- 証券コード
    signal_date DATE,                -- シグナル日
    signal_type TEXT,                -- シグナルタイプ（BUY/SELL）
    price REAL,                      -- シグナル価格
    reason TEXT,                     -- シグナル理由
    confidence REAL,                 -- 信頼度（0-1）
    created_at TIMESTAMP,            -- 作成日時
    FOREIGN KEY (code) REFERENCES stocks(code)
);
```

## 🔧 **データベース操作**

### **初期化**
```bash
cd python
python3 init_database.py
```

### **データベース接続確認**
```bash
# SQLiteコマンドラインで接続
sqlite3 db/stock.db

# テーブル一覧表示
.tables

# スキーマ確認
.schema stocks

# 終了
.quit
```

### **基本的なSQLクエリ例**

#### **保有株式の確認**
```sql
SELECT 
    s.code,
    s.name,
    s.sector,
    ph.quantity,
    ph.purchase_price,
    ph.purchase_date
FROM stocks s
JOIN portfolio_holdings ph ON s.code = ph.code
WHERE ph.portfolio_name = 'practice';
```

#### **最新の株価データ確認**
```sql
SELECT 
    code,
    date,
    close,
    volume
FROM stock_prices 
WHERE code = '7974.T'
ORDER BY date DESC 
LIMIT 10;
```

#### **売買シグナルの確認**
```sql
SELECT 
    code,
    signal_date,
    signal_type,
    price,
    reason
FROM trading_signals
WHERE signal_date >= date('now', '-30 days')
ORDER BY signal_date DESC;
```

## 📊 **データ管理**

### **データのバックアップ**
```bash
# データベースのバックアップ
cp db/stock.db db/stock_backup_$(date +%Y%m%d).db

# 特定日付のバックアップ
cp db/stock.db db/stock_backup_20240901.db
```

### **データの復元**
```bash
# バックアップから復元
cp db/stock_backup_20240901.db db/stock.db
```

### **データのクリーンアップ**
```sql
-- 古い株価データの削除（1年以上前）
DELETE FROM stock_prices 
WHERE date < date('now', '-1 year');

-- 古い売買シグナルの削除（6ヶ月以上前）
DELETE FROM trading_signals 
WHERE signal_date < date('now', '-6 months');
```

## ⚠️ **注意事項**

### **データベースの整合性**
- 外部キー制約により、関連データの整合性が保たれます
- 株式コードを削除する前に、関連するデータを確認してください

### **パフォーマンス**
- 大量のデータがある場合は、インデックスの追加を検討
- 定期的なVACUUM実行でデータベースサイズを最適化

### **バックアップ**
- 重要なデータ変更前には必ずバックアップを取得
- 複数のバックアップを保持することを推奨

## 🔍 **トラブルシューティング**

### **よくある問題**

1. **データベースが開けない**
   - ファイルの権限を確認
   - 他のプロセスが使用中でないか確認

2. **テーブルが見つからない**
   - `init_database.py`を実行してテーブルを作成
   - スキーマを確認

3. **データが表示されない**
   - 外部キー制約を確認
   - データの挿入日時を確認

## �� **関連ファイル**

- データベース初期化: `../init_database.py`
- 設定ファイル: `../config.py`
- ポートフォリオ分析: `../portfolio_analyzer.py`
- データ収集: `../data_collector.py`

---

**注意**: データベースファイルは重要なデータを含むため、適切にバックアップを取得し、安全に管理してください。
