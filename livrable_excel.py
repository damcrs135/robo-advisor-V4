"""
livrable_excel.py — Fichier Excel remis au client

    generer_excel(dossier, dossier_sortie=None) -> chemin du fichier .xlsx

Cinq onglets mis en forme (aucune macro) : Synthèse, Portefeuille, Performances, Simulation, Justification.
Les libellés suivent la langue du dossier (fr / en). Les graphiques sont de vrais graphiques Excel.
"""

from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import LineChart, PieChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.formatting.rule import DataBarRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.table import Table, TableStyleInfo

import regles
from textes import NOMS_ENVELOPPES, t

BLEU, BLEU_CLAIR, GRIS, VERT, ROUGE = "1F3A5F", "EAF2FB", "F4F6F9", "12873F", "C0392B"
FMT_PCT, FMT_PCT2, FMT_EUR = "0.0%", "0.00%", '#,##0 "€"'
FINE = Side(style="thin", color="D9DEE5")
BORD = Border(bottom=FINE)

LIB = {
    "fr": {"synthese": "Synthèse", "portefeuille": "Portefeuille", "perfs": "Performances", "simulation": "Simulation",
           "justif": "Justification", "titre": "Votre portefeuille", "sous": "Synthèse de votre dossier",
           "date": "Date", "montant": "Montant investi", "versement": "Versement mensuel", "horizon": "Horizon de simulation",
           "annees": "ans", "objectif": "Objectif chiffré", "profil": "Profil de risque", "env": "Enveloppe",
           "frais": "Frais annuels moyens", "vol": "Volatilité historique", "def": "Scénario défavorable (10 %)",
           "cen": "Scénario central (50 %)", "fav": "Scénario favorable (90 %)", "proba": "Probabilité d'atteindre l'objectif",
           "cap_final": "Capital après {n} ans", "expl": "Explication", "cols": ["Ligne", "Identifiant", "Classe", "Poids", "Montant",
           "Frais", "Risque (SRI)", "Enveloppe", "Détail"], "total": "Total", "indic": "Indicateurs historiques",
           "p1": "Performance 1 an", "p3": "Performance 3 ans", "p5": "Performance 5 ans", "vola": "Volatilité annualisée",
           "dd": "Perte maximale", "sharpe": "Ratio de Sharpe", "var": "Perte journalière dépassée 1 jour sur 20 (VaR 95 %)",
           "sri": "Indicateur de risque estimé (1 à 7)", "src": "Source des cours", "depuis": "Historique depuis",
           "alloc": "Allocation par classe", "classe": "Classe", "poids": "Poids", "annee": "Année",
           "colsim": ["Année", "Défavorable (10 %)", "Central (50 %)", "Favorable (90 %)", "Portefeuille 60/40", "Capital versé"],
           "evol": "Évolution possible du capital", "hyp": "Hypothèses de la simulation", "source": "Source",
           "corr": "Corrélations", "pourquoi": "Pourquoi ces choix ?", "avert": "Projet pédagogique de M2 Banque-Finance : ceci n'est pas un conseil en investissement réel. Les performances passées ne préjugent pas des performances futures.",
           "nd": "n.d.", "classes_nom": "classes"},
    "en": {"synthese": "Summary", "portefeuille": "Portfolio", "perfs": "Performance", "simulation": "Simulation",
           "justif": "Rationale", "titre": "Your portfolio", "sous": "Summary of your file",
           "date": "Date", "montant": "Amount invested", "versement": "Monthly contribution", "horizon": "Simulation horizon",
           "annees": "years", "objectif": "Target amount", "profil": "Risk profile", "env": "Wrapper",
           "frais": "Average annual fees", "vol": "Historical volatility", "def": "Unfavourable scenario (10%)",
           "cen": "Central scenario (50%)", "fav": "Favourable scenario (90%)", "proba": "Probability of reaching the target",
           "cap_final": "Capital after {n} years", "expl": "Explanation", "cols": ["Holding", "Identifier", "Class", "Weight", "Amount",
           "Fees", "Risk (SRI)", "Wrapper", "Details"], "total": "Total", "indic": "Historical indicators",
           "p1": "1-year return", "p3": "3-year return", "p5": "5-year return", "vola": "Annualised volatility",
           "dd": "Maximum drawdown", "sharpe": "Sharpe ratio", "var": "Daily loss exceeded 1 day in 20 (95% VaR)",
           "sri": "Estimated risk indicator (1 to 7)", "src": "Price source", "depuis": "History since",
           "alloc": "Allocation by class", "classe": "Class", "poids": "Weight", "annee": "Year",
           "colsim": ["Year", "Unfavourable (10%)", "Central (50%)", "Favourable (90%)", "60/40 portfolio", "Capital contributed"],
           "evol": "How your capital could evolve", "hyp": "Simulation assumptions", "source": "Source",
           "corr": "Correlations", "pourquoi": "Why these choices?", "avert": "Master's student project (Banking & Finance): this is not real investment advice. Past performance is no guide to future performance.",
           "nd": "n/a", "classes_nom": "classes"},
}


def _titre(ws, texte, sous, largeur_cols):
    """Bandeau bleu en haut de l'onglet."""
    ws.sheet_view.showGridLines = False
    for r in (1, 2):
        for c in range(1, largeur_cols + 1):
            ws.cell(row=r, column=c).fill = PatternFill("solid", fgColor=BLEU)
    ws["A1"] = texte
    ws["A1"].font = Font(bold=True, size=18, color="FFFFFF", name="Calibri")
    ws["A2"] = sous
    ws["A2"].font = Font(size=10, color="C9D6E3", name="Calibri")
    ws.row_dimensions[1].height = 30


def _entetes(ws, ligne, valeurs, col0=1):
    for j, v in enumerate(valeurs, start=col0):
        c = ws.cell(row=ligne, column=j, value=v)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=BLEU)
        c.alignment = Alignment(horizontal="center" if j > col0 else "left", vertical="center", wrap_text=True)
    ws.row_dimensions[ligne].height = 24


def _largeurs(ws, largeurs):
    for lettre, l in largeurs.items():
        ws.column_dimensions[lettre].width = l


def _val(x, nd):
    return nd if x is None else x


def generer_excel(dossier: dict, dossier_sortie: str | None = None) -> str:
    """Crée le fichier Excel du client et renvoie son chemin."""
    lg = "en" if dossier.get("langue") == "en" else "fr"
    L = LIB[lg]
    u = regles.charger_univers()
    r = dossier["reponses"]
    p = dossier["profil"]
    ind = dossier.get("indicateurs", {}) or {}
    sim = dossier.get("simulation", {}) or {}
    pf = dossier["portefeuille"]
    montant = r.get("montant", 0) or 0
    jour = dossier.get("date", date.today().isoformat())
    env = dossier.get("enveloppe", "")
    env_lignes = regles.repartition_enveloppes(pf, env, montant)
    nom_profil = regles.PROFILS[p["profil"]]["nom_en" if lg == "en" else "nom"]
    cls = t("classes", lg)
    n_ans = dossier.get("horizon_ans") or (len(sim.get("p50", [])) - 1 if sim else None)

    wb = Workbook()
    wb.remove(wb.active)

    # ------------------------------------------------------------------ Synthèse
    ws = wb.create_sheet(L["synthese"])
    _titre(ws, L["titre"], f"{L['sous']} — {jour}", 4)
    kpis = [(L["montant"], montant, FMT_EUR), (L["profil"], f"{p['profil']}/5 — {nom_profil}", None),
            (L["env"], NOMS_ENVELOPPES[lg].get(env, env), None)]
    for j, (lib, val, fmt) in enumerate(kpis):
        col = 1 + j if j < 2 else 3
        c = ws.cell(row=4, column=col, value=lib)
        c.font, c.fill = Font(size=9, color="6B7785"), PatternFill("solid", fgColor=GRIS)
        v = ws.cell(row=5, column=col, value=val)
        v.font, v.fill = Font(bold=True, size=14, color=BLEU), PatternFill("solid", fgColor=GRIS)
        v.alignment = Alignment(horizontal="left")
        if fmt:
            v.number_format = fmt
    lignes = [(L["versement"], r.get("versement_mensuel", 0), FMT_EUR),
              (L["horizon"], f"{n_ans} {L['annees']}" if n_ans else None, None),
              (L["objectif"], r.get("cible") or None, FMT_EUR),
              (L["frais"], ind.get("ter_moyen"), FMT_PCT2),
              (L["vol"], ind.get("volatilite"), FMT_PCT)]
    if sim:
        lignes += [(L["def"], sim["p10"][-1], FMT_EUR), (L["cen"], sim["p50"][-1], FMT_EUR), (L["fav"], sim["p90"][-1], FMT_EUR)]
        if sim.get("proba_cible") is not None:
            lignes.append((L["proba"], sim["proba_cible"], "0%"))
    ligne = 7
    for lib, val, fmt in lignes:
        a = ws.cell(row=ligne, column=1, value=lib)
        a.font, a.border = Font(color="4A5560"), BORD
        b = ws.cell(row=ligne, column=2, value=_val(val, L["nd"]))
        b.font, b.border, b.alignment = Font(bold=True), BORD, Alignment(horizontal="right")
        if fmt and val is not None:
            b.number_format = fmt
        ligne += 1
    ligne += 1
    ws.cell(row=ligne, column=1, value=L["expl"]).font = Font(bold=True, size=12, color=BLEU)
    ws.merge_cells(start_row=ligne + 1, start_column=1, end_row=ligne + 1, end_column=4)
    c = ws.cell(row=ligne + 1, column=1, value=dossier.get("explication", ""))
    c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[ligne + 1].height = 150
    ws.cell(row=ligne + 3, column=1, value=L["avert"]).font = Font(italic=True, size=8, color="6B7785")
    _largeurs(ws, {"A": 42, "B": 26, "C": 30, "D": 30})

    # ------------------------------------------------------------------ Portefeuille
    ws = wb.create_sheet(L["portefeuille"])
    _titre(ws, L["portefeuille"], f"{nom_profil} — {NOMS_ENVELOPPES[lg].get(env, env)}", 9)
    _entetes(ws, 4, L["cols"])
    ordre = ["monetaire", "obligations", "actions", "diversifiants", "scpi", "actif"]
    lignes_pf = sorted(pf.items(), key=lambda x: (ordre.index(u.loc[x[0], "classe"]), -x[1]))
    ligne = 5
    for isin, w in lignes_pf:
        l = u.loc[isin]
        typ = l["type"]
        ident = l["ticker_yahoo"] if typ == "action" else ("—" if typ == "obligation" else isin)
        if typ == "obligation":
            cp = float(l["coupon"] or 0)
            detail = f"{l['emetteur']} · {l['notation']} · coupon {cp:.2%} · {l['maturite']}"
        elif typ == "action":
            detail = f"{l['secteur']} · {l['pays']}"
        else:
            detail = l["description"]
        ter = l["ter_num"] if l["ter_num"] == l["ter_num"] and l["ter_num"] else None
        sri = l["sri"] if str(l["sri"]).isdigit() else "—"
        vals = [l["nom"], ident, cls[l["classe"]], w, w * montant, ter if ter else "—", int(sri) if sri != "—" else sri,
                env_lignes.get(isin, ""), detail]
        for j, v in enumerate(vals, start=1):
            c = ws.cell(row=ligne, column=j, value=v)
            c.border = BORD
            c.alignment = Alignment(vertical="center", wrap_text=(j in (1, 9)), horizontal="left" if j in (1, 2, 3, 9) else "center")
        ws.cell(row=ligne, column=4).number_format = FMT_PCT
        ws.cell(row=ligne, column=5).number_format = FMT_EUR
        ws.cell(row=ligne, column=6).number_format = FMT_PCT2
        ligne += 1
    deb, fin = 5, ligne - 1
    ws.cell(row=ligne, column=1, value=L["total"]).font = Font(bold=True)
    for col, fmt in ((4, FMT_PCT), (5, FMT_EUR)):
        lettre = "D" if col == 4 else "E"
        c = ws.cell(row=ligne, column=col, value=f"=SUM({lettre}{deb}:{lettre}{fin})")
        c.font, c.number_format, c.alignment = Font(bold=True), fmt, Alignment(horizontal="center")
    for j in range(1, 10):
        ws.cell(row=ligne, column=j).fill = PatternFill("solid", fgColor=BLEU_CLAIR)
    ws.conditional_formatting.add(f"D{deb}:D{fin}", DataBarRule(start_type="num", start_value=0, end_type="num", end_value=0.3, color="3E7CB1"))
    ws.freeze_panes = "B5"
    ws.auto_filter.ref = f"A4:I{fin}"
    ws.cell(row=ligne + 2, column=1, value=L["avert"]).font = Font(italic=True, size=8, color="6B7785")
    _largeurs(ws, {"A": 44, "B": 16, "C": 22, "D": 10, "E": 14, "F": 9, "G": 11, "H": 14, "I": 60})
    ws.page_setup.orientation, ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = "landscape", 1, 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True

    # ------------------------------------------------------------------ Performances
    ws = wb.create_sheet(L["perfs"])
    _titre(ws, L["perfs"], L["indic"], 8)
    pct_lignes = [("p1", ind.get("perf_1a"), FMT_PCT), ("p3", ind.get("perf_3a"), FMT_PCT), ("p5", ind.get("perf_5a"), FMT_PCT),
                  ("vola", ind.get("volatilite"), FMT_PCT), ("dd", ind.get("drawdown_max"), FMT_PCT),
                  ("sharpe", ind.get("sharpe"), "0.00"), ("frais", ind.get("ter_moyen"), FMT_PCT2),
                  ("var", ind.get("var_95"), FMT_PCT2), ("sri", ind.get("sri_estime"), "0"),
                  ("src", ind.get("source_prix"), None), ("depuis", ind.get("historique_depuis"), None)]
    for i, (cle, val, fmt) in enumerate(pct_lignes, start=4):
        a = ws.cell(row=i, column=1, value=L[cle])
        a.font, a.border = Font(color="4A5560"), BORD
        b = ws.cell(row=i, column=2, value=_val(val, L["nd"]))
        b.font, b.border, b.alignment = Font(bold=True), BORD, Alignment(horizontal="right")
        if fmt and val is not None:
            b.number_format = fmt
            if isinstance(val, float) and cle in ("p1", "p3", "p5"):
                b.font = Font(bold=True, color=VERT if val >= 0 else ROUGE)
    base = 4 + len(pct_lignes) + 2
    ws.cell(row=base, column=1, value=L["alloc"]).font = Font(bold=True, size=12, color=BLEU)
    _entetes(ws, base + 1, [L["classe"], L["poids"]])
    classes = {k: v for k, v in regles.poids_par_classe(pf).items() if v > 0}
    for i, (cl, w) in enumerate(classes.items(), start=base + 2):
        ws.cell(row=i, column=1, value=cls[cl]).border = BORD
        c = ws.cell(row=i, column=2, value=w)
        c.number_format, c.border, c.alignment = FMT_PCT, BORD, Alignment(horizontal="right")
    if classes:
        pie = PieChart()
        pie.title = L["alloc"]
        pie.add_data(Reference(ws, min_col=2, min_row=base + 1, max_row=base + 1 + len(classes)), titles_from_data=True)
        pie.set_categories(Reference(ws, min_col=1, min_row=base + 2, max_row=base + 1 + len(classes)))
        pie.dataLabels = DataLabelList()
        pie.dataLabels.showPercent = True
        pie.dataLabels.showVal = pie.dataLabels.showCatName = pie.dataLabels.showSerName = pie.dataLabels.showLeaderLines = False
        pie.width, pie.height = 12, 9
        ws.add_chart(pie, "D4")
    _largeurs(ws, {"A": 52, "B": 18, "C": 4})

    # ------------------------------------------------------------------ Simulation
    ws = wb.create_sheet(L["simulation"])
    _titre(ws, L["simulation"], L["evol"], 6)
    if sim:
        _entetes(ws, 4, L["colsim"])
        an0 = date.today().year
        n = len(sim["p50"])
        for a in range(n):
            vals = [f"{an0 + a}", sim["p10"][a], sim["p50"][a], sim["p90"][a], sim["ref_6040"][a], sim["capital_verse"][a]]
            for j, v in enumerate(vals, start=1):
                c = ws.cell(row=5 + a, column=j, value=v)
                c.border = BORD
                c.alignment = Alignment(horizontal="left" if j == 1 else "right")
                if j > 1:
                    c.number_format = FMT_EUR
        ch = LineChart()
        ch.title = L["evol"]
        ch.height, ch.width = 10, 24
        ch.add_data(Reference(ws, min_col=2, max_col=6, min_row=4, max_row=4 + n), titles_from_data=True)
        ch.set_categories(Reference(ws, min_col=1, min_row=5, max_row=4 + n))
        couleurs = ["C62828", "1F3A5F", "2E7D32", "9AA5B1", "BBBBBB"]
        for s_, c_ in zip(ch.series, couleurs):
            s_.graphicalProperties.line.solidFill = c_
            s_.graphicalProperties.line.width = 32000 if c_ == "1F3A5F" else 18000
            s_.smooth = False
        ch.y_axis.number_format = '#,##0 "€"'
        ch.y_axis.delete = ch.x_axis.delete = False
        ch.legend.position = "b"
        ws.add_chart(ch, f"A{n + 10}")
        hyp = sim.get("hypotheses", {})
        b = n + 6
        ws.cell(row=b, column=1, value=L["hyp"]).font = Font(bold=True, color=BLEU)
        ws.cell(row=b + 1, column=1, value=f"{L['source']} : {hyp.get('source', '')}").font = Font(size=9, color="4A5560")
        ws.cell(row=b + 2, column=1, value=f"{L['corr']} : {hyp.get('methode_correlation', '')}").font = Font(size=9, color="4A5560")
    ws.freeze_panes = "A5"
    _largeurs(ws, {"A": 12, "B": 20, "C": 20, "D": 20, "E": 20, "F": 20})

    # ------------------------------------------------------------------ Justification
    ws = wb.create_sheet(L["justif"])
    _titre(ws, L["justif"], L["pourquoi"], 1)
    for i, phrase in enumerate(dossier.get("justifications", []), start=4):
        c = ws.cell(row=i, column=1, value=phrase)
        c.alignment, c.border = Alignment(wrap_text=True, vertical="top"), BORD
        ws.row_dimensions[i].height = 32 if len(phrase) > 110 else 18
    _largeurs(ws, {"A": 130})

    # ------------------------------------------------------------------ Analyses V4 (si présentes)
    _onglets_v4(wb, dossier, lg, montant)

    for ws in wb.worksheets:      # impression : une page de large, en paysage
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
    wb.active = 0
    sortie = Path(dossier_sortie or tempfile.mkdtemp())
    sortie.mkdir(parents=True, exist_ok=True)
    chemin = sortie / f"portefeuille_{jour}.xlsx"
    wb.save(chemin)
    return str(chemin)


def _tableau_simple(ws, ligne, entetes, lignes, formats=None):
    """En-têtes en ligne `ligne`, puis une ligne par élément ; formats = {colonne: format}."""
    _entetes(ws, ligne, entetes)
    for i, valeurs in enumerate(lignes, start=ligne + 1):
        for j, v in enumerate(valeurs, start=1):
            c = ws.cell(row=i, column=j, value=v)
            c.border = BORD
            c.alignment = Alignment(vertical="center", wrap_text=True, horizontal="left" if j == 1 else "right")
            if formats and j in formats:
                c.number_format = formats[j]
    return ligne + len(lignes) + 1


def _onglets_v4(wb, dossier: dict, lg: str, montant: float) -> None:
    en = lg == "en"
    if dossier.get("stress"):
        ws = wb.create_sheet(("Stress tests", "Stress tests")[en])
        _titre(ws, ("Stress tests", "Stress tests")[en], ("Le portefeuille dans les grandes crises", "The portfolio in major crises")[en], 5)
        lignes = [[x["nom"], x["periode"], x["variation"], x["variation_eur"], x["recuperation_ans"]] for x in dossier["stress"]]
        fin = _tableau_simple(ws, 4, [("Scénario", "Scenario")[en], ("Période", "Period")[en], ("Impact", "Impact")[en],
                                      ("En euros", "In euros")[en], ("Récupération (ans)", "Recovery (years)")[en]],
                              lignes, {3: FMT_PCT, 4: FMT_EUR, 5: "0.0"})
        mk = dossier.get("markowitz")
        if mk:
            ws.cell(row=fin + 2, column=1, value=("Position risque / rendement attendue", "Expected risk / return")[en]).font = Font(bold=True, color=BLEU)
            ws.cell(row=fin + 3, column=1, value=("Volatilité attendue", "Expected volatility")[en])
            ws.cell(row=fin + 3, column=3, value=mk["vol"]).number_format = FMT_PCT
            ws.cell(row=fin + 4, column=1, value=("Rendement attendu", "Expected return")[en])
            ws.cell(row=fin + 4, column=3, value=mk["mu"]).number_format = FMT_PCT2
        _largeurs(ws, {"A": 36, "B": 34, "C": 12, "D": 16, "E": 18})
    if dossier.get("fiscalite"):
        ws = wb.create_sheet(("Fiscalité", "Tax")[en])
        _titre(ws, ("Fiscalité", "Tax")[en], ("Capital net après impôts selon l'enveloppe (règles 2026)", "Net capital after tax by wrapper (2026 rules)")[en], 7)
        lignes = [[x["nom"], x["verse"], x["capital_brut"], x["impot_revenu"], x["prelevements_sociaux"], x["capital_net"], x["taux_effectif"]]
                  for x in dossier["fiscalite"]]
        fin = _tableau_simple(ws, 4, [("Enveloppe", "Wrapper")[en], ("Versé", "Contributed")[en], ("Capital brut", "Gross")[en],
                                      ("Impôt sur le revenu", "Income tax")[en], ("Prélèvements sociaux", "Social charges")[en],
                                      ("Capital net", "Net")[en], ("Taux effectif", "Effective rate")[en]],
                              lignes, {2: FMT_EUR, 3: FMT_EUR, 4: FMT_EUR, 5: FMT_EUR, 6: FMT_EUR, 7: FMT_PCT})
        ws.cell(row=fin + 1, column=1, value=("Retrait total à l'horizon ; flat tax 31,4 % ; PS 18,6 % (CTO, PEA) et 17,2 % (assurance-vie).",
                                              "Full withdrawal at horizon; 31.4% flat tax; social charges 18.6% / 17.2%.")[en]).font = Font(italic=True, size=9, color="6B7785")
        _largeurs(ws, {"A": 36, "B": 14, "C": 14, "D": 16, "E": 18, "F": 14, "G": 13})
    if dossier.get("esg"):
        e = dossier["esg"]
        ws = wb.create_sheet(("Durabilité", "Sustainability")[en])
        _titre(ws, ("Durabilité", "Sustainability")[en], ("Indicateurs extra-financiers (estimations)", "Non-financial indicators (estimates)")[en], 3)
        lignes = [[("Part ESG", "ESG share")[en], e["part_esg"]], [("Intensité carbone (t CO2e / M€ CA)", "Carbon intensity")[en], e["intensite_carbone"]],
                  [("Référence indice monde", "World index benchmark")[en], e["reference_monde"]],
                  [("Couverture des données", "Data coverage")[en], e["couverture_carbone"]]]
        lignes += [[("Exposition : ", "Exposure: ")[en] + k, v] for k, v in e["exposition_tags"].items()]
        _tableau_simple(ws, 4, [("Indicateur", "Indicator")[en], ("Valeur", "Value")[en]], lignes)
        for r_ in range(5, 5 + len(lignes)):
            c = ws.cell(row=r_, column=2)
            if isinstance(c.value, float) and c.value <= 1:
                c.number_format = FMT_PCT
            elif isinstance(c.value, float):
                c.number_format = "0"
        _largeurs(ws, {"A": 44, "B": 16})
    if dossier.get("controles"):
        ws = wb.create_sheet(("Conformité", "Compliance")[en])
        _titre(ws, ("Conformité", "Compliance")[en], ("Contrôles d'adéquation", "Suitability checks")[en], 4)
        lib = {"ok": ("Conforme", "Compliant"), "attention": ("À documenter", "To document"), "bloquant": ("Bloquant", "Blocking")}
        lignes = [[c["titre"], lib[c["statut"]][en], c["detail"], c["regle"]] for c in dossier["controles"]]
        _tableau_simple(ws, 4, [("Contrôle", "Check")[en], ("Statut", "Status")[en], ("Détail", "Detail")[en], ("Référence", "Reference")[en]], lignes)
        couleurs = {"Conforme": "E6F4EA", "Compliant": "E6F4EA", "À documenter": "FFF4DB", "To document": "FFF4DB", "Bloquant": "FDE8E8", "Blocking": "FDE8E8"}
        for r_ in range(5, 5 + len(lignes)):
            c = ws.cell(row=r_, column=2)
            c.fill = PatternFill("solid", fgColor=couleurs.get(c.value, "FFFFFF"))
            c.alignment = Alignment(horizontal="center", vertical="center")
            ws.cell(row=r_, column=3).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
            ws.cell(row=r_, column=4).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
            ws.row_dimensions[r_].height = 32
        _largeurs(ws, {"A": 40, "B": 15, "C": 70, "D": 45})
