import requests
import os

def send_discord(webhook_url, message, file_path=None):
    if not webhook_url or not webhook_url.strip():
        return
    try:
        payload = {"content": message}
        # Ensure we use an absolute path for reliability
        if file_path:
            abs_path = os.path.abspath(file_path)
            if os.path.exists(abs_path):
                with open(abs_path, 'rb') as f:
                    r = requests.post(webhook_url, data=payload, files={'file': ('screenshot.png', f, 'image/png')})
                    return r.status_code
        
        r = requests.post(webhook_url, json=payload)
        return r.status_code
    except Exception:
        return None
