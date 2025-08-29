// Slack通知
function sendSlack(msg) {
  const webhook = "https://hooks.slack.com/services/xxxx/yyyy/zzzz";
  UrlFetchApp.fetch(webhook, {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify({ text: msg })
  });
}

// LINE Notify通知
function sendLine(msg) {
  const token = "YOUR_LINE_NOTIFY_TOKEN";
  UrlFetchApp.fetch("https://notify-api.line.me/api/notify", {
    method: "post",
    headers: { Authorization: "Bearer " + token },
    payload: { message: msg }
  });
}