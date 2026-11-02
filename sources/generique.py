"""Extracteur générique : une page de liste + un motif de lien = des concours.
Sert pour les sites dont la mise en page est simple (lots et valeur dans le texte du bloc)."""
import re
from urllib.parse import urljoin

from .commun import telecharger, texte, montants, date_fin_depuis_texte, type_depuis_texte, carte_autour

_BRUIT = re.compile(r"\b(Participer|Je participe|Jouer|Voir le concours|Lire la suite|En savoir plus|"
                    r"Nouveau|Ajouté le \S+|Clôture\s*:?|Fin\s*:?)\b", re.I)


class Source:
    def __init__(self, nom, base, pages, lien, prefixe, id_depuis_url=None, fin_depuis_url=None,
                 orga_depuis_url=None):
        self.NOM, self.base, self.pages, self.lien, self.prefixe = nom, base, pages, lien, prefixe
        self.id_depuis_url = id_depuis_url or (lambda u: re.sub(r"\W+", "-", u.split("/")[-1])[-60:])
        self.fin_depuis_url = fin_depuis_url
        self.orga_depuis_url = orga_depuis_url

    def _une_carte(self, a):
        carte = carte_autour(a, self.lien)
        brut = texte(carte)
        url = urljoin(self.base, a["href"])
        titre = texte(carte.find(["h2", "h3", "h4"])) or texte(a)
        m = re.search(r"(?:Lots|Cadeaux?) à gagner\s*:?\s*(.+?)(?:Principe|Comment participer|Réponses?\s*:|Commentaires|Concours noté|Règlement|$)", brut, re.I)
        lots = m.group(1) if m else brut
        lots = re.sub(r"\s+", " ", _BRUIT.sub(" ", lots)).strip(" •·-")
        vals = montants(lots)
        fin = (self.fin_depuis_url(url) if self.fin_depuis_url else None) or date_fin_depuis_texte(brut)
        orga = self.orga_depuis_url(url) if self.orga_depuis_url else ""
        return {
            "id": f"{self.prefixe}-{self.id_depuis_url(url)}", "source": self.NOM,
            "titre": (titre or lots)[:160], "organisateur": orga[:80], "lots": lots[:400],
            "valeur": max(vals) if vals else None, "fin": fin, "type": type_depuis_texte(brut),
            "categorie": None, "lien": url, "lien_source": url, "texte_brut": brut[:1500],
        }

    def collecter(self, journal=print):
        vus, out = set(), []
        for page in self.pages():
            try:
                soup = telecharger(urljoin(self.base, page))
            except Exception as e:
                journal(f"[{self.NOM}] {page} : {e}")
                continue
            for a in soup.find_all("a", href=self.lien):
                href = a["href"].split("#")[0]
                if href in vus:
                    continue
                vus.add(href)
                try:
                    out.append(self._une_carte(a))
                except Exception as e:
                    journal(f"[{self.NOM}] carte ignorée ({href}) : {e}")
        return out
