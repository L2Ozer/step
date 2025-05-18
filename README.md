# Extracteur de QCM

Ce projet permet d'extraire automatiquement les questions et les propositions de réponses à partir de fichiers PDF de QCM, puis de les sauvegarder dans une base de données Supabase.

## Fonctionnalités

- Téléchargement de PDF à partir d'une URL
- Extraction des métadonnées (UE, type, année, etc.)
- Extraction des questions et de leur numéro
- Extraction des propositions de réponses (A, B, C, D, E)
- Sauvegarde dans Supabase

## Prérequis

- Python 3.8+
- Compte Supabase
- Compte Mistral AI (pour l'API)

## Installation

1. Cloner le dépôt
```bash
git clone [URL_DU_DEPOT]
cd [NOM_DU_PROJET]
```

2. Installer les dépendances
```bash
pip install -r requirements.txt
```

3. Configurer les variables d'environnement
```bash
# Créer un fichier .env avec les variables suivantes
MISTRAL_API_KEY=votre_clé_api_mistral
SUPABASE_URL=votre_url_supabase
SUPABASE_KEY=votre_clé_supabase
```

## Utilisation

```bash
python -m qcm_extraction.main "URL_DU_PDF"
```

## Structure du projet

- `qcm_extraction/`: Module principal
  - `main.py`: Point d'entrée
  - `extractor.py`: Logique d'extraction
  - `models.py`: Modèles de données

## Structure de la base de données

Le projet utilise une base de données Supabase avec les tables suivantes :

- `images` : Images associées aux contenus
  - `id` : int4
  - `type_contenu` : text
  - `image_url` : text
  - `contenu_id` : uuid
  - `uuid` : uuid

- `tables` : Tables dans le document
  - `id` : int4
  - `contenu` : jsonb
  - `type_contenu` : text
  - `contenu_id` : uuid

- `corrections` : Corrections associées aux réponses
  - `id` : int4
  - `created_at` : timestamp
  - `latex` : text
  - `uuid` : uuid
  - `contenu` : jsonb
  - `reponse_uuid` : uuid

- `reponses` : Propositions de réponses pour les questions
  - `id` : int4
  - `lettre` : bpchar
  - `est_correcte` : bool
  - `question_id` : uuid
  - `latex` : text
  - `uuid` : uuid
  - `contenu` : jsonb

- `questions` : Questions des QCMs
  - `qcm_id` : int4
  - `numero` : int4
  - `id` : uuid
  - `uuid` : uuid
  - `contenu` : jsonb

- `qcm` : QCMs
  - `id` : int4
  - `ue_id` : int4
  - `date_examen` : timestamp
  - `type` : text
  - `annee` : text
  - `uuid` : uuid

- `ue` : Unités d'enseignement
  - `id` : int4
  - `numero` : text
  - `date_examen` : timestamp
  - `universite_id` : int4

- `universites` : Universités
  - `id` : int4
  - `numero` : int4
  - `nom` : text
  - `ville` : text

## Développement

Pour contribuer au projet :

1. Créer une branche pour votre fonctionnalité
2. Développer et tester votre code
3. Soumettre une pull request

## Tests

Pour lancer les tests :
```bash
python -m pytest qcm_extraction/tests/
```

## Licence

MIT 