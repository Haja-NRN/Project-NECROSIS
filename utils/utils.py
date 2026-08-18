# utils/utils.py
import time
import random
import os
import sys
import subprocess
import uuid

def get_machine_id():
    """Retourne un identifiant unique de la machine."""
    try:
        return str(uuid.getnode())
    except:
        return os.environ.get('COMPUTERNAME', os.environ.get('HOSTNAME', 'unknown'))

def sleep_with_jitter(base_seconds, jitter_ratio=0.3):
    """Sommeil avec délai aléatoire."""
    delay = base_seconds * (1 + random.uniform(-jitter_ratio, jitter_ratio))
    time.sleep(max(0, delay))

def relaunch_app(new_script_path):
    """Relance le processus avec un nouveau script."""
    subprocess.Popen([sys.executable, new_script_path])
    sys.exit(0)