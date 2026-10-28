// 画面で使う Tailwind クラスを静的 CSS へ書き出す設定。
// バッジ等のクラス名はバックエンド (/api/choices) から渡されるため Python 側も走査する。
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "../python/web/templates/**/*.html",
    "../python/web/constants.py",
    "../python/trading/stock_status.py",
  ],
  theme: { extend: {} },
  plugins: [],
};
