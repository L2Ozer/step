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

- `universites` : Liste des universités
  - `id` : UUID
  - `nom` : Nom de l'université
  - `created_at` : Date de création

- `ue` : Unités d'enseignement
  - `id` : UUID
  - `numero` : Numéro de l'UE
  - `nom` : Nom de l'UE
  - `universite_id` : Référence vers l'université
  - `created_at` : Date de création

- `qcm` : QCMs
  - `id` : UUID
  - `ue_id` : Référence vers l'UE
  - `type` : Type de QCM (QCM, Correction, Colle, etc.)
  - `titre` : Titre du QCM
  - `session` : Numéro de session
  - `annee_academique` : Année académique
  - `date_examen` : Date de l'examen
  - `created_at` : Date de création

- `questions` : Questions des QCMs
  - `id` : UUID
  - `qcm_id` : Référence vers le QCM
  - `numero` : Numéro de la question
  - `texte` : Texte de la question
  - `explication` : Explication de la réponse
  - `created_at` : Date de création

- `options` : Options de réponse
  - `id` : UUID
  - `question_id` : Référence vers la question
  - `lettre` : Lettre de l'option (A, B, C, etc.)
  - `texte` : Texte de l'option
  - `est_correcte` : Booléen indiquant si c'est la bonne réponse
  - `created_at` : Date de création

- `images` : Images associées aux questions
  - `id` : UUID
  - `question_id` : Référence vers la question
  - `url` : URL de l'image dans le stockage Supabase
  - `alt` : Texte alternatif
  - `created_at` : Date de création

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