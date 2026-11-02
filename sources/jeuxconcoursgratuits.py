"""jeuxconcoursgratuits.fr — liste triée par valeur + par date de fin."""
import re
from urllib.parse import urljoin

from .commun import telecharger, texte, montants, date_fin_depuis_texte, type_depuis_texte, carte_autour

NOM = "jeuxconcoursgratuits.fr"
BASE = "https://jeuxconcoursgratuits.fr/"
PAGES = ["concours?sort=prize", "concours?sort=ending_soon", "concours"]
LIEN = re.compile(r"/concours/(?!archives)[a-z0-9-]+/[a-z0-9-]+-[a-z0-9]{4}/?$")
CATEGORIES = {"cash": "Argent", "voyage": "Voyage", "divers": "Autres", "high-tech": "High-Tech",
              "mode": "Mode", "alimentaire": "Gastronomie", "jeux": "Jeux", "maison": "Maison", "auto": "Auto"}


def _une_carte(a):
    # Ici chaque concours est souvent un grand lien qui contient tout le texte.
    carte = a if len(texte(a)) > 25 else carte_autour(a, LIEN)
    brut = texte(carte)
    url = urljoin(BASE, a["href"])
    cat_slug, slug = re.search(r"/concours/([a-z0-9-]+)/([a-z0-9-]+)/?$", url).groups()
    cid = slug.rsplit("-", 1)[-1]

    propre = re.sub(r"[🏆🎲🔥]", " ", brut)
    propre = re.sub(r"Participer gratuitement\s*→?", "", propre).strip()
    lots = re.sub(r"\bJ\s*-\s*\d+\b", " ", propre)
    for c in ("Cash", "Voyage", "Autres", "High-Tech", "Mode", "Gastronomie", "Jeux", "Maison", "Auto", *CATEGORIES.values()):
        lots = re.sub(rf"^\s*{re.escape(c)}\b", "", lots)
    orga_txt = slug.rsplit("-", 1)[0].split("-")[0]
    lots = re.sub(rf"^\s*{re.escape(orga_txt)}\S*\s*", "", lots.strip(), flags=re.I)
    lots = re.sub(r"\b(Participation libre|Tirage au sort)\b", "", lots)
    lots = re.sub(r"\s+", " ", lots).strip(" ·•-")
    vals = montants(propre)
    # Ici la valeur entre parenthèses est le total de tous les lots : on la ramène à un lot.
    paren = montants(" ".join(re.findall(r"\(([^)]*€[^)]*)\)", propre)))
    qte = re.match(r"\s*(\d{1,3}(?:[ .]\d{3})*|\d+)\s", lots)
    if paren and qte:
        n = int(re.sub(r"[ .]", "", qte.group(1)))
        if n > 1:
            vals = [max(paren) / n]
    orga = slug.rsplit("-", 1)[0].split("-")[0].title()
    return {
        "id": f"jcg-{cid}", "source": NOM, "titre": lots[:160], "organisateur": orga,
        "lots": lots[:400], "valeur": max(vals) if vals else None,
        "fin": date_fin_depuis_texte(propre), "type": type_depuis_texte(propre),
        "categorie": CATEGORIES.get(cat_slug, cat_slug.title()),
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
            if "assistant" in a.get_text(" ").lower():
                continue
            href = a["href"].split("#")[0].rstrip("/")
            if href in vus:
                continue
            vus.add(href)
            try:
                out.append(_une_carte(a))
            except Exception as e:
                journal(f"[{NOM}] carte ignorée ({href}) : {e}")
    return out
