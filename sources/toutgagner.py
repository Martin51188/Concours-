"""toutgagner.com — liste triée par dotation (les plus gros lots d'abord)."""
import re
from urllib.parse import urljoin

from .commun import telecharger, texte, montants, date_fin_depuis_texte, type_depuis_texte, carte_autour

NOM = "toutgagner.com"
BASE = "https://toutgagner.com/"
NB_PAGES = 6
LIEN = re.compile(r"/concours/[gc]\d+\.html")


def _une_carte(a):
    carte = carte_autour(a, LIEN)
    brut = texte(carte)
    url = urljoin(BASE, a["href"])
    cid = re.search(r"/concours/([gc]\d+)\.html", url).group(1)

    orga = ""
    regl = carte.find("a", href=re.compile(r"/jeux-concours/([^/]+)/reglement-"))
    if regl:
        orga = re.search(r"/jeux-concours/([^/]+)/reglement-", regl["href"]).group(1).replace("-", " ").title()
    titre = texte(carte.find(["h2", "h3", "h4"])) or texte(a)
    if re.fullmatch(r"[Xx]+", titre.replace(" ", "")):  # titre masqué pour les non-abonnés
        titre = ""

    valeur = None
    m = re.search(r"Dotation\s*:?\s*([\d   .]+)\s*€", brut)
    if m:
        v = montants(m.group(1) + " €")
        valeur = v[0] if v else None
    m = re.search(r"Les lots à gagner\s*:?\s*(.+?)(?:Dotation|Fin du jeu|Date limite|Types? de jeu|$)", brut, re.I)
    lots = m.group(1).strip() if m else brut
    lots = re.sub(r"(Au tirage au sort|Aux instants gagnants|Au prétirage[^:]*)\s*:\s*", "", lots).strip()
    lots = re.sub(r"\s*Participer\s*$", "", lots)
    vals = montants(lots)
    valeur_lot = max(vals) if vals else valeur

    fin = None
    m = re.search(r"Date limite\s*:?\s*(\d{2}/\d{2}/\d{4})", brut)
    fin = date_fin_depuis_texte(m.group(1) if m else brut)
    m = re.search(r"Types? de jeu[- ]concours\s*:?\s*([^:]+?)(?:\bPays\b|\b[AÂ]ge\b|\bAjouté|\bRèglement|$)", brut)
    age = re.search(r"\b[AÂ]ge\s*:?\s*([^:]{0,40}?ans(?: et plus)?)", brut)
    pays = re.search(r"\bPays\s*:?\s*([A-Za-zÀ-ÿ ,]+?)\s*(?:\b[AÂ]ge\b|\bAjouté|\bTypes?\b|\bRèglement|$)", brut)
    return {
        "id": f"tg-{cid}", "source": NOM, "titre": (titre or orga)[:160], "organisateur": orga[:80],
        "lots": lots[:400], "valeur": valeur_lot, "dotation_totale": valeur,
        "fin": fin, "type": type_depuis_texte(m.group(1) if m else brut), "categorie": None,
        "age": age.group(1).strip() if age else None, "pays": pays.group(1).strip() if pays else None,
        "lien": url, "lien_source": url, "texte_brut": brut[:1500],
    }


def collecter(journal=print):
    vus, out = set(), []
    for n in range(1, NB_PAGES + 1):
        url = urljoin(BASE, "jeux-concours/") + f"?par=dotation&page={n}"
        try:
            soup = telecharger(url)
        except Exception as e:
            journal(f"[{NOM}] page {n} : {e}")
            break
        trouves = 0
        for a in soup.find_all("a", href=LIEN):
            if "A LA UNE" in a.find_parent().get_text(" ")[:80].upper():
                continue
            href = a["href"].split("#")[0]
            if href in vus:
                continue
            vus.add(href)
            trouves += 1
            try:
                out.append(_une_carte(a))
            except Exception as e:
                journal(f"[{NOM}] carte ignorée ({href}) : {e}")
        if not trouves:
            break
    return out
