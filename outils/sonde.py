"""Diagnostic : enregistre les pages de liste brutes de chaque site pour ajuster les extracteurs."""
import sys, re, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import requests
from sources.commun import UA

PAGES = {
    "sb_worldwide": "https://www.sweepstakesbible.com/tags/worldwide",
    "sa_intl": "https://www.sweepsadvantage.com/international-sweepstakes",
    "os_worldwide": "https://online-sweepstakes.com/worldwide-giveaway/",
    "gl_intl": "https://giveawaylisting.com/international-giveaway-list/",
    "ofertar": "https://ofertar.pt/global-giveaways",
    "sweepsdb": "https://sweepsdb.com/",
    "giveawaydrop": "https://giveawaydrop.com/",
    "paradis_fr": "https://www.leparadisdesjeuxconcours.fr/",
    "c2000": "https://www.concours2000.com/",
}
out = pathlib.Path("sonde"); out.mkdir(exist_ok=True)
for nom, url in PAGES.items():
    try:
        r = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "fr-FR"}, timeout=25, allow_redirects=True)
        (out / f"{nom}.html").write_bytes(r.content)
        print(f"{nom:20} {r.status_code} {len(r.content):>8} o  -> {r.url}")
    except Exception as e:
        print(f"{nom:20} ERREUR {e}")
