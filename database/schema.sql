-- QCM Medical Extraction System - Database Schema
-- ================================================
-- Script de création des tables pour Supabase/PostgreSQL

-- Création de la table des universités
CREATE TABLE IF NOT EXISTS universites (
    id SERIAL PRIMARY KEY,
    numero INTEGER,
    nom TEXT NOT NULL,
    ville TEXT
);

-- Création de la table des unités d'enseignement (UE)
CREATE TABLE IF NOT EXISTS ue (
    id SERIAL PRIMARY KEY,
    numero TEXT NOT NULL,
    date_examen TIMESTAMP,
    universite_id INTEGER REFERENCES universites(id)
);

-- Création de la table des QCM
CREATE TABLE IF NOT EXISTS qcm (
    id SERIAL PRIMARY KEY,
    ue_id INTEGER REFERENCES ue(id),
    date_examen TIMESTAMP,
    type TEXT NOT NULL,
    annee TEXT NOT NULL,
    uuid UUID DEFAULT gen_random_uuid() UNIQUE
);

-- Création de la table des questions
CREATE TABLE IF NOT EXISTS questions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    qcm_id INTEGER REFERENCES qcm(id),
    numero INTEGER NOT NULL,
    uuid UUID DEFAULT gen_random_uuid() UNIQUE,
    contenu JSONB NOT NULL
);

-- Création de la table des réponses/propositions
CREATE TABLE IF NOT EXISTS reponses (
    id SERIAL PRIMARY KEY,
    question_id UUID REFERENCES questions(id),
    lettre CHAR(1) NOT NULL,
    est_correcte BOOLEAN DEFAULT FALSE,
    latex TEXT,
    uuid UUID DEFAULT gen_random_uuid() UNIQUE,
    contenu JSONB NOT NULL,
    UNIQUE(question_id, lettre)
);

-- Création de la table des corrections
CREATE TABLE IF NOT EXISTS corrections (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    latex TEXT,
    uuid UUID DEFAULT gen_random_uuid() UNIQUE,
    contenu JSONB,
    reponse_uuid UUID REFERENCES reponses(uuid)
);

-- Création de la table des images
CREATE TABLE IF NOT EXISTS images (
    id SERIAL PRIMARY KEY,
    type_contenu TEXT,
    image_url TEXT,
    contenu_id UUID,
    uuid UUID DEFAULT gen_random_uuid() UNIQUE
);

-- Création de la table des tables (pour documents structurés)
CREATE TABLE IF NOT EXISTS tables (
    id SERIAL PRIMARY KEY,
    contenu JSONB,
    type_contenu TEXT,
    contenu_id UUID
);

-- Index pour optimiser les performances
CREATE INDEX IF NOT EXISTS idx_qcm_type_annee ON qcm(type, annee);
CREATE INDEX IF NOT EXISTS idx_questions_qcm_id ON questions(qcm_id);
CREATE INDEX IF NOT EXISTS idx_questions_numero ON questions(numero);
CREATE INDEX IF NOT EXISTS idx_reponses_question_id ON reponses(question_id);
CREATE INDEX IF NOT EXISTS idx_reponses_lettre ON reponses(lettre);
CREATE INDEX IF NOT EXISTS idx_reponses_correcte ON reponses(est_correcte);

-- Contraintes additionnelles
ALTER TABLE qcm ADD CONSTRAINT unique_qcm_type_annee_ue UNIQUE(type, annee, ue_id);
ALTER TABLE questions ADD CONSTRAINT unique_question_numero_qcm UNIQUE(numero, qcm_id);

-- Données d'exemple pour les universités
INSERT INTO universites (numero, nom, ville) VALUES 
(1, 'Université de Nancy', 'Nancy'),
(2, 'Université de Strasbourg', 'Strasbourg'),
(3, 'Université de Reims', 'Reims')
ON CONFLICT DO NOTHING;

-- Données d'exemple pour les UE
INSERT INTO ue (numero, universite_id) VALUES 
('UE1', 1),
('UE2', 1),
('UE3', 1),
('UE4', 1),
('UE5', 1),
('UE6', 1),
('UE7', 1)
ON CONFLICT DO NOTHING;

-- Commentaires sur les tables
COMMENT ON TABLE qcm IS 'Table principale contenant les métadonnées des QCM médicaux';
COMMENT ON TABLE questions IS 'Questions extraites des QCM avec contenu JSON';
COMMENT ON TABLE reponses IS 'Propositions de réponses A, B, C, D, E pour chaque question';
COMMENT ON TABLE corrections IS 'Corrections et explications associées aux réponses';

-- Fonctions utilitaires
CREATE OR REPLACE FUNCTION count_correct_answers(qcm_id_param INTEGER)
RETURNS TABLE(
    question_numero INTEGER,
    correct_count INTEGER,
    total_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        q.numero as question_numero,
        COUNT(r.id) FILTER (WHERE r.est_correcte = true)::INTEGER as correct_count,
        COUNT(r.id)::INTEGER as total_count
    FROM questions q
    LEFT JOIN reponses r ON q.id = r.question_id
    WHERE q.qcm_id = qcm_id_param
    GROUP BY q.numero
    ORDER BY q.numero;
END;
$$ LANGUAGE plpgsql;

-- Vue pour avoir un aperçu rapide des QCM
CREATE OR REPLACE VIEW qcm_summary AS
SELECT 
    q.id,
    q.type,
    q.annee,
    ue.numero as ue_numero,
    COUNT(DISTINCT quest.id) as questions_count,
    COUNT(r.id) as propositions_count,
    COUNT(r.id) FILTER (WHERE r.est_correcte = true) as correct_answers_count,
    ROUND(
        (COUNT(r.id) FILTER (WHERE r.est_correcte = true) * 100.0 / NULLIF(COUNT(r.id), 0)), 
        1
    ) as correct_percentage
FROM qcm q
LEFT JOIN ue ON q.ue_id = ue.id
LEFT JOIN questions quest ON q.id = quest.qcm_id
LEFT JOIN reponses r ON quest.id = r.question_id
GROUP BY q.id, q.type, q.annee, ue.numero
ORDER BY q.id; 