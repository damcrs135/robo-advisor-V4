# Robo-advisor patrimonial — V4

Projet de M2 Banque-Finance : un robo-advisor **simulé** (aucun argent investi) pour des clients de 100 k€ à 1 M€,
pensé comme un outil de banque privée : parcours client conforme à MiFID II, analyses de risque avancées,
espace conseiller et piste d'audit. Français et anglais.

## Ce que fait l'application

| Page | Contenu |
| --- | --- |
| Accueil | Actualités, marchés, résumé du portefeuille, pédagogie |
| Mon questionnaire | 35 questions en 5 étapes, questions adaptatives, récapitulatif modifiable avant validation |
| Mon profil | 4 notes (tolérance, horizon, capacité, connaissances), limites, alertes, choix libre du niveau de risque |
| Mon portefeuille | Actions et obligations en direct, historique réel, fiches par ligne, personnalisation ±10 points, contrôle d'adéquation et validation |
| Risques et optimisation | Frontière efficiente de Markowitz (avec les 5 profils, le 60/40 et le portefeuille tangent) ; 5 stress tests (2008, Covid, 2022, taux +2 pts, krach −30 %) |
| Projection | Monte Carlo 10 000 trajectoires, scénarios « et si » (horizon, versements, objectif), impact des frais |
| Fiscalité | Capital net après impôts en assurance-vie, PEA et compte-titres (règles 2026) |
| Durabilité | Préférences MiFID II, part ESG, secteurs sensibles, intensité carbone estimée |
| Explication | Texte rédigé par IA (Gemini) avec garde-fou anti-chiffres inventés, justification ligne par ligne |
| Mes documents | Déclaration d'adéquation PDF et fichier Excel complets |
| Espace conseiller | Tableau de bord des dossiers, 12 contrôles de conformité, statuts, journal d'audit, export CSV |
| Méthodologie | Chaîne de décision, hypothèses, corrélations, qualité des données, limites |

## Architecture

```
app.py                navigation, style, barre latérale
etat.py               session, calculs partagés (mis en cache), composants visuels
vues/                 une page par fichier
scoring.py            profil de risque               questionnaire.py   les 35 questions
regles.py             profils, contraintes, construction du portefeuille, enveloppes
analytics.py          cours, performances, volatilité, Sharpe, drawdown
simulation.py         Monte Carlo et impact des frais
optimisation.py       frontière efficiente (scipy)   stress.py          scénarios de crise
fiscalite.py          comparaison des enveloppes      esg.py             indicateurs extra-financiers
conformite.py         contrôles d'adéquation          dossiers.py        dossiers clients et journal d'audit
livrable_pdf.py       déclaration d'adéquation        livrable_excel.py  fichier Excel
llm.py                explication par IA
tests/                tests automatiques (moteurs + parcours complets dans l'interface)
```

Les moteurs métier ne dépendent pas de Streamlit. Les tests (`py -m pytest`) les vérifient et exécutent toutes les
pages avec un faux Streamlit (`tests/banc_streamlit.py`). Sur GitHub, ils tournent à chaque envoi (onglet **Actions**).

## Lancer

```
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

Espace conseiller : code `conseiller` par défaut, à changer avec le secret `CODE_CONSEILLER` (voir `.streamlit/secrets.toml.example`).

## Sources et limites

- Hypothèses de marché : Amundi Investment Institute, *Capital Market Assumptions*, 2026 (10 ans).
- Fiscalité 2026 : flat tax 31,4 %, prélèvements sociaux 18,6 % (CTO, PEA) et 17,2 % (assurance-vie).
- Corrélations de Markowitz, chocs de stress et intensité carbone : ordres de grandeur, documentés dans l'application.
- Coupons, échéances et rendements des obligations : illustratifs. Dossiers clients effacés au redémarrage du serveur de démo.

Projet pédagogique : ceci n'est pas un conseil en investissement.
