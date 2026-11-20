"""
textes.py — Tous les textes du site en français et en anglais (Damien)

Utilisation : t("cle", langue) ou t("cle", langue, nom="Prudent") pour les textes à trous.
Les libellés des questions sont dans questionnaire.py.
"""

TEXTES = {
    "fr": {
        "titre": "Robo-advisor patrimonial",
        "avertissement": "Projet pédagogique de M2 Banque-Finance : ceci n'est pas un conseil en investissement réel. Aucun argent n'est investi.",
        "langue": "Langue",
        "etapes": ["Accueil", "Montant", "Questionnaire", "Profil", "", "Portefeuille", "Simulation", "Explication"],
        "continuer": "Continuer",
        "retour": "Retour",
        "commencer": "Commencer",
        "montant_q": "Quel montant souhaitez-vous investir (en euros) ?",
        "montant_bas": "Ce service est réservé aux montants d'au moins 100 000 €. Pour un montant inférieur, "
                       "un livret réglementé ou un contrat d'assurance-vie classique est plus adapté.",
        "montant_haut": "Au-delà de 1 000 000 €, votre situation mérite un accompagnement personnalisé : "
                        "nous vous orientons vers un banquier privé.",
        "valider_reponses": "Valider mes réponses",
        "profil_titre": "Votre profil : {nom} ({num}/5)",
        "profil_regle": "Votre profil est la plus petite de vos 4 notes : c'est la règle prudente appliquée par les banques.",
        "notes": {"tolerance": "Tolérance au risque", "horizon": "Horizon", "capacite": "Capacité à subir des pertes",
                  "connaissances": "Connaissances"},
        "note": "Note (sur 5)",
        "plafonds": "Ce qui limite votre profil",
        "alertes": "Points d'attention",
        "enveloppe_titre": "Enveloppe recommandée : {env}",
        "ajuster": "Personnaliser (±10 points, dans les limites de votre profil)",
        "delta_actions": "Actions (points)",
        "delta_oblig": "Obligations (points)",
        "ajust_monetaire": "La poche monétaire / fonds en euros compense automatiquement.",
        "ajust_refuse": "Ajustement refusé : {raison}",
        "vol_depassee": "Ajustement refusé : la volatilité ({vol}) dépasserait le maximum de votre profil ({max}). "
                        "Le portefeuille de référence est conservé.",
        "indicateurs": "Indicateurs (historique)",
        "perf_1a": "Performance 1 an", "perf_3a": "Performance 3 ans", "volatilite": "Volatilité",
        "drawdown": "Perte maximale", "sharpe": "Sharpe", "ter": "Frais moyens", "sri_estime": "SRI estimé",
        "nd": "n.d.",
        "source_prix": "Source des cours : {src}",
        "colonnes": {"nom": "Nom", "isin": "ISIN", "poids": "Poids", "montant": "Montant", "classe": "Classe",
                     "description": "Description", "perf_1a": "Perf. 1 an", "perf_3a": "Perf. 3 ans", "sri": "SRI",
                     "sfdr": "SFDR", "ter": "Frais", "enveloppe": "Enveloppe", "source": "Source"},
        "classes": {"actions": "Actions", "obligations": "Obligations", "monetaire": "Monétaire et fonds euros",
                    "diversifiants": "Diversifiants", "scpi": "SCPI", "actif": "Fonds actifs"},
        "avertissements": "Limites des données",
        "var": "VaR 95 % (1 jour)",
        "simulation_titre": "Évolution possible de votre capital",
        "horizon_sim": "Horizon de simulation (années)",
        "favorable": "Favorable (90 %)", "central": "Central (50 %)", "defavorable": "Défavorable (10 %)",
        "ref_6040": "Portefeuille 60/40 (médiane)", "verse": "Capital versé",
        "proba": "Probabilité d'atteindre {cible}",
        "pas_cible": "Pas d'objectif chiffré : indiquez un montant cible dans le questionnaire pour obtenir une probabilité.",
        "hypotheses": "Hypothèses de la simulation",
        "hyp_texte": "Rendement attendu net de frais : {mu} ; volatilité : {vol} ; {n} trajectoires. "
                     "Source : {src}. Corrélations : {corr}.",
        "ter_trad": "Frais d'une gestion traditionnelle (% par an) — valeur de démonstration, à sourcer (TODO)",
        "explication_titre": "Pourquoi ce portefeuille ?",
        "telech_excel": "Télécharger le fichier Excel",
        "telech_pdf": "Télécharger la déclaration d'adéquation (PDF)",
        "pdf_titre": "Déclaration d'adéquation",
        "pdf_sections": ["1. Votre situation et vos objectifs", "2. Votre profil de risque", "3. Enveloppe et portefeuille",
                         "4. Risques", "5. Frais", "6. Adéquation"],
        "pdf_adequation": "Au vu de vos réponses, le portefeuille proposé correspond à votre profil {nom} : "
                          "sa part d'actions et sa volatilité restent dans les limites fixées pour ce profil, et "
                          "l'enveloppe {env} est cohérente avec votre objectif et votre horizon.",
        "pdf_adequation_nd": "Au vu de vos réponses, la part d'actions du portefeuille proposé respecte la grille de votre "
                             "profil {nom} et l'enveloppe {env} est cohérente avec votre objectif et votre horizon. "
                             "La volatilité historique n'a pas pu être vérifiée (cours indisponibles).",
        "pdf_adequation_hors": "Attention : la volatilité historique du portefeuille ({vol}) dépasse le maximum fixé pour "
                               "le profil {nom} ({max}). Le portefeuille doit être revu avant toute recommandation.",
        "pdf_risques": "Perte en capital possible sur toutes les lignes sauf le fonds en euros. Les performances passées "
                       "ne préjugent pas des performances futures. Les simulations reposent sur des hypothèses publiées "
                       "et ne constituent pas une garantie.",
        "genere_le": "Document généré le {date}",
    },
    "en": {
        "titre": "Wealth robo-advisor",
        "avertissement": "Master's degree student project (Banking & Finance): this is not real investment advice. No money is invested.",
        "langue": "Language",
        "etapes": ["Welcome", "Amount", "Questionnaire", "Profile", "", "Portfolio", "Simulation", "Explanation"],
        "continuer": "Continue",
        "retour": "Back",
        "commencer": "Start",
        "montant_q": "How much would you like to invest (in euros)?",
        "montant_bas": "This service is for amounts of at least €100,000. For smaller amounts, a regulated savings "
                       "account or a standard life insurance policy is more suitable.",
        "montant_haut": "Above €1,000,000, your situation deserves tailored advice: we refer you to a private banker.",
        "valider_reponses": "Submit my answers",
        "profil_titre": "Your profile: {nom} ({num}/5)",
        "profil_regle": "Your profile is the lowest of your 4 scores: the prudent rule used by banks.",
        "notes": {"tolerance": "Risk tolerance", "horizon": "Horizon", "capacite": "Capacity to bear losses",
                  "connaissances": "Knowledge"},
        "note": "Score (out of 5)",
        "plafonds": "What limits your profile",
        "alertes": "Points of attention",
        "enveloppe_titre": "Recommended wrapper: {env}",
        "ajuster": "Customise (±10 points, within your profile's limits)",
        "delta_actions": "Equities (points)",
        "delta_oblig": "Bonds (points)",
        "ajust_monetaire": "The money market / euro fund bucket adjusts automatically.",
        "ajust_refuse": "Adjustment refused: {raison}",
        "vol_depassee": "Adjustment refused: volatility ({vol}) would exceed your profile's maximum ({max}). "
                        "The reference portfolio is kept.",
        "indicateurs": "Indicators (historical)",
        "perf_1a": "1-year return", "perf_3a": "3-year return", "volatilite": "Volatility",
        "drawdown": "Maximum drawdown", "sharpe": "Sharpe", "ter": "Average fees", "sri_estime": "Estimated SRI",
        "nd": "n/a",
        "source_prix": "Price source: {src}",
        "colonnes": {"nom": "Name", "isin": "ISIN", "poids": "Weight", "montant": "Amount", "classe": "Class",
                     "description": "Description", "perf_1a": "1Y return", "perf_3a": "3Y return", "sri": "SRI",
                     "sfdr": "SFDR", "ter": "Fees", "enveloppe": "Wrapper", "source": "Source"},
        "classes": {"actions": "Equities", "obligations": "Bonds", "monetaire": "Money market & euro fund",
                    "diversifiants": "Diversifiers", "scpi": "SCPI", "actif": "Active funds"},
        "avertissements": "Data limitations",
        "var": "95% VaR (1 day)",
        "simulation_titre": "How your capital could evolve",
        "horizon_sim": "Simulation horizon (years)",
        "favorable": "Favourable (90%)", "central": "Central (50%)", "defavorable": "Unfavourable (10%)",
        "ref_6040": "60/40 portfolio (median)", "verse": "Capital contributed",
        "proba": "Probability of reaching {cible}",
        "pas_cible": "No target amount: enter one in the questionnaire to get a probability.",
        "hypotheses": "Simulation assumptions",
        "hyp_texte": "Expected return net of fees: {mu}; volatility: {vol}; {n} paths. Source: {src}. Correlations: {corr}.",
        "ter_trad": "Fees of traditional management (% p.a.) — demo value, source needed (TODO)",
        "explication_titre": "Why this portfolio?",
        "telech_excel": "Download the Excel file",
        "telech_pdf": "Download the suitability statement (PDF)",
        "pdf_titre": "Suitability statement",
        "pdf_sections": ["1. Your situation and goals", "2. Your risk profile", "3. Wrapper and portfolio",
                         "4. Risks", "5. Fees", "6. Suitability"],
        "pdf_adequation": "Given your answers, the proposed portfolio matches your {nom} profile: its equity share "
                          "and volatility stay within the limits set for this profile, and the {env} wrapper is "
                          "consistent with your goal and horizon.",
        "pdf_adequation_nd": "Given your answers, the proposed portfolio's equity share follows the grid of your {nom} "
                             "profile and the {env} wrapper is consistent with your goal and horizon. Historical "
                             "volatility could not be checked (prices unavailable).",
        "pdf_adequation_hors": "Warning: the portfolio's historical volatility ({vol}) exceeds the maximum set for the {nom} "
                               "profile ({max}). The portfolio must be reviewed before any recommendation.",
        "pdf_risques": "Capital loss is possible on every line except the euro fund. Past performance is no guide to "
                       "future performance. Simulations rely on published assumptions and are not a guarantee.",
        "genere_le": "Document generated on {date}",
    },
}

NOMS_ENVELOPPES = {
    "fr": {"assurance-vie": "Assurance-vie", "PEA": "PEA (+ compte-titres en complément)", "CTO": "Compte-titres"},
    "en": {"assurance-vie": "Life insurance", "PEA": "PEA (+ securities account)", "CTO": "Securities account"},
}


def t(cle: str, langue: str = "fr", **valeurs):
    """Renvoie le texte `cle` dans la langue demandée (français par défaut)."""
    texte = TEXTES.get(langue, TEXTES["fr"]).get(cle, TEXTES["fr"].get(cle, cle))
    return texte.format(**valeurs) if valeurs and isinstance(texte, str) else texte
