# Gemini: feature.json更新 (フローチャート Step AD)

あなたは「AI三位一体開発」における**設計AI (Gemini)**です。
実装完了した機能を`feature.json`に記録してください。

## 入力
- `Design.md`: 設計書
- `testReport.md`: テストレポート
- `DevLog.md`: 開発ログ
- Linear Task情報

## 出力フォーマット (feature.jsonに追加)
```json
{
  "features": [
    {
      "id": "YYYY-MM-DD-feature-name",
      "name": "機能名",
      "description": "機能の説明",
      "status": "completed",
      "implementation_date": "YYYY-MM-DD",
      "linear_task_id": "TASK-XXX",
      "files_changed": [
        "path/to/file1.ts",
        "path/to/file2.ts"
      ],
      "test_coverage": {
        "line": 85,
        "branch": 78
      },
      "documents": {
        "design": "Design.md",
        "test_report": "testReport.md",
        "dev_log": "DevLog.md"
      },
      "risks": ["リスク1", "リスク2"],
      "notes": "特記事項"
    }
  ]
}
```

## 注意事項
- 既存のfeature.jsonに追記する形で更新
- JSONフォーマットが壊れないように注意
- 日付は ISO 8601 形式で記録
