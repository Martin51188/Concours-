"""Outils partagés par les extracteurs : téléchargement poli, lecture des montants, dates, types."""
import re
import time
import datetime as dt
import unicodedata

import requests
from bs4 import BeautifulSoup

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
_session = requests.Session()
_session.headers.update({"User-Agent": UA, "Accept-Language": "fr-FR,fr;q=0.9"})
_dernier_appel = 0.0


def telecharger(url, pause=1.5):
    """GET avec une pause entre deux requêtes pour ne pas surcharger les sites."""
    global _dernier_appel
    attente = pause - (time.time() - _dernier_appel)
    if attente > 0:
        time.sleep(attente)
    r = _session.get(url, timeout=25)
    _dernier_appel = time.time()
    r.raise_for_status()
    if not r.encoding or r.encoding.lower() == "iso-8859-1":
        r.encoding = r.apparent_encoding
    return BeautifulSoup(r.text, "html.parser")


def texte(el):
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip() if el else ""


def sans_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn").lower()


# ---------- montants ----------
_MONTANT = re.compile(
    r"(\d{1,3}(?:[   .]\d{3})+|\d+)(?:[,.](\d{1,2}))?\s*(?:€|euros?\b|eur\b)", re.I)


def montants(s):
    out = []
    for m in _MONTANT.finditer(s or ""):
        entier = re.sub(r"[   .]", "", m.group(1))
        try:
            v = float(entier)
        except ValueError:
            continue
        if 0 < v < 5_000_000:
            out.append(v)
    return out


# Valeur approximative quand le lot n'a pas de prix affiché (marquée « estimée »).
ESTIMATIONS = [
    (r"voiture|vehicule|automobile|\bsuv\b|tesla", 20000),
    (r"camping[- ]?car", 40000),
    (r"croisiere", 3000),
    (r"sejour|voyage|billets? d.avion|vol aller|week-?end", 1200),
    (r"macbook", 1300), (r"iphone", 1000), (r"ipad", 500), (r"airpods", 200),
    (r"samsung galaxy s\d|smartphone|telephone", 600),
    (r"ps5|playstation 5", 500), (r"xbox series", 450), (r"switch", 330),
    (r"ordinateur|pc portable|laptop", 900), (r"tele(vision|viseur)|\btv\b|oled", 700),
    (r"trottinette electrique", 450), (r"velo electrique|vae\b", 1500), (r"velo", 500),
    (r"dyson", 450), (r"thermomix", 1400), (r"robot (patissier|cuiseur)", 400),
    (r"montre connectee|apple watch", 400), (r"casque", 150), (r"enceinte", 120),
    (r"appareil photo|gopro", 400), (r"drone", 400), (r"console", 350),
]


def estimer_valeur(lots):
    t = sans_accents(lots)
    for motif, v in ESTIMATIONS:
        if re.search(motif, t):
            return float(v)
    return None


# ---------- dates ----------
MOIS = {m: i + 1 for i, m in enumerate(
    ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout",
     "septembre", "octobre", "novembre", "decembre"])}
MOIS.update({"janv": 1, "fev": 2, "fevr": 2, "avr": 4, "juil": 7, "sept": 9, "oct": 10, "nov": 11, "dec": 12})


def date_fin_depuis_texte(s, aujourd_hui=None):
    """Trouve une date de fin dans un texte libre : 14/11/2026, 14-11-2026, « dans 12 jours », J-5, demain…"""
    auj = aujourd_hui or dt.date.today()
    t = sans_accents(s)
    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", t)
    if m:
        try:
            return dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass
    m = re.search(r"\bj\s*-\s*(\d{1,3})\b", t)
    if m:
        return auj + dt.timedelta(days=int(m.group(1)))
    m = re.search(r"dans (\d{1,3}) jours?", t)
    if m:
        return auj + dt.timedelta(days=int(m.group(1)))
    if re.search(r"apres-demain", t):
        return auj + dt.timedelta(days=2)
    if re.search(r"\bdemain\b", t):
        return auj + dt.timedelta(days=1)
    if re.search(r"aujourd.hui|ce soir|derniers? jours?", t):
        return auj
    m = re.search(r"\b(\d{1,2}) (" + "|".join(MOIS) + r")\.?(?: (\d{4}))?", t)
    if m:
        an = int(m.group(3)) if m.group(3) else auj.year
        try:
            d = dt.date(an, MOIS[m.group(2)], int(m.group(1)))
            if not m.group(3) and d < auj - dt.timedelta(days=60):
                d = d.replace(year=an + 1)
            return d
        except ValueError:
            pass
    return None


def type_depuis_texte(s):
    t = sans_accents(s)
    if "instagram" in t:
        return "instagram"
    if "facebook" in t:
        return "facebook"
    if re.search(r"instant(s)? gagnants?", t):
        return "instant"
    if re.search(r"tirage|participation libre|inscription|questionnaire|quiz", t):
        return "tirage"
    return "autre"


def carte_autour(a, motif_lien, max_montee=7, max_car=1500):
    """Remonte depuis un lien jusqu'au bloc qui représente un concours entier
    (le plus grand ancêtre qui ne contient qu'un seul concours)."""
    meilleur = a
    el = a
    for _ in range(max_montee):
        el = el.parent
        if el is None or el.name in ("body", "html"):
            break
        liens = {x.get("href", "").split("#")[0] for x in el.find_all("a", href=motif_lien)}
        if len(liens) > 1 or len(texte(el)) > max_car:
            break
        meilleur = el
    return meilleur
