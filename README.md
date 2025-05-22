# Extracteur de QCM

Ce projet permet d'extraire automatiquement les questions et les propositions de réponses à partir de fichiers PDF de QCM, puis de les sauvegarder dans une base de données Supabase.

## Fonctionnalités

- Téléchargement de PDF à partir d'une URL
- Extraction des métadonnées (UE, type, année, etc.)
- Extraction des questions et de leur numéro
- Extraction des propositions de réponses (A, B, C, D, E)
- Sauvegarde dans Supabase
- Traitement spécifique pour les sections problématiques
- Récupération manuelle des propositions manquantes

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
  - `database.py`: Interactions avec Supabase

## Améliorations récentes

### Version 1.2.0
- Amélioration des prompts pour l'extraction des propositions
- Ajout d'un traitement spécifique pour les sections/questions problématiques (1, 33)
- Optimisation de la détection des sections de page
- Mécanisme de récupération amélioré pour les questions sans propositions
- Statistiques sur la taille des sections pour détecter les anomalies

### Version 1.1.0
- Correction de la regex pour la détection des en-têtes de page
- Correction de la confusion entre "uuid" et "id" lors de l'insertion des propositions
- Ajout d'une seconde tentative avec prompt simplifié pour les sections sans propositions
- Ajout de logs supplémentaires pour faciliter le débogage

## Mises à jour récentes

### 2023-03-30: Adaptation au schéma de la base de données

- Correction de la méthode `save_to_supabase` pour utiliser correctement le schéma réel de la base
- Suppression du champ "titre" qui n'existe pas dans la table "qcm"
- Ajout du champ "uuid" pour les tables concernées
- Conversion des données pour le champ "contenu" de type jsonb dans les tables "questions" et "reponses"
- Correction de la détection des doublons en utilisant les champs type et année

Ces modifications permettent de résoudre l'erreur précédente liée à l'utilisation d'une colonne "metadata" qui n'existe pas dans la structure de la base de données.

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

## Résolution des problèmes courants

### Propositions manquantes
Si certaines propositions ne sont pas extraites correctement :
1. Vérifiez les logs pour identifier les sections problématiques
2. Examinez le contenu des sections problématiques dans le PDF original
3. Utilisez l'option de récupération manuelle pour les questions spécifiques

### Rate limits de l'API
Si vous rencontrez des erreurs de rate limit :
1. Augmentez les délais entre les appels API
2. Réduisez le nombre de sections traitées en une fois
3. Utilisez une clé API avec des limites plus élevées

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