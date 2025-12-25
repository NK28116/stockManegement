#!/usr/bin/env bash
set -e

# dirs
mkdir -p .ai/prompts

# turn
echo serena > .ai/turn

# diff
git diff --cached > .ai/tmp_diff.txt

# base template
if [[ ! -f .ai/prompts/serena-review.template.txt ]]; then
  cat << 'EOF' > .ai/prompts/serena-review.template.txt
あなたは Serena です。
以下の情報を使って「commit 可能か」をレビューしてください。

【必須入力】
- git diff --cached
- .ai/commit-check.md
- docs/architecture.md
- docs/decisions.md

【やること】
1. 変更内容を要約
2. 設計との不整合を検出
3. Claude/Gemini の役割逸脱がないか確認
4. commit 単位が適切か判断

【出力】
- .ai/serena-review.md を更新
- OKなら「ready-to-commit」と明記
- NGなら理由と修正指示を書く

※ commit は絶対に実行しない
EOF
fi

OUT=.ai/prompts/serena-review.txt

# generate
cat .ai/prompts/serena-review.template.txt > "$OUT"

echo -e "\n---\n### git diff --cached\n" >> "$OUT"
cat .ai/tmp_diff.txt >> "$OUT"

echo -e "\n---\n### commit-check\n" >> "$OUT"
cat .ai/commit-check.md >> "$OUT"

echo -e "\n---\n### architecture\n" >> "$OUT"
cat docs/architecture.md >> "$OUT"

echo -e "\n---\n### decisions\n" >> "$OUT"
cat docs/decisions.md >> "$OUT"

echo "✅ Serena prompt generated: $OUT"