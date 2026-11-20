"""
dossiers.py — Dossiers clients et piste d'audit (espace conseiller)

Chaque recommandation validée par un client crée un dossier JSON dans data/dossiers/ :
identifiant pseudonyme, date, réponses, profil, portefeuille, contrôles de conformité, journal des événements.
Aucun nom ni coordonnée n'est demandé au client (minimisation des données, esprit RGPD).

Limite de la démo : sur Streamlit Community Cloud, le disque est effacé quand l'application redémarre.
En production, ces dossiers iraient dans une base de données.
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent / "data" / "dossiers"
STATUTS = ["à valider", "validé", "à revoir", "archivé"]


def _chemin(identifiant: str) -> Path:
    if not identifiant.replace("-", "").isalnum():
        raise ValueError("Identifiant invalide")
    return DOSSIER / f"{identifiant}.json"


def _maintenant() -> str:
    return datetime.now().isoformat(timespec="seconds")


def nouvel_identifiant() -> str:
    return f"RA-{datetime.now():%Y%m%d}-{secrets.token_hex(2).upper()}"


def enregistrer(donnees: dict, identifiant: str | None = None, auteur: str = "client") -> str:
    """Crée ou met à jour un dossier. Renvoie son identifiant."""
    DOSSIER.mkdir(parents=True, exist_ok=True)
    identifiant = identifiant or nouvel_identifiant()
    ancien = charger(identifiant) if _chemin(identifiant).exists() else None
    journal = (ancien or {}).get("journal", [])
    journal.append({"date": _maintenant(), "auteur": auteur,
                    "evenement": "Dossier mis à jour" if ancien else "Recommandation émise"})
    dossier = {**(ancien or {}), **donnees, "id": identifiant, "maj": _maintenant(), "journal": journal}
    dossier.setdefault("cree_le", _maintenant())
    dossier.setdefault("statut", "à valider")
    _chemin(identifiant).write_text(json.dumps(dossier, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return identifiant


def charger(identifiant: str) -> dict | None:
    p = _chemin(identifiant)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def lister() -> list[dict]:
    """Tous les dossiers, du plus récent au plus ancien."""
    if not DOSSIER.exists():
        return []
    res = []
    for p in DOSSIER.glob("RA-*.json"):
        d = charger(p.stem)
        if d:
            res.append(d)
    return sorted(res, key=lambda d: d.get("maj", ""), reverse=True)


def evenement(identifiant: str, texte: str, auteur: str = "conseiller", statut: str | None = None) -> None:
    """Ajoute une ligne au journal (et change le statut si demandé)."""
    d = charger(identifiant)
    if d is None:
        raise KeyError(identifiant)
    if statut:
        if statut not in STATUTS:
            raise ValueError(statut)
        d["statut"] = statut
        texte = f"{texte} — statut : {statut}" if texte else f"Statut : {statut}"
    d.setdefault("journal", []).append({"date": _maintenant(), "auteur": auteur, "evenement": texte})
    d["maj"] = _maintenant()
    _chemin(identifiant).write_text(json.dumps(d, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


def supprimer(identifiant: str) -> None:
    p = _chemin(identifiant)
    if p.exists():
        p.unlink()
