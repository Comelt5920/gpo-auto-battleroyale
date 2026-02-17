import requests

def send_discord(webhook_url, message, file_path=None):
    if not webhook_url or not webhook_url.strip():
        return
    try:
        payload = {"content": message}
        if file_path and os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                requests.post(webhook_url, data=payload, files={'file': f})
        else:
            requests.post(webhook_url, json=payload)
    except Exception:
        pass
