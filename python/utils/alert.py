import requests

SLACK_WEBHOOK = "https://hooks.slack.com/services/XXXX"
LINE_TOKEN = "YOUR_LINE_TOKEN"

def send_alert(message: str):
    # Slack
    requests.post(SLACK_WEBHOOK, json={"text": message})
    # LINE
    requests.post("https://notify-api.line.me/api/notify",
                  headers={"Authorization": f"Bearer {LINE_TOKEN}"},
                  data={"message": message})