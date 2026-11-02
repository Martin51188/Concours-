"""Petit serveur local : sert le tableau de bord sur http://127.0.0.1:8765 et l'API de l'agent."""
import json
import sys
import threading
import webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

import agent

PORT = 8765
WEB = Path(__file__).resolve().parent / "web"
_verrou_scan = threading.Lock()


class Gestionnaire(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(WEB), **k)

    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _corps(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        if self.path.startswith("/api/concours"):
            return self._json(agent.liste_concours())
        if self.path.startswith("/api/config"):
            return self._json(agent.lire_config())
        return super().do_GET()

    def do_POST(self):
        try:
            if self.path == "/api/statut":
                b = self._corps()
                agent.changer_statut(b["id"], b["statut"])
                return self._json({"ok": True})
            if self.path == "/api/config":
                b = self._corps()
                cfg = agent.lire_config()
                cfg.update({k: v for k, v in b.items() if k in agent.CONFIG_DEFAUT})
                agent.ecrire_config(cfg)
                return self._json({"ok": True})
            if self.path == "/api/scan":
                if not _verrou_scan.acquire(blocking=False):
                    return self._json({"ok": False, "erreurs": ["Une recherche est déjà en cours."]}, 409)
                try:
                    r = agent.collecter()
                    r.pop("top", None)
                    r.pop("top_tous", None)
                    return self._json(r)
                finally:
                    _verrou_scan.release()
            self._json({"ok": False, "erreur": "inconnu"}, 404)
        except Exception as e:
            self._json({"ok": False, "erreurs": [str(e)]}, 500)


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Gestionnaire)
    url = f"http://127.0.0.1:{PORT}/"
    print(f"Chasseur de Concours ouvert sur {url}  (ferme cette fenêtre pour arrêter)")
    if "--sans-navigateur" not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
