"""Trouve le lien direct vers le formulaire de la marque (un seul clic pour participer)
et repère les concours qui se jouent en fait sur un réseau social."""
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote_plus, urlparse

import requests
from bs4 import BeautifulSoup

from .commun import UA, sans_accents

SOCIAUX = {
    "instagram.com": "instagram", "facebook.com": "facebook", "fb.me": "facebook", "fb.com": "facebook",
    "m.facebook.com": "facebook", "x.com": "reseau", "twitter.com": "reseau", "t.co": "reseau",
    "tiktok.com": "reseau", "youtube.com": "reseau", "youtu.be": "reseau", "threads.net": "reseau",
    "snapchat.com": "reseau", "twitch.tv": "reseau", "discord.gg": "reseau", "discord.com": "reseau",
}
_H = {"User-Agent": UA, "Accept-Language": "fr-FR,fr;q=0.9"}


def type_social(url):
    hote = (urlparse(url or "").hostname or "").lower().removeprefix("www.")
    for dom, t in SOCIAUX.items():
        if hote == dom or hote.endswith("." + dom):
            return t
    return None


def _get(url, **kw):
    return requests.get(url, headers=_H, timeout=15, **kw)


def _final(url):
    """URL finale après redirections HTTP (sans télécharger toute la page)."""
    try:
        r = _get(url, allow_redirects=True, stream=True)
        fin = r.url
        r.close()
        return fin
    except Exception:
        return url


def _jcb(c):
    # La page /concours/N.html redirige en JavaScript : location='https://…'
    t = _get(c["lien"]).text
    m = re.search(r"location\s*=\s*['\"](https?://[^'\"]+)", t)
    return m.group(1) if m else None


def _sweepstakes_bible(c):
    s = BeautifulSoup(_get(c["lien"]).text, "html.parser")
    a = s.find("a", string=re.compile(r"ENTER TO WIN", re.I), href=re.compile(r"^https?://"))
    return a["href"] if a else None


def _jcg_social(c):
    t = sans_accents(_get(c["lien"]).text[:400000])
    m = re.search(r"comment participer a ce concours.{0,400}", t)
    zone = m.group(0) if m else ""
    if re.search(r"instagram", zone):
        return "instagram"
    if re.search(r"facebook", zone):
        return "facebook"
    if re.search(r"compte x\b|ex-twitter|twitter|tiktok|youtube", zone):
        return "reseau"
    return None


def resoudre(c):
    """Complète c['lien_direct'] et corrige c['type'] si le concours est sur un réseau social."""
    src, direct = c["source"], c.get("lien_direct")
    try:
        if src == "jeu-concours.biz":
            direct = _jcb(c)
        elif src == "sweepstakesbible.com":
            direct = _sweepstakes_bible(c)
        elif src == "concours-du-net.com":
            direct = "https://www.concours-du-net.com/track.php?token=" + c["id"].split("-", 1)[1]
        elif src == "jeuxconcoursgratuits.fr":
            t = _jcg_social(c)
            if t:
                c["type"] = t
        elif src == "toutgagner.com":
            # Le lien de toutgagner demande un compte : on va droit au 1er résultat de recherche.
            q = f"jeu concours {c['organisateur']} {c['lots'][:60]}"
            direct = "https://duckduckgo.com/?q=" + quote_plus("\\" + q)
        if direct and src in ("ledemondujeu.com", "concours-du-net.com"):
            direct = _final(direct)   # suit le traqueur jusqu'au site de la marque
    except Exception:
        pass
    if direct:
        c["lien_direct"] = direct
        t = type_social(direct)
        if t:
            c["type"] = t
    return c


def resoudre_tous(liste, max_n=500, journal=print):
    a_faire = liste[:max_n]
    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(resoudre, a_faire))
    sociaux = sum(c["type"] in ("instagram", "facebook", "reseau") for c in a_faire)
    directs = sum(bool(c.get("lien_direct")) for c in a_faire)
    journal(f"liens directs trouvés : {directs}/{len(a_faire)} · concours sur réseaux sociaux repérés : {sociaux}")
