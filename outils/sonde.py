"""Diagnostic : enregistre les pages de liste brutes de chaque site pour ajuster les extracteurs."""
import sys, re, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import requests
from sources.commun import UA

PAGES = {
    "det_jeuxconcoursgratuits_0": "https://jeuxconcoursgratuits.fr/concours/cash/pepsico-100-000-menus-colonel-original-gubi",
    "det_jeuxconcoursgratuits_1": "https://jeuxconcoursgratuits.fr/concours/high-tech/rainbow6-ubi-com-ordinateur-gamer-4250-pctn",
    "det_sweepstakesbible_0": "https://www.sweepstakesbible.com/giveaways/ski-utah-super-stoked-snowy-sweepstakes-2026",
    "det_sweepstakesbible_1": "https://www.sweepstakesbible.com/giveaways/pfl-road-to-dubai-trip-sweepstakes",
    "det_toutgagner_0": "https://toutgagner.com/concours/g2217639.html",
    "det_toutgagner_1": "https://toutgagner.com/concours/g2219036.html",
    "det_jeu-concours_0": "https://www.jeu-concours.biz/concours/479875.html",
    "det_jeu-concours_1": "https://www.jeu-concours.biz/concours/480935.html",
    "det_ledemondujeu_0": "https://www.ledemondujeu.com/concours-delko.fr-gagnez-1-voiture-100-electrique-customisee-par-un-artiste-jusqu-au-30-novembre-2026.php",
    "det_ledemondujeu_1": "https://www.ledemondujeu.com/concours-ici.fr-gagnez-2-bons-sejours-belambra-clubs-de-5000-jusqu-au-06-novembre-2026.php",
    "det_concours-du-net_0": "https://www.concours-du-net.com/jeu-concours-vertbaudet-aa0f1394d75408ff",
    "det_concours-du-net_1": "https://www.concours-du-net.com/jeu-concours-thebradery-be33de57cfcd6111",
    "det_sweepsdb_0": "https://sweepsdb.com/go/10237817",
    "det_sweepsdb_1": "https://sweepsdb.com/go/10239440",
}
out = pathlib.Path("sonde"); out.mkdir(exist_ok=True)
for nom, url in PAGES.items():
    try:
        r = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "fr-FR"}, timeout=25, allow_redirects=True)
        (out / f"{nom}.html").write_bytes(r.content)
        print(f"{nom:20} {r.status_code} {len(r.content):>8} o  -> {r.url}")
    except Exception as e:
        print(f"{nom:20} ERREUR {e}")
