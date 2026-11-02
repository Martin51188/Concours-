"""Chasseur de Concours — l'agent.

Chaque passage :
  1. va lire les sites qui recensent les jeux concours français,
  2. lit pour chaque concours les lots, leur valeur, la date de fin et le type,
  3. garde ceux qui correspondent à tes critères (config.json),
  4. les range dans data/concours.db avec un score (les meilleurs en premier).

Tu participes toi-même depuis le tableau de bord : les règlements annulent
les participations faites par un robot.

Utilisation :  python agent.py            (collecte une fois)
               python agent.py --notifier (collecte + notification Windows)
"""
import json
import math
import re
import sqlite3
import subprocess
import sys
import datetime as dt
from pathlib import Path

import os
import urllib.request

from sources import jeu_concours_biz, toutgagner, jeuxconcoursgratuits
from sources.autres import concours_du_net, demon_du_jeu
from sources.commun import estimer_valeur, sans_accents

ICI = Path(__file__).resolve().parent
CONFIG = ICI / "config.json"
BASE_DONNEES = ICI / "data" / "concours.db"
JOURNAL = ICI / "data" / "journal.txt"
SOURCES = [jeu_concours_biz, toutgagner, jeuxconcoursgratuits, concours_du_net, demon_du_jeu]

CONFIG_DEFAUT = {
    "valeur_min": 100,
    "jours_min": 0,
    "types_exclus": [],
    "mots_exclus": ["achat obligatoire", "preuve d'achat", "ticket de caisse", "réservé aux enfants",
                    "belgique uniquement", "suisse uniquement", "canada", "québec", "luxembourg uniquement"],
    "mots_voulus": ["iphone", "ps5", "voyage", "chèque", "carte cadeau", "ordinateur", "switch"],
    "age_utilisateur": 18,
    "profil": {"civilite": "M.", "prenom": "", "nom": "", "email": "", "telephone": "",
               "adresse": "", "code_postal": "", "ville": "", "date_naissance": ""},
}


# ---------------- config ----------------
def lire_config():
    if CONFIG.exists():
        try:
            c = json.loads(CONFIG.read_text(encoding="utf-8"))
            return {**CONFIG_DEFAUT, **c, "profil": {**CONFIG_DEFAUT["profil"], **c.get("profil", {})}}
        except Exception:
            pass
    ecrire_config(CONFIG_DEFAUT)
    return json.loads(json.dumps(CONFIG_DEFAUT))


def ecrire_config(c):
    CONFIG.write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------- base de données ----------------
def connexion():
    BASE_DONNEES.parent.mkdir(exist_ok=True)
    db = sqlite3.connect(BASE_DONNEES)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS concours (
        id TEXT PRIMARY KEY, source TEXT, titre TEXT, organisateur TEXT, lots TEXT,
        valeur REAL, valeur_estimee INTEGER DEFAULT 0, fin TEXT, type TEXT, categorie TEXT,
        lien TEXT, lien_source TEXT, cle TEXT, ajoute_le TEXT, vu_le TEXT,
        statut TEXT DEFAULT 'nouveau', statut_le TEXT, texte_brut TEXT)""")
    db.execute("CREATE INDEX IF NOT EXISTS i_cle ON concours(cle)")
    return db


def journal(msg):
    ligne = f"{dt.datetime.now():%Y-%m-%d %H:%M} {msg}"
    print(ligne)
    try:
        JOURNAL.parent.mkdir(exist_ok=True)
        with JOURNAL.open("a", encoding="utf-8") as f:
            f.write(ligne + "\n")
    except Exception:
        pass


# ---------------- tri ----------------
def _age_ok(age_txt, age_user):
    """Exclut les concours réservés à une tranche d'âge qui ne te correspond pas (ex. « 3 à 10 ans »)."""
    if not age_txt:
        return True
    nb = [int(x) for x in re.findall(r"\d+", age_txt)]
    if len(nb) >= 2 and not (nb[0] <= age_user <= nb[1]):
        return False
    if len(nb) == 1 and "plus" in age_txt and age_user < nb[0]:
        return False
    return True


def garder(c, cfg, auj):
    """Renvoie (True, '') si le concours passe les filtres, sinon (False, raison)."""
    if c["fin"] and (c["fin"] - auj).days < cfg["jours_min"]:
        return False, "se termine trop tôt"
    if c["fin"] and c["fin"] < auj:
        return False, "terminé"
    if not c["fin"] and c["valeur"] is None:
        return False, "infos incomplètes"
    if c["type"] in cfg["types_exclus"]:
        return False, f"type {c['type']} exclu"
    t = sans_accents(c["lots"] + " " + c.get("texte_brut", ""))
    for mot in cfg["mots_exclus"]:
        if mot.strip() and sans_accents(mot.strip()) in t:
            return False, f"mot exclu « {mot} »"
    if not _age_ok(c.get("age"), cfg.get("age_utilisateur", 18)):
        return False, "tranche d'âge"
    if c["valeur"] is not None and c["valeur"] < cfg["valeur_min"]:
        return False, "valeur trop faible"
    return True, ""


def score(c, cfg, auj):
    v = c["valeur"] or 0
    s = math.log10(max(v, 10)) * 2.5                    # 100 € → 5 ; 1 000 € → 7,5 ; 10 000 € → 10
    if c.get("valeur_estimee"):
        s -= 0.7
    if c["fin"]:
        j = (dt.date.fromisoformat(c["fin"]) if isinstance(c["fin"], str) else c["fin"]) - auj
        s += 1.2 if j.days <= 2 else 0.6 if j.days <= 7 else 0
    s += {"tirage": 0.8, "instant": 0.6, "autre": 0, "facebook": -0.5, "instagram": -0.8}.get(c["type"], 0)
    t = sans_accents(c["lots"])
    if any(sans_accents(m.strip()) in t for m in cfg["mots_voulus"] if m.strip()):
        s += 1.5
    return round(s, 2)


def cle_doublon(c):
    """Le même concours apparaît souvent sur plusieurs sites : organisateur + date de fin + valeur."""
    orga = re.sub(r"[^a-z0-9]", "", sans_accents(c["organisateur"] or c["titre"]))[:12]
    return f"{orga}|{c['fin'] or ''}|{int(c['valeur'] or 0)}"


# ---------------- passage complet ----------------
def collecter():
    cfg = lire_config()
    auj = dt.date.today()
    db = connexion()
    nouveaux, erreurs, bruts = [], [], []

    for src in SOURCES:
        try:
            lot = src.collecter(journal=lambda m: (erreurs.append(m), journal(m)))
            journal(f"[{src.NOM}] {len(lot)} concours lus")
            bruts += lot
        except Exception as e:
            erreurs.append(f"[{src.NOM}] {e}")
            journal(f"[{src.NOM}] ERREUR {e}")

    rejets = {}
    for c in bruts:
        c["valeur_estimee"] = 0
        if c["valeur"] is None:
            est = estimer_valeur(c["lots"])
            if est:
                c["valeur"], c["valeur_estimee"] = est, 1
        ok, raison = garder(c, cfg, auj)
        if not ok:
            rejets[raison] = rejets.get(raison, 0) + 1
            continue
        c["cle"] = cle_doublon(c)
        fin = c["fin"].isoformat() if c["fin"] else None
        existe = db.execute("SELECT id FROM concours WHERE id=?", (c["id"],)).fetchone()
        if existe:
            db.execute("UPDATE concours SET vu_le=?, valeur=?, valeur_estimee=?, fin=?, lots=? WHERE id=?",
                       (auj.isoformat(), c["valeur"], c["valeur_estimee"], fin, c["lots"], c["id"]))
            continue
        if c["valeur"] and db.execute("SELECT 1 FROM concours WHERE cle=?", (c["cle"],)).fetchone():
            rejets["doublon"] = rejets.get("doublon", 0) + 1
            continue
        db.execute("""INSERT INTO concours (id, source, titre, organisateur, lots, valeur, valeur_estimee, fin,
                      type, categorie, lien, lien_source, cle, ajoute_le, vu_le, texte_brut)
                      VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                   (c["id"], c["source"], c["titre"], c["organisateur"], c["lots"], c["valeur"],
                    c["valeur_estimee"], fin, c["type"], c.get("categorie"), c["lien"], c["lien_source"],
                    c["cle"], auj.isoformat(), auj.isoformat(), c.get("texte_brut", "")))
        nouveaux.append(c)
    db.commit()
    db.close()
    journal(f"{len(bruts)} lus, {len(nouveaux)} nouveaux retenus, écartés : {rejets}")
    return {"ok": True, "lus": len(bruts), "nouveaux": len(nouveaux), "ecartes": rejets,
            "erreurs": erreurs[:10], "top": sorted(nouveaux, key=lambda c: -(c["valeur"] or 0))[:3],
            "top_tous": sorted(nouveaux, key=lambda c: -(c["valeur"] or 0))}


def liste_concours():
    cfg = lire_config()
    auj = dt.date.today()
    db = connexion()
    lignes = [dict(r) for r in db.execute("SELECT * FROM concours")]
    db.close()
    out = []
    for c in lignes:
        if c["fin"] and c["fin"] < auj.isoformat() and c["statut"] != "participe":
            continue  # terminé : on ne l'affiche plus
        c.pop("texte_brut", None)
        c["valeur_estimee"] = bool(c["valeur_estimee"])
        c["score"] = score(c, cfg, auj)
        out.append(c)
    out.sort(key=lambda c: -c["score"])
    faits = [c for c in out if c["statut"] == "participe"]
    return {
        "maj": dernier_passage(),
        "concours": out,
        "stats": {
            "total": len(out),
            "nouveaux": sum(c["statut"] in ("nouveau", "favori") for c in out),
            "participes": len(faits),
            "participes_aujourdhui": sum((c["statut_le"] or "").startswith(auj.isoformat()) for c in faits),
            "valeur_totale": round(sum(c["valeur"] or 0 for c in faits)),
        },
    }


def changer_statut(cid, statut):
    if statut not in ("nouveau", "participe", "ignore", "favori"):
        raise ValueError("statut inconnu")
    db = connexion()
    db.execute("UPDATE concours SET statut=?, statut_le=? WHERE id=?",
               (statut, dt.datetime.now().isoformat(timespec="seconds"), cid))
    db.commit()
    db.close()


def dernier_passage():
    try:
        for ligne in reversed(JOURNAL.read_text(encoding="utf-8").splitlines()):
            if "nouveaux retenus" in ligne:
                return dt.datetime.strptime(ligne[:16], "%Y-%m-%d %H:%M").isoformat()
    except Exception:
        pass
    return None


def notifier(res):
    """Petite bulle de notification Windows (sans rien installer)."""
    if sys.platform != "win32" or not res["nouveaux"]:
        return
    top = res["top"][0] if res["top"] else None
    msg = f"{res['nouveaux']} nouveaux concours"
    if top:
        msg += f" — dont {top['organisateur'] or top['titre'][:30]} ({int(top['valeur'] or 0)} €)"
    msg = msg.replace("'", "’")
    ps = ("Add-Type -AssemblyName System.Windows.Forms; Add-Type -AssemblyName System.Drawing;"
          "$n=New-Object System.Windows.Forms.NotifyIcon; $n.Icon=[System.Drawing.SystemIcons]::Information;"
          "$n.BalloonTipTitle='Chasseur de Concours'; $n.BalloonTipText='" + msg + "';"
          "$n.Visible=$true; $n.ShowBalloonTip(8000); Start-Sleep -s 9; $n.Dispose()")
    subprocess.Popen(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def publier():
    """Écrit web/concours.json pour la version en ligne (GitHub Pages)."""
    d = liste_concours()
    cfg = lire_config()
    for c in d["concours"]:
        c["statut"] = "nouveau"   # en ligne, les statuts sont gardés sur ton téléphone
        c.pop("statut_le", None)
        c.pop("cle", None)
    d["maj"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    d["config"] = {k: cfg[k] for k in ("valeur_min", "jours_min", "types_exclus", "mots_exclus", "mots_voulus")}
    (ICI / "web" / "concours.json").write_text(json.dumps(d, ensure_ascii=False, default=str), encoding="utf-8")
    journal(f"concours.json publié ({len(d['concours'])} concours)")


def notifier_telephone(res):
    """Notification sur le téléphone via l'appli gratuite ntfy (sujet dans NTFY_TOPIC)."""
    sujet = os.environ.get("NTFY_TOPIC")
    seuil = float(os.environ.get("NTFY_SEUIL", "300"))
    gros = [c for c in res.get("top_tous", []) if (c["valeur"] or 0) >= seuil]
    if not sujet or not gros:
        return
    lignes = [f"• {c['organisateur'] or c['titre'][:40]} — {int(c['valeur'])} €"
              + (f" (fin {c['fin']:%d/%m})" if c.get("fin") else "") for c in gros[:5]]
    corps = "\n".join(lignes) + (f"\n…et {len(gros) - 5} autres" if len(gros) > 5 else "")
    titre = f"{len(gros)} nouveau{'x' if len(gros) > 1 else ''} concours à plus de {int(seuil)} €"
    req = urllib.request.Request(f"https://ntfy.sh/{sujet}", data=corps.encode("utf-8"), method="POST",
                                 headers={"Title": titre.encode("utf-8"), "Tags": "tada",
                                          "Click": os.environ.get("URL_TABLEAU", "")})
    try:
        urllib.request.urlopen(req, timeout=15)
        journal(f"notification envoyée ({len(gros)} concours)")
    except Exception as e:
        journal(f"notification impossible : {e}")


if __name__ == "__main__":
    r = collecter()
    if "--notifier" in sys.argv:
        notifier(r)
    if "--publier" in sys.argv:
        publier()
        notifier_telephone(r)
