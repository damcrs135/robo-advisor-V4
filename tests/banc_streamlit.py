"""
banc_streamlit.py — Faux Streamlit pour exécuter les pages du site dans les tests (sans navigateur).

Il ne dessine rien : il exécute le script comme Streamlit le ferait, garde la session entre deux
exécutions, simule les clics (avec leurs callbacks) et le choix de page. Il sert à vérifier qu'aucune
page ne plante, quels que soient l'état et les réponses.

Utilisation :
    banc = Banc()                 # installe les faux modules streamlit / plotly / yfinance
    banc.lancer()                 # exécute app.py une fois
    banc.cliquer("btn_commencer") # appelle le callback puis relance
    banc.page = "analyse"         # choisit la page affichée par st.navigation
"""

from __future__ import annotations

import runpy
import sys
import types
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent


class Relance(Exception):
    """Levée par st.rerun()."""


class Arret(Exception):
    """Levée par st.stop()."""


class EtatSession(dict):
    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError as e:
            raise AttributeError(k) from e

    def __setattr__(self, k, v):
        self[k] = v

    def __delattr__(self, k):
        del self[k]


class _Rien:
    """Objet neutre : tout appel ou attribut renvoie un objet neutre ; utilisable comme contexte."""

    def __init__(self, st=None):
        self._st = st

    def __getattr__(self, nom):
        if self._st is not None and hasattr(self._st, nom):
            return getattr(self._st, nom)
        return _Rien()

    def __call__(self, *a, **k):
        return _Rien()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def __iter__(self):
        return iter([])

    def __bool__(self):
        return False


class Page:
    def __init__(self, cible, title=None, icon=None, url_path=None, default=False):
        self.cible, self.title, self.icon, self.default = cible, title, icon, default
        self.url_path = url_path or (cible.__name__ if callable(cible) else str(cible))

    def run(self):
        return self.cible()


class FauxStreamlit(types.ModuleType):
    def __init__(self, banc):
        super().__init__("streamlit")
        self._banc = banc
        self.session_state = banc.etat
        self.secrets = {}
        self.query_params = {}
        self.column_config = _Rien()
        self.Page = Page

    # --- mise en page
    def _bloc(self, *a, **k):
        return _Rien(self)

    container = expander = form = popover = empty = spinner = status = _bloc
    sidebar = property(lambda self: _Rien(self))

    def columns(self, spec, **k):
        n = spec if isinstance(spec, int) else len(spec)
        return [_Rien(self) for _ in range(n)]

    def tabs(self, noms, **k):
        return [_Rien(self) for _ in noms]

    # --- affichage (sans effet)
    def __getattr__(self, nom):
        if nom.startswith("__"):
            raise AttributeError(nom)
        return lambda *a, **k: _Rien(self)

    # --- widgets
    def _valeur(self, key, defaut):
        if key is not None:
            if key in self.session_state:
                return self.session_state[key]
            self.session_state[key] = defaut
        return defaut

    def _cb(self, key, on_change, args, kwargs):
        if key is not None and on_change is not None:
            self._banc.callbacks[key] = (on_change, args or (), kwargs or {})

    def radio(self, label, options, index=0, key=None, on_change=None, args=None, kwargs=None, format_func=str, **k):
        options = list(options)
        for o in options:
            format_func(o)
        self._cb(key, on_change, args, kwargs)
        return self._valeur(key, None if index is None or not options else options[index])

    def selectbox(self, label, options, index=0, key=None, on_change=None, args=None, kwargs=None, format_func=str, **k):
        return self.radio(label, options, index, key, on_change, args, kwargs, format_func)

    def segmented_control(self, label, options, default=None, key=None, on_change=None, args=None, kwargs=None, format_func=str, **k):
        options = list(options)
        for o in options:
            format_func(o)
        self._cb(key, on_change, args, kwargs)
        return self._valeur(key, default)

    pills = segmented_control

    def multiselect(self, label, options, default=None, key=None, on_change=None, args=None, kwargs=None, format_func=str, **k):
        for o in options:
            format_func(o)
        self._cb(key, on_change, args, kwargs)
        return self._valeur(key, list(default or []))

    def number_input(self, label, min_value=None, max_value=None, value="min", step=None, key=None, on_change=None, args=None, kwargs=None, **k):
        self._cb(key, on_change, args, kwargs)
        defaut = (min_value if min_value is not None else 0) if value == "min" else value
        return self._valeur(key, defaut)

    def slider(self, label, min_value=None, max_value=None, value=None, step=None, key=None, on_change=None, args=None, kwargs=None, **k):
        self._cb(key, on_change, args, kwargs)
        return self._valeur(key, value if value is not None else min_value)

    select_slider = slider

    def checkbox(self, label, value=False, key=None, on_change=None, args=None, kwargs=None, **k):
        self._cb(key, on_change, args, kwargs)
        return self._valeur(key, value)

    toggle = checkbox

    def text_input(self, label, value="", key=None, on_change=None, args=None, kwargs=None, **k):
        self._cb(key, on_change, args, kwargs)
        return self._valeur(key, value)

    text_area = text_input

    def button(self, label, key=None, on_click=None, args=None, kwargs=None, disabled=False, **k):
        cle = key or label
        if disabled:
            self._banc.desactives.add(cle)
            return False
        self._banc.boutons[cle] = (on_click, args or (), kwargs or {})
        return self._banc.clics.pop(cle, False)

    form_submit_button = button

    def download_button(self, label, data=None, key=None, **k):
        if callable(data):
            data()
        self._banc.boutons[key or label] = (None, (), {})
        return False

    def link_button(self, *a, **k):
        return False

    def page_link(self, *a, **k):
        return _Rien(self)

    def plotly_chart(self, fig, **k):
        self._banc.graphiques.append(fig)
        return _Rien(self)

    def navigation(self, pages, **k):
        if isinstance(pages, dict):
            pages = [p for groupe in pages.values() for p in groupe]
        self._banc.pages = {p.url_path: p for p in pages}
        voulue = self._banc.page
        for p in pages:
            if p.url_path == voulue:
                return p
        return next((p for p in pages if p.default), pages[0])

    def switch_page(self, page):
        self._banc.page = page.url_path if isinstance(page, Page) else str(page)
        raise Relance()

    def rerun(self, *a, **k):
        raise Relance()

    def stop(self):
        raise Arret()

    @staticmethod
    def cache_data(fonction=None, **k):
        if fonction is None:
            return lambda f: f
        return fonction

    cache_resource = cache_data

    @staticmethod
    def dialog(*a, **k):
        return lambda f: f

    @staticmethod
    def fragment(fonction=None, **k):
        return fonction if fonction is not None else (lambda f: f)


class _FauxPlotly(types.ModuleType):
    def __getattr__(self, nom):
        if nom.startswith("__"):
            raise AttributeError(nom)
        return lambda *a, **k: _Rien()


class Banc:
    def __init__(self, fichier: str = "app.py"):
        self.fichier = str(RACINE / fichier)
        self.etat = EtatSession()
        self.callbacks, self.boutons, self.clics, self.desactives = {}, {}, {}, set()
        self.pages, self.page, self.graphiques = {}, None, []
        self.st = FauxStreamlit(self)
        plotly = _FauxPlotly("plotly")
        go = _FauxPlotly("plotly.graph_objects")
        plotly.graph_objects = go
        yf = _FauxPlotly("yfinance")
        sys.modules.update({"streamlit": self.st, "plotly": plotly, "plotly.graph_objects": go, "yfinance": yf})
        # les modules du site qui ont importé un ancien faux Streamlit sont rechargés
        for nom in ["etat", "accueil_marche", "app"] + [m for m in sys.modules if m == "vues" or m.startswith("vues.")]:
            sys.modules.pop(nom, None)
        if str(RACINE) not in sys.path:
            sys.path.insert(0, str(RACINE))

    def lancer(self, max_relances: int = 8):
        for _ in range(max_relances):
            self.boutons, self.graphiques, self.desactives = {}, [], set()
            try:
                runpy.run_path(self.fichier, run_name="__main__")
                return
            except Relance:
                continue
            except Arret:
                return
        raise RuntimeError("Trop de relances successives (boucle de st.rerun ?)")

    def cliquer(self, cle: str):
        """Clique sur un bouton affiché lors de la dernière exécution, puis relance le script."""
        if cle not in self.boutons:
            raise KeyError(f"Bouton {cle!r} absent. Boutons affichés : {sorted(self.boutons)}")
        cb, args, kwargs = self.boutons[cle]
        try:
            if cb:
                cb(*args, **kwargs)
        except Relance:
            pass
        self.clics[cle] = True
        self.lancer()

    def choisir(self, cle: str, valeur):
        """Change la valeur d'un widget (comme un clic de l'utilisateur), appelle son on_change, relance."""
        self.etat[cle] = valeur
        if cle in self.callbacks:
            cb, args, kwargs = self.callbacks[cle]
            cb(*args, **kwargs)
        self.lancer()

    def aller(self, page: str):
        self.page = page
        self.lancer()
