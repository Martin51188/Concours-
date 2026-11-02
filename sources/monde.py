"""Concours internationaux ouverts au monde entier (donc aux résidents français).
Les valeurs en dollars sont converties approximativement en euros."""
import re
import datetime as dt
from urllib.parse import urljoin

from .commun import telecharger, texte, montants, carte_autour, type_depuis_texte

USD_EUR = 0.92
_DOLLARS = re.compile(r"\$\s?(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*([kKmM])?")


def dollars(s):
    """$9,578 → 9578 ; $10.2K+ → 10200 ; renvoie des euros."""
    out = []
    for m in _DOLLARS.finditer(s or ""):
        v = float(m.group(1).replace(",", ""))
        mult = {"k": 1e3, "m": 1e6}.get((m.group(2) or "").lower(), 1)
        out.append(round(v * mult * USD_EUR))
    return out + montants(s)


def _fin(brut):
    auj = dt.date.today()
    m = re.search(r"(?:Open For|Ends in)\s*:?\s*(\d{1,3})\s*Days?", brut, re.I)
    if m:
        return auj + dt.timedelta(days=int(m.group(1)))
    m = re.search(r"Ends in\s*\d{1,2}\s*Hours?", brut, re.I)
    return auj if m else None


def _entree(nom, prefixe, url, brut, titre, lots):
    vals = dollars(brut)
    t = type_depuis_texte(brut)
    return {
        "id": f"{prefixe}-{re.sub(r'[^a-z0-9]+', '-', url.lower())[-50:]}", "source": nom,
        "titre": titre[:160], "organisateur": "", "lots": lots[:400],
        "valeur": float(max(vals)) if vals else None, "fin": _fin(brut),
        "type": "tirage" if t == "autre" else t, "categorie": "🌍 International", "pays": "Monde",
        "lien": url, "lien_source": url, "texte_brut": brut[:1500],
    }


class SweepstakesBible:
    NOM = "sweepstakesbible.com"
    LIEN = re.compile(r"/giveaways/[a-z0-9-]+/?$")

    def collecter(self, journal=print):
        vus, out = set(), []
        for n in range(1, 6):
            url = "https://www.sweepstakesbible.com/tags/worldwide" + (f"?page={n}" if n > 1 else "")
            try:
                soup = telecharger(url)
            except Exception as e:
                journal(f"[{self.NOM}] page {n} : {e}")
                break
            nouveaux = 0
            for a in soup.find_all("a", href=self.LIEN):
                href = urljoin(url, a["href"])
                if href in vus:
                    continue
                vus.add(href)
                carte = carte_autour(a, self.LIEN)
                brut = texte(carte)
                if "worldwide" not in brut.lower():
                    continue
                titre = re.split(r"\s+Open For", brut)[0]
                titre = re.sub(r"^\d{4}\s+", "", titre)
                out.append(_entree(self.NOM, "sbw", href, brut, titre, titre))
                nouveaux += 1
            if not nouveaux:
                break
        return out


class SweepsDB:
    """Base mondiale : on ne garde que ce qui est annoncé ouvert à l'international."""
    NOM = "sweepsdb.com"
    LIEN = re.compile(r"^(?:https://sweepsdb\.com)?/?go/\d+")
    OUVERT = re.compile(r"worldwide|world ?wide|international|all countries|global giveaway|open to everyone", re.I)

    def collecter(self, journal=print):
        out, vus = [], set()
        try:
            soup = telecharger("https://sweepsdb.com/")
        except Exception as e:
            journal(f"[{self.NOM}] {e}")
            return out
        for a in soup.find_all("a", href=self.LIEN):
            href = urljoin("https://sweepsdb.com/", a["href"])
            if href in vus:
                continue
            vus.add(href)
            brut = texte(carte_autour(a, self.LIEN))
            if not self.OUVERT.search(brut):
                continue
            m = re.match(r"\d{1,2} \w{3}\s+(.+?)\s+Ends in", brut)
            titre = m.group(1) if m else brut[:90]
            desc = re.split(r"\d+ winners?|Entries", brut, maxsplit=1)[-1]
            out.append(_entree(self.NOM, "sdb", href, brut, titre, f"{titre} — {desc.strip()}"))
        return out


sweepstakes_bible = SweepstakesBible()
sweepsdb = SweepsDB()
