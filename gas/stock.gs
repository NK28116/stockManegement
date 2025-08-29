// 株価取得（例：Google Financeを利用）
function getStockPrice(code) {
  const url = "https://www.google.com/finance/quote/" + code + ":TYO";
  const html = UrlFetchApp.fetch(url).getContentText();

  // ページ内から株価を抽出
  const regex = /<div class="YMlKec fxKbKc">¥([\d,]+)/;
  const match = html.match(regex);
  if (match) {
    return parseFloat(match[1].replace(/,/g, ""));
  }
  throw new Error("株価が取得できません: " + code);
}

// テスト実行用
function testGetPrice() {
  Logger.log(getStockPrice("7203")); // トヨタ
}