# Third-Party Notices

このリポジトリのコードは [MIT License](LICENSE) で公開しています。
ただし、以下の第三者の成果物を同梱・利用しており、それぞれのライセンスに従います。

## リポジトリに同梱しているもの

| 名称 | バージョン | 同梱場所 | ライセンス |
| --- | --- | --- | --- |
| Vue.js | 3.5.13 | `python/web/static/vendor/vue.global.prod.js` | MIT |
| Tailwind CSS (生成された CSS) | 3.4.17 | `python/web/static/css/tailwind.css` | MIT |

`tailwind.css` は Tailwind CSS が `frontend/` の設定から生成したものです。リセット部分 (Preflight) は
modern-normalize (MIT, Copyright (c) Sindre Sorhus) をもとにしています。
再生成の手順は `frontend/package.json` を参照してください。

### Vue.js

```
The MIT License (MIT)

Copyright (c) 2018-present, Yuxi (Evan) You and Vue contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
```

### Tailwind CSS

```
MIT License

Copyright (c) Tailwind Labs, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 同梱せず、インストール時に取得するもの

- **Python パッケージ**: `requirements.txt` / `requirements-dev.txt` に記載したものを `pip` で取得します。
  各パッケージのライセンスはそれぞれの配布元に従います。
- **フォント**: チャートの日本語表示には、`japanize-matplotlib` が同梱する IPAexGothic
  ([IPA フォントライセンス v1.0](https://moji.or.jp/ipafont/license/)) または OS のフォントを使います。
  フォントファイル自体はこのリポジトリに含めていません。
- **Node.js パッケージ** (`frontend/`): アセットの再生成時にだけ使う開発用の依存です。

## データと商標について

- 株価データは [yfinance](https://github.com/ranaroussi/yfinance) を通じて Yahoo! Finance から取得します。
  yfinance は Yahoo とは無関係のオープンソースプロジェクトです。取得したデータの利用・再配布は、
  Yahoo の利用規約に従ってください。このリポジトリはデータの正確性・継続的な提供を保証しません。
- 証券会社の API 仕様書 (kabuステーション API など) は各社の著作物のため、このリポジトリには含めません。
  利用する場合は各社の公式サイトから取得してください。
- 文書・画面・サンプルデータに現れる会社名・銘柄名・サービス名は、各社の商標または登録商標です。
