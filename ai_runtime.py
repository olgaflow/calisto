"""Moteur IA integre a Calisto.

Ce module regroupe tout ce qui concerne Ollama : detection du serveur local,
demarrage automatique sans fenetre console et gestion des modeles installes.
"""

import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

OLLAMA_HOST = "127.0.0.1"
OLLAMA_PORT = 11434
OLLAMA_URL = "http://{}:{}".format(OLLAMA_HOST, OLLAMA_PORT)
DOWNLOAD_URL = "https://ollama.com/download"

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def is_running(timeout=1.0):
    """Vrai si le serveur Ollama repond sur le port local."""
    try:
        with socket.create_connection((OLLAMA_HOST, OLLAMA_PORT), timeout=timeout):
            return True
    except OSError:
        return False


def find_executable():
    """Retrouve l'executable ollama (PATH puis installations habituelles)."""
    candidates = []
    found = shutil.which("ollama")
    if found:
        candidates.append(Path(found))
    local_appdata = os.environ.get("LOCALAPPDATA")
    program_files = os.environ.get("ProgramFiles")
    if local_appdata:
        candidates.append(Path(local_appdata) / "Programs" / "Ollama" / "ollama.exe")
    if program_files:
        candidates.append(Path(program_files) / "Ollama" / "ollama.exe")
    for path in candidates:
        if path.exists():
            return str(path)
    return None


def start_server(executable=None):
    """Demarre Ollama en arriere-plan, sans fenetre console."""
    executable = executable or find_executable()
    if not executable:
        return False
    try:
        subprocess.Popen(
            [executable, "serve"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=_NO_WINDOW,
        )
        return True
    except Exception:
        return False


def wait_for_server(timeout=25.0):
    """Attend que le serveur Ollama accepte les connexions."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_running(0.5):
            return True
        time.sleep(0.5)
    return False


def ensure_server(timeout=25.0):
    """Garantit la presence du moteur IA.

    Retourne un couple (disponible, message) directement affichable par l'interface.
    """
    if is_running():
        return True, "IA en ligne"
    executable = find_executable()
    if not executable:
        return False, "Ollama n'est pas installe"
    if not start_server(executable):
        return False, "Impossible de demarrer Ollama"
    if wait_for_server(timeout):
        return True, "IA demarree"
    return False, "Ollama ne demarre pas"


def list_models():
    """Noms des modeles Ollama deja telecharges."""
    try:
        import ollama

        result = ollama.list()
    except Exception:
        return []
    if isinstance(result, dict):
        models = result.get("models", []) or []
    else:
        models = getattr(result, "models", []) or []
    names = []
    for model in models:
        if isinstance(model, dict):
            name = model.get("model") or model.get("name") or ""
        else:
            name = getattr(model, "model", "") or getattr(model, "name", "")
        if name:
            names.append(name)
    return names


def has_model(name):
    """Vrai si le modele demande est deja installe."""
    if not name:
        return False
    wanted = name.strip().lower()
    for model in list_models():
        if model.lower() == wanted or model.split(":")[0].lower() == wanted:
            return True
    return False


def pull_model(name, on_progress=None):
    """Telecharge un modele. Bloquant : a appeler dans un thread."""
    try:
        import ollama

        for chunk in ollama.pull(model=name, stream=True):
            if on_progress:
                try:
                    on_progress(chunk)
                except Exception:
                    pass
        return True
    except Exception:
        return False
