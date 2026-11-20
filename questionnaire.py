"""
questionnaire.py — Les questions du robo-advisor (Peter)

33 questions en 5 blocs. Chaque question est un dictionnaire :
    id        : clé utilisée dans le dictionnaire `reponses`
    bloc      : A (situation), B (objectifs), C (connaissances), D (tolérance), E (préférences)
    type      : "nombre", "choix", "oui_non", "vrai_faux", "multi"
    fr / en   : libellé de la question
    options   : liste de (valeur, libellé FR, libellé EN, points) pour les questions à choix
    bonne     : bonne réponse (questions vrai/faux du quiz)

Les points des questions du bloc D (1 à 5) servent à calculer la note de tolérance.
Les questions vrai/faux du bloc C donnent le score du quiz (0 à 5).
"""

BLOCS = {
    "A": {"fr": "Votre situation", "en": "Your situation"},
    "B": {"fr": "Vos objectifs", "en": "Your goals"},
    "C": {"fr": "Vos connaissances", "en": "Your knowledge"},
    "D": {"fr": "Votre rapport au risque", "en": "Your attitude to risk"},
    "E": {"fr": "Vos préférences", "en": "Your preferences"},
}

QUESTIONS = [
    # ----------------------------------------------------------------- Bloc A
    {"id": "age", "bloc": "A", "type": "nombre", "min": 18, "max": 100, "defaut": 18,
     "fr": "Quel est votre âge ?", "en": "How old are you?"},
    {"id": "situation_familiale", "bloc": "A", "type": "choix",
     "fr": "Votre situation familiale ?", "en": "Your family situation?",
     "options": [("celibataire", "Célibataire", "Single", 0),
                 ("couple", "En couple / marié(e) / pacsé(e)", "In a couple / married", 0),
                 ("couple_enfants", "En couple avec enfant(s)", "Couple with child(ren)", 0),
                 ("seul_enfants", "Seul(e) avec enfant(s)", "Single parent", 0)]},
    {"id": "revenus", "bloc": "A", "type": "choix",
     "fr": "Vos revenus nets annuels du foyer ?", "en": "Your household's annual net income?",
     "options": [("<50k", "Moins de 50 000 €", "Under €50,000", 0),
                 ("50-100k", "50 000 à 100 000 €", "€50,000 to €100,000", 0),
                 ("100-200k", "100 000 à 200 000 €", "€100,000 to €200,000", 0),
                 (">200k", "Plus de 200 000 €", "Over €200,000", 0)]},
    {"id": "patrimoine", "bloc": "A", "type": "nombre", "min": 0, "max": 100_000_000, "defaut": 0, "pas": 10_000,
     "fr": "Montant total de votre patrimoine (immobilier compris), en euros ?",
     "en": "Total value of your wealth (including real estate), in euros?"},
    {"id": "epargne_precaution", "bloc": "A", "type": "oui_non",
     "fr": "Disposez-vous d'une épargne de précaution (au moins 3 à 6 mois de dépenses) en dehors de ce placement ?",
     "en": "Do you hold an emergency fund (at least 3 to 6 months of expenses) outside this investment?"},
    {"id": "credits", "bloc": "A", "type": "oui_non",
     "fr": "Avez-vous des crédits en cours (immobilier, consommation) ?",
     "en": "Do you have outstanding loans (mortgage, consumer credit)?"},
    {"id": "taux_effort", "bloc": "A", "type": "choix",
     "fr": "Quelle part de vos revenus est absorbée par vos remboursements de crédits ?",
     "en": "What share of your income goes to loan repayments?",
     "options": [("0", "Aucun crédit en cours", "No loans", 5),
                 ("<20", "Moins de 20 %", "Under 20%", 5),
                 ("20-35", "De 20 à 35 %", "20% to 35%", 4),
                 (">35", "Plus de 35 %", "Over 35%", 3)]},
    {"id": "statut_pro", "bloc": "A", "type": "choix",
     "fr": "Votre situation professionnelle ?", "en": "Your employment status?",
     "options": [("salarie_cdi", "Salarié(e) en CDI / fonctionnaire", "Permanent employee / civil servant", 5),
                 ("cdd", "Salarié(e) en CDD / intérim", "Fixed-term / temp employee", 4),
                 ("independant", "Indépendant(e) / chef d'entreprise / profession libérale", "Self-employed / business owner", 4),
                 ("retraite", "Retraité(e)", "Retired", 4),
                 ("sans_emploi", "Sans emploi / étudiant(e)", "Unemployed / student", 3)]},
    {"id": "stabilite_revenus", "bloc": "A", "type": "choix",
     "fr": "Vos revenus des prochaines années vous semblent-ils stables ?",
     "en": "Do you expect your income to stay stable in the coming years?",
     "options": [("stables", "Oui, stables ou en hausse", "Yes, stable or rising", 5),
                 ("variables", "Variables d'une année à l'autre", "Variable from year to year", 4),
                 ("baisse", "Probablement en baisse", "Likely to fall", 3)]},
    # ----------------------------------------------------------------- Bloc B
    {"id": "objectif", "bloc": "B", "type": "choix",
     "fr": "Quel est votre objectif principal ?", "en": "What is your main goal?",
     "options": [("retraite", "Préparer ma retraite", "Prepare for retirement", 0),
                 ("immobilier", "Financer un achat immobilier", "Fund a property purchase", 0),
                 ("valorisation", "Faire fructifier mon capital", "Grow my capital", 0),
                 ("revenus", "Obtenir des revenus complémentaires", "Generate extra income", 0),
                 ("transmission", "Transmettre un capital", "Pass on wealth", 0)]},
    {"id": "horizon", "bloc": "B", "type": "choix",
     "fr": "Dans combien de temps pensez-vous avoir besoin de cet argent ?",
     "en": "When do you expect to need this money?",
     "options": [("<2", "Moins de 2 ans", "Under 2 years", 1),
                 ("2-5", "2 à 5 ans", "2 to 5 years", 3),
                 ("5-8", "5 à 8 ans", "5 to 8 years", 4),
                 (">8", "Plus de 8 ans", "More than 8 years", 5)]},
    {"id": "priorite", "bloc": "B", "type": "choix",
     "fr": "Entre sécurité et performance, quelle est votre priorité ?",
     "en": "Between safety and performance, what is your priority?",
     "options": [("securite", "Protéger mon capital avant tout", "Protect my capital above all", 1),
                 ("prudent", "Plutôt la sécurité, avec un peu de performance", "Mostly safety, with some performance", 2),
                 ("equilibre", "Un équilibre entre les deux", "A balance of both", 3),
                 ("performance", "Plutôt la performance, en acceptant les à-coups", "Mostly performance, accepting swings", 4),
                 ("max", "La performance maximale à long terme", "Maximum long-term performance", 5)]},
    {"id": "rendement_attendu", "bloc": "B", "type": "choix",
     "fr": "Quel rendement annuel moyen espérez-vous ?",
     "en": "What average annual return do you hope for?",
     "options": [("2-3", "2 à 3 % par an", "2% to 3% a year", 1),
                 ("4-5", "4 à 5 % par an", "4% to 5% a year", 2),
                 ("6-8", "6 à 8 % par an", "6% to 8% a year", 4),
                 (">8", "Plus de 8 % par an", "Over 8% a year", 5)]},
    {"id": "versement_mensuel", "bloc": "B", "type": "nombre", "min": 0, "max": 50_000, "defaut": 1_000, "pas": 100,
     "fr": "Versements mensuels prévus (en euros, 0 si aucun) ?",
     "en": "Planned monthly contributions (in euros, 0 if none)?"},
    {"id": "cible", "bloc": "B", "type": "nombre", "min": 0, "max": 100_000_000, "defaut": 0, "pas": 10_000,
     "fr": "Montant que vous aimeriez atteindre à l'horizon (en euros, 0 si pas d'objectif chiffré) ?",
     "en": "Amount you would like to reach at the horizon (in euros, 0 if no specific target)?"},
    {"id": "besoin_liquidite", "bloc": "B", "type": "oui_non",
     "fr": "Pourriez-vous avoir besoin de retirer une partie de cet argent avant l'horizon ?",
     "en": "Might you need to withdraw part of this money before the horizon?"},
    # ----------------------------------------------------------------- Bloc C
    {"id": "quiz_etf", "bloc": "C", "type": "vrai_faux", "bonne": True,
     "fr": "Vrai ou faux : un ETF cherche à reproduire la performance d'un indice, comme le MSCI World.",
     "en": "True or false: an ETF aims to replicate the performance of an index, such as the MSCI World."},
    {"id": "quiz_taux", "bloc": "C", "type": "vrai_faux", "bonne": False,
     "fr": "Vrai ou faux : quand les taux d'intérêt montent, le prix des obligations existantes monte aussi.",
     "en": "True or false: when interest rates rise, the price of existing bonds rises too."},
    {"id": "quiz_diversification", "bloc": "C", "type": "vrai_faux", "bonne": True,
     "fr": "Vrai ou faux : répartir son argent entre plusieurs actifs permet de réduire le risque global.",
     "en": "True or false: spreading money across several assets reduces overall risk."},
    {"id": "quiz_perte", "bloc": "C", "type": "vrai_faux", "bonne": True,
     "fr": "Vrai ou faux : un placement en actions peut perdre une partie du capital investi.",
     "en": "True or false: an equity investment can lose part of the capital invested."},
    {"id": "quiz_fonds_euros", "bloc": "C", "type": "vrai_faux", "bonne": True,
     "fr": "Vrai ou faux : en assurance-vie, le capital placé sur le fonds en euros est garanti par l'assureur.",
     "en": "True or false: in life insurance, capital in the euro fund is guaranteed by the insurer."},
    {"id": "anciennete", "bloc": "C", "type": "choix",
     "fr": "Depuis combien de temps investissez-vous sur les marchés financiers ?",
     "en": "How long have you been investing in financial markets?",
     "options": [("jamais", "Jamais, c'est ma première fois", "Never, this is my first time", 3),
                 ("<2", "Moins de 2 ans", "Under 2 years", 3),
                 ("2-5", "2 à 5 ans", "2 to 5 years", 4),
                 (">5", "Plus de 5 ans", "Over 5 years", 5)]},
    {"id": "frequence", "bloc": "C", "type": "choix",
     "fr": "À quelle fréquence passez-vous des ordres (achat / vente) ?",
     "en": "How often do you place orders (buy / sell)?",
     "options": [("jamais", "Jamais", "Never", 3),
                 ("rare", "Moins d'une fois par an", "Less than once a year", 3),
                 ("annuel", "Quelques fois par an", "A few times a year", 4),
                 ("mensuel", "Au moins une fois par mois", "At least once a month", 5)]},
    {"id": "niveau", "bloc": "C", "type": "choix",
     "fr": "Comment jugez-vous votre niveau de connaissance de la finance ?",
     "en": "How would you rate your financial knowledge?",
     "options": [("debutant", "Débutant", "Beginner", 3),
                 ("intermediaire", "Intermédiaire", "Intermediate", 4),
                 ("confirme", "Confirmé", "Advanced", 5)]},
    {"id": "produits_detenus", "bloc": "C", "type": "multi",
     "fr": "Quels produits détenez-vous ou avez-vous déjà détenus ?",
     "en": "Which products do you hold or have you held?",
     "options": [("livrets", "Livrets d'épargne", "Savings accounts", 0),
                 ("assurance_vie", "Assurance-vie", "Life insurance", 0),
                 ("actions", "Actions", "Shares", 0),
                 ("etf", "ETF", "ETFs", 0),
                 ("obligations", "Obligations", "Bonds", 0),
                 ("scpi", "SCPI", "SCPI (real estate funds)", 0)]},
    # ----------------------------------------------------------------- Bloc D
    {"id": "reaction_baisse", "bloc": "D", "type": "choix",
     "fr": "Votre portefeuille perd 20 % en quelques mois. Que faites-vous ?",
     "en": "Your portfolio loses 20% in a few months. What do you do?",
     "options": [("tout_vendre", "Je vends tout", "I sell everything", 1),
                 ("vendre_partie", "Je vends une partie", "I sell part of it", 2),
                 ("attendre", "J'attends que ça remonte", "I wait for a recovery", 3),
                 ("rien", "Je ne change rien, c'est normal", "I change nothing, it's normal", 4),
                 ("renforcer", "J'en profite pour investir plus", "I invest more", 5)]},
    {"id": "perte_max", "bloc": "D", "type": "choix",
     "fr": "Quelle perte maximale sur un an pourriez-vous accepter ?",
     "en": "What maximum loss over one year could you accept?",
     "options": [("0", "Aucune perte", "No loss", 1),
                 ("5", "Jusqu'à -5 %", "Up to -5%", 2),
                 ("10", "Jusqu'à -10 %", "Up to -10%", 3),
                 ("20", "Jusqu'à -20 %", "Up to -20%", 4),
                 ("30", "Plus de -20 %", "More than -20%", 5)]},
    {"id": "choix_portefeuille", "bloc": "D", "type": "choix",
     "fr": "Sur un an, quel portefeuille préférez-vous ? (fourchettes indicatives de gain / perte)",
     "en": "Over one year, which portfolio do you prefer? (indicative gain / loss ranges)",
     "options": [("A", "A : entre -2 % et +4 %", "A: between -2% and +4%", 1),
                 ("B", "B : entre -8 % et +10 %", "B: between -8% and +10%", 2),
                 ("C", "C : entre -15 % et +18 %", "C: between -15% and +18%", 4),
                 ("D", "D : entre -25 % et +30 %", "D: between -25% and +30%", 5)]},
    {"id": "tirage", "bloc": "D", "type": "choix",
     "fr": "Vous avez le choix entre 5 000 € garantis, ou une chance sur deux de gagner 12 000 € (sinon 0 €). Que choisissez-vous ?",
     "en": "You can take €5,000 for sure, or a 50% chance of winning €12,000 (otherwise €0). Which do you choose?",
     "options": [("certain", "Les 5 000 € garantis", "The guaranteed €5,000", 1),
                 ("indecis", "Je suis indécis(e), plutôt les 5 000 €", "Undecided, leaning to €5,000", 2),
                 ("risque", "Le pari à 12 000 €", "The €12,000 gamble", 4)]},
    {"id": "gain_perte", "bloc": "D", "type": "choix",
     "fr": "Pour vous, une perte de 10 % pèse...",
     "en": "For you, a 10% loss weighs...",
     "options": [("beaucoup", "Bien plus qu'un gain de 10 %", "Much more than a 10% gain", 1),
                 ("un_peu", "Un peu plus qu'un gain de 10 %", "A bit more than a 10% gain", 3),
                 ("pareil", "Autant qu'un gain de 10 %", "The same as a 10% gain", 4),
                 ("moins", "Moins qu'un gain de 10 %, je regarde le long terme", "Less than a 10% gain, I look long term", 5)]},
    {"id": "suivi", "bloc": "D", "type": "choix",
     "fr": "À quelle fréquence aimeriez-vous suivre la valeur de votre portefeuille ?",
     "en": "How often would you like to check your portfolio value?",
     "options": [("quotidien", "Tous les jours, les variations m'inquiètent", "Daily, swings worry me", 2),
                 ("mensuel", "Une fois par mois", "Once a month", 3),
                 ("trimestre", "Une fois par trimestre", "Once a quarter", 4),
                 ("annuel", "Une fois par an, je suis serein(e)", "Once a year, I am relaxed", 5)]},
    # ----------------------------------------------------------------- Bloc E
    {"id": "durabilite", "bloc": "E", "type": "choix",
     "fr": "Quelle place pour la durabilité dans vos placements ?",
     "en": "How important is sustainability in your investments?",
     "options": [("aucune", "Aucune préférence", "No preference", 0),
                 ("exclusions", "Exclure certains secteurs", "Exclude some sectors", 0),
                 ("article 8", "Fonds promouvant des critères ESG (article 8)", "Funds promoting ESG (Article 8)", 0),
                 ("article 9", "Fonds à objectif durable (article 9)", "Funds with a sustainable objective (Article 9)", 0)]},
    {"id": "enveloppe_souhaitee", "bloc": "E", "type": "choix",
     "fr": "Avez-vous une préférence pour l'enveloppe d'investissement ?",
     "en": "Do you prefer a particular investment wrapper?",
     "options": [("auto", "Non, conseillez-moi", "No, advise me", 0),
                 ("assurance-vie", "Assurance-vie", "Life insurance", 0),
                 ("PEA", "PEA", "PEA (equity savings plan)", 0),
                 ("CTO", "Compte-titres", "Securities account", 0)]},
    {"id": "zone", "bloc": "E", "type": "choix",
     "fr": "Quelle zone géographique privilégier pour les actions ?",
     "en": "Which geographic area should equities favour?",
     "options": [("Monde", "Monde", "World", 0),
                 ("Europe", "Europe", "Europe", 0),
                 ("France", "France", "France", 0)]},
    {"id": "exclusions", "bloc": "E", "type": "multi",
     "fr": "Secteurs que vous souhaitez exclure ?", "en": "Sectors you wish to exclude?",
     "options": [("armement", "Armement", "Weapons", 0),
                 ("tabac", "Tabac", "Tobacco", 0),
                 ("fossiles", "Énergies fossiles", "Fossil fuels", 0),
                 ("alcool", "Alcool", "Alcohol", 0),
                 ("aerien", "Transport aérien", "Aviation", 0),
                 ("nucleaire", "Nucléaire", "Nuclear", 0)]},
]

QUIZ = [q["id"] for q in QUESTIONS if q["type"] == "vrai_faux"]
TOLERANCE = ["reaction_baisse", "perte_max", "choix_portefeuille", "tirage", "gain_perte", "suivi", "priorite"]
EXPERIENCE = ["anciennete", "frequence", "niveau"]
OPTIONNELLES = {"enveloppe_souhaitee": "auto"}   # valeur par défaut si la question est absente


def question(id_question: str) -> dict:
    """Renvoie la question dont l'identifiant est donné."""
    for q in QUESTIONS:
        if q["id"] == id_question:
            return q
    raise KeyError(id_question)


def points(id_question: str, valeur) -> int:
    """Points associés à une réponse à choix."""
    for v, *_ , pts in question(id_question)["options"]:
        if v == valeur:
            return pts
    raise ValueError(f"Réponse inconnue {valeur!r} à la question {id_question}")


def points_ou_none(id_question: str, valeur):
    """Comme points() mais renvoie None si la réponse est absente ou inconnue (jamais d'exception)."""
    try:
        return points(id_question, valeur)
    except (ValueError, KeyError, TypeError):
        return None


def libelle(id_question: str, valeur, langue: str = "fr") -> str:
    """Libellé lisible d'une réponse (pour le PDF et l'Excel)."""
    q = question(id_question)
    if q["type"] == "oui_non":
        return {True: "Oui" if langue == "fr" else "Yes", False: "Non" if langue == "fr" else "No"}.get(valeur, str(valeur))
    if q["type"] == "vrai_faux":
        return {True: "Vrai" if langue == "fr" else "True", False: "Faux" if langue == "fr" else "False"}.get(valeur, str(valeur))
    if q["type"] in ("choix", "multi"):
        idx = 1 if langue == "fr" else 2
        table = {o[0]: o[idx] for o in q["options"]}
        if isinstance(valeur, (list, tuple)):
            return ", ".join(table.get(v, str(v)) for v in valeur) or "—"
        return table.get(valeur, str(valeur))
    return f"{valeur:,.0f}".replace(",", " ") if isinstance(valeur, (int, float)) else str(valeur)


def score_quiz(reponses: dict) -> int:
    """Nombre de bonnes réponses au quiz (0 à 5)."""
    return sum(1 for qid in QUIZ if reponses.get(qid) == question(qid)["bonne"])
