# Claude: 引継ぎドキュメント更新 (フローチャート Step AA-AC)

あなたは「AI三位一体開発」における**実装AI (Claude)**です。
実装完了後、引継ぎのためのドキュメントを更新してください。

## タスク1: CLAUDE.md更新 (Step AA)
### 目的
次回以降のClaude実行時に、今回の実装内容を理解できるようにする

### 更新内容
```markdown
# CLAUDE.md

## 最新の実装 (YYYY-MM-DD)
### 実装した機能
(機能名と概要)

### 変更したファイル
- `path/to/file1.ts`: (変更内容の概要)
- `path/to/file2.ts`: (変更内容の概要)

### 重要な実装上の判断
- (なぜこの実装方法を選んだか)
- (注意すべきポイント)

### 関連ドキュメント
- Design.md: (参照セクション)
- testReport.md: (テスト結果)
- Linear Task: TASK-XXX
```

## タスク2: Obsidian Vault更新 (Step AB)
### 目的
プロジェクト全体の知識ベースを更新する

### 更新対象
1. **実装ノート**: `vault/implementations/YYYY-MM-DD-feature-name.md`
   - 実装内容の詳細
   - 技術的な判断の理由
   - トラブルシューティング情報

2. **関連リンク更新**
   - 関連する既存ノートへのリンクを追加
   - タグ付け (`#implementation`, `#feature-name`)

3. **アーキテクチャ図の更新** (必要に応じて)

## タスク3: Linear Task完了 (Step AC)
1. Task Statusを **"done"** に変更
2. 完了コメントを記載:
   ```
   実装完了
   - CLAUDE.md: 更新済み
   - Obsidian: 更新済み
   - テスト: すべてパス (カバレッジ XX%)
   ```

## 完了チェックリスト
- [ ] CLAUDE.mdが更新されている
- [ ] Obsidian Vaultに実装ノートが作成されている
- [ ] Linear TaskがDoneになっている
- [ ] 次回のClaude実行時に参照すべき情報が整理されている
