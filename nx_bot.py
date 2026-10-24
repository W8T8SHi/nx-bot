#!/usr/bin/env python3
"""Prévient sur Discord quand multi-downloader-nx publie une nouvelle version.

  DISCORD_WEBHOOK   URL du webhook Discord (obligatoire)
  DISCORD_MENTION   ex. "<@123456789012345678>" (facultatif)

  python3 nx_bot.py          # une vérification (cron / GitHub Actions)
  python3 nx_bot.py --test   # envoie un message de test
  python3 nx_bot.py --loop   # tourne en continu sur ton PC (vérifie toutes les 30 min)

La dernière version connue est dans derniere_version.txt (au départ : v5.8.6).
"""
import json, os, sys, time, urllib.request, urllib.error

API = "https://api.github.com/repos/anidl/multi-downloader-nx/releases/latest"
HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "derniere_version.txt")


def post(content, embed=None):
    url = os.environ.get("DISCORD_WEBHOOK")
    if not url:
        sys.exit("Variable DISCORD_WEBHOOK manquante.")
    body = {"content": content}
    if embed:
        body["embeds"] = [embed]
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json", "User-Agent": "nx-notifier/1.0"})
    for _ in range(3):
        try:
            urllib.request.urlopen(req, timeout=15).read()
            return True
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(float(json.loads(e.read() or b"{}").get("retry_after", 2)))
                continue
            print("Erreur Discord", e.code)
            return False
        except Exception as e:
            print("Erreur réseau :", e)
            time.sleep(2)
    return False


def latest():
    h = {"Accept": "application/vnd.github+json", "User-Agent": "nx-notifier/1.0"}
    if os.environ.get("GITHUB_TOKEN"):
        h["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    return json.loads(urllib.request.urlopen(urllib.request.Request(API, headers=h), timeout=15).read())


def known():
    try:
        return open(STATE, encoding="utf8").read().strip()
    except OSError:
        return ""


def check():
    try:
        r = latest()
        tag = r["tag_name"]
    except Exception as e:
        print("GitHub illisible :", e)
        return
    old = known()
    if tag == old:
        print("Pas de nouvelle version (", tag, ")")
        return
    if not old:  # premier lancement : on mémorise sans message
        open(STATE, "w", encoding="utf8").write(tag + "\n")
        print("Version de départ :", tag)
        return
    body = (r.get("body") or "").strip()
    embed = {
        "title": f"🛠️ multi-downloader-nx {tag}",
        "description": (r.get("name") or tag) + ("\n\n" + body[:600] if body else ""),
        "url": r.get("html_url") or "https://github.com/anidl/multi-downloader-nx/releases",
        "color": 0x3B82F6,
    }
    mention = os.environ.get("DISCORD_MENTION", "")
    if post((mention + " " if mention else "") + f"Nouvelle version de multi-downloader-nx : {tag} (avant : {old})", embed):
        open(STATE, "w", encoding="utf8").write(tag + "\n")
        print("Annoncé :", tag)


if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else ""
    if a == "--test":
        print("Test envoyé." if post("✅ Test : le bot multi-downloader-nx est connecté. Version suivie : " + (known() or "?")) else "Échec.")
    elif a == "--loop":
        print("Bot lancé (Ctrl+C pour arrêter).")
        while True:
            check()
            time.sleep(1800)
    else:
        check()
