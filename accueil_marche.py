"""accueil_marche.py - V5 : marchés dépliables (colonne de droite), section pédagogique, FR/EN"""
import html
import xml.etree.ElementTree as ET
from urllib.parse import quote

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf

import questionnaire as qn
from textes import t

import donnees

MODE_DEMO = donnees.mode() != "direct"   # réglage unique : ROBO_DONNEES (voir donnees.py)


# ================================================================ Textes FR / EN
TXT = {
    "fr": {
        "bienvenue": "Bienvenue",
        "sous_titre": "Votre portefeuille sur mesure, en quelques minutes",
        "actus": "ACTUALITÉS", "portefeuille": "MON PORTEFEUILLE", "marches": "MARCHÉS",
        "actus_nd": "Actualités indisponibles.",
        "creez": "Créez votre portefeuille",
        "creez_sous": f"{len(qn.QUESTIONS)} questions, environ 10 minutes.",
        "commencer": "Commencer le questionnaire",
        "branchement": "Ici, on branchera le démarrage du questionnaire.",
        "etapes": [("Montant", "combien souhaitez-vous investir"),
                   ("Questionnaire", "votre profil de risque"),
                   ("Portefeuille", "allocation, simulation, documents")],
        "ensuite": "Ce que vous verrez ici ensuite",
        "valeur": "Valeur", "perf": "Performance", "profil": "Profil de risque",
        "g_alloc": "Graphique d'allocation", "g_evol": "Évolution simulée",
        "indices": "INDICES", "matieres": "MATIÈRES PREMIÈRES", "changes": "CHANGES & CRYPTO",
        "periodes": ["1 mois", "1 an", "5 ans", "20 ans"],
        "lignes": "Principales lignes (poids indicatif)",
        "courbes": "COMPARER LES INDICES", "base100": "Base 100",
        "comprendre": "POUR MIEUX COMPRENDRE",
        "profil_titre": "📈 Votre profil de risque",
        "profil_txt": "Votre profil est la plus petite de 4 notes : tolérance au risque, horizon de placement, "
                      "capacité à subir des pertes et connaissances financières. Plus le profil est élevé, plus la "
                      "part d'actions est importante, et plus les variations peuvent être fortes.",
        "th_profil": ["Profil", "Répartition", "Horizon conseillé", "Risque (SRI)"],
        "profils": ["1 Prudent", "2 Modéré", "3 Équilibré", "4 Dynamique", "5 Offensif"],
        "horizons": ["2 ans et +", "3 ans et +", "5 ans et +", "8 ans et +", "10 ans et +"],
        "sris": ["1 à 2", "2 à 3", "3 à 4", "4 à 5", "5 à 6"],
        "leg": ["Actions", "Obligations", "Monétaire"],
        "indicatif": "Exemples indicatifs. Votre profil sera déterminé par le questionnaire.",
        "bases": [
            ("🏢", "Les actions", "Vous devenez copropriétaire d'une entreprise. Rendement potentiel élevé à long "
             "terme, mais le cours peut baisser fortement. Pas de capital garanti."),
            ("📄", "Les obligations", "Vous prêtez de l'argent à un État ou une entreprise, qui vous verse des "
             "intérêts. En général moins risquées que les actions, mais leur prix varie avec les taux."),
            ("🛡️", "Fonds en euros et monétaire", "Poche de sécurité : faible rendement, faible risque. Le fonds en "
             "euros (assurance-vie) garantit le capital, le monétaire vise la stabilité."),
            ("🧺", "Les ETF", "Fonds coté qui réplique un indice (CAC 40, MSCI World). Un seul achat donne accès à "
             "des centaines d'entreprises, avec des frais réduits."),
            ("🔀", "La diversification", "Ne pas mettre tous ses œufs dans le même panier : répartir entre classes "
             "d'actifs, pays et secteurs pour réduire l'impact d'une mauvaise surprise."),
            ("⚖️", "Risque et rendement", "Un rendement plus élevé s'accompagne toujours d'un risque de perte plus "
             "élevé. Les performances passées ne préjugent pas des performances futures."),
        ],
        "sri_titre": "📏 L'indicateur de risque SRI (de 1 à 7)",
        "sri_txt": "Présent sur les documents réglementaires (DIC), il note le risque d'un produit : "
                   "1 = le moins risqué, 7 = le plus risqué.",
        "env_titre": "🏦 Assurance-vie, PEA ou compte-titres",
        "env_th": ["Enveloppe", "Points forts", "À savoir"],
        "env": [("Assurance-vie", "Fonds en euros, fiscalité avantageuse après 8 ans, transmission",
                 "Frais sur versements et de gestion"),
                ("PEA", "Fiscalité allégée après 5 ans, actions européennes", "Plafond de 150 000 €"),
                ("Compte-titres", "Aucun plafond, tous les supports", "Pas d'avantage fiscal")],
        "verif": "Contenus pédagogiques indicatifs, à vérifier auprès de sources officielles (AMF, Banque de France).",
        "avert": "⚠️ Projet pédagogique : ceci n'est pas un conseil en investissement réel.",
        "notes": {"CAC 40": "Les 40 plus grandes sociétés cotées à Paris.",
                  "S&P 500": "Les 500 plus grandes sociétés américaines.",
                  "Nasdaq": "Valeurs technologiques américaines.",
                  "Nikkei": "225 grandes sociétés cotées à Tokyo.",
                  "DAX": "40 grandes sociétés cotées à Francfort.",
                  "Brent": "Matière première : prix influencé par l'offre, la demande et la géopolitique.",
                  "Or / Gold": "Matière première : évolue avec le dollar, les taux et l'inflation.",
                  "Argent / Silver": "Matière première utilisée en industrie et comme valeur refuge.",
                  "EUR/USD": "Combien de dollars pour 1 euro.",
                  "Bitcoin": "Crypto-actif très volatil, sans valeur sous-jacente."},
        "cats": [("🌍 Monde", "actualité internationale monde"),
                 ("💶 Économie", "économie actualité France"),
                 ("📈 Finance", "bourse marchés financiers"),
                 ("🏛️ Politique", "politique actualité")],
        "rss_lang": "hl=fr&gl=FR&ceid=FR:fr",
    },
    "en": {
        "bienvenue": "Welcome",
        "sous_titre": "Your tailor-made portfolio, in a few minutes",
        "actus": "NEWS", "portefeuille": "MY PORTFOLIO", "marches": "MARKETS",
        "actus_nd": "News unavailable.",
        "creez": "Build your portfolio",
        "creez_sous": f"{len(qn.QUESTIONS)} questions, around 10 minutes.",
        "commencer": "Start the questionnaire",
        "branchement": "The questionnaire will be connected here.",
        "etapes": [("Amount", "how much would you like to invest"),
                   ("Questionnaire", "your risk profile"),
                   ("Portfolio", "allocation, simulation, documents")],
        "ensuite": "What you will see here next",
        "valeur": "Value", "perf": "Performance", "profil": "Risk profile",
        "g_alloc": "Allocation chart", "g_evol": "Simulated growth",
        "indices": "INDICES", "matieres": "COMMODITIES", "changes": "FX & CRYPTO",
        "periodes": ["1 month", "1 year", "5 years", "20 years"],
        "lignes": "Main holdings (indicative weight)",
        "courbes": "COMPARE THE INDICES", "base100": "Base 100",
        "comprendre": "TO UNDERSTAND BETTER",
        "profil_titre": "📈 Your risk profile",
        "profil_txt": "Your profile is the lowest of 4 scores: risk tolerance, investment horizon, capacity to bear "
                      "losses and financial knowledge. The higher the profile, the larger the equity share, and the "
                      "stronger the possible swings.",
        "th_profil": ["Profile", "Allocation", "Suggested horizon", "Risk (SRI)"],
        "profils": ["1 Cautious", "2 Moderate", "3 Balanced", "4 Dynamic", "5 Aggressive"],
        "horizons": ["2 years +", "3 years +", "5 years +", "8 years +", "10 years +"],
        "sris": ["1 to 2", "2 to 3", "3 to 4", "4 to 5", "5 to 6"],
        "leg": ["Equities", "Bonds", "Money market"],
        "indicatif": "Indicative examples. Your profile will be set by the questionnaire.",
        "bases": [
            ("🏢", "Equities", "You become a part-owner of a company. High potential return over the long term, "
             "but the price can fall sharply. Capital is not guaranteed."),
            ("📄", "Bonds", "You lend money to a government or a company, which pays you interest. Usually less "
             "risky than equities, but their price moves with interest rates."),
            ("🛡️", "Euro fund and money market", "Safety bucket: low return, low risk. The euro fund (life "
             "insurance) guarantees the capital; money market funds aim for stability."),
            ("🧺", "ETFs", "A listed fund that tracks an index (CAC 40, MSCI World). One purchase gives access to "
             "hundreds of companies, at low cost."),
            ("🔀", "Diversification", "Do not put all your eggs in one basket: spread across asset classes, "
             "countries and sectors to soften the impact of a bad surprise."),
            ("⚖️", "Risk and return", "A higher return always comes with a higher risk of loss. Past performance "
             "is no guide to future performance."),
        ],
        "sri_titre": "📏 The SRI risk indicator (1 to 7)",
        "sri_txt": "Shown on regulatory documents (KID), it rates a product's risk: 1 = lowest risk, 7 = highest risk.",
        "env_titre": "🏦 Life insurance, PEA or securities account",
        "env_th": ["Wrapper", "Strengths", "Good to know"],
        "env": [("Life insurance", "Euro fund, favourable taxation after 8 years, estate planning",
                 "Entry and management fees"),
                ("PEA", "Reduced taxation after 5 years, European equities", "€150,000 ceiling"),
                ("Securities account", "No ceiling, all products", "No tax advantage")],
        "verif": "Indicative educational content, to be checked against official sources (AMF, Banque de France).",
        "avert": "⚠️ Student project: this is not real investment advice.",
        "notes": {"CAC 40": "The 40 largest companies listed in Paris.",
                  "S&P 500": "The 500 largest US companies.",
                  "Nasdaq": "US technology stocks.",
                  "Nikkei": "225 large companies listed in Tokyo.",
                  "DAX": "40 large companies listed in Frankfurt.",
                  "Brent": "Commodity: price driven by supply, demand and geopolitics.",
                  "Or / Gold": "Commodity: moves with the dollar, interest rates and inflation.",
                  "Argent / Silver": "Commodity used in industry and as a safe haven.",
                  "EUR/USD": "How many dollars for 1 euro.",
                  "Bitcoin": "Very volatile crypto-asset with no underlying value."},
        "cats": [("🌍 World", "world news"),
                 ("💶 Economy", "economy news"),
                 ("📈 Finance", "stock markets finance"),
                 ("🏛️ Politics", "politics news")],
        "rss_lang": "hl=en&gl=US&ceid=US:en",
    },
}

MARCHES = {
    "indices": {"CAC 40": "^FCHI", "S&P 500": "^GSPC", "Nasdaq": "^IXIC",
                "Nikkei": "^N225", "DAX": "^GDAXI"},
    "matieres": {"Brent": "BZ=F", "Or / Gold": "GC=F", "Argent / Silver": "SI=F"},
    "changes": {"EUR/USD": "EURUSD=X", "Bitcoin": "BTC-USD"},
}
# Compositions indicatives (liste fixe, à mettre à jour à la main)
COMPOSITIONS = {
    "CAC 40": [("LVMH", 11), ("Hermès", 8), ("TotalEnergies", 8), ("Schneider Electric", 7),
               ("Sanofi", 6), ("Airbus", 5)],
    "S&P 500": [("Apple", 7), ("Microsoft", 7), ("Nvidia", 7), ("Amazon", 4), ("Alphabet", 4), ("Meta", 3)],
    "Nasdaq": [("Nvidia", 9), ("Microsoft", 8), ("Apple", 8), ("Amazon", 5), ("Broadcom", 4), ("Meta", 4)],
    "Nikkei": [("Fast Retailing", 9), ("Advantest", 6), ("Tokyo Electron", 6), ("SoftBank Group", 5)],
    "DAX": [("SAP", 12), ("Siemens", 9), ("Allianz", 8), ("Deutsche Telekom", 7)],
}
COURBES = {"CAC 40": ("^FCHI", "#1F3A5F"), "S&P 500": ("^GSPC", "#3E7CB1"), "Nasdaq": ("^IXIC", "#D85A30")}
PERIODES_YF = ["1mo", "1y", "5y", "20y"]
PROFILS_TYPES = [(10, 50, 40), (25, 50, 25), (45, 40, 15), (65, 25, 10), (85, 10, 5)]
COULEURS = ["#1F3A5F", "#3E7CB1", "#C9D6E3"]


# ================================================================ Données
PRIX_DEMO = {"^FCHI": 8139.0, "^GSPC": 7376.86, "^IXIC": 24579.43, "^N225": 57434.77,
             "^GDAXI": 25820.36, "BZ=F": 98.32, "GC=F": 4074.9, "SI=F": 51.94,
             "EURUSD=X": 1.114, "BTC-USD": 75844.0}


def _graine(ticker):
    import hashlib
    return int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16)


@st.cache_data(ttl=600)
def cours(ticker):
    if MODE_DEMO:
        var = np.random.default_rng(_graine(ticker)).normal(0, 0.008)
        return PRIX_DEMO.get(ticker, 100.0), float(var)
    try:
        h = yf.Ticker(ticker).history(period="5d")["Close"].dropna()
        return float(h.iloc[-1]), float(h.iloc[-1] / h.iloc[-2] - 1)
    except Exception:
        return None, None


@st.cache_data(ttl=1800)
def serie(ticker, periode):
    if MODE_DEMO:
        n = {"1mo": 22, "1y": 252, "5y": 1260, "20y": 5040}[periode]
        rng = np.random.default_rng(_graine(ticker) + n)
        rendements = rng.normal(0.0003, 0.01, n)
        prix = PRIX_DEMO.get(ticker, 100.0)
        valeurs = prix * np.cumprod(1 + rendements) / np.cumprod(1 + rendements)[-1]
        return pd.Series(valeurs, index=pd.bdate_range(end=pd.Timestamp.today(), periods=n))
    alternatives = {"^GSPC": ["^GSPC", "^SPX", "SPY"]}.get(ticker, [ticker])
    for tk in alternatives:
        try:
            if periode == "20y":
                debut = (pd.Timestamp.today() - pd.DateOffset(years=20)).strftime("%Y-%m-%d")
                h = yf.Ticker(tk).history(start=debut, interval="1wk")["Close"].dropna()
            else:
                h = yf.Ticker(tk).history(period=periode)["Close"].dropna()
            if len(h) > 1:
                return h
        except Exception:
            continue
    return None


@st.cache_data(ttl=900)
def actualites(rss, n=10):
    if MODE_DEMO:
        return [(f"Actualité d'exemple n°{i} (mode démo)", "#") for i in range(1, n + 1)]
    try:
        racine = ET.fromstring(requests.get(rss, timeout=8).content)
        return [(i.findtext("title"), i.findtext("link")) for i in racine.iter("item")][:n]
    except Exception:
        return []


def afficher_accueil(L, aller, resume=None):
    """Affiche la page d'accueil. L = langue (fr/en), aller = fonction de navigation d'app.py."""
    # ================================================================ Style
    st.markdown(
        """
        <style>
          .bandeau {background:#1F3A5F; border-radius:12px; padding:22px 28px; margin-bottom:18px;}
          .bandeau h1 {margin:0; padding:0; font-size:40px; font-weight:700; color:#FFFFFF;}
          .bandeau p {margin:4px 0 0 0; font-size:16px; color:#C9D6E3;}
          .titre-col {font-size:16px; letter-spacing:1.8px; color:#1F3A5F; font-weight:700;
                      text-align:center; margin:0 0 8px 0;}
          .sous-titre {font-size:12px; letter-spacing:1.5px; color:#3E6389; font-weight:700;
                       margin:10px 0 2px 0;}
          .actu {padding:7px 0; border-bottom:1px solid #eef1f5; font-size:14px; line-height:1.35;}
          .actu a {text-decoration:none;}
          .etape {display:flex; gap:10px; align-items:center; margin:8px 0; font-size:15px;}
          .num {width:26px; height:26px; border-radius:50%; background:#E3EEF9; color:#1F3A5F;
                display:flex; align-items:center; justify-content:center; font-weight:600;
                font-size:13px; flex:none;}
          .cmp {display:flex; align-items:center; gap:8px; font-size:12px; margin:3px 0;}
          .cmp .n {width:120px; flex:none;} .cmp .b {height:10px; background:#3E7CB1; border-radius:2px;}
          .note {font-size:12px; color:#6b7785; margin-bottom:4px;}
          table.p {width:100%; border-collapse:collapse; font-size:14px;}
          table.p th {text-align:left; color:#6b7785; font-weight:500; font-size:12px; padding:6px 4px;
                      border-bottom:1px solid #c9d6e3;}
          table.p td {padding:9px 4px; border-bottom:1px solid #eef1f5; vertical-align:middle;}
          .barre {display:flex; height:16px; border-radius:3px; overflow:hidden;}
          .leg {display:flex; gap:16px; justify-content:center; font-size:12px; color:#6b7785; margin-top:8px;}
          .grille {display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:12px;}
          .carte {border:1px solid #e3e8ef; border-radius:12px; padding:14px; background:#fff;}
          .carte b {font-size:15px; color:#1B2A41;}
          .carte p {font-size:13px; color:#6b7785; margin:6px 0 0 0; line-height:1.5;}
          .sri {display:flex; gap:4px; margin-top:8px;}
          .sri div {flex:1; text-align:center; font-size:12px; padding:5px 0; border-radius:4px; color:#1B2A41;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    T = TXT[L]

    # ================================================================ Bandeau
    st.markdown(f'<div class="bandeau"><h1>{T["bienvenue"]}</h1><p>{T["sous_titre"]}</p></div>',
                unsafe_allow_html=True)

    # ================================================================ 3 colonnes
    if MODE_DEMO:
        st.caption("🧪 " + ("Mode démo : actualités et marchés fictifs, aucun appel internet." if L == "fr"
                            else "Demo mode: simulated news and markets, no internet calls."))

    HAUTEUR = 640
    gauche, milieu, droite = st.columns([3, 4, 2.6], gap="medium")

    # ---------- Gauche : actualités
    with gauche:
        st.markdown(f'<div class="titre-col">{T["actus"]}</div>', unsafe_allow_html=True)
        with st.container(border=True, height=HAUTEUR):
            onglets = st.tabs([nom for nom, _ in T["cats"]])
            for onglet, (nom, requete) in zip(onglets, T["cats"]):
                with onglet:
                    url = f"https://news.google.com/rss/search?q={quote(requete)}&{T['rss_lang']}"
                    news = actualites(url, 15)
                    if not news:
                        st.caption(T["actus_nd"])
                    else:
                        st.markdown(
                            "".join(f'<div class="actu"><a href="{html.escape(lien or "#")}" target="_blank">'
                                    f'{html.escape(titre or "")}</a></div>' for titre, lien in news),
                            unsafe_allow_html=True,
                        )

    # ---------- Milieu : portefeuille (première connexion)
    with milieu:
        st.markdown(f'<div class="titre-col">{T["portefeuille"]}</div>', unsafe_allow_html=True)
        with st.container(border=True, height=HAUTEUR):
            if resume:
                fr = L == "fr"
                mt = resume["montant"]
                eur_ = lambda x: f"{x:,.0f} €".replace(",", " ")
                cols = ["#1F3A5F", "#3E7CB1", "#9CC3E6", "#C9D6E3", "#D85A30", "#12873f"]
                n = resume["profil_num"]
                barres = "".join(f"<div style='flex:1;height:6px;border-radius:3px;background:{'#1F3A5F' if i < n else '#d6e4f2'}'></div>" for i in range(5))
                st.markdown(
                    "<div style='background:#EAF2FB;border-radius:8px;padding:12px 14px;margin-bottom:10px'>"
                    f"<div style='display:flex;justify-content:space-between;align-items:baseline'><span style='color:#1F3A5F;font-size:13px'>{'Votre profil' if fr else 'Your profile'}</span>"
                    f"<span style='color:#1F3A5F;font-size:20px;font-weight:600'>{resume['profil_nom']}</span></div>"
                    f"<div style='display:flex;gap:4px;margin-top:8px'>{barres}</div>"
                    f"<div style='color:#1F3A5F;font-size:12px;margin-top:4px'>{'Niveau' if fr else 'Level'} {n} {'sur' if fr else 'of'} 5</div></div>",
                    unsafe_allow_html=True,
                )
                m = st.columns(2)
                m[0].markdown(f"<div style='background:#F4F6F9;border-radius:8px;padding:10px 12px'><div style='font-size:12px;color:#6b7785'>{'Montant investi' if fr else 'Amount invested'}</div><div style='font-size:20px;font-weight:600;color:#1B2A41'>{eur_(mt)}</div></div>", unsafe_allow_html=True)
                m[1].markdown(f"<div style='background:#F4F6F9;border-radius:8px;padding:10px 12px'><div style='font-size:12px;color:#6b7785'>{'Enveloppe' if fr else 'Wrapper'}</div><div style='font-size:14px;font-weight:600;color:#1B2A41;line-height:1.3'>{resume['enveloppe']}</div></div>", unsafe_allow_html=True)
                pj = resume.get("perf_jour")
                if pj is not None:
                    cj = "#12873f" if pj[0] >= 0 else "#c0392b"
                    st.markdown(f"<div style='background:#F4F6F9;border-radius:8px;padding:10px 12px;margin-top:8px;display:flex;justify-content:space-between;align-items:baseline'>"
                                f"<span style='font-size:12px;color:#6b7785'>{'Performance du jour (fictive)' if fr else 'Today (simulated)'}</span>"
                                f"<span style='font-size:18px;font-weight:600;color:{cj}'>{pj[0]:+.2f} % · {pj[1]:+,.0f} €</span></div>".replace(",", " "),
                                unsafe_allow_html=True)
                al = resume["allocation"]
                tot = sum(al.values()) or 1
                seg = "".join(f"<div style='width:{v/tot*100:.1f}%;background:{cols[i % 6]}'></div>" for i, v in enumerate(al.values()))
                lignes = "".join(
                    f"<div style='display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #eef1f5;font-size:13px'>"
                    f"<span><span style='display:inline-block;width:9px;height:9px;border-radius:50%;background:{cols[i % 6]};margin-right:8px'></span>{k}</span>"
                    f"<span>{v:.0f} % · {eur_(v/100*mt)}</span></div>" for i, (k, v) in enumerate(al.items()))
                st.markdown(
                    f"<div style='font-size:13px;color:#6b7785;margin:12px 0 6px'>{'Répartition' if fr else 'Allocation'}</div>"
                    f"<div style='display:flex;height:14px;border-radius:7px;overflow:hidden;margin-bottom:8px'>{seg}</div>{lignes}",
                    unsafe_allow_html=True,
                )
                st.button("Voir le détail du portefeuille" if fr else "See portfolio details", type="primary",
                          width="stretch", on_click=aller, args=("portefeuille",), key="btn_res_pf")
                b1, b2 = st.columns(2)
                b1.button("Projection" if fr else "Projection", width="stretch",
                          on_click=aller, args=("projection",), key="btn_res_sim")
                b2.button("Mes documents" if fr else "My documents", width="stretch",
                          on_click=aller, args=("documents",), key="btn_res_doc")
                st.button("Refaire le questionnaire" if fr else "Redo the questionnaire", type="tertiary",
                          width="stretch", on_click=aller, args=("refaire",), key="btn_res_refaire")
            else:
                st.markdown(
                    "<div style='text-align:center;padding-top:8px'>"
                    "<div style='font-size:34px'>📊</div>"
                    f"<div style='font-size:22px;font-weight:600;color:#1B2A41'>{T['creez']}</div>"
                    f"<div style='color:#6b7785;margin:4px 0 8px'>{T['creez_sous']}</div></div>",
                    unsafe_allow_html=True,
                )
                _, centre, _ = st.columns([1, 2, 1])
                with centre:
                    st.button(T["commencer"], type="primary", width="stretch",
                              on_click=aller, args=("parcours",), key="btn_commencer_accueil")
                st.markdown(
                    "".join(f'<div class="etape"><div class="num">{i}</div>'
                            f'<div><b>{a}</b> : {b}</div></div>' for i, (a, b) in enumerate(T["etapes"], 1)),
                    unsafe_allow_html=True,
                )
                st.divider()
                st.caption(T["ensuite"])
                c = st.columns(3)
                c[0].metric(T["valeur"], "— €")
                c[1].metric(T["perf"], "— %")
                c[2].metric(T["profil"], "—/5")
                g = st.columns(2)
                g[0].container(border=True, height=90).caption(T["g_alloc"])
                g[1].container(border=True, height=90).caption(T["g_evol"])

    # ---------- Droite : marchés dépliables
    with droite:
        st.markdown(f'<div class="titre-col">{T["marches"]}</div>', unsafe_allow_html=True)
        with st.container(border=True, height=HAUTEUR):
            for groupe, valeurs in MARCHES.items():
                st.markdown(f'<div class="sous-titre">{T[groupe]}</div>', unsafe_allow_html=True)
                for nom, ticker in valeurs.items():
                    prix, var = cours(ticker)
                    if prix is None:
                        etiquette = f"**{nom}**   n.d."
                    else:
                        couleur = "green" if var >= 0 else "red"
                        p = f"{prix:,.2f}".replace(",", " ")
                        etiquette = f"**{nom}**   {p}   :{couleur}[{var * 100:+.2f} %]"
                    with st.expander(etiquette):
                        st.markdown(f'<div class="note">{T["notes"].get(nom, "")}</div>',
                                    unsafe_allow_html=True)
                        periode = st.radio("Période", T["periodes"], index=1, horizontal=True,
                                           label_visibility="collapsed", key=f"per_{ticker}_{L}")
                        s = serie(ticker, PERIODES_YF[T["periodes"].index(periode)])
                        if s is None:
                            st.caption("n.d.")
                        else:
                            fig = go.Figure(go.Scatter(x=s.index, y=s.values, mode="lines",
                                                       line=dict(color="#1F3A5F", width=2)))
                            fig.update_layout(height=190, margin=dict(l=0, r=0, t=5, b=0),
                                              showlegend=False, hovermode="x unified")
                            st.plotly_chart(fig, width="stretch", key=f"fig_{ticker}_{L}")
                        compo = COMPOSITIONS.get(nom)
                        if compo:
                            lignes = f'<div class="note" style="margin-top:6px">{T["lignes"]}</div>'
                            lignes += "".join(
                                f'<div class="cmp"><span class="n">{n}</span>'
                                f'<div class="b" style="width:{p * 8}px"></div><span>{p} %</span></div>'
                                for n, p in compo)
                            st.markdown(lignes, unsafe_allow_html=True)

    st.write("")

    # ================================================================ Comparer les indices (pleine largeur)
    st.markdown(f'<div class="titre-col">{T["courbes"]}</div>', unsafe_allow_html=True)
    with st.container(border=True):
        periode = st.radio("Période", T["periodes"], index=1, horizontal=True,
                           label_visibility="collapsed", key=f"periode_comparaison_{L}")
        fig = go.Figure()
        for nom, (ticker, couleur) in COURBES.items():
            s = serie(ticker, PERIODES_YF[T["periodes"].index(periode)])
            if s is None:
                continue
            base = s / s.iloc[0] * 100
            fig.add_trace(go.Scatter(x=base.index, y=base.values, mode="lines",
                                     name=f"{nom} ({base.iloc[-1] - 100:+.1f} %)",
                                     line=dict(color=couleur, width=2)))
        if fig.data:
            fig.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0), yaxis_title=T["base100"],
                              hovermode="x unified",
                              legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"))
            st.plotly_chart(fig, width="stretch", key=f"fig_comparaison_{L}")
        else:
            st.caption("n.d.")

    st.write("")

    # ================================================================ Pour mieux comprendre (affiché directement)
    st.markdown(f'<div class="titre-col">{T["comprendre"]}</div>', unsafe_allow_html=True)

    # --- Profil de risque + tableau des portefeuilles types
    with st.container(border=True):
        st.markdown(f"#### {T['profil_titre']}")
        st.write(T["profil_txt"])
        lignes = "".join(
            f'<tr><td><b>{nom}</b></td><td style="width:40%"><div class="barre">'
            + "".join(f'<div style="width:{p}%;background:{c}"></div>' for p, c in zip(rep, COULEURS))
            + f"</div></td><td>{hor}</td><td>{sri}</td></tr>"
            for nom, rep, hor, sri in zip(T["profils"], PROFILS_TYPES, T["horizons"], T["sris"])
        )
        entetes = "".join(f"<th>{h}</th>" for h in T["th_profil"])
        legende = "".join(f'<span><span style="color:{c}">■</span> {n}</span>'
                          for c, n in zip(COULEURS, T["leg"]))
        st.markdown(f'<table class="p"><tr>{entetes}</tr>{lignes}</table><div class="leg">{legende}</div>',
                    unsafe_allow_html=True)
        st.caption(T["indicatif"])

    st.write("")

    # --- Les bases pour un débutant
    cartes = "".join(f'<div class="carte"><b>{ic} {titre}</b><p>{txt}</p></div>'
                     for ic, titre, txt in T["bases"])
    st.markdown(f'<div class="grille">{cartes}</div>', unsafe_allow_html=True)

    st.write("")

    # --- Échelle SRI
    couleurs_sri = ["#D5ECDD", "#D5ECDD", "#FBEBC4", "#FBEBC4", "#FBEBC4", "#F6CDD1", "#F6CDD1"]
    echelle = "".join(f'<div style="background:{c}">{i}</div>' for i, c in enumerate(couleurs_sri, 1))
    st.markdown(
        f'<div class="carte"><b>{T["sri_titre"]}</b><p>{T["sri_txt"]}</p><div class="sri">{echelle}</div></div>',
        unsafe_allow_html=True,
    )

    st.write("")

    # --- Enveloppes
    entetes = "".join(f"<th>{h}</th>" for h in T["env_th"])
    lignes = "".join(f"<tr><td><b>{a}</b></td><td>{b}</td><td>{c}</td></tr>" for a, b, c in T["env"])
    st.markdown(
        f'<div class="carte"><b>{T["env_titre"]}</b><table class="p"><tr>{entetes}</tr>{lignes}</table></div>',
        unsafe_allow_html=True,
    )

    st.caption(T["verif"])
    st.caption(T["avert"])


if __name__ == "__main__":
    st.set_page_config(page_title="Robo-advisor", page_icon="📈", layout="wide")
    _langue = st.sidebar.radio("Langue / Language", ["fr", "en"], horizontal=True)
    afficher_accueil(_langue, lambda n: None)
