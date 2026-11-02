"""jeu-concours.biz — liste des nouveaux concours + liste complète."""
import re
import datetime as dt
from urllib.parse import urljoin

from .commun import telecharger, texte, montants, date_fin_depuis_texte, type_depuis_texte, carte_autour

NOM = "jeu-concours.biz"
BASE = "https://www.jeu-concours.biz/"
PAGES = ["nouveaux-concours.html"] + [f"nouveaux-concours.html?page={n}" for n in range(2, 6)] + ["concours-bientot-clos.html"]
LIEN = re.compile(r"(?:^|/)concours/\d+\.html$")


def _une_carte(a):
    carte = carte_autour(a, LIEN)
    brut = texte(carte)
    url = urljoin(BASE, a["href"])
    cid = re.search(r"concours/(\d+)\.html", url).group(1)

    orga = ""
    lien_orga = carte.find("a", href=re.compile(r"(?:^|/)jeux-concours/[^/]+/?$"))
    if lien_orga:
        orga = texte(lien_orga)
    titre_el = carte.find(["h2", "h3", "h4"])
    titre = texte(titre_el) or orga

    fin = None
    clos = carte.find("a", href=re.compile(r"concours-clos-le-(\d{2})-(\d{2})-(\d{4})"))
    if clos:
        j, m, a_ = re.search(r"clos-le-(\d{2})-(\d{2})-(\d{4})", clos["href"]).groups()
        fin = dt.date(int(a_), int(m), int(j))
    else:
        fin = date_fin_depuis_texte(brut)

    lots = brut
    m = re.search(r"Cadeaux? à gagner\s*:?\s*(.+?)(?:Principe du concours|Réponses?\s*:|Concours noté|jeu n°|$)", brut, re.I)
    if m:
        lots = m.group(1).strip()
    lots = re.sub(r"\s*PARTICIPER\b.*$", "", lots)

    # Les types sont souvent des icônes : on lit aussi les alt/title des images.
    icones = " ".join((i.get("alt") or "") + " " + (i.get("title") or "") for i in carte.find_all(["img", "span", "i"]))
    vals = montants(lots)
    return {
        "id": f"jcb-{cid}", "source": NOM, "titre": titre[:160], "organisateur": orga[:80],
        "lots": lots[:400], "valeur": max(vals) if vals else None,
        "fin": fin, "type": type_depuis_texte(icones + " " + brut), "categorie": None,
        "lien": url, "lien_source": url, "texte_brut": brut[:1500],
    }


def collecter(journal=print):
    vus, out = set(), []
    for page in PAGES:
        try:
            soup = telecharger(urljoin(BASE, page))
        except Exception as e:
            journal(f"[{NOM}] {page} : {e}")
            continue
        for a in soup.find_all("a", href=LIEN):
            href = a["href"].split("#")[0]
            if href in vus:
                continue
            vus.add(href)
            try:
                out.append(_une_carte(a))
            except Exception as e:
                journal(f"[{NOM}] carte ignorée ({href}) : {e}")
    return out
