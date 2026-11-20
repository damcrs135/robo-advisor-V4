"""
livrable_pdf.py — Déclaration d'adéquation en PDF

    generer_pdf(dossier, dossier_sortie=None) -> chemin du fichier créé

Contenu : synthèse, profil de risque et ses limites, allocation, portefeuille ligne par ligne,
simulation, risques et frais, annexe des réponses, conclusion d'adéquation.
Bibliothèque : reportlab (polices standard, accents et € inclus).
"""

from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, PageTemplate, Paragraph, Spacer, Table,
                                TableStyle)

import questionnaire as qn
import regles
from textes import NOMS_ENVELOPPES, t

BLEU = colors.HexColor("#1F3A5F")
CLAIR = colors.HexColor("#EAF2FB")
GRIS = colors.HexColor("#F4F6F9")
TEXTE = colors.HexColor("#1B2A41")
DISCRET = colors.HexColor("#6B7785")
LIGNE = colors.HexColor("#D9DEE5")
COULEURS_CLASSES = {"monetaire": "#3E7CB1", "obligations": "#12873F", "actions": "#1F3A5F", "diversifiants": "#D85A30",
                    "scpi": "#9AA5B1", "actif": "#9CC3E6"}
ORDRE = ["monetaire", "obligations", "actions", "diversifiants", "scpi", "actif"]
LARGEUR = A4[0] - 36 * mm

ST = {
    "corps": ParagraphStyle("corps", fontName="Helvetica", fontSize=9, leading=13, textColor=TEXTE, alignment=TA_LEFT),
    "petit": ParagraphStyle("petit", fontName="Helvetica", fontSize=7.5, leading=10, textColor=DISCRET),
    "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=8, leading=10, textColor=TEXTE),
    "cellb": ParagraphStyle("cellb", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=TEXTE),
    "tete": ParagraphStyle("tete", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=colors.white),
    "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=BLEU, spaceAfter=2),
    "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=BLEU, spaceBefore=12, spaceAfter=5, keepWithNext=1),
    "kpi_l": ParagraphStyle("kpi_l", fontName="Helvetica", fontSize=7.5, leading=9, textColor=DISCRET),
    "kpi_v": ParagraphStyle("kpi_v", fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=BLEU),
}


def _s(x) -> str:
    """Texte compatible avec les polices standard du PDF (caractères exotiques remplacés)."""
    x = str(x).replace(" ", " ").replace(" ", " ").replace("→", "->").replace("≥", ">=").replace("≤", "<=")
    return x.encode("cp1252", "replace").decode("cp1252")


def _p(texte, style="corps"):
    return Paragraph(escape(_s(texte)), ST[style])


def _pct(x, d=1):
    return "n.d." if x is None else f"{x * 100:.{d}f} %".replace(".", ",")


def _eur(x):
    return "n.d." if x is None else f"{x:,.0f} €".replace(",", " ")


def _tableau(lignes, largeurs, entete=True, zebre=True, align_droite=()):
    data = []
    for i, ligne in enumerate(lignes):
        st = "tete" if (entete and i == 0) else "cell"
        data.append([c if not isinstance(c, str) else Paragraph(escape(_s(c)), ST[st]) for c in ligne])
    tab = Table(data, colWidths=largeurs, repeatRows=1 if entete else 0)
    style = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, LIGNE),
             ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
             ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]
    if entete:
        style.append(("BACKGROUND", (0, 0), (-1, 0), BLEU))
    if zebre:
        for i in range(1 if entete else 0, len(data)):
            if i % 2 == 0:
                style.append(("BACKGROUND", (0, i), (-1, i), GRIS))
    tab.setStyle(TableStyle(style))
    return tab


def _barre_notes(note):
    d = Drawing(70, 8)
    for i in range(5):
        d.add(Rect(i * 14, 1, 11, 6, fillColor=BLEU if i < note else colors.HexColor("#D6E4F2"), strokeColor=None))
    return d


def _barre_allocation(poids, cls):
    h = 14
    d = Drawing(LARGEUR, h + 26)
    x = 0
    for c in ORDRE:
        w = poids.get(c, 0)
        if w <= 0:
            continue
        d.add(Rect(x, 22, w * LARGEUR, h, fillColor=colors.HexColor(COULEURS_CLASSES[c]), strokeColor=colors.white))
        x += w * LARGEUR
    x = 0
    for c in ORDRE:
        if poids.get(c, 0) <= 0:
            continue
        d.add(Rect(x, 6, 7, 7, fillColor=colors.HexColor(COULEURS_CLASSES[c]), strokeColor=None))
        txt = f"{_s(cls[c])} {poids[c] * 100:.0f} %"
        d.add(String(x + 10, 6, txt, fontName="Helvetica", fontSize=7.5, fillColor=TEXTE))
        x += 10 + 4.2 * len(txt) + 14
    return d


def _courbe(sim, lg):
    n = len(sim["p50"])
    d = Drawing(LARGEUR, 190)
    lp = LinePlot()
    lp.x, lp.y, lp.width, lp.height = 62, 34, LARGEUR - 80, 138
    an0 = date.today().year
    series = [("p90", "#2E7D32", 1), ("p50", "#1F3A5F", 2.2), ("p10", "#C62828", 1), ("ref_6040", "#9AA5B1", 1), ("capital_verse", "#BBBBBB", 1)]
    lp.data = [[(an0 + a, sim[k][a]) for a in range(n)] for k, _, _ in series]
    for i, (_, c, w) in enumerate(series):
        lp.lines[i].strokeColor, lp.lines[i].strokeWidth = colors.HexColor(c), w
        lp.lines[i].symbol = None
    lp.lines[4].strokeDashArray = [2, 2]
    lp.xValueAxis.valueMin, lp.xValueAxis.valueMax = an0, an0 + n - 1
    lp.xValueAxis.valueStep = max(1, (n - 1) // 8)
    lp.xValueAxis.labels.fontSize = lp.yValueAxis.labels.fontSize = 7
    lp.xValueAxis.labels.fontName = lp.yValueAxis.labels.fontName = 'Helvetica'
    lp.xValueAxis.labels.dy = -2
    lp.yValueAxis.labelTextFormat = lambda v: f"{v / 1000:,.0f} k€".replace(",", " ")
    lp.yValueAxis.gridStrokeColor = LIGNE
    lp.yValueAxis.visibleGrid = True
    d.add(lp)
    noms = [t("favorable", lg), t("central", lg), t("defavorable", lg), t("ref_6040", lg), t("verse", lg)]
    x = 62
    for (k, c, _), nom in zip(series, noms):
        d.add(Rect(x, 6, 8, 8, fillColor=colors.HexColor(c), strokeColor=None))
        d.add(String(x + 11, 7, _s(nom), fontName="Helvetica", fontSize=7, fillColor=TEXTE))
        x += 14 + 4 * len(nom) + 6
    return d


def _habillage(titre, avert):
    def f(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(BLEU)
        canvas.rect(0, A4[1] - 14 * mm, A4[0], 14 * mm, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(18 * mm, A4[1] - 9 * mm, _s(titre))
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(A4[0] - 18 * mm, A4[1] - 9 * mm, f"{doc.page}")
        canvas.setFillColor(DISCRET)
        canvas.setFont("Helvetica", 6.5)
        texte = _s(avert)
        milieu = len(texte) // 2
        coupe = texte.rfind(" ", 0, milieu + 20)
        canvas.drawCentredString(A4[0] / 2, 11 * mm, texte[:coupe])
        canvas.drawCentredString(A4[0] / 2, 8 * mm, texte[coupe + 1:])
        canvas.restoreState()
    return f


def generer_pdf(dossier: dict, dossier_sortie: str | None = None) -> str:
    """Crée la déclaration d'adéquation et renvoie son chemin."""
    lg = "en" if dossier.get("langue") == "en" else "fr"
    en = lg == "en"
    u = regles.charger_univers()
    r = dossier["reponses"]
    p = dossier["profil"]
    num = p["profil"]
    nom_profil = regles.PROFILS[num]["nom_en" if en else "nom"]
    env = dossier.get("enveloppe", "")
    nom_env = NOMS_ENVELOPPES[lg].get(env, env)
    ind = dossier.get("indicateurs", {}) or {}
    sim = dossier.get("simulation", {}) or {}
    pf = dossier["portefeuille"]
    montant = r.get("montant", 0) or 0
    jour = dossier.get("date", date.today().isoformat())
    cls = t("classes", lg)
    sections = t("pdf_sections", lg)
    n_ans = dossier.get("horizon_ans")

    sortie = Path(dossier_sortie or tempfile.mkdtemp())
    sortie.mkdir(parents=True, exist_ok=True)
    chemin = sortie / f"declaration_adequation_{jour}.pdf"
    doc = BaseDocTemplate(str(chemin), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                          topMargin=22 * mm, bottomMargin=20 * mm, title=_s(t("pdf_titre", lg)), author="Robo-advisor")
    doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(18 * mm, 20 * mm, LARGEUR, A4[1] - 42 * mm, id="f", leftPadding=0,
                                                              rightPadding=0, topPadding=0, bottomPadding=0)],
                                       onPage=_habillage(t("titre", lg), t("avertissement", lg)))])
    h = []

    # --- Titre et chiffres clés
    ref = f"  ·  Réf. {dossier['dossier_id']}" if dossier.get("dossier_id") else ""
    h += [_p(t("pdf_titre", lg), "h1"), _p(t("genere_le", lg, date=jour) + ref, "petit"), Spacer(1, 8)]
    kpis = [(("Montant investi", "Amount invested")[en], _eur(montant)), (("Profil de risque", "Risk profile")[en], f"{num}/5 - {nom_profil}"),
            (("Enveloppe", "Wrapper")[en], nom_env),
            (("Horizon de simulation", "Simulation horizon")[en], f"{n_ans} {'years' if en else 'ans'}" if n_ans else "n.d.")]
    cases = [[Paragraph(escape(_s(a)), ST["kpi_l"]), ] for a, _ in kpis]
    ligne_l = [Paragraph(escape(_s(a)), ST["kpi_l"]) for a, _ in kpis]
    ligne_v = [Paragraph(escape(_s(b)), ST["kpi_v"]) for _, b in kpis]
    tk = Table([ligne_l, ligne_v], colWidths=[LARGEUR / 4] * 4)
    tk.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), CLAIR), ("LEFTPADDING", (0, 0), (-1, -1), 8),
                            ("TOPPADDING", (0, 0), (-1, 0), 7), ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
                            ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    h.append(tk)

    # --- 1. Profil
    h.append(_p("1. " + sections[1][3:], "h2"))
    h.append(_p(t("profil_titre", lg, nom=nom_profil, num=num) + ". " + t("profil_regle", lg)))
    h.append(Spacer(1, 5))
    noms_notes = t("notes", lg)
    lignes = [[t("note", lg).split(" (")[0], "", ""]] + [[noms_notes[k], _barre_notes(v), f"{v}/5"] for k, v in p["notes"].items()]
    tn = _tableau(lignes, [90 * mm, 50 * mm, LARGEUR - 140 * mm])
    h.append(tn)
    if p.get("quiz_score") is not None:
        h += [Spacer(1, 4), _p(("Knowledge quiz: " if en else "Quiz de connaissances : ") + f"{p['quiz_score']}/5.", "petit")]
    if p.get("plafonds"):
        h += [Spacer(1, 4), _p(t("plafonds", lg), "cellb")] + [_p("- " + x) for x in p["plafonds"]]
    if p.get("profil_calcule") and p["profil_calcule"] != num:
        pc = p["profil_calcule"]
        if en:
            msg = f"At the client's request, the profile was {'raised' if num > pc else 'lowered'} from {pc} to {num}."
        else:
            msg = f"À la demande du client, le profil a été {'relevé' if num > pc else 'abaissé'} de {pc} à {num}."
        h += [Spacer(1, 4), _p(msg)]
    if p.get("alertes"):
        h += [Spacer(1, 4), _p(t("alertes", lg), "cellb")] + [_p("- " + x) for x in p["alertes"]]

    # --- 2. Allocation et portefeuille
    h.append(_p("2. " + sections[2][3:], "h2"))
    h.append(_p(t("enveloppe_titre", lg, env=nom_env)))
    h.append(Spacer(1, 4))
    poids = regles.poids_par_classe(pf)
    h.append(_barre_allocation(poids, cls))
    env_lignes = regles.repartition_enveloppes(pf, env, montant)
    col = t("colonnes", lg)
    lignes = [[col["nom"], col["poids"], col["montant"], col["ter"], "SRI", col["enveloppe"]]]
    styles_sup = []
    for c in ORDRE:
        isins = sorted([i for i in pf if u.loc[i, "classe"] == c], key=lambda i: -pf[i])
        if not isins:
            continue
        lignes.append([f"{cls[c]}", _pct(poids[c], 0), _eur(poids[c] * montant), "", "", ""])
        styles_sup.append(len(lignes) - 1)
        for isin in isins:
            l = u.loc[isin]
            ter = "-" if not l["ter_num"] == l["ter_num"] or not l["ter_num"] else _pct(l["ter_num"], 2)
            if l["type"] == "obligation":
                cp = float(l["coupon"] or 0)
                sous = f"{l['emetteur']}, {l['notation']}, coupon {_pct(cp, 2)}, {l['maturite']}"
            elif l["type"] == "action":
                sous = f"{l['ticker_yahoo']} - {l['secteur']} ({l['pays']})"
            else:
                sous = isin
            nom = Paragraph(f"{escape(_s(l['nom']))}<br/><font size=6.5 color='#6B7785'>{escape(_s(sous))}</font>", ST["cell"])
            lignes.append([nom, _pct(pf[isin]), _eur(pf[isin] * montant), ter, str(l["sri"]) if str(l["sri"]).isdigit() else "-", env_lignes[isin]])
    tp = _tableau(lignes, [74 * mm, 15 * mm, 25 * mm, 14 * mm, 10 * mm, LARGEUR - 138 * mm], zebre=False)
    st = [("BACKGROUND", (0, i), (-1, i), CLAIR) for i in styles_sup]
    tp.setStyle(TableStyle(st))
    h += [Spacer(1, 4), tp]

    # --- 3. Simulation
    if sim:
        h.append(_p("3. " + t("simulation_titre", lg), "h2"))
        h.append(_courbe(sim, lg))
        tr = _tableau([[("Scénario", "Scenario")[en], ("Capital final", "Final capital")[en]],
                       [t("defavorable", lg), _eur(sim["p10"][-1])], [t("central", lg), _eur(sim["p50"][-1])],
                       [t("favorable", lg), _eur(sim["p90"][-1])]] +
                      ([[t("proba", lg, cible=_eur(r.get("cible"))), _pct(sim["proba_cible"], 0)]] if sim.get("proba_cible") is not None else []),
                      [110 * mm, LARGEUR - 110 * mm])
        h += [Spacer(1, 4), tr]
    ris = [[("Indicateur historique", "Historical indicator")[en], ("Valeur", "Value")[en]],
           [t("volatilite", lg), _pct(ind.get("volatilite"))], [t("drawdown", lg), _pct(ind.get("drawdown_max"))],
           [t("sri_estime", lg), str(ind.get("sri_estime") or "n.d.")],
           [("SRI maximum du profil", "Maximum SRI of the profile")[en], str(regles.PROFILS[num]["sri_max"])],
           [("Frais annuels moyens", "Average annual fees")[en], _pct(ind.get("ter_moyen"), 2)]]
    h += [_p("4. " + (("Risques et frais", "Risks and fees")[en]), "h2"), _tableau(ris, [110 * mm, LARGEUR - 110 * mm]), Spacer(1, 4), _p(t("pdf_risques", lg), "petit")]

    num_section = 5
    # --- Analyses de la V4 (présentes si le dossier les contient)
    if dossier.get("stress"):
        h.append(_p(f"{num_section}. " + ("Stress tests et optimisation", "Stress tests and optimisation")[en], "h2"))
        num_section += 1
        lignes = [[("Scénario", "Scenario")[en], ("Impact", "Impact")[en], ("En euros", "In euros")[en],
                   ("Récupération", "Recovery")[en]]]
        for x in dossier["stress"]:
            rec = "-" if x["recuperation_ans"] is None else (f"{x['recuperation_ans']:.1f} " + ("ans", "years")[en]).replace(".", "," if not en else ".")
            lignes.append([f"{x['nom']} ({x['periode']})", _pct(x["variation"]), _eur(x["variation_eur"]), rec])
        h.append(_tableau(lignes, [92 * mm, 22 * mm, 30 * mm, LARGEUR - 144 * mm]))
        mk = dossier.get("markowitz")
        if mk:
            h += [Spacer(1, 4), _p((f"Position risque / rendement (hypothèses Amundi, corrélations de long terme) : volatilité attendue "
                                    f"{_pct(mk['vol'])}, rendement attendu {_pct(mk['mu'], 2)} par an, brut de frais.") if not en else
                                   (f"Risk / return position: expected volatility {_pct(mk['vol'])}, expected return {_pct(mk['mu'], 2)} a year."))]
        h.append(_p(("Chocs par classe d'actifs : ordres de grandeur des crises passées ou chocs hypothétiques ; la récupération suppose "
                     "le rendement attendu du portefeuille.", "Class shocks: past crises or hypothetical shocks.")[en], "petit"))
    if dossier.get("fiscalite"):
        h.append(_p(f"{num_section}. " + ("Comparaison fiscale des enveloppes", "Tax comparison of wrappers")[en], "h2"))
        num_section += 1
        lignes = [[("Enveloppe", "Wrapper")[en], ("Capital brut", "Gross")[en], ("Impôts", "Taxes")[en], ("Capital net", "Net")[en],
                   ("Taux effectif", "Effective rate")[en]]]
        for x in dossier["fiscalite"]:
            lignes.append([x["nom"] + (" *" if x["meilleur"] else ""), _eur(x["capital_brut"]), _eur(x["impots"]),
                           _eur(x["capital_net"]), _pct(x["taux_effectif"])])
        h.append(_tableau(lignes, [60 * mm, 28 * mm, 28 * mm, 30 * mm, LARGEUR - 146 * mm]))
        h.append(_p(("* meilleur capital net. Règles 2026 : flat tax 31,4 % (CTO), prélèvements sociaux 18,6 % (PEA après 5 ans), "
                     "assurance-vie 17,2 % + 7,5 % après 8 ans et abattement. Retrait total à l'horizon, simplifié.",
                     "* best net capital. 2026 rules, full withdrawal at horizon, simplified.")[en], "petit"))
    if dossier.get("esg"):
        e = dossier["esg"]
        h.append(_p(f"{num_section}. " + ("Durabilité", "Sustainability")[en], "h2"))
        num_section += 1
        ic = e.get("intensite_carbone")
        lignes = [[("Indicateur", "Indicator")[en], ("Valeur", "Value")[en]],
                  [("Part des lignes retenues par le filtre ESG", "Share passing the ESG screen")[en], _pct(e["part_esg"], 0)],
                  [("Intensité carbone estimée (t CO2e / M€ de CA)", "Estimated carbon intensity (t CO2e / EURm)")[en],
                   "n.d." if ic is None else f"{ic:.0f} (" + ("indice monde", "world index")[en] + f" {e['reference_monde']})"],
                  [("Exposition aux secteurs sensibles", "Sensitive sectors exposure")[en],
                   ", ".join(f"{k} {_pct(v)}" for k, v in e["exposition_tags"].items()) or ("aucune", "none")[en]]]
        h.append(_tableau(lignes, [110 * mm, LARGEUR - 110 * mm]))
    if dossier.get("controles"):
        h.append(_p(f"{num_section}. " + ("Contrôles d'adéquation", "Suitability checks")[en], "h2"))
        num_section += 1
        lib = {"ok": ("Conforme", "Compliant"), "attention": ("À documenter", "To document"), "bloquant": ("Bloquant", "Blocking")}
        lignes = [[("Contrôle", "Check")[en], ("Statut", "Status")[en], ("Détail", "Detail")[en]]]
        for c in dossier["controles"]:
            lignes.append([c["titre"], lib[c["statut"]][en], c["detail"]])
        h.append(_tableau(lignes, [55 * mm, 22 * mm, LARGEUR - 77 * mm]))

    # --- Adéquation
    h.append(_p(f"{num_section}. " + sections[5][3:], "h2"))
    vol, vol_max = ind.get("volatilite"), regles.PROFILS[num]["vol_max"]
    if vol is None:
        texte = t("pdf_adequation_nd", lg, nom=nom_profil, env=nom_env)
    elif vol > vol_max:
        texte = t("pdf_adequation_hors", lg, nom=nom_profil, vol=_pct(vol), max=_pct(vol_max))
    else:
        texte = t("pdf_adequation", lg, nom=nom_profil, env=nom_env)
    cadre = Table([[_p(texte)]], colWidths=[LARGEUR])
    cadre.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), CLAIR), ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                               ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    signature = Table([[_p(("Date : ", "Date: ")[en] + jour), _p(("Signature du client", "Client's signature")[en])]], colWidths=[LARGEUR / 2] * 2, rowHeights=[28 * mm])
    signature.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEABOVE", (1, 0), (1, 0), 0.5, DISCRET)]))
    h.append(KeepTogether([cadre, Spacer(1, 10), signature]))

    # --- Annexe : réponses
    h.append(_p(("Annexe - Vos réponses au questionnaire", "Appendix - Your questionnaire answers")[en], "h2"))
    lignes = [[("Question", "Question")[en], ("Réponse", "Answer")[en]]]
    for q in qn.QUESTIONS:
        if q["id"] not in r or q["id"].startswith("quiz_"):
            continue
        v = r[q["id"]]
        txt = _eur(v) if q["id"] in ("patrimoine", "versement_mensuel", "cible") else (str(v) if q["type"] == "nombre" else qn.libelle(q["id"], v, lg))
        lignes.append([q[lg], txt])
    h.append(_tableau(lignes, [115 * mm, LARGEUR - 115 * mm]))

    doc.build(h)
    return str(chemin)
