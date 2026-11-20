"""
telecharger_prix.py — Télécharge les cours de l'univers et crée data/prix_snapshot.csv (Aly)

À lancer sur votre ordinateur (le serveur de démo peut être bloqué par Yahoo) :
    python3 telecharger_prix.py              # télécharge et écrit le snapshot
    python3 telecharger_prix.py --maj-univers   # écrit aussi les tickers trouvés dans univers.csv

Étapes :
1. lit data/univers.csv ;
2. pour chaque ligne cotée sans ticker (TODO), cherche le ticker Yahoo à partir de l'ISIN ;
3. télécharge les cours ajustés depuis 2005 ;
4. écrit data/prix_snapshot.csv (une colonne par ticker) et affiche un bilan.
Pensez ensuite à pousser data/prix_snapshot.csv sur GitHub : c'est la copie de secours du site.
"""

import sys
from pathlib import Path

import pandas as pd
import yfinance as yf

DOSSIER = Path(__file__).resolve().parent
UNIVERS = DOSSIER / "data" / "univers.csv"
TITRES = DOSSIER / "data" / "univers_titres.csv"
SNAPSHOT = DOSSIER / "data" / "prix_snapshot.csv"
DEBUT = "2005-01-01"


def chercher_ticker(isin: str) -> str | None:
    """Cherche sur Yahoo un ticker correspondant à l'ISIN (privilégie les cotations en euros)."""
    try:
        resultats = yf.Search(isin, max_results=8).quotes
    except Exception as e:
        print(f"  recherche impossible pour {isin} : {e}")
        return None
    if not resultats:
        return None
    preferes = [q for q in resultats if str(q.get("symbol", "")).endswith((".PA", ".DE", ".AS", ".F", ".MI"))]
    return (preferes or resultats)[0].get("symbol")


def main(maj_univers: bool = False) -> None:
    u = pd.read_csv(UNIVERS, dtype=str, keep_default_na=False)
    cotees = u[u["taux_annuel"] == ""]        # fonds euros et SCPI n'ont pas de cours
    tickers = {}
    for _, l in cotees.iterrows():
        t = l["ticker_yahoo"]
        if t in ("", "TODO"):
            print(f"Recherche du ticker de {l['nom']} ({l['isin']})…")
            t = chercher_ticker(l["isin"])
            print(f"  -> {t or 'introuvable'}")
            if t and maj_univers:
                u.loc[u["isin"] == l["isin"], "ticker_yahoo"] = t
        if t:
            tickers[l["isin"]] = t

    # Actions en direct (univers_titres.csv) : les obligations n'ont pas de cours
    if TITRES.exists():
        t2 = pd.read_csv(TITRES, dtype=str, keep_default_na=False)
        for _, l in t2[(t2["taux_annuel"] == "") & (t2["ticker_yahoo"] != "")].iterrows():
            tickers[l["isin"]] = l["ticker_yahoo"]
    tickers["_sans_risque"] = "XEON.DE"          # ETF €STR : taux sans risque du ratio de Sharpe

    print(f"\nTéléchargement de {len(tickers)} séries depuis {DEBUT}…")
    data = yf.download(sorted(set(tickers.values())), start=DEBUT, auto_adjust=True,
                       progress=True, group_by="column", threads=True)
    close = data["Close"] if isinstance(data.columns, pd.MultiIndex) else data[["Close"]]
    close.index = pd.to_datetime(close.index).tz_localize(None)
    close = close.dropna(how="all").sort_index()

    print("\nBilan :")
    for isin, t in tickers.items():
        s = close[t].dropna() if t in close.columns else pd.Series(dtype=float)
        etat = f"{len(s):5d} jours depuis {s.index[0].date()}" if len(s) else "AUCUNE DONNÉE"
        print(f"  {t:12s} {etat}")
    close.round(6).to_csv(SNAPSHOT)
    print(f"\nÉcrit : {SNAPSHOT} ({close.shape[0]} dates × {close.shape[1]} séries)")
    if maj_univers:
        u.to_csv(UNIVERS, index=False)
        print(f"univers.csv mis à jour avec les tickers trouvés : relisez-le avant de le pousser.")


if __name__ == "__main__":
    main(maj_univers="--maj-univers" in sys.argv)
