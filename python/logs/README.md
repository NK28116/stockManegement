`python/logs`ディレクトリにREADME.mdファイルを作成します。ログファイルの管理と使用方法について説明する内容にします。

```markdown:python/logs/README.md
# ログファイル管理ガイド

## 📁 **ディレクトリ概要**
`python/logs/`は、株式投資分析システムの実行ログを保存するディレクトリです。

## 📊 **ログファイル一覧**

### **portfolio_analyzer.log**
- **用途**: ポートフォリオ分析の実行ログ
- **内容**: データ取得、分析処理、エラー情報
- **更新頻度**: 分析実行時

### **data_collector.log**
- **用途**: 株価データ収集の実行ログ
- **内容**: API呼び出し、データ保存、エラー情報
- **更新頻度**: データ収集実行時

## 🔍 **ログの確認方法**

### **リアルタイム監視**
```bash
# 最新のログをリアルタイムで表示
tail -f portfolio_analyzer.log

# 最新のログを表示
tail -20 portfolio_analyzer.log
```

### **エラーの確認**
```bash
# エラーログのみを表示
grep "ERROR" portfolio_analyzer.log

# 警告ログのみを表示
grep "WARNING" portfolio_analyzer.log
```

### **特定の銘柄のログ確認**
```bash
# 特定の銘柄に関するログを表示
grep "7203.T" portfolio_analyzer.log
```

## 📝 **ログレベルの説明**

| レベル | 説明 | 対応 |
|--------|------|------|
| **INFO** | 通常の処理情報 | 確認のみ |
| **WARNING** | 警告（処理は継続） | 要監視 |
| **ERROR** | エラー（処理失敗） | 要対応 |
| **DEBUG** | 詳細なデバッグ情報 | 開発時のみ |

## �� **ログファイルの管理**

### **ログローテーション**
- ログファイルが大きくなりすぎた場合は、古いログを削除
- 推奨: 1ヶ月以上古いログは削除

### **ディスク容量の確認**
```bash
# ログディレクトリの容量確認
du -sh python/logs/

# 各ログファイルのサイズ確認
ls -lh python/logs/*.log
```

## ⚠️ **トラブルシューティング**

### **よくある問題と対処法**

1. **ログファイルが作成されない**
   - ディレクトリの書き込み権限を確認
   - 仮想環境が有効化されているか確認

2. **ログが出力されない**
   - ログレベルが適切に設定されているか確認
   - ファイルパスが正しいか確認

3. **ログファイルが大きすぎる**
   - 古いログを削除
   - ログローテーションの設定を検討

## 🔧 **ログ設定のカスタマイズ**

### **ログレベルの変更**
`portfolio_analyzer.py`でログレベルを調整：
```python
logging.basicConfig(
    level=logging.DEBUG,  # INFO → DEBUG に変更
    # ... 他の設定
)
```

### **ログファイルの最大サイズ設定**
```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    'logs/portfolio_analyzer.log',
    maxBytes=1024*1024,  # 1MB
    backupCount=5
)
```

## 📚 **関連ドキュメント**

- メインREADME: `../docs/README.md`
- 設定ファイル: `../config.py`
- ポートフォリオ分析: `../portfolio_analyzer.py`

---

**注意**: ログファイルには機密情報が含まれる場合があります。適切に管理し、不要になったログは定期的に削除してください。
```

このREADME.mdファイルにより、ログファイルの管理方法、確認方法、トラブルシューティングが分かりやすくなります。保有株式の分析を実行する際のログ確認や、問題が発生した際の原因特定に役立ちます。