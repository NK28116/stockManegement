# チャートの日本語フォント設定 (PRIDEV-482)

matplotlib で生成するチャート画像の日本語が文字化けしないようにするための設定。

## 仕組み

フォント設定は `python/visualization/font_setup.py` の `setup_japanese_font()` に集約されている。
各描画モジュール (`stock_chart_visualizer.py` / `plot_indicators.py`) は import 時にこれを呼ぶだけで、
自前で `rcParams["font.family"]` を触らない。

フォントの決定順序:

1. 環境変数 `MATPLOTLIB_FONT_FAMILY` で明示指定されたフォント
2. `japanize_matplotlib` 同梱の `IPAexGothic` (OS 非依存のベースライン)
3. OS 標準の日本語フォント
   - macOS: Hiragino Sans / Hiragino Kaku Gothic ProN / Hiragino Maru Gothic Pro
   - Windows: Meiryo / Yu Gothic / MS Gothic
   - Linux: Noto Sans CJK JP / Noto Sans JP / IPAexGothic / IPAGothic / TakaoGothic / VL Gothic

本番コンテナ (`python:3.12-slim`) には OS レベルの日本語フォントが無いため、
`requirements.txt` の `japanize-matplotlib` が実質のフォント供給元になる。

## フォントが見つからない場合の挙動

| `MATPLOTLIB_FONT_STRICT` | 挙動 |
| --- | --- |
| 未設定 (既定) | ERROR ログを出して matplotlib 既定フォントで続行する。`setup_japanese_font()` は `japanese_supported=False` を返す (描画は文字化けする) |
| `true` | `JapaneseFontUnavailableError` を送出する。文字化けした画像を配信したくない本番向け |

## 環境変数

| 環境変数 | 既定値 | 説明 |
| --- | --- | --- |
| `MATPLOTLIB_FONT_FAMILY` | (なし) | 使用フォントを明示指定する。未インストールなら次の候補へフォールバック |
| `MATPLOTLIB_FONT_STRICT` | `false` | 日本語フォントが無い場合に例外を送出するか |

## 回帰テスト

```bash
PYTHONPATH=. pytest tests/test_font_setup.py -v
```

日本語のタイトル・軸ラベル・凡例を含む図を実際に PNG へ描画し、matplotlib の
「Glyph ... missing from font(s) ...」警告が出ないことを検証する。
検知ロジック自体が働いていることも、日本語非対応フォントを設定したケースで確認している。
