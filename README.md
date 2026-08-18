
# 🦎 NECROSIS - Malware Caméléon Autonome

**Projet Master 2 Sécurité des Réseaux et Systèmes Avancés**

---

## 📋 Description

NECROSIS est un malware caméléon autonome conçu à des fins de recherche en sécurité offensive. Il est capable d'analyser son environnement d'exécution, de muter pour échapper aux signatures, d'extraire de manière exhaustive les identifiants d'authentification et de les exfiltrer de façon furtive.

---

## 🏗️ Architecture du projet

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATEUR (main.py)                           │
│                     Exécution séquentielle des 5 phases                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          │                           │                           │
          ▼                           ▼                           ▼
┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
│  EnvironmentDetector │   │     CodeMutator     │   │  CredentialSiphon   │
│  - Détection EDR    │   │  - Mutation AST     │   │  - LSASS/SAM        │
│  - Anti-sandbox     │   │  - Code mort        │   │  - Navigateurs      │
│  - Fingerprinting   │   │  - Anti-debug       │   │  - SSH / ARP        │
└─────────────────────┘   └─────────────────────┘   └──────────┬──────────┘
          │                           │                        │
          └───────────────────────────┼────────────────────────┼──┐
                                      │                        │  │
                                      ▼                        │  │
                          ┌─────────────────────┐             │  │
                          │  PivotingEngine     │◄────────────┘  │
                          │  - Net view / Ping  │  (credentials) │
                          │  - Pass-the-Hash    │                │
                          │  - Propagation SMB  │                │
                          └─────────────────────┘                │
                                     │                           │
                                     ▼                           │
                          ┌─────────────────────┐                │
                          │ PersistenceManager  │ (autonome)     │
                          │  - Startup          │                │
                          │  - Schtasks / Cron  │                │
                          └─────────────────────┘                │
                                                                │
                                      ┌─────────────────────────┘
                                      │ (credentials)
                                      ▼
                          ┌─────────────────────┐
                          │ ExfiltrationManager │
                          │  - Compression zlib │◄─────────────┐
                          │  - AES-256-GCM      │              │ (clés)
                          │  - RSA-2048 (pub)   │              │
                          │  - HTTP POST        │              │
                          └─────────────────────┘              │
                                     │                         │
                                     ▼                         │
                          ┌─────────────────────┐              │
                          │  Services Crypto    │──────────────┘
                          │  - AESService       │
                          │  - RSAService       │
                          └─────────────────────┘
```

---

## 📁 Structure du projet

```
NECROSIS/
├── main.py                    # Orchestrateur principal
├── server.py                  # Serveur C2 (Flask)
├── requirements.txt           # Dépendances Python
├── build_exe.py               # Script de compilation PyInstaller
├── generate_keys.py           # Script de génération des clés RSA
├── services/
│   ├── environment_detector.py
│   ├── mutator.py
│   ├── credential_siphon.py
│   ├── pivoting.py
│   ├── persistence.py
│   ├── exfiltration.py
│   ├── aes_service.py
│   └── rsa_service.py
├── utils/
│   └── utils.py
├── keys/
│   ├── private_key.pem        # Clé privée RSA (serveur)
│   └── public_key.pem         # Clé publique RSA (embarquée)
└── received_data/             # Données exfiltrées
```
---
## 🔧 Installation

### 1. Cloner le projet

```bash
git clone https://github.com/your-username/NECROSIS.git
cd NECROSIS
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Générer les clés RSA

```bash
python generate_keys.py
```

Les clés sont générées dans le dossier `keys/` :
- `private_key.pem` → à conserver sur le serveur C2
- `public_key.pem` → à embarquer dans le malware

### 4. Compiler en exécutable (optionnel)

```bash
python build_exe.py
```

L'exécutable sera généré dans `dist/main.exe`.

---

## 🚀 Utilisation

### 1. Démarrer le serveur C2

```bash
python server.py
```

Le serveur écoute sur `http://0.0.0.0:5000/telemetry`.

### 2. Exécuter le malware (mode script)

```bash
python main.py
```

### 3. Exécuter le malware (mode compilé)

```bash
dist/main.exe
```

---

## 📊 Workflow d'exécution

```
DÉMARRAGE
    │
    ▼
PHASE 0 : Détection & Mutation
    │
    ▼
┌───────────────────────────────┐
│ Environnement suspect ?        │
│ ET mutation_count < 3 ?        │
└───────────────────────────────┘
    │                    │
   OUI                  NON
    │                    │
    ▼                    ▼
Mutation + Relance    PHASE 1 : Extraction
    │                    │
    └──────►DÉMARRAGE    │
                        ▼
                PHASE 2 : Pivotement
                        │
                        ▼
                ┌───────────────────┐
                │ Authentification  │
                │ réussie ?         │
                └───────────────────┘
                   │          │
                  OUI        NON
                   │          │
                   ▼          │
              Propagation      │
                   │          │
                   └────┬─────┘
                        ▼
                PHASE 3 : Persistance
                        │
                        ▼
                PHASE 4 : Exfiltration
                        │
                        ▼
                SERVEUR C2
                        │
                        ▼
                       FIN
```

---

## 🧩 Modules détaillés

### EnvironmentDetector
- Analyse CPU/RAM (détection sandbox)
- Recherche processus EDR/AV
- Détection virtualisation (VMware, VBox)
- Détection honeytokens

### CodeMutator
- Mutation AST (renommage variables/fonctions)
- Ajout de code mort
- Injection anti-debug

### CredentialSiphon
- **Windows** : LSASS dump, SAM/System, Chrome cookies, Firefox logins
- **Linux** : /etc/shadow, clés SSH privées
- **Réseau** : Table ARP

### PivotingEngine
- Découverte réseau (net view, ping sweep, ARP)
- Pass-the-Hash (NTLM) avec Impacket
- Propagation SMB

### PersistenceManager
- **Windows** : Startup folder + Schtasks
- **Linux** : Cron @reboot

### ExfiltrationManager
- Chiffrement AES-256-GCM
- Chiffrement RSA-2048 (clé publique)
- Compression zlib + Base64
- Jittering (±30%)
- HTTP POST /telemetry

---

## 🔐 Protocole de chiffrement

```
1. Génération clé AES-256-GCM éphémère
2. Chiffrement des credentials avec AES
3. Chiffrement de la clé AES avec RSA-2048 (clé publique)
4. Compression zlib + encodage Base64
5. Envoi HTTP POST vers le serveur C2
```

### Structure du payload JSON

```json
{
  "machine_id": "UUID",
  "aes_key": "RSA_encrypted_key_b64",
  "encrypted_credentials": "AES_encrypted_data_b64",
  "targets": [
    {"ip": "192.168.1.10", "hostname": "SRV-FILES", "os": "Windows"}
  ],
  "timestamp": "2026-08-18T14:30:00Z",
  "mutation_count": 2
}
```

---

## 🛡️ Détection & Recommandations défensives

### Indicateurs de compromission (IoC)

| Catégorie | Indicateur |
|-----------|------------|
| **Fichiers** | `mutated_*.py`, `lsass_*.dmp`, `SAM.save`, `SYSTEM.save` |
| **Réseau** | HTTP POST vers `/telemetry`, User-Agent alternants |
| **Comportement** | Accès LSASS, `arp -a`, `net view`, `schtasks`, `wmic` |

### Règles de détection

- Surveillance des accès à `lsass.exe` et aux ruches SAM/System
- Détection de commandes réseau (arp, net, ip neigh)
- Corrélation d'événements (dump LSASS + HTTP POST)

### Mesures de hardening

- Principe du moindre privilège
- Application KB2871997 (Pass-the-Hash)
- Segmentation réseau
- AppLocker / SELinux
- Sensibilisation des utilisateurs

---

## 📚 Dépendances

- `cryptography==50.0.0` – Chiffrement AES/RSA
- `psutil==7.2.2` – Télémétrie système
- `flask` – Serveur C2
- `requests` – Requêtes HTTP

---

## 📝 Scripts utilitaires

| Script | Fonction |
|--------|----------|
| `generate_keys.py` | Génère les clés RSA (privée/publique) dans `keys/` |
| `build_exe.py` | Compile le projet en exécutable Windows avec PyInstaller |

---

## 📝 Auteur

**Projet NECROSIS** – Master 2 Sécurité des Réseaux et Systèmes Avancés

---

## ⚠️ Avertissement

Ce projet est développé à des fins **académiques et de recherche** uniquement. Il ne doit pas être utilisé à des fins malveillantes. L'auteur décline toute responsabilité en cas d'utilisation abusive.

---