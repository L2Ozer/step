# QCM Médical Extractor

Ce projet est un système d'extraction automatisé de QCM médicaux depuis des fichiers PDF vers une base de données Supabase.

## Fonctionnalités

- Extraction de texte à partir de PDF médicaux via OCR (Mistral OCR)
- Analyse intelligente du contenu pour identifier :
  - Les métadonnées du document (UE, type de document, année, etc.)
  - Les questions individuelles
  - Les propositions de réponse pour chaque question
  - Les réponses correctes
- Sauvegarde automatique dans une base de données Supabase
- Correction automatique des problèmes d'OCR (en particulier pour les questions 16-18)
- Détection et prévention des doublons

## Prérequis

- Python 3.9+
- Clé API Mistral
- Compte Supabase avec URL et clé API

## Installation

1. Cloner le dépôt :
```
git clone https://github.com/votre-username/qcm-extractor.git
cd qcm-extractor
```

2. Créer un environnement virtuel et installer les dépendances :
```
python -m venv venv
source venv/bin/activate  # sous Unix/MacOS
# ou
venv\Scripts\activate  # sous Windows
pip install -r requirements.txt
```

3. Configurer les variables d'environnement (créer un fichier `.env` à la racine du projet) :
```
MISTRAL_API_KEY=votre_cle_api_mistral
SUPABASE_URL=votre_url_supabase
SUPABASE_KEY=votre_cle_api_supabase
```

## Utilisation

### Extraction d'un PDF de QCM

```python
from qcm_extraction.extractor import QCMExtractor

# Initialiser l'extracteur
extractor = QCMExtractor()

# Extraire les métadonnées d'un PDF
pdf_url = "https://chemin-vers-votre-pdf.pdf"
metadata = extractor.extract_metadata_from_path(pdf_url)

# Les questions et propositions sont automatiquement extraites et sauvegardées dans Supabase
```

### Scripts utilitaires

- `test_extraction.py` : Test d'extraction sur un PDF spécifique
- `auto_fix_ocr.py` : Correction manuelle des problèmes d'OCR pour les questions 16-18
- `fix_duplicate_qcms.py` : Outil pour gérer les doublons dans la base de données

## Structure de la base de données

- **qcm** : Stocke les métadonnées des QCM
- **questions** : Contient les questions individuelles liées à un QCM
- **reponses** : Contient les propositions pour chaque question

## Caractéristiques techniques

- Utilisation de l'API OCR de Mistral pour l'extraction de texte
- Utilisation de modèles de langage pour l'analyse de contenu
- Mécanismes de retry pour gérer les erreurs d'API
- Stratégies d'extraction multi-passes pour maximiser la qualité
- Détection automatique des pages de mauvaise qualité OCR
- Remplacement intelligent du contenu pour les sections problématiques

## Contributeurs

- [Votre nom]

## Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails. 