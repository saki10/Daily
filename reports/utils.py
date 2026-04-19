import requests

def send_teams_webhook(webhook_url, text):

    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "summary": "Daily 日報",
        "themeColor": "0076D7",
        "title": "本日の日報",
        "text": text
    }

    headers = {
        "Content-Type": "application/json"
    }

    response = requests.post(webhook_url, json=payload, headers=headers)

def format_for_teams(text):
    if not text:
        return ""

    # 箇条書き改行
    text = text.replace("・", "\n・")

    # 文末で改行
    text = text.replace("。", "。\n")

    # 「 ・」の前で改行
    text = text.replace(" ・", "\n・")

    return text.strip()