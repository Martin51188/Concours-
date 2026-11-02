"""Diagnostic : enregistre les pages de liste brutes de chaque site pour ajuster les extracteurs."""
import sys, re, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import requests
from sources.commun import UA

PAGES = {
    "jcb_nouveaux": "https://www.jeu-concours.biz/nouveaux-concours.html",
    "tg_dotation": "https://toutgagner.com/jeux-concours/?par=dotation",
    "jcg": "https://jeuxconcoursgratuits.fr/concours?sort=prize",
    "cdn": "https://www.concours-du-net.com/nouveaux-concours",
    "ldj": "https://www.ledemondujeu.com/nouveaux-jeux-concours.html",
    "paradis": "https://www.leparadisdesjeuxconcours.com/",
    "zone": "https://www.zone-concours.fr/",
    "c2000": "https://www.concours2000.com/",
    "koncours": "https://www.konkours.com/",
    "ouah": "https://www.jeux-concours-ouah.com/",
    "kuzeo_go_paradis": "https://www.kuzeo.com/go/leparadisdesjeuxconcours",
    "kuzeo_go_zone": "https://www.kuzeo.com/go/zone-concours",
    "kuzeo_go_c2000": "https://www.kuzeo.com/go/concours2000",
    "kuzeo_go_koncours": "https://www.kuzeo.com/go/koncours",
}
out = pathlib.Path("sonde"); out.mkdir(exist_ok=True)
for nom, url in PAGES.items():
    try:
        r = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "fr-FR"}, timeout=25, allow_redirects=True)
        (out / f"{nom}.html").write_bytes(r.content)
        print(f"{nom:20} {r.status_code} {len(r.content):>8} o  -> {r.url}")
    except Exception as e:
        print(f"{nom:20} ERREUR {e}")
