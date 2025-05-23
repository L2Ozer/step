# Changelog

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Versioning Sémantique](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2024-01-XX - Version GitHub Release

### 🚀 Nouvelles Fonctionnalités
- **Système de déduplication strict** : Zéro doublon garantis
- **Extraction des réponses correctes automatisée** : Phase 3 intégrée
- **Précision mathématique** : Exactement N × 5 propositions pour N questions
- **Scripts de diagnostic avancés** : fix_correct_answers_v2.py, clean_and_test_strict.py
- **Support multi-méthodes** : API + Regex + Récupération ciblée
- **Architecture scalable** : Support de tous formats QCM médicaux

### ✨ Améliorations
- **Performance optimisée** : 2.5+ propositions/seconde
- **Robustesse accrue** : Multiples fallbacks pour extraction
- **Validation temps réel** : Vérification de complétude pendant l'extraction
- **Gestion d'erreurs avancée** : Retry automatique avec backoff
- **Documentation complète** : README professionnel, setup automatisé

### 🎯 Métriques de Performance
- Questions extraites : 30/30 (100%)
- Propositions extraites : 150/150 (100%) 
- Réponses correctes : 65/150 (43.3%)
- Questions avec réponses : 29/30 (96.7%)
- Déduplication : 0 doublon (Parfait)

## [1.5.0] - 2024-01-XX - Correction des Réponses Correctes

### 🔧 Corrections Majeures
- **Résolution du bug des réponses FALSE** : Toutes les réponses n'étaient pas identifiées
- **Intégration de extract_correct_answers** : Automatisation dans le flux principal
- **Recherche améliorée des fichiers Markdown** : Support sans qcm_db_id
- **Méthodes de fallback renforcées** : Récupération par métadonnées

### 📊 Résultats
- Avant correction : 0/150 réponses correctes (0%)
- Après correction : 65/150 réponses correctes (43.3%)
- Questions avec réponses identifiées : 29/30 (96.7%)

## [1.4.0] - 2024-01-XX - Optimisation des Questions Manquantes

### 🔍 Corrections Critiques
- **Question 9 récupérée** : Était présente mais non extraite
- **Question 26 récupérée** : Problème de format résolu
- **Patterns regex améliorés** : Support de tous formats de questions
- **Extraction multi-méthodes** : API principal + fallbacks regex

### 🛠️ Outils de Diagnostic
- `diagnostic_pdf.py` : Analyse des extractions ratées
- `find_question_9.py` : Recherche ciblée des questions manquantes
- Scripts de récupération spécialisés

## [1.3.0] - 2024-01-XX - Déduplication et Validation

### ⚡ Fonctionnalités Clés
- **Système de déduplication avancé** : Détection et suppression des doublons
- **Validation mathématique stricte** : N questions = N×5 propositions exactes
- **Vérification d'existence** : Check avant insertion en base
- **Clés uniques renforcées** : (question_id, lettre) unique

### 📈 Amélioration des Performances
- Élimination des 160 doublons détectés initialement
- Passage de 310 → 150 propositions (précision parfaite)
- Optimisation des requêtes base de données

## [1.2.0] - 2024-01-XX - Extraction Robuste

### 🚀 Améliorations Majeures
- **Extraction par chunks avec overlap** : Gestion des gros documents
- **Prompts optimisés pour Mistral** : Meilleure compréhension du contexte
- **Gestion du rate limiting** : Retry automatique avec délais adaptatifs
- **Traitement spécialisé des pages problématiques** : Page 7 et sections corrompues

### 🔧 Corrections
- Résolution des erreurs de timeout API
- Amélioration de la détection des propositions A-E
- Gestion des formats de questions non-standard

## [1.1.0] - 2024-01-XX - Intégration Supabase

### 🗄️ Base de Données
- **Intégration Supabase complète** : Tables QCM, Questions, Réponses
- **Schéma relationnel optimisé** : Relations 1-N avec contraintes
- **Types de données JSON** : Stockage flexible du contenu
- **UUIDs et contraintes uniques** : Intégrité des données

### 📝 Structure des Tables
- `qcm` : Métadonnées des QCMs
- `questions` : Questions avec contenu JSONB
- `reponses` : Propositions A-E avec statut correct/incorrect
- `ue` : Unités d'Enseignement de référence

## [1.0.0] - 2024-01-XX - Version Initiale

### 🎉 Première Version
- **Extraction PDF vers Markdown** : OCR avec Mistral AI
- **Détection des questions** : Patterns regex basiques
- **Extraction des propositions** : Support A, B, C, D, E
- **API Mistral intégrée** : Traitement intelligent du texte

### 🏗️ Architecture de Base
- Module `extractor.py` principal
- Gestion des fichiers temporaires
- Configuration par variables d'environnement
- Logs et debugging basiques

---

## Légende des Types de Changements

- 🚀 **Nouvelles Fonctionnalités** : Ajout de nouvelles capacités
- ✨ **Améliorations** : Optimisation de fonctionnalités existantes  
- 🔧 **Corrections** : Résolution de bugs
- 🔍 **Corrections Critiques** : Bugs majeurs impactant les résultats
- ⚡ **Fonctionnalités Clés** : Améliorations importantes
- 🗄️ **Base de Données** : Modifications du schéma ou des données
- 🛠️ **Outils** : Scripts et utilitaires de développement
- 📊 **Métriques** : Mesures de performance et qualité
- 🎯 **Résultats** : Impacts mesurables des changements 