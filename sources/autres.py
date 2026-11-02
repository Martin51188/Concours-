"""Sites supplémentaires branchés sur l'extracteur générique."""
import re
import datetime as dt

from .commun import MOIS, sans_accents
from .generique import Source


def _jours_passes(fmt, n=5):
    auj = dt.date.today()
    return [fmt.format(d=(auj - dt.timedelta(days=i)).isoformat()) for i in range(1, n + 1)]


def _fin_demon(url):
    # …-jusqu-au-31-decembre-2026.php
    m = re.search(r"jusqu-au-(\d{1,2})-([a-z]+)-(\d{4})", sans_accents(url))
    if m and m.group(2) in MOIS:
        try:
            return dt.date(int(m.group(3)), MOIS[m.group(2)], int(m.group(1)))
        except ValueError:
            return None
    return None


concours_du_net = Source(
    nom="concours-du-net.com", base="https://www.concours-du-net.com/",
    pages=lambda: ["nouveaux-concours"] + _jours_passes("nouveaux-concours-{d}"),
    lien=re.compile(r"/jeu-concours-[a-z0-9-]+-[0-9a-f]{16}$"), prefixe="cdn",
    id_depuis_url=lambda u: u[-16:],
    orga_depuis_url=lambda u: re.search(r"jeu-concours-(.+)-[0-9a-f]{16}$", u).group(1).replace("-", " ").title(),
)

demon_du_jeu = Source(
    nom="ledemondujeu.com", base="https://www.ledemondujeu.com/",
    pages=lambda: ["nouveaux-jeux-concours.html", "jeux-concours-cloture.html"]
    + _jours_passes("nouveaux-jeux-concours-{d}.html", 3),
    lien=re.compile(r"/?concours-[^/]+-jusqu-au-[^/]+\.php$"), prefixe="ldj",
    id_depuis_url=lambda u: re.sub(r"[^a-z0-9]+", "-", u.split("/")[-1].lower())[8:70],
    fin_depuis_url=_fin_demon,
    lien_direct=re.compile(r"toconc\.php\?c=\d+"),
    orga_depuis_url=lambda u: re.search(r"concours-([^-]+(?:\.[a-z]{2,4})?)-", u.split("/")[-1]).group(1),
)
