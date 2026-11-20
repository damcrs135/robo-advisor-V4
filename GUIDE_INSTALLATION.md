# Guide d'installation pas à pas (Mac)

Durée : environ 45 minutes la première fois. Chaque étape se termine par un contrôle « ✅ » : ne passez à la suivante que si le contrôle est bon.

Le Terminal se trouve dans **Applications > Utilitaires > Terminal**. Les lignes dans les encadrés sont à copier-coller dans le Terminal, une par une, puis Entrée.

---

## 1. Installer Python

1. Allez sur **python.org > Downloads > macOS** et téléchargez la dernière version 3.12 ou 3.13 (« macOS 64-bit universal2 installer »).
2. Ouvrez le fichier `.pkg` et suivez l'installation.
3. À la fin, une fenêtre Finder s'ouvre : double-cliquez sur **Install Certificates.command** (indispensable pour que Yahoo et Gemini répondent).

```bash
python3 --version
```

✅ Le Terminal affiche `Python 3.12.x` ou `Python 3.13.x`.

## 2. Mettre le code dans le dépôt GitHub

1. Installez **GitHub Desktop** (desktop.github.com) et connectez-vous.
2. **File > Clone repository** : choisissez `robo-advisor`. Par défaut il est copié dans `Documents/GitHub/robo-advisor`.
3. Décompressez le zip livré et copiez **tout son contenu** dans ce dossier (remplacez les bouchons existants).
   Dans le Finder, `Cmd + Maj + .` affiche les dossiers cachés `.streamlit` et `.gitignore` : vérifiez qu'ils ont bien été copiés.

✅ Dans GitHub Desktop, l'onglet **Changes** liste les fichiers modifiés.

## 3. Installer les librairies

```bash
cd ~/Documents/GitHub/robo-advisor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`source .venv/bin/activate` est à refaire à chaque nouvelle fenêtre de Terminal (le début de ligne affiche alors `(.venv)`).

✅ La dernière ligne affiche `Successfully installed …` sans erreur rouge.

## 4. Lancer les tests

```bash
python -m pytest -q
```

✅ La dernière ligne affiche `… passed` sans `failed` (le nombre peut augmenter si vous ajoutez des tests). Les tests utilisent des cours **synthétiques** : ils vérifient le code, pas les marchés.

## 5. Télécharger les cours (Yahoo Finance)

```bash
python telecharger_prix.py --maj-univers
```

Le script :
- cherche le ticker Yahoo des deux fonds actifs (Carmignac Patrimoine, Comgest Monde) à partir de leur ISIN ;
- télécharge les cours depuis 2005 ;
- écrit `data/prix_snapshot.csv` (copie de secours lue par le site si Yahoo bloque) ;
- affiche un bilan ligne par ligne.

✅ Le bilan affiche un nombre de jours pour chaque ticker. Pour toute ligne marquée `AUCUNE DONNÉE`, cherchez le bon ticker sur finance.yahoo.com (recherche par ISIN) et corrigez la colonne `ticker_yahoo` de `data/univers.csv`, puis relancez le script.

Ouvrez ensuite `data/univers.csv` et vérifiez les tickers ajoutés automatiquement : la recherche Yahoo peut se tromper de part (A, C, I…). La bonne part est celle de l'ISIN.

## 6. Clé de l'API Gemini (explication par IA)

1. Allez sur **aistudio.google.com**, connectez-vous avec un compte Google (idéalement le Gmail du projet).
2. Cliquez sur **Get API key**, puis créez une clé. Copiez-la.
3. Dans le Terminal :

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
open -e .streamlit/secrets.toml
```

4. Dans TextEdit, remplacez `collez-ici-votre-cle-google-ai-studio` par la clé (gardez les guillemets), enregistrez.
5. Dans AI Studio, regardez quels modèles sont proposés gratuitement. Si les noms diffèrent de ceux de `llm.py` (`MODELES_PAR_DEFAUT`), décommentez la ligne `GEMINI_MODEL` du fichier de secrets et mettez le bon nom.

Important :
- `secrets.toml` est dans `.gitignore` : GitHub Desktop ne doit **pas** le proposer au commit. S'il apparaît, ne le cochez pas.
- Selon les conditions de Google, les données envoyées sur l'offre gratuite peuvent être utilisées pour améliorer ses services : vérifiez-le dans les conditions d'AI Studio. Le site n'envoie que des chiffres calculés pour un client fictif, jamais de nom.

✅ À l'étape 8 du site, la mention sous le texte indique `gemini:<nom du modèle>`. Si elle indique `plan B : …`, la raison est écrite (pas de clé, quota, chiffre non fourni par le robot…). Le site fonctionne quand même.

## 7. Lancer le site en local

```bash
streamlit run app.py
```

Le navigateur s'ouvre sur `http://localhost:8501`. Pour arrêter : `Ctrl + C` dans le Terminal.

✅ Vous pouvez faire tout le parcours : accueil → montant → questionnaire → profil → portefeuille → simulation → explication, et « Mes documents » depuis l'accueil.

## 8. Mettre en ligne sur Streamlit Community Cloud

1. Dans GitHub Desktop : cochez tous les fichiers **sauf** `secrets.toml`, message « V1 complète », **Commit**, puis **Push origin**. Ouvrez une Pull Request vers `main` (circuit de la section 4.5), Damien la fusionne.
2. Allez sur **share.streamlit.io**, connectez-vous avec GitHub.
3. **Create app** > dépôt `robo-advisor`, branche `main`, fichier principal `app.py`.
4. Dans **Advanced settings** : choisissez Python 3.12 ou plus, et collez le contenu de votre `secrets.toml` dans la zone **Secrets**.
5. **Deploy**. Le premier démarrage prend quelques minutes.

Les serveurs gratuits sont parfois bloqués par Yahoo : le site lit alors automatiquement `data/prix_snapshot.csv`. **Pensez à pousser ce fichier** et à le régénérer (étape 5) quelques jours avant la soutenance.

✅ L'adresse publique ouvre le site ; « Source des cours » (étape Portefeuille) indique `yahoo` ou `snapshot`, jamais `aucune`.

---

## En cas de problème

| Symptôme | Solution |
| --- | --- |
| `command not found: python` | Utilisez `python3`, ou activez l'environnement : `source .venv/bin/activate` |
| `SSL: CERTIFICATE_VERIFY_FAILED` | Relancez **Install Certificates.command** (dossier Python dans Applications) |
| Indicateurs « n.d. » sur le site | Pas de cours : lancez l'étape 5 et poussez `data/prix_snapshot.csv` |
| Texte d'explication = phrases fixes | Plan B : lisez la raison affichée sous le texte (étape 6) |
| Le site en ligne plante au démarrage | Sur share.streamlit.io : **Manage app** > journaux ; le plus souvent une librairie absente de `requirements.txt` |
