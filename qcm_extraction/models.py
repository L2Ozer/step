from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

class Universite(BaseModel):
    id: str = Field(default=None)
    nom: str
    created_at: datetime = Field(default_factory=datetime.now)

class UE(BaseModel):
    id: str = Field(default=None)
    numero: str
    nom: str
    universite_id: str
    created_at: datetime = Field(default_factory=datetime.now)

class QCM(BaseModel):
    id: str = Field(default=None)
    ue_id: str
    type: str = Field(default="QCM")
    titre: str
    session: Optional[str] = None
    annee_academique: Optional[str] = None
    date_examen: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)

class Option(BaseModel):
    id: str = Field(default=None)
    question_id: str
    lettre: str
    texte: str
    est_correcte: bool = False
    created_at: datetime = Field(default_factory=datetime.now)

class Question(BaseModel):
    id: str = Field(default=None)
    qcm_id: str
    numero: int
    texte: str
    explication: Optional[str] = None
    options: List[Option] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)

class Image(BaseModel):
    id: str = Field(default=None)
    question_id: str
    url: str
    alt: str = "Image de la question"
    created_at: datetime = Field(default_factory=datetime.now) 