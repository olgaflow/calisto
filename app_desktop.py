import customtkinter as ctk
from tkinter import filedialog, messagebox
import ollama
import threading
import os
import json
import re
import queue
import time
import socket
from collections.abc import Mapping
from pathlib import Path
from ddgs import DDGS
from PyPDF2 import PdfReader
from fpdf import FPDF
import urllib.request

try:
    from dev_window import DevWindow
except Exception:
    DevWindow = None

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

MODEL = "llama3.2"
VERSION = "1.2.0"
UPDATE_URL = "https://raw.githubusercontent.com/Kilo-Org/calisto/master/version.txt"
MEMORY_FILE = "memory.json"
CONVERSATIONS_DIR = "conversations"
ACTIVITY_FILE = "activity.json"
GENERATED_DIR = "generated"
IA_CREATIONS_DIR = "ia_creations"
MAX_WEB_SEARCH_ROUNDS = 3
MAX_WEB_SEARCH_CALLS = 3
WEB_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "rechercher_sur_internet",
        "description": (
            "Recherche des pages web ou des actualités récentes avec DuckDuckGo. "
            "À utiliser obligatoirement quand l'utilisateur demande une recherche en ligne, "
            "des informations récentes ou des sources."
        ),
        "parameters": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Une requête de mots-clés précise, reformulée pour un moteur de recherche.",
                },
                "region": {
                    "type": "string",
                    "enum": ["fr-fr", "be-fr", "ca-fr", "wt-wt", "us-en", "uk-en"],
                    "description": "Région et langue des résultats; fr-fr par défaut.",
                },
                "timelimit": {
                    "type": "string",
                    "enum": ["d", "w", "m", "y"],
                    "description": "Ancienneté maximale : d=jour, w=semaine, m=mois, y=année. Omettre pour toutes les dates.",
                },
                "search_type": {
                    "type": "string",
                    "enum": ["text", "news"],
                    "description": "Utiliser news pour les actualités; sinon text.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Nombre de résultats souhaité, de 1 à 10.",
                },
            },
        },
    },
}

BG_APP = "#0a0a0b"
BG_PANEL = "#1a1a1b"
BG_INPUT = "#343541"
TEXT_MAIN = "#d1d5db"
TEXT_MUTED = "#9ca3af"
BUBBLE_USER = "#444654"
BUBBLE_AI = "#2a2a2e"
ACCENT = "#10a37f"
ACCENT_HOVER = "#0d8a6a"
MODE_WORK = "#10a37f"
MODE_GAME = "#ef4444"
MODE_CUSTOM = "#a855f7"


class MemoryManager:
    def __init__(self, path=MEMORY_FILE):
        self.path = path
        self.items = []
        self.load()

    def load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    self.items = json.load(f)
        except Exception:
            self.items = []

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.items, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("Erreur sauvegarde memoire:", e)

    def add(self, text, source="manuel"):
        self.items.append({"text": text, "source": source})
        self.save()

    def delete(self, index):
        if 0 <= index < len(self.items):
            self.items.pop(index)
            self.save()

    def get_context(self):
        if not self.items:
            return ""
        lines = "\n".join("- [{}] {}".format(it.get("source", "?"), it["text"]) for it in self.items)
        return "\n\nMemoire utilisateur :\n{}\n".format(lines)


class ActivityTracker:
    def __init__(self, path=ACTIVITY_FILE):
        self.path = path
        self.sessions = []
        self.current = None
        self.load()

    def load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.sessions = data.get("sessions", [])
        except Exception:
            self.sessions = []

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({"sessions": self.sessions}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("Erreur sauvegarde activite:", e)

    def start(self, mode, label=""):
        self.current = {"mode": mode, "label": label, "start": time.time(),
                        "start_str": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}

    def stop(self):
        if not self.current:
            return None
        end = time.time()
        session = dict(self.current)
        session["end"] = end
        session["end_str"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        session["duration"] = round(end - self.current["start"], 2)
        self.sessions.append(session)
        self.save()
        result = session
        self.current = None
        return result

    def is_active(self):
        return self.current is not None

    def get_stats(self):
        if not self.sessions:
            return {"total_hours": 0, "by_mode": {}, "by_day": {}, "by_hour": {}, "favorite_mode": None, "count": 0}
        total = sum(s.get("duration", 0) for s in self.sessions)
        by_mode, by_day, by_hour = {}, {}, {}
        for s in self.sessions:
            mode = s.get("mode", "inconnu")
            by_mode[mode] = by_mode.get(mode, 0) + s.get("duration", 0)
            day = time.strftime("%Y-%m-%d", time.localtime(s.get("start", 0)))
            by_day[day] = by_day.get(day, 0) + s.get("duration", 0)
            hour = time.strftime("%H", time.localtime(s.get("start", 0)))
            by_hour[hour] = by_hour.get(hour, 0) + s.get("duration", 0)
        favorite = max(by_mode, key=by_mode.get) if by_mode else None
        return {"total_hours": round(total / 3600, 2), "by_mode": {k: round(v / 3600, 2) for k, v in by_mode.items()},
                "by_day": {k: round(v / 3600, 2) for k, v in by_day.items()},
                "by_hour": {k: round(v / 3600, 2) for k, v in by_hour.items()}, "favorite_mode": favorite, "count": len(self.sessions)}


def web_search(query, max_results=8, region="fr-fr", timelimit=None, search_type="text"):
    query = str(query).strip()
    if not query:
        raise ValueError("La recherche web nécessite une requête non vide.")
    if len(query) > 500:
        raise ValueError("La requête de recherche web ne peut pas dépasser 500 caractères.")
    try:
        max_results = max(1, min(int(max_results), 10))
    except (TypeError, ValueError) as error:
        raise ValueError("Le nombre de résultats doit être compris entre 1 et 10.") from error
    regions = {"fr-fr", "be-fr", "ca-fr", "wt-wt", "us-en", "uk-en"}
    if region not in regions:
        raise ValueError("La région de recherche demandée n'est pas prise en charge.")
    if timelimit not in (None, "d", "w", "m", "y"):
        raise ValueError("La période doit être d, w, m ou y.")
    if search_type not in ("text", "news"):
        raise ValueError("Le type de recherche doit être text ou news.")
    results = []
    seen_urls = set()
    search_errors = []
    for backend in ("auto", "bing", "yahoo", "yandex"):
        try:
            with DDGS(timeout=8) as ddgs:
                search = ddgs.news if search_type == "news" else ddgs.text
                backend_results = search(
                    query,
                    region=region,
                    safesearch="moderate",
                    timelimit=timelimit,
                    max_results=max_results,
                    backend=backend,
                )
            for result in backend_results:
                url = str(result.get("href") or result.get("url") or "").strip()
                deduplication_key = url.casefold() or str(result.get("title", "")).strip().casefold()
                if deduplication_key and deduplication_key not in seen_urls:
                    seen_urls.add(deduplication_key)
                    results.append(result)
                if len(results) >= max_results:
                    break
            if len(results) >= max_results:
                break
        except Exception as error:
            search_errors.append("{}: {}".format(backend, error))
    if not results and search_errors:
        raise RuntimeError(
            "Tous les moteurs de recherche ont échoué : {}".format("; ".join(search_errors))
        )
    if not results:
        return (
            "Aucun résultat trouvé pour cette requête. Essaie une formulation plus courte, "
            "des mots-clés alternatifs ou une autre région."
        )
    out = []
    for index, result in enumerate(results[:max_results], start=1):
        title = str(result.get("title", "")).strip()
        snippet = str(result.get("body", "")).strip()
        url = str(result.get("href") or result.get("url") or "").strip()
        source = str(result.get("source", "")).strip()
        date = str(result.get("date", "")).strip()
        details = []
        if source:
            details.append("Média : {}".format(source))
        if date:
            details.append("Date : {}".format(date))
        if details:
            snippet = "{}\n{}".format(snippet, " | ".join(details)).strip()
        out.append(
            "{}. {}\n{}\nSource : {}".format(
                index,
                title or "Résultat sans titre",
                snippet[:1200],
                url or "URL indisponible",
            )
        )
    return "\n\n---\n\n".join(out)


def _value(item, key, default=None):
    if isinstance(item, Mapping):
        return item.get(key, default)
    return getattr(item, key, default)


def _serialize_tool_message(message):
    if isinstance(message, Mapping):
        return dict(message)
    if hasattr(message, "model_dump"):
        return message.model_dump(exclude_none=True)
    return {
        "role": _value(message, "role", "assistant"),
        "content": _value(message, "content", "") or "",
        "tool_calls": _value(message, "tool_calls", []),
    }


def chat_with_web_search(model, messages, temperature, enabled, on_search=None):
    """Run Ollama's native tool-call cycle, executing only the approved web search."""
    conversation = [dict(message) for message in messages]
    search_count = 0
    for round_index in range(MAX_WEB_SEARCH_ROUNDS + 1):
        can_call_tools = enabled and round_index < MAX_WEB_SEARCH_ROUNDS
        request = {
            "model": model,
            "messages": conversation,
            "options": {
                "temperature": temperature,
                "num_ctx": 24576,
                "num_predict": 8192,
            },
        }
        if can_call_tools:
            request["tools"] = [WEB_SEARCH_TOOL]
        response = ollama.chat(**request)
        assistant_message = _value(response, "message", {})
        tool_calls = _value(assistant_message, "tool_calls", []) or []
        if not tool_calls:
            content = _value(assistant_message, "content", "")
            if content:
                return content
            raise RuntimeError("Le modèle Ollama a renvoyé une réponse vide.")
        if not can_call_tools:
            raise RuntimeError(
                "Le modèle continue de demander des outils après la limite de recherches autorisée."
            )

        conversation.append(_serialize_tool_message(assistant_message))
        for tool_call in tool_calls:
            function = _value(tool_call, "function", {})
            name = _value(function, "name", "")
            arguments = _value(function, "arguments", {})
            if name != "rechercher_sur_internet":
                result = "Erreur : cet outil n'est pas autorisé."
            elif not isinstance(arguments, Mapping):
                result = "Erreur : les arguments de recherche fournis par le modèle sont invalides."
            else:
                query = arguments.get("query")
                if not isinstance(query, str) or not query.strip():
                    result = "Erreur : la requête de recherche est vide ou invalide."
                elif search_count >= MAX_WEB_SEARCH_CALLS:
                    result = "Limite atteinte : aucune recherche web supplémentaire n'est autorisée pour cette réponse."
                else:
                    search_count += 1
                    if on_search:
                        on_search(query.strip())
                    try:
                        search_options = {
                            key: arguments[key]
                            for key in ("region", "timelimit", "search_type", "max_results")
                            if key in arguments
                        }
                        result = web_search(query, **search_options)
                    except (RuntimeError, ValueError) as error:
                        result = "La recherche web a échoué : {}".format(error)
            conversation.append(
                {
                    "role": "tool",
                    "tool_name": name or "outil_inconnu",
                    "content": result,
                }
            )
    raise RuntimeError("La boucle d'outils web s'est terminée sans réponse finale.")


def read_file_content(path):
    """Lit le contenu d'un fichier texte ou PDF."""
    try:
        data = path.read_bytes()
        # PDF
        if path.suffix.lower() == ".pdf":
            try:
                reader = PdfReader(str(path))
                text_parts = []
                for page in reader.pages:
                    try:
                        text_parts.append(page.extract_text() or "")
                    except Exception:
                        pass
                pdf_text = "\n".join(text_parts).strip()
                if pdf_text:
                    return pdf_text
                return "[PDF lisible mais aucun texte extrait ({} octets)]".format(len(data))
            except Exception as e:
                return "[Erreur lecture PDF : {}]".format(str(e))
        # Texte
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return "[Fichier binaire : {} ({} octets)]".format(path.name, len(data))
    except Exception as e:
        return "[Erreur lecture {} : {}]".format(path.name, str(e))


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Calisto")
        self.geometry("1250x800")
        self.minsize(900, 600)
        self.configure(fg_color=BG_APP)

        self.memory = MemoryManager()
        self.activity = ActivityTracker()
        self.current_conv = None
        self.messages = []
        self.attached_files = []
        self.streaming = False
        self.ui_queue = queue.Queue()
        self._pending_editor_context = ""
        self._editor_request_model = MODEL
        self._editor_request_temperature = 0.7
        self._editor_request_system = ""

        self.model_var = ctk.StringVar(value=MODEL)
        self.temp_var = ctk.DoubleVar(value=0.7)
        self.sys_text_var = ctk.StringVar(value="Tu es Calisto, un assistant chaleureux et naturel. Tu parles en français comme si tu discutais avec une personne, pas comme un robot. Sois simple, direct, conversational. N'utilise pas de formules froides, de listes à puces interminables ni de texte artificiel. Réponds comme tu le ferais à l'oral, de façon fluide et humaine. Si la question est simple, réponds simplement, sans chercher sur internet sauf si on te le demande explicitement.")
        self.web_search_var = ctk.BooleanVar(value=False)
        self.inline_completion_var = ctk.BooleanVar(value=True)
        self.last_user_prompt = ""
        self._learning_sujets = []

        self.mode_var = ctk.StringVar(value="aucun")
        self.mode_timer_running = False
        self.mode_start_time = 0

        # Autorisations IA
        self.ai_can_create_files = ctk.BooleanVar(value=False)
        self.ai_can_modify_app = ctk.BooleanVar(value=False)

        # Espace de travail code intégré à la fenêtre principale
        self.dev_window = None

        os.makedirs(CONVERSATIONS_DIR, exist_ok=True)
        os.makedirs(GENERATED_DIR, exist_ok=True)
        os.makedirs(IA_CREATIONS_DIR, exist_ok=True)
        self._build_ui()
        if DevWindow is not None:
            self.dev_window = DevWindow(self, master=self.code_tab)
            self.dev_window.grid(row=0, column=0, sticky="nsew")
        else:
            ctk.CTkLabel(
                self.code_tab,
                text="L'éditeur de code n'a pas pu être chargé.",
                text_color=TEXT_MUTED,
            ).grid(row=0, column=0, padx=20, pady=20)
        self._refresh_conversation_list()
        self._refresh_mode_panel()
        self._update_clock()
        self.after(100, self._process_ui_queue)
        self.after(1000, self._tick_mode_timer)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.resizable(True, True)

    def _build_system_prompt(self, extra_context=""):
        """Construit le prompt système unique et cohérent pour l'IA."""
        now = time.strftime("%A %d %B %Y à %H:%M", time.localtime())
        base = self.sys_text_var.get() or "Tu es Calisto, un assistant chaleureux et naturel."
        system = "{}\n\nDate et heure actuelles : {}.\n{}".format(base, now, extra_context)
        # Règles de conversation naturelle
        system += (
            "\n\nRègles de conversation :"
            "\n- Parle de façon naturelle, chaleureuse et directe, comme à l'oral."
            "\n- Si tu ne comprends pas la question, dis-le clairement et demande une précision plutôt que d'inventer une réponse."
            "\n- Si l'utilisateur repose la même question, ne répète pas exactement la même réponse : approfondis, change d'angle ou donne un exemple concret."
            "\n- Évite le ton robotique, les listes à puces interminables et les formules artificielles."
        )
        # Règles de code (si pertinent)
        system += (
            "\n\nPour toute demande sur le projet ouvert, analyse d'abord les noms, liens et contenus des fichiers transmis."
            "\nPour une demande de code, produis une seule version finale par fichier, sans variantes ni blocs dupliqués."
            "\nIndique le fichier cible dans un seul bloc Markdown complet avec son langage et un nom explicite, ex. ```css filename=style.css."
            "\nNe fournis jamais un simple extrait de quelques lignes ni des marqueurs comme 'code existant' à la place du code complet."
            "\nNe mets jamais du CSS ou du JavaScript dans un fichier HTML si un fichier CSS ou JavaScript dédié existe."
            "\nNe modifie jamais directement les fichiers : chaque proposition devra être validée par l'utilisateur."
        )
        # Recherche web : seulement si explicitement demandée
        if self.web_search_var.get():
            system += (
                "\n\nLa recherche web est disponible mais ne l'utilise JAMAIS pour répondre à une question sur du code local, "
                "un fichier ouvert, ou une question générale de programmation hors ligne. N'appelle rechercher_sur_internet "
                "QUE si l'utilisateur demande explicitement des informations en ligne, des actualités récentes ou des sources web."
            )
        system += "\n" + self.memory.get_context()
        return system

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.application_tabs = ctk.CTkTabview(
            self,
            fg_color=BG_APP,
            segmented_button_selected_color=ACCENT,
            segmented_button_selected_hover_color=ACCENT_HOVER,
        )
        self.application_tabs.grid(row=0, column=0, sticky="nsew")
        self.application_tabs.add("Chat classique")
        self.application_tabs.add("Code + chat")
        self.chat_tab = self.application_tabs.tab("Chat classique")
        self.code_tab = self.application_tabs.tab("Code + chat")
        self.chat_tab.grid_columnconfigure(1, weight=1)
        self.chat_tab.grid_rowconfigure(0, weight=1)
        self.code_tab.grid_columnconfigure(0, weight=1)
        self.code_tab.grid_rowconfigure(0, weight=1)

        # Sidebar gauche
        self.sidebar = ctk.CTkFrame(self.chat_tab, width=300, fg_color=BG_PANEL, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        ctk.CTkLabel(self.sidebar, text="Conversations", font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT_MAIN).pack(pady=(18, 8), padx=16, anchor="w")
        ctk.CTkButton(self.sidebar, text="Nouvelle conversation", height=34, fg_color=ACCENT, hover_color=ACCENT_HOVER, font=ctk.CTkFont(size=12, weight="bold"), command=self.new_conversation).pack(padx=16, pady=(0, 12), fill="x")
        ctk.CTkButton(self.sidebar, text="Mode Apprentissage", height=34, fg_color=MODE_GAME, hover_color="#c0392b", font=ctk.CTkFont(size=12, weight="bold"), command=self.open_learning_mode).pack(padx=16, pady=(0, 4), fill="x")

        self.conv_list = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.conv_list.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        sep = ctk.CTkFrame(self.sidebar, fg_color="#2a2a2e", height=1)
        sep.pack(fill="x", padx=16, pady=(6, 14))

        ctk.CTkLabel(self.sidebar, text="Modes d'activite", font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT_MAIN).pack(pady=(0, 8), padx=16, anchor="w")
        self.mode_panel = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.mode_panel.pack(fill="x", padx=16, pady=(0, 16))

        # Contenu principal
        self.main = ctk.CTkFrame(self.chat_tab, fg_color=BG_APP, corner_radius=0)
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(2, weight=1)

        # Header compact (meme couleur que le fond)
        self.header = ctk.CTkFrame(self.main, fg_color=BG_APP, height=42, corner_radius=0)
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.grid_propagate(False)

        self.conv_title_label = ctk.CTkLabel(self.header, text="Aucune conversation", font=ctk.CTkFont(size=17, weight="bold"), text_color=TEXT_MAIN)
        self.conv_title_label.pack(side="left", padx=(14, 5), pady=6)
        self.conv_title_label.bind("<Button-1>", lambda e: self.rename_conversation())
        ctk.CTkLabel(self.header, text="✏️", font=ctk.CTkFont(size=13), text_color=TEXT_MUTED, cursor="hand2").pack(side="left", padx=(0, 10), pady=6)
        self.clock_label = ctk.CTkLabel(self.header, text="", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED)
        self.clock_label.pack(side="left", padx=10, pady=6)
        self.status_ollama = ctk.CTkLabel(self.header, text="● Ollama", font=ctk.CTkFont(size=11), text_color="#c24141")
        self.status_ollama.pack(side="left", padx=(16, 0), pady=6)
        self._check_ollama()

        # Boutons à droite dans le header
        btn_frame = ctk.CTkFrame(self.header, fg_color="transparent")
        btn_frame.pack(side="right", padx=12, pady=4)
        ctk.CTkButton(btn_frame, text="⚙️ Réglages IA", width=120, command=self.open_settings, fg_color="#a855f7", hover_color="#9333ea", font=ctk.CTkFont(size=12, weight="bold"), text_color="#ffffff").pack(side="right", padx=4, pady=4)
        ctk.CTkButton(btn_frame, text="💾 Enregistrer fichier IA", width=130, command=self.save_ai_content_to_file, fg_color=ACCENT, hover_color=ACCENT_HOVER, font=ctk.CTkFont(size=11, weight="bold"), text_color="#ffffff").pack(side="right", padx=4, pady=4)
        ctk.CTkButton(btn_frame, text="📤 Exporter", width=80, command=self.export_conversation, fg_color=BG_INPUT, hover_color="#4b4c54", font=ctk.CTkFont(size=11)).pack(side="right", padx=4, pady=4)
        ctk.CTkButton(btn_frame, text="🗑 Supprimer", width=100, command=self.delete_current_conversation, fg_color="#8f3030", hover_color="#702626", font=ctk.CTkFont(size=11)).pack(side="right", padx=4, pady=4)
        ctk.CTkButton(btn_frame, text="🔄 Régénérer", width=90, command=self.regenerate, fg_color=BG_INPUT, hover_color="#4b4c54", font=ctk.CTkFont(size=11)).pack(side="right", padx=4, pady=4)
        ctk.CTkButton(btn_frame, text="⬆ Mise à jour", width=90, command=lambda: self.check_for_updates(show_no_update=True), fg_color="#6366f1", hover_color="#4f46e5", font=ctk.CTkFont(size=11, weight="bold")).pack(side="right", padx=4, pady=4)

        # Barre outils (fichier / web) - ligne separee, affichee quand une conversation est ouverte
        self.tools_bar = ctk.CTkFrame(self.main, fg_color=BG_PANEL, height=34, corner_radius=0)
        self.tools_bar.grid(row=1, column=0, sticky="ew")
        self.tools_bar.grid_remove()
        right_tools = ctk.CTkFrame(self.tools_bar, fg_color="transparent")
        right_tools.pack(side="right", padx=14, pady=4)
        ctk.CTkButton(right_tools, text="📎 Fichier", width=92, command=self.attach_file, fg_color=BG_INPUT, hover_color="#4b4c54", font=ctk.CTkFont(size=11)).pack(side="right", padx=4, pady=4)
        ctk.CTkButton(right_tools, text="🌐 Web", width=82, command=self.do_web_search, fg_color="#6366f1", hover_color="#4f46e5", font=ctk.CTkFont(size=11)).pack(side="right", padx=4, pady=4)

        # Zone chat
        self.chat_container = ctk.CTkScrollableFrame(self.main, fg_color=BG_APP)
        self.chat_container.grid(row=2, column=0, sticky="nsew")
        self.chat_container.grid_columnconfigure(0, weight=1)
        self.chat_container._parent_canvas.configure(bg=BG_APP, highlightthickness=0)

        # Zone saisie
        bottom = ctk.CTkFrame(self.main, fg_color=BG_APP, height=150, corner_radius=0)
        bottom.grid(row=3, column=0, sticky="ew")
        bottom.grid_propagate(False)
        bottom.grid_columnconfigure(0, weight=1)
        self.entry = ctk.CTkTextbox(bottom, height=90, font=ctk.CTkFont(size=13), fg_color=BG_INPUT, border_color="#4b4c54", text_color=TEXT_MAIN)
        self.entry.grid(row=0, column=0, sticky="nsew", padx=18, pady=12)
        self.entry.bind("<Return>", self.on_enter)
        self.entry.bind("<Shift-Return>", self.on_shift_enter)

        # Zone affichage fichiers joints
        self.file_chips_frame = ctk.CTkFrame(bottom, fg_color="transparent")
        self.file_chips_frame.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 4))
        self.file_chips_frame.grid_columnconfigure(0, weight=1)
        self.file_chips_label = ctk.CTkLabel(self.file_chips_frame, text="", font=ctk.CTkFont(size=11), text_color="#a78bfa", anchor="w")
        self.file_chips_label.grid(row=0, column=0, sticky="w")

        right = ctk.CTkFrame(bottom, fg_color="transparent")
        right.grid(row=0, column=1, sticky="ns", padx=(0, 16))
        self.send_btn = ctk.CTkButton(right, text="Envoyer", width=92, height=34, command=self.send, fg_color=ACCENT, hover_color=ACCENT_HOVER, font=ctk.CTkFont(size=13, weight="bold"))
        self.send_btn.pack(pady=(0, 6))
        ctk.CTkButton(right, text="Effacer", width=92, height=28, command=self.clear_current_chat, fg_color=BG_INPUT, hover_color="#4b4c54", font=ctk.CTkFont(size=11)).pack()

        self.status_var = ctk.StringVar(value="Pret")
        ctk.CTkLabel(self.main, textvariable=self.status_var, font=ctk.CTkFont(size=11), text_color=TEXT_MUTED).grid(row=4, column=0, sticky="e", padx=18, pady=(0, 6))

    # --- Modes ---
    def _refresh_mode_panel(self):
        for w in self.mode_panel.winfo_children():
            w.destroy()
        modes = [("aucun", "Aucun", TEXT_MUTED), ("travail", "Travail / Web Dev", MODE_WORK), ("jeux", "Jeux", MODE_GAME), ("personnalise", "Personnalise", MODE_CUSTOM)]
        for key, label, color in modes:
            row = ctk.CTkFrame(self.mode_panel, fg_color="transparent")
            row.pack(fill="x", pady=3)
            active = (self.mode_var.get() == key and self.activity.is_active())
            btn_color = color if active else "#2a2a2e"
            text_color = "#ffffff" if active else TEXT_MAIN
            ctk.CTkButton(row, text=label, width=120, height=30, fg_color=btn_color, hover_color=color, text_color=text_color, font=ctk.CTkFont(size=12, weight="bold" if active else "normal"), command=lambda k=key, l=label: self.toggle_mode(k, l)).pack(side="left", padx=(0, 6))
            if self.mode_var.get() == key and active:
                ctk.CTkLabel(row, text="● ACTIF", font=ctk.CTkFont(size=10, weight="bold"), text_color=color).pack(side="left", padx=(6, 0))
        self.mode_timer_label = ctk.CTkLabel(self.mode_panel, text="00:00:00", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_MUTED)
        self.mode_timer_label.pack(pady=(10, 0))

    def toggle_mode(self, key, label):
        if self.activity.is_active() and self.mode_var.get() == key:
            self.activity.stop()
            self.mode_var.set("aucun")
            self.mode_timer_running = False
            self.status_var.set("Mode '{}' termine. Temps enregistre.".format(label))
            self._refresh_mode_panel()
            return
        if self.activity.is_active():
            self.activity.stop()
        self.mode_var.set(key)
        self.activity.start(key, label)
        self.mode_timer_running = True
        self.mode_start_time = time.time()
        self.status_var.set("Mode '{}' demarre.".format(label))
        self._refresh_mode_panel()

        if key == "travail" and self.dev_window is not None:
            self.application_tabs.set("Code + chat")
            self.dev_window.editor.focus_set()

    def on_close(self):
        if self.dev_window is not None:
            self.dev_window.on_close()
        self.destroy()

    def _tick_mode_timer(self):
        if self.mode_timer_running and self.activity.is_active():
            elapsed = int(time.time() - self.mode_start_time)
            h = elapsed // 3600
            m = (elapsed % 3600) // 60
            s = elapsed % 60
            self.mode_timer_label.configure(text="{:02d}:{:02d}:{:02d}".format(h, m, s))
        self.after(1000, self._tick_mode_timer)

    def _update_clock(self):
        now = time.strftime("%A %d %B %Y — %H:%M", time.localtime())
        self.clock_label.configure(text=now)
        self.after(60000, self._update_clock)

    def _activity_stats_text(self):
        st = self.activity.get_stats()
        if st["count"] == 0:
            return "Aucune activite enregistree."
        lines = ["Statistiques d'activite", "Temps total : {} h".format(st["total_hours"]), "Sessions : {}".format(st["count"])]
        if st["favorite_mode"]:
            lines.append("Mode favori : {}".format(st["favorite_mode"]))
        lines.append("")
        lines.append("Par mode :")
        for k, v in st["by_mode"].items():
            lines.append("  - {} : {} h".format(k, v))
        lines.append("")
        lines.append("Par jour (7 derniers) :")
        for d, v in sorted(st["by_day"].items())[-7:]:
            lines.append("  - {} : {} h".format(d, v))
        lines.append("")
        lines.append("Par heure :")
        for h in sorted(st["by_hour"].keys()):
            lines.append("  - {}h : {} h".format(h, st["by_hour"][h]))
        return "\n".join(lines)

    # --- Conversations ---
    def _list_conversation_files(self):
        try:
            files = list(Path(CONVERSATIONS_DIR).glob("*.json"))
        except Exception:
            return []
        out = []
        for f in files:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                out.append({"file": f.name, "id": data.get("id", f.stem), "title": data.get("title", "Sans titre"), "updated_at": data.get("updated_at", 0), "messages": data.get("messages", [])})
            except Exception:
                continue
        out.sort(key=lambda c: c["updated_at"], reverse=True)
        return out

    def _refresh_conversation_list(self):
        for w in self.conv_list.winfo_children():
            w.destroy()
        convs = self._list_conversation_files()
        for c in convs:
            row = ctk.CTkFrame(self.conv_list, fg_color="transparent")
            row.pack(fill="x", pady=3, padx=2)
            is_active = (self.current_conv and self.current_conv.get("file") == c["file"])
            row.configure(fg_color=BG_INPUT if is_active else "transparent")
            title = c["title"] if c["title"] else "Sans titre"
            if len(title) > 28:
                title = title[:25] + "..."
            btn = ctk.CTkButton(row, text=title, anchor="w", fg_color="transparent", text_color=TEXT_MAIN if is_active else TEXT_MUTED, hover_color=BG_INPUT, height=30, font=ctk.CTkFont(size=12), command=lambda c=c: self.select_conversation(c))
            btn.pack(side="left", fill="x", expand=True, padx=(4, 4), pady=2)
            ctk.CTkButton(row, text="🗑️ Suppr", width=70, height=28, fg_color="#8f3030", hover_color="#c24141", text_color="#ffffff", font=ctk.CTkFont(size=11, weight="bold"), command=lambda c=c: self.delete_conversation(c)).pack(side="right", padx=6, pady=2)
        if not self.current_conv and convs:
            self.select_conversation(convs[0])

    def new_conversation(self):
        if self.streaming:
            self.status_var.set("Attendez la fin de la reponse avant de creer une conversation.")
            return
        cid = str(int(time.time() * 1000))
        conv = {"id": cid, "file": "conv_{}.json".format(cid), "title": "Nouvelle conversation", "created_at": time.time(), "updated_at": time.time(), "messages": []}
        path = Path(CONVERSATIONS_DIR) / conv["file"]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(conv, f, ensure_ascii=False, indent=2)
        self.select_conversation(conv)
        self._refresh_conversation_list()
        self._send_welcome_message()

    def _send_welcome_message(self):
        """Message d'accueil qui explique les fonctionnalités de l'IA."""
        welcome = """Bienvenue dans Calisto ! 👋

Je suis votre IA locale (Ollama). Voici ce que je peux faire pour vous :

💬 **Discuter** - Posez-moi n'importe quelle question
📎 **Analyser des fichiers** - Joignez des fichiers (PDF, texte, code, images jusqu'à 100 Mo)
🌐 **Rechercher sur le web** - Activer dans les paramètres pour rechercher en ligne
📊 **Suivre votre activité** - Utilisez les modes Travail/Jeux pour chronométrer vos sessions
💾 **Créer des fichiers** - Je peux générer du code, des documents, des pages web (à activer dans Paramètres > Réglages IA)
🛠️ **Modifier l'application** - Je peux proposer des modifications au code de Calisto (à activer dans Paramètres > Réglages IA)

Pour activer la création de fichiers ou la modification de l'application, cliquez sur **⚙️ Réglages IA** en haut à droite et cochez les options correspondantes.

Comment puis-je vous aider aujourd'hui ?"""
        self.messages.append({"role": "assistant", "content": welcome})
        self._add_bubble("IA", welcome, "assistant")
        self._save_current()

    def select_conversation(self, conv):
        if self.streaming and self.current_conv and self.current_conv.get("file") != conv.get("file"):
            self.status_var.set("Attendez la fin de la reponse avant de changer de conversation.")
            return
        self.current_conv = conv
        self.messages = list(conv.get("messages", []))
        self.conv_title_label.configure(text=conv.get("title", "Sans titre"))
        self._render_chat()
        self._refresh_conversation_list()
        self.tools_bar.grid()
        self.status_var.set("Conversation chargee")

    def delete_conversation(self, conv):
        if self.streaming:
            self.status_var.set("Attendez la fin de la reponse avant de supprimer une conversation.")
            return
        if self.current_conv and self.current_conv.get("file") == conv.get("file"):
            if not messagebox.askyesno("Confirmer", "Supprimer cette conversation en cours ?"):
                return
        else:
            if not messagebox.askyesno("Confirmer", "Supprimer cette conversation ?"):
                return
        try:
            (Path(CONVERSATIONS_DIR) / conv["file"]).unlink()
        except OSError as error:
            messagebox.showerror("Suppression impossible", "La conversation n'a pas pu etre supprimee :\n{}".format(error))
            return
        if self.current_conv and self.current_conv.get("file") == conv.get("file"):
            self.current_conv = None
            self.messages = []
            self.conv_title_label.configure(text="Aucune conversation")
            for widget in self.chat_container.winfo_children():
                widget.destroy()
            self.tools_bar.grid_remove()
        self._refresh_conversation_list()

    def delete_current_conversation(self):
        if not self.current_conv:
            messagebox.showwarning("Suppression", "Aucune conversation n'est ouverte.")
            return
        self.delete_conversation(self.current_conv)

    def rename_conversation(self):
        if not self.current_conv:
            return
        dialog = ctk.CTkInputDialog(text="Nouveau titre :", title="Renommer la conversation")
        nouveau = dialog.get_input()
        if nouveau is None:
            return
        nouveau = nouveau.strip()
        if not nouveau:
            nouveau = "Sans titre"
        self.current_conv["title"] = nouveau
        self.conv_title_label.configure(text=nouveau)
        self._save_current()
        self._refresh_conversation_list()

    def _save_current(self):
        if not self.current_conv:
            return
        self.current_conv["messages"] = self.messages
        if self.current_conv.get("title") == "Nouvelle conversation" and self.messages:
            for m in self.messages:
                if m.get("role") == "user":
                    self.current_conv["title"] = m["content"][:40]
                    break
        path = Path(CONVERSATIONS_DIR) / self.current_conv["file"]
        self.current_conv["updated_at"] = time.time()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.current_conv, f, ensure_ascii=False, indent=2)
        self._refresh_conversation_list()

    def _render_chat(self):
        for w in self.chat_container.winfo_children():
            w.destroy()
        for m in self.messages:
            role = m.get("role", "user")
            sender = "Vous" if role == "user" else ("Systeme" if role == "system" else "IA")
            self._add_bubble(sender, m.get("content", ""), role, animate=False)

    # --- Memoire ---
    def add_memory(self, text, source="manuel"):
        self.memory.add(text, source)

    def delete_memory(self, index):
        self.memory.delete(index)

    def clear_memory(self):
        if messagebox.askyesno("Confirmer", "Vider toute la memoire ?"):
            self.memory.items = []
            self.memory.save()

    # --- Fichiers ---
    def attach_file(self):
        path = filedialog.askopenfilename(title="Choisir un fichier", filetypes=[("Tous", "*.*"), ("Texte", "*.txt *.md *.py *.csv *.json"), ("PDF", "*.pdf"), ("Images", "*.png *.jpg *.jpeg *.webp")])
        if not path:
            return
        try:
            p = Path(path)
            if p.stat().st_size > 100_000_000:
                messagebox.showwarning("Trop volumineux", "Limite 100 Mo.")
                return
            self.attached_files.append(p)
            self._refresh_file_chips()
            self.status_var.set("Fichier joint : {}".format(p.name))
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def _refresh_file_chips(self):
        # Afficher les noms des fichiers joints
        if not self.attached_files:
            self.file_chips_label.configure(text="")
            return
        noms = " | ".join("📎 {}".format(p.name) for p in self.attached_files)
        self.file_chips_label.configure(text=noms)

    # --- Chat ---
    def on_enter(self, event):
        if self.streaming:
            return "break"
        if event.state & 0x1:
            return None
        self.send()
        return "break"

    def on_shift_enter(self, event):
        return None

    def _get_editor_context(self):
        if self.dev_window is not None and self.dev_window.winfo_exists():
            return self.dev_window.get_ai_context()
        return ""

    def begin_editor_exchange(self, prompt):
        if self.streaming:
            return False
        if not self.current_conv:
            self.new_conversation()
        self._editor_request_model = self.model_var.get() or MODEL
        self._editor_request_temperature = self.temp_var.get()
        mode = self.mode_var.get()
        active = self.activity.is_active()
        self._editor_request_system = self.sys_text_var.get() + self.memory.get_context()
        self._editor_request_system += "\n\nMode d'activite actuel : {}.".format(mode if active else "Aucun")
        self._editor_request_system += "\nStatistiques d'activite :\n{}".format(self._activity_stats_text())
        if mode == "travail" and active:
            self._editor_request_system += "\nL'utilisateur est en mode travail/formation developpeur web."
        self.last_user_prompt = prompt
        self.messages.append({"role": "user", "content": prompt})
        self._add_bubble("Vous", prompt, "user")
        self._save_current()
        self.streaming = True
        self.send_btn.configure(state="disabled", fg_color="#4b4c54")
        self.status_var.set("L'IA repond depuis l'editeur...")
        return True

    def finish_editor_exchange(self, response=None, error=None):
        if error:
            message = "Erreur IA de l'editeur : {}".format(error)
            self.messages.append({"role": "system", "content": message})
            self._add_bubble("Systeme", message, "system")
            self.status_var.set(message)
        elif response is not None:
            self.messages.append({"role": "assistant", "content": response})
            self._add_bubble("IA", response, "assistant")
            self.status_var.set("Reponse de l'editeur ajoutee a la conversation centrale")
        self._save_current()
        self._finish()

    def ask_ai_central(self, prompt, context_files=None):
        """Repond depuis l'historique partage, sans creer une conversation parallele."""
        extra = ""
        if self._editor_request_system:
            extra += "\nMode d'activité actuel : {}.".format(self._editor_request_system)
        if self._pending_editor_context:
            extra += (
                "\n\nL'utilisateur travaille dans l'editeur. Pour les changements de code, "
                "analyse les noms et liens des fichiers du projet fournis avec sa question. "
                "produis une seule version finale et un seul bloc complet par fichier cible, sans variantes ni doublons. "
                "Indique le fichier cible; separe HTML, CSS et JavaScript en blocs distincts "
                "et utilise un nom de fichier explicite dans la balise, ex. ```css filename=style.css. "
                "Si un fichier cible manque, choisis son nom; l'editeur le cree automatiquement. "
                "Pour une demande de correction, donne le code complet corrige dans ces blocs, pas seulement des conseils. "
                "Ne donne pas un extrait de quelques lignes, de points de suspension ou un marqueur a la place du code complet. "
                "Ne mets pas du CSS dans le HTML si une feuille CSS existe."
            )
        file_ctx = ""
        if context_files:
            file_ctx += "\n\nContexte actuel du projet ouvert dans l'editeur. Analyse ces fichiers avant de proposer une modification. "
            file_ctx += "Conserve les liens entre HTML, CSS et JavaScript et cible le bon fichier existant :\n"
            for fname, fcontent in context_files.items():
                file_ctx += "\n--- FICHIER : {} ---\n{}\n--- FIN DU FICHIER ---\n".format(fname, fcontent)
        extra += file_ctx

        history = [
            dict(message)
            for message in self.messages[-12:]
            if message.get("role") in ("user", "assistant")
        ]
        for message in history:
            message["content"] = message.get("content", "")[:3000]
        if not history or history[-1].get("role") != "user" or history[-1].get("content") != prompt:
            raise RuntimeError("La conversation centrale a change pendant la demande de l'editeur.")
        history[-1]["content"] += extra
        msgs = [{"role": "system", "content": self._build_system_prompt(extra)}] + history
        reponse = chat_with_web_search(
            self._editor_request_model,
            msgs,
            self._editor_request_temperature,
            enabled=self.web_search_var.get(),
            on_search=lambda query: self.after(
                0,
                lambda search_query=query: self.status_var.set(
                    "Recherche web : {}".format(search_query)
                ),
            ),
        )
        return reponse

    def send(self):
        if self.streaming:
            return
        if not self.current_conv:
            self.new_conversation()
        prompt = self.entry.get("1.0", "end").strip()
        if not prompt and not self.attached_files:
            return
        self._is_repeat_query = (prompt == getattr(self, "last_user_prompt", None))
        self.last_user_prompt = prompt
        parts = [prompt] if prompt else []
        for p in self.attached_files:
            content = read_file_content(p)
            parts.append("\n\n[Fichier : {}]\n{}".format(p.name, content))
        full = "\n".join(parts)
        self.entry.delete("1.0", "end")
        self.attached_files = []
        self._refresh_file_chips()
        self.messages.append({"role": "user", "content": full})
        self._add_bubble("Vous", prompt if prompt else "[Fichier(s)]", "user")
        self._save_current()
        self._pending_editor_context = self._get_editor_context()
        self.streaming = True
        self.send_btn.configure(state="disabled", fg_color="#4b4c54")
        self.status_var.set("L'IA repond...")
        threading.Thread(target=self._stream, daemon=True).start()

    def _add_bubble(self, sender, text, role, animate=True):
        row = ctk.CTkFrame(self.chat_container, fg_color="transparent")
        row.pack(fill="x", pady=5, padx=10)
        if role == "user":
            row.pack_configure(anchor="e")
            bubble_color = BUBBLE_USER
            header_color = "#ffffff"
            side = "right"
            padx = (60, 8)
        elif role == "system":
            row.pack_configure(anchor="center")
            bubble_color = BG_PANEL
            header_color = "#ff9999"
            side = "left"
            padx = (8, 8)
        else:
            row.pack_configure(anchor="w")
            bubble_color = BUBBLE_AI
            header_color = "#a78bfa"
            side = "left"
            padx = (8, 60)
        bubble = ctk.CTkFrame(row, fg_color=bubble_color, corner_radius=12)
        bubble.pack(side=side, padx=padx)
        ctk.CTkLabel(bubble, text=sender, font=ctk.CTkFont(size=12, weight="bold"), text_color=header_color, anchor="w").pack(fill="x", padx=16, pady=(11, 4))
        lbl = ctk.CTkLabel(bubble, text=text, font=ctk.CTkFont(size=14), text_color=TEXT_MAIN,
                           justify="left", wraplength=650, anchor="w")
        lbl.pack(fill="x", padx=16, pady=(0, 12))
        if role in ("user", "assistant"):
            copy_btn = ctk.CTkButton(bubble, text="📋", width=24, height=24, fg_color="transparent", hover_color=bubble_color, text_color=header_color, font=ctk.CTkFont(size=12), command=lambda t=text: self.copy_to_clipboard(t))
            copy_btn.pack(side="right", padx=8, pady=8)
        self.update_idletasks()
        self.after(30, self._scroll_bottom)
        return bubble, lbl

    def _scroll_bottom(self):
        try:
            self.update_idletasks()
            self.chat_container._parent_canvas.yview_moveto(1.0)
            self.after(100, lambda: self.chat_container._parent_canvas.yview_moveto(1.0))
            self.after(200, lambda: self.chat_container._parent_canvas.yview_moveto(1.0))
        except Exception:
            pass

    def _stream(self):
        model = self.model_var.get() or MODEL
        temperature = self.temp_var.get()
        memory_ctx = self.memory.get_context()
        now = time.strftime("%A %d %B %Y à %H:%M", time.localtime())
        stats_txt = self._activity_stats_text()
        mode = self.mode_var.get()
        active = self.activity.is_active()
        mode_label = self.mode_var.get() if active else "Aucun"
        extra = (
            "\nDate et heure actuelles : {}.\nMode d'activité actuel : {} ({}).\nStatistiques d'activité :\n{}".format(
                now, mode_label, mode, stats_txt
            )
        )
        if mode == "travail" and active:
            extra += "\n\nTu es en mode TRAVAIL / FORMATION DEVELOPPEUR WEB. L'utilisateur est en train de travailler. Propose activement ton aide sur HTML, CSS, JavaScript, React, Node.js, ou tout sujet de developpement web, sans qu'il ait a te le demander. Sois pedagogique et encourageant."
        if self.ai_can_create_files.get():
            extra += "\n\nTu as l'autorisation de creer des fichiers pour l'utilisateur. Pour creer un fichier, utilise ce format exact dans ta reponse :\n[CREER_FICHIER: nom_du_fichier.ext]\ncontenu du fichier\n[/CREER_FICHIER]\nLe fichier sera enregistre dans le dossier ia_creations/. Tu peux creer des scripts, des pages web, des documents, etc. Tu peux aussi creer des fichiers PDF (.pdf)."
        if self.ai_can_modify_app.get():
            extra += "\n\nTu as l'autorisation de modifier le code de l'application Calisto elle-même. Pour modifier un fichier de l'application, utilise ce format exact :\n[MODIFIER_APP: chemin_du_fichier.py]\nnouveau contenu du fichier\n[/MODIFIER_APP]\nUne demande de confirmation s'affichera a l'utilisateur avant chaque modification."
        if self._pending_editor_context:
            extra += (
                "\n\nL'utilisateur travaille dans l'editeur. Pour les changements de code, "
                "analyse les noms et liens des fichiers du projet fournis avec sa question. "
                "produis une seule version finale et un seul bloc complet par fichier cible, sans variantes ni doublons. "
                "Indique le fichier cible; separe HTML, CSS et JavaScript en blocs distincts "
                "et utilise un nom de fichier explicite dans la balise, ex. ```css filename=style.css. "
                "Si un fichier cible manque, choisis son nom; l'editeur le cree automatiquement. "
                "Pour une demande de correction, donne le code complet corrige dans ces blocs, pas seulement des conseils. "
                "Ne donne pas un extrait de quelques lignes, de points de suspension ou un marqueur a la place du code complet. "
                "Ne mets pas du CSS dans le HTML si une feuille CSS existe."
            )
        system = self._build_system_prompt(extra)
        conversation = [dict(message) for message in self.messages[-12:]]
        for message in conversation:
            message["content"] = message.get("content", "")[:3000]
        if self._pending_editor_context and conversation and conversation[-1].get("role") == "user":
            conversation[-1] = dict(conversation[-1])
            conversation[-1]["content"] += (
                "\n\nFichiers et etat actuels de l'editeur (analyse-les avant de repondre) :\n"
                + self._pending_editor_context
            )
        msgs = [{"role": "system", "content": system}] + conversation
        if getattr(self, "_is_repeat_query", False):
            msgs.insert(1, {"role": "system", "content": "NOTE : l'utilisateur repose exactement la meme question que precedemment. Ne repete pas exactement la meme reponse. Approfondis, donne un angle different, un exemple concret, ou demande poliment ce qui n'a pas ete compris dans ta precedente reponse pour mieux l'aider."})
            self._is_repeat_query = False
        full = ""
        try:
            if self.web_search_var.get():
                full = chat_with_web_search(
                    model,
                    msgs,
                    temperature,
                    enabled=True,
                    on_search=lambda query: self.ui_queue.put(("search", query)),
                )
                bubble, lbl = self._add_bubble("IA", "", "assistant")
                self.ui_queue.put(("done", lbl, full, bubble))
                return
            # Retry simple en cas d'echec Ollama
            last_err = None
            for attempt in range(2):
                try:
                    stream = ollama.chat(
                        model=model,
                        messages=msgs,
                        stream=True,
                        options={"temperature": temperature, "num_ctx": 8192, "num_predict": 2048},
                    )
                    break
                except Exception as e:
                    last_err = e
                    time.sleep(1)
            else:
                raise last_err
            bubble, lbl = self._add_bubble("IA", "", "assistant")
            for chunk in stream:
                tok = chunk["message"]["content"]
                full += tok
                self.ui_queue.put(("token", lbl, tok))
            self.ui_queue.put(("done", lbl, full, bubble))
        except Exception as e:
            self.ui_queue.put(("error", str(e)))

    def _process_ui_queue(self):
        try:
            while True:
                ev = self.ui_queue.get_nowait()
                if ev[0] == "token":
                    _, lbl, tok = ev
                    if lbl.winfo_exists():
                        lbl.configure(text=lbl.cget("text") + tok)
                        self._scroll_bottom()
                elif ev[0] == "search":
                    self.status_var.set("Recherche web : {}".format(ev[1]))
                elif ev[0] == "done":
                    _, lbl, full, bubble = ev
                    if lbl.winfo_exists():
                        lbl.configure(text=full)
                        self._scroll_bottom()
                    self.messages.append({"role": "assistant", "content": full})
                    self._save_current()
                    self._finish()
                    self.check_ai_creation_commands(full)
                elif ev[0] == "error":
                    messagebox.showerror("Erreur Ollama", ev[1])
                    self._finish()
        except queue.Empty:
            pass
        self.after(50, self._process_ui_queue)

    def _finish(self):
        self.streaming = False
        self.send_btn.configure(state="normal", fg_color=ACCENT)
        self.status_var.set("Pret")

    def check_ai_creation_commands(self, text):
        """Detecte les commandes de creation de fichier dans le texte de l'IA."""
        import re
        # Pattern: [CREER_FICHIER: chemin]contenu[/CREER_FICHIER]
        pattern = r"\[CREER_FICHIER: ([^\]]+)\](.*?)\[/CREER_FICHIER\]"
        matches = re.findall(pattern, text, re.DOTALL)
        for filepath, content in matches:
            filepath = filepath.strip()
            content = content.strip()
            self.handle_ai_creation_request("fichier", filepath, content)

        # Pattern: [MODIFIER_APP: chemin]contenu[/MODIFIER_APP]
        pattern2 = r"\[MODIFIER_APP: ([^\]]+)\](.*?)\[/MODIFIER_APP\]"
        matches2 = re.findall(pattern2, text, re.DOTALL)
        for filepath, content in matches2:
            filepath = filepath.strip()
            content = content.strip()
            self.handle_ai_creation_request("app", filepath, content)

    def handle_ai_creation_request(self, command_type, filepath, content):
        """Gere une demande de creation/modification de fichier par l'IA avec confirmation."""
        if command_type == "app" and not self.ai_can_modify_app.get():
            # Demande d'autorisation speciale pour modifier l'app
            resp = messagebox.askyesno(
                "Autorisation IA",
                "L'IA propose de modifier le fichier de l'application :\n{}\n\nVoulez-vous autoriser cette modification ?".format(filepath)
            )
            if not resp:
                self.status_var.set("Modification de l'app refusee par l'utilisateur")
                return
        elif command_type == "fichier" and not self.ai_can_create_files.get():
            resp = messagebox.askyesno(
                "Autorisation IA",
                "L'IA propose de creer un fichier :\n{}\n\nVoulez-vous autoriser cette creation ?".format(filepath)
            )
            if not resp:
                self.status_var.set("Creation de fichier refusee par l'utilisateur")
                return
        else:
            # Confirmation normale meme si autorise
            resp = messagebox.askyesno(
                "Confirmer action IA",
                "L'IA propose de {} le fichier :\n{}\n\nVoulez-vous confirmer ?".format(
                    "modifier l'application" if command_type == "app" else "creer", filepath
                )
            )
            if not resp:
                self.status_var.set("Action IA annulee")
                return

        # Executer la creation/modification
        try:
            if command_type == "app":
                target_path = Path(filepath)
            else:
                target_path = Path(IA_CREATIONS_DIR) / filepath

            target_path.parent.mkdir(parents=True, exist_ok=True)
            # Generate PDF if requested
            if str(filepath).lower().endswith('.pdf'):
                try:
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font('Helvetica', '', 12)
                    for line in str(content).splitlines():
                        # wrap long lines
                        pdf.multi_cell(0, 10, line)
                    pdf.output(str(target_path))
                    self.status_var.set("PDF cree par l'IA : {}".format(filepath))
                    messagebox.showinfo("Succès", "Fichier créé avec succès :\n{}".format(filepath))
                    return
                except Exception as e:
                    messagebox.showerror("Erreur PDF", "Impossible de créer le PDF :\n{}".format(str(e)))
                    return
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(content)

            self.status_var.set("Fichier {} par l'IA : {}".format(
                "modifie" if command_type == "app" else "cree", filepath
            ))
            messagebox.showinfo("Succès", "Fichier {} avec succès :\n{}".format(
                "modifié" if command_type == "app" else "créé", filepath
            ))
        except Exception as e:
            messagebox.showerror("Erreur", "Impossible d'ecrire le fichier :\n{}".format(str(e)))

    def _check_ollama(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            result = s.connect_ex(("127.0.0.1", 11434))
            s.close()
            if result == 0:
                self.status_ollama.configure(text="● Ollama", text_color="#10a37f")
            else:
                self.status_ollama.configure(text="● Ollama hors ligne", text_color="#c24141")
        except Exception:
            self.status_ollama.configure(text="● Ollama inconnu", text_color="#c24141")
        self.after(30000, self._check_ollama)

    def regenerate(self):
        if not self.current_conv or not self.messages:
            return
        if self.streaming:
            return
        if self.messages and self.messages[-1].get("role") == "assistant":
            self.messages.pop()
            for w in self.chat_container.winfo_children():
                w.destroy()
            for m in self.messages:
                role = m.get("role", "user")
                sender = "Vous" if role == "user" else ("Systeme" if role == "system" else "IA")
                self._add_bubble(sender, m.get("content", ""), role, animate=False)
            self._save_current()
            self.streaming = True
            self.send_btn.configure(state="disabled", fg_color="#4b4c54")
            self.status_var.set("L'IA repond...")
            threading.Thread(target=self._stream, daemon=True).start()

    def copy_to_clipboard(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status_var.set("Copie dans le presse-papiers")
        self.after(2000, lambda: self.status_var.set("Pret"))

    def save_ai_content_to_file(self):
        """Enregistre le dernier message de l'IA dans un fichier."""
        if not self.messages:
            messagebox.showwarning("Enregistrement", "Aucun message à enregistrer.")
            return
        # Trouver le dernier message de l'IA
        ai_message = None
        for m in reversed(self.messages):
            if m.get("role") == "assistant":
                ai_message = m.get("content", "")
                break
        if not ai_message:
            messagebox.showwarning("Enregistrement", "Aucune réponse de l'IA à enregistrer.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Tous", "*.*"), ("Texte", "*.txt"), ("Python", "*.py"), ("HTML", "*.html"), ("CSS", "*.css"), ("JavaScript", "*.js"), ("JSON", "*.json"), ("Markdown", "*.md")], title="Enregistrer le contenu de l'IA", initialdir=GENERATED_DIR)
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(ai_message)
            self.status_var.set("Fichier enregistre : {}".format(path))
        except Exception as e:
            messagebox.showerror("Erreur enregistrement", str(e))

    def export_conversation(self):
        if not self.current_conv:
            messagebox.showwarning("Export", "Aucune conversation a exporter.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json"), ("Texte", "*.txt")], title="Exporter la conversation")
        if not path:
            return
        try:
            if path.endswith(".txt"):
                lines = []
                for m in self.messages:
                    role = m.get("role", "user")
                    sender = "Vous" if role == "user" else ("Systeme" if role == "system" else "IA")
                    lines.append("{}: {}".format(sender, m.get("content", "")))
                content = "\n\n".join(lines)
            else:
                content = json.dumps(self.current_conv, ensure_ascii=False, indent=2)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.status_var.set("Exporte : {}".format(path))
        except Exception as e:
            messagebox.showerror("Erreur export", str(e))

    def clear_current_chat(self):
        if self.streaming:
            self.status_var.set("Attendez la fin de la reponse avant d'effacer la conversation.")
            return
        if not self.current_conv:
            return
        self.messages = []
        self.current_conv["messages"] = []
        path = Path(CONVERSATIONS_DIR) / self.current_conv["file"]
        self.current_conv["updated_at"] = time.time()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.current_conv, f, ensure_ascii=False, indent=2)
        for w in self.chat_container.winfo_children():
            w.destroy()
        self.status_var.set("Conversation effacee")

    def do_web_search(self):
        if self.streaming:
            return
        if not self.current_conv:
            self.new_conversation()
        q = self.last_user_prompt or self.entry.get("1.0", "end").strip()
        if not q:
            messagebox.showwarning("Recherche", "Aucune question.")
            return
        self.streaming = True
        self.send_btn.configure(state="disabled", fg_color="#4b4c54")
        self.status_var.set("Recherche web...")
        threading.Thread(target=self._web_thread, args=(q,), daemon=True).start()

    def _web_thread(self, q):
        try:
            res = web_search(q)
            self.memory.add("Recherche web '{}' :\n{}".format(q, res), source="web")
            self.after(0, lambda: self._add_bubble("Systeme", "🔍 Recherche pour : {}\nResultat enregistre en memoire.".format(q), "system"))
            self.after(0, lambda: self.status_var.set("Recherche terminee. Reposez votre question."))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Erreur recherche", str(e)))
        finally:
            self.streaming = False
            self.after(0, lambda: self.send_btn.configure(state="normal", fg_color=ACCENT))

    def check_for_updates(self, show_no_update=True):
        def worker():
            try:
                req = urllib.request.Request(UPDATE_URL, headers={"User-Agent": "Calisto-Updater"})
                with urllib.request.urlopen(req, timeout=10) as r:
                    distant = r.read().decode("utf-8").strip()
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Mise à jour", "Impossible de verifier les mises a jour :\n{}".format(e)))
                return
            if distant and distant != VERSION:
                self.after(0, lambda: self._ask_update(distant))
            elif show_no_update:
                self.after(0, lambda: messagebox.showinfo("Mise à jour", "Vous utilisez la version la plus recente ({}).".format(VERSION)))
        threading.Thread(target=worker, daemon=True).start()

    def _ask_update(self, distant_version):
        win = ctk.CTkToplevel(self)
        win.title("Mise à jour disponible")
        win.geometry("520x320")
        win.configure(fg_color=BG_APP)
        win.transient(self)
        win.grab_set()
        win.resizable(True, True)
        ctk.CTkLabel(win, text="Nouvelle version disponible", font=ctk.CTkFont(size=16, weight="bold"), text_color=ACCENT).pack(pady=(20, 8))
        ctk.CTkLabel(win, text="Version actuelle : {}".format(VERSION), text_color=TEXT_MUTED).pack(pady=2)
        ctk.CTkLabel(win, text="Version disponible : {}".format(distant_version), text_color=TEXT_MAIN).pack(pady=2)
        ctk.CTkLabel(win, text="Telecharger et installer maintenant ?", font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(18, 8))
        btns = ctk.CTkFrame(win, fg_color="transparent")
        btns.pack(pady=10)
        ctk.CTkButton(btns, text="Mettre a jour", command=lambda: self._download_update(distant_version, win), fg_color=ACCENT, hover_color=ACCENT_HOVER, font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=8)
        ctk.CTkButton(btns, text="Plus tard", command=win.destroy, fg_color="#4b4c54", hover_color="#3a3a3e").pack(side="left", padx=8)

    def _download_update(self, distant_version, win):
        win.destroy()
        progress_win = ctk.CTkToplevel(self)
        progress_win.title("Telechargement...")
        progress_win.geometry("460x200")
        progress_win.configure(fg_color=BG_APP)
        progress_win.transient(self)
        progress_win.grab_set()
        progress_win.resizable(True, True)
        ctk.CTkLabel(progress_win, text="Telechargement de la version {}".format(distant_version), font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT_MAIN).pack(pady=(20, 10))
        status_var = ctk.StringVar(value="Preparation...")
        ctk.CTkLabel(progress_win, textvariable=status_var, text_color=TEXT_MUTED).pack(pady=4)
        progress_bar = ctk.CTkProgressBar(progress_win, width=340)
        progress_bar.pack(pady=10)
        progress_bar.set(0)

        def worker():
            try:
                import urllib.request as ulreq
                url = "https://raw.githubusercontent.com/Kilo-Org/calisto/master/app_desktop.py"
                req = ulreq.Request(url, headers={"User-Agent": "Calisto-Updater"})
                with ulreq.urlopen(req, timeout=30) as r:
                    total = int(r.headers.get("Content-Length", 0))
                    downloaded = 0
                    blocks = []
                    while True:
                        block = r.read(8192)
                        if not block:
                            break
                        blocks.append(block)
                        downloaded += len(block)
                        if total:
                            self.after(0, lambda d=downloaded, t=total: progress_bar.set(d / t))
                            self.after(0, lambda d=downloaded, t=total: status_var.format("{} / {} octets".format(d, t)))
                content = b"".join(blocks).decode("utf-8")
                app_path = Path(__file__).resolve()
                backup = app_path.with_suffix(".py.bak")
                app_path.rename(backup)
                app_path.write_text(content, encoding="utf-8")
                self.after(0, lambda: [
                    progress_win.destroy(),
                    messagebox.showinfo("Mise à jour", "Mise à jour vers la version {} installee.\nRelancez l'application pour appliquer les changements.".format(distant_version))
                ])
            except Exception as e:
                self.after(0, lambda: [
                    progress_win.destroy(),
                    messagebox.showerror("Erreur", "Echec de la mise à jour :\n{}".format(e))
                ])
        threading.Thread(target=worker, daemon=True).start()

    def open_settings(self):
        win = ctk.CTkToplevel(self)
        win.title("Paramètres")
        win.geometry("560x800")
        win.configure(fg_color=BG_APP)
        win.transient(self)
        win.grab_set()
        win.resizable(True, True)
        ctk.CTkLabel(win, text="Paramètres", font=ctk.CTkFont(size=20, weight="bold"), text_color=TEXT_MAIN).pack(pady=(22, 18))
        body = ctk.CTkFrame(win, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=28, pady=8)
        r = ctk.CTkFrame(body, fg_color="transparent"); r.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(r, text="Modele Ollama:", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
        ctk.CTkEntry(r, textvariable=self.model_var, width=170, height=32).pack(side="right")
        r = ctk.CTkFrame(body, fg_color="transparent"); r.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(r, text="Temperature:", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
        ctk.CTkEntry(r, textvariable=self.temp_var, width=60, height=32).pack(side="right", padx=(10, 0))
        ctk.CTkSlider(r, from_=0.0, to=1.5, variable=self.temp_var, width=190).pack(side="right", padx=(10, 0))
        ctk.CTkSwitch(body, text="Autoriser l'IA à rechercher sur internet (DuckDuckGo)", variable=self.web_search_var, font=ctk.CTkFont(size=13)).pack(anchor="w", pady=(10, 14))
        ctk.CTkSwitch(
            body,
            text="Suggestions de code IA en direct dans l'éditeur",
            variable=self.inline_completion_var,
            command=self._toggle_inline_completion,
            font=ctk.CTkFont(size=13),
        ).pack(anchor="w", pady=(5, 14))
        ctk.CTkSwitch(body, text="Autoriser l'IA à créer des fichiers", variable=self.ai_can_create_files, font=ctk.CTkFont(size=13)).pack(anchor="w", pady=(5, 2))
        ctk.CTkLabel(body, text="(les fichiers sont crees dans ia_creations/)", font=ctk.CTkFont(size=10), text_color=TEXT_MUTED).pack(anchor="w", pady=(0, 10))
        ctk.CTkSwitch(body, text="Autoriser l'IA à modifier l'application", variable=self.ai_can_modify_app, font=ctk.CTkFont(size=13)).pack(anchor="w", pady=(5, 2))
        ctk.CTkLabel(body, text="(modifie le code de Calisto - demande de confirmation a chaque fois)", font=ctk.CTkFont(size=10), text_color=TEXT_MUTED).pack(anchor="w", pady=(0, 14))
        ctk.CTkLabel(body, text="Instruction systeme (personnalite):", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(5, 6))
        sys_txt = ctk.CTkTextbox(body, height=90, font=ctk.CTkFont(size=12), fg_color=BG_INPUT, border_color="#4b4c54", text_color=TEXT_MAIN)
        sys_txt.pack(fill="x", pady=(0, 14)); sys_txt.insert("1.0", self.sys_text_var.get())
        ctk.CTkLabel(body, text="Memoire (faits a retenir):", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(5, 6))
        mf = ctk.CTkFrame(body, fg_color="transparent"); mf.pack(fill="x", pady=(0, 8))
        mem_ent = ctk.CTkEntry(mf, placeholder_text="Ajouter un souvenir...", height=32)
        mem_ent.pack(side="left", fill="x", expand=True, padx=(0, 8))
        mem_ent.bind("<Return>", lambda e: s_add())
        mem_sc = ctk.CTkScrollableFrame(body, fg_color=BG_PANEL, height=150)
        mem_sc.pack(fill="x", pady=(0, 10))
        def refresh():
            for w in mem_sc.winfo_children():
                w.destroy()
            for i, it in enumerate(self.memory.items):
                src = it.get("source", "manuel")
                rr = ctk.CTkFrame(mem_sc, fg_color=BG_INPUT, corner_radius=6)
                rr.pack(fill="x", pady=2)
                rr.grid_columnconfigure(0, weight=1)
                ctk.CTkLabel(rr, text="[{}] {}".format(src, it["text"]), anchor="w", font=ctk.CTkFont(size=11), wraplength=400).pack(side="left", padx=10, pady=4, fill="x", expand=True)
                ctk.CTkButton(rr, text="🗑️", width=24, height=24, fg_color="transparent", text_color="#c24141", hover_color="#c24141", command=lambda i=i: s_del(i)).pack(side="right", padx=6)
        def s_add():
            t = mem_ent.get().strip()
            if not t:
                return
            self.memory.add(t, "manuel")
            mem_ent.delete(0, "end")
            refresh()
        def s_del(i):
            self.memory.delete(i)
            refresh()
        def s_clear():
            if messagebox.askyesno("Confirmer", "Vider toute la memoire ?", parent=win):
                self.memory.items = []
                self.memory.save()
                refresh()
        refresh()
        bf = ctk.CTkFrame(body, fg_color="transparent"); bf.pack(fill="x", pady=(0, 14))
        ctk.CTkButton(bf, text="Vider tout", command=s_clear, fg_color="#c24141", hover_color="#a33434", height=30, font=ctk.CTkFont(size=12)).pack(side="right")
        ctk.CTkLabel(body, text="Activite enregistree:", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(16, 6))
        act_txt = ctk.CTkTextbox(body, height=130, font=ctk.CTkFont(size=11), fg_color=BG_INPUT, border_color="#4b4c54", text_color=TEXT_MAIN)
        act_txt.pack(fill="x", pady=(0, 14))
        act_txt.insert("1.0", self._activity_stats_text())
        act_txt.configure(state="disabled")
        ctk.CTkLabel(body, text="Aide / Raccourcis", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(18, 6))
        help_txt = (
            "Editeur de code (dev_window) :\n"
            "  Ctrl+S : Sauvegarder   |   Ctrl+F : Rechercher / Remplacer   |   Ctrl+G : Aller a la ligne\n"
            "  Ctrl+/ : Commenter / decommenter   |   Ctrl+Molette : Zoom\n"
            "  Auto-fermeture : ( ) [ ] { } \" \" ' '\n"
            "  Surbrillance des accolades correspondantes\n"
            "  Inline AI completions : suggestions en direct (onglet IA)\n\n"
            "Chat IA :\n"
            "  Posez vos questions simplement, l'IA repond directement sans recherche web inutile.\n"
            "  La recherche internet ne se declenche que si vous le demandez explicitement.\n"
            "  Personnalite editable dans le champ 'Instruction systeme' ci-dessus."
        )
        ctk.CTkLabel(body, text=help_txt, font=ctk.CTkFont(size=11), text_color=TEXT_MUTED, justify="left").pack(anchor="w", pady=(0, 14))
        ctk.CTkButton(body, text="Verifier les mises à jour", command=lambda: self.check_for_updates(show_no_update=True), fg_color="#6366f1", hover_color="#4f46e5", height=30, font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(0, 10))
        foot = ctk.CTkFrame(win, fg_color=BG_APP, height=60, corner_radius=0)
        foot.pack(fill="x", side="bottom"); foot.pack_propagate(False)
        def save_close():
            self.sys_text_var.set(sys_txt.get("1.0", "end").strip())
            self.memory.save()
            self.status_var.set("Paramètres enregistres")
            win.destroy()
        ctk.CTkButton(foot, text="Annuler", width=92, command=win.destroy, fg_color=BG_INPUT, hover_color="#4b4c54").pack(side="right", padx=16, pady=14)
        ctk.CTkButton(foot, text="Enregistrer", width=112, command=save_close, fg_color=ACCENT, hover_color=ACCENT_HOVER, font=ctk.CTkFont(size=13, weight="bold")).pack(side="right", padx=(0, 8), pady=14)

    def _toggle_inline_completion(self):
        if self.dev_window is not None and self.dev_window.winfo_exists():
            self.dev_window.set_inline_completion_enabled(self.inline_completion_var.get())

    # ---------- Mode Apprentissage / Jeux ----------
    def open_learning_mode(self):
        if self.streaming:
            self.status_var.set("Attendez la fin de la reponse avant d'ouvrir le mode apprentissage.")
            return
        LearningModeWindow(self)


LEARNING_LEVELS = {
    "junior": {"label": "Junior", "max_files": 5, "advice_freq": "beaucoup", "tolerance": "élevée"},
    "facile": {"label": "Facile", "max_files": 4, "advice_freq": "peu", "tolerance": "élevée"},
    "normale": {"label": "Normale", "max_files": 3, "advice_freq": "modéré", "tolerance": "moyenne"},
    "difficile": {"label": "Difficile", "max_files": 3, "advice_freq": "minimal", "tolerance": "faible"},
    "legendaire": {"label": "Légendaire", "max_files": 2, "advice_freq": "aucun", "tolerance": "aucune"},
    "senior": {"label": "Senior", "max_files": 4, "advice_freq": "très peu", "tolerance": "strict"},
}


class LearningModeWindow:
    def __init__(self, parent_app):
        self.app = parent_app
        self.win = ctk.CTkToplevel(parent_app)
        self.win.title("Mode Apprentissage - Calisto")
        self.win.geometry("1100x750")
        self.win.configure(fg_color=BG_APP)
        self.win.transient(parent_app)
        self.win.grab_set()
        self.win.resizable(True, True)

        self.level = ctk.StringVar(value="junior")
        self.start_time = None
        self.timer_job = None
        self.files = {}
        self.max_files = 5
        self.current_file = "index.html"
        self.paused = False
        self.current_subject = ""
        self.exercise_count = 0

        self._build_ui()
        self._start_timer()

    def _build_ui(self):
        header = ctk.CTkFrame(self.win, fg_color=BG_PANEL, height=50)
        header.pack(fill="x", padx=10, pady=10)
        header.pack_propagate(False)

        ctk.CTkLabel(header, text="Mode Apprentissage", font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT_MAIN).pack(side="left", padx=15, pady=10)
        self.exercise_label = ctk.CTkLabel(header, text="Exercice 0", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_MUTED)
        self.exercise_label.pack(side="left", padx=15, pady=10)
        self.level_btn = ctk.CTkOptionMenu(header, values=[LEARNING_LEVELS[k]["label"] for k in LEARNING_LEVELS], command=self._on_level_change, width=140)
        self.level_btn.set("Junior")
        self.level_btn.pack(side="right", padx=15, pady=10)

        self.timer_label = ctk.CTkLabel(self.win, text="00:00:00", font=ctk.CTkFont(size=22, weight="bold"), text_color=ACCENT)
        self.timer_label.pack(pady=(0, 10))

        body = ctk.CTkFrame(self.win, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=10, pady=5)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=2)
        body.grid_columnconfigure(2, weight=1)
        body.grid_rowconfigure(0, weight=1)

        # Colonne gauche : fichiers
        files_frame = ctk.CTkFrame(body, fg_color=BG_PANEL)
        files_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        ctk.CTkLabel(files_frame, text="Fichiers", font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_MAIN).pack(pady=8)
        self.files_list = ctk.CTkScrollableFrame(files_frame, fg_color="transparent")
        self.files_list.pack(fill="both", expand=True, padx=5, pady=5)
        self.file_buttons = {}
        self._refresh_files_ui()
        ctk.CTkButton(files_frame, text="+ Nouveau fichier", width=120, command=self._add_file, fg_color="#6366f1", hover_color="#4f46e5", font=ctk.CTkFont(size=11)).pack(pady=5)

        # Colonne centre : editeur
        editor_frame = ctk.CTkFrame(body, fg_color="#1e1e1e")
        editor_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        editor_frame.grid_rowconfigure(1, weight=1)
        editor_frame.grid_columnconfigure(0, weight=1)

        self.editor_label = ctk.CTkLabel(editor_frame, text="index.html", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_MUTED)
        self.editor_label.grid(row=0, column=0, sticky="w", padx=10, pady=5)

        self.code_editor = ctk.CTkTextbox(editor_frame, font=ctk.CTkFont(family="Consolas", size=13), fg_color="#1e1e1e", text_color="#d4d4d4", border_width=0)
        self.code_editor.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        # Interdiction copier-coller
        self.code_editor.bind("<Control-c>", lambda e: "break")
        self.code_editor.bind("<Control-v>", lambda e: "break")
        self.code_editor.bind("<Control-x>", lambda e: "break")
        self.code_editor.bind("<Button-3>", lambda e: "break")
        self.code_editor.bind("<KeyRelease>", self._on_code_change)

        # Colonne droite : IA
        ia_frame = ctk.CTkFrame(body, fg_color=BG_PANEL)
        ia_frame.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
        ia_frame.grid_rowconfigure(1, weight=1)
        ia_frame.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(ia_frame, text="Instructions IA", font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_MAIN).pack(pady=8)
        self.ia_instructions = ctk.CTkTextbox(ia_frame, font=ctk.CTkFont(size=11), fg_color=BG_INPUT, border_color="#4b4c54", text_color=TEXT_MAIN)
        self.ia_instructions.pack(fill="both", expand=True, padx=5, pady=5)
        self.ia_instructions.configure(state="disabled")

        ctk.CTkLabel(ia_frame, text="Conseils IA", font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_MAIN).pack(pady=(10, 5))
        self.ia_advice = ctk.CTkTextbox(ia_frame, font=ctk.CTkFont(size=11), fg_color=BG_INPUT, border_color="#4b4c54", text_color=TEXT_MAIN)
        self.ia_advice.pack(fill="both", expand=True, padx=5, pady=5)
        self.ia_advice.configure(state="disabled")

        btn_frame = ctk.CTkFrame(self.win, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)

        self.abandon_btn = ctk.CTkButton(btn_frame, text="Abandonner", command=self._abandon, fg_color="#c24141", hover_color="#a33434", font=ctk.CTkFont(size=12, weight="bold"))
        self.abandon_btn.pack(side="left", padx=10)
        self.pause_btn = ctk.CTkButton(btn_frame, text="Pause", command=self._toggle_pause, fg_color="#b45309", hover_color="#d97706", font=ctk.CTkFont(size=12, weight="bold"))
        self.pause_btn.pack(side="left", padx=10)
        self.verify_btn = ctk.CTkButton(btn_frame, text="Verifier le site", command=self._verify, fg_color=ACCENT, hover_color=ACCENT_HOVER, font=ctk.CTkFont(size=12, weight="bold"))
        self.verify_btn.pack(side="right", padx=10)

        self.status_label = ctk.CTkLabel(self.win, text="", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED)
        self.status_label.pack(pady=(0, 5))

        self.files["index.html"] = "<!DOCTYPE html>\n<html>\n<head>\n    <title>Mon site</title>\n</head>\n<body>\n    <h1>Bonjour</h1>\n</body>\n</html>"
        self._open_file("index.html")
        self.status_label.configure(text="Generation du sujet en cours...", text_color=TEXT_MAIN)
        self._set_level_instructions("junior")
        threading.Thread(target=self._generate_subject, daemon=True).start()

    def _on_level_change(self, value):
        for k, v in LEARNING_LEVELS.items():
            if v["label"] == value:
                self.level.set(k)
                self.max_files = v["max_files"]
                self._set_level_instructions(k)
                self._refresh_files_ui()
                self.status_label.configure(text="Generation du sujet en cours...", text_color=TEXT_MAIN)
                threading.Thread(target=self._generate_subject, daemon=True).start()
                break

    def _set_level_instructions(self, key):
        lv = LEARNING_LEVELS[key]
        instr = (
            "Niveau : {}\n\n".format(lv["label"]) +
            "But : cree un site web fonctionnel (HTML, CSS, JavaScript) sans aide exterieure.\n" +
            "Tu ne peux pas parler a l'IA, pas de copier-coller.\n" +
            "Seul le bouton 'Verifier le site' permet a l'IA de valider ou refuser ton travail.\n" +
            "Tolerance : {}\n".format(lv["tolerance"]) +
            "Conseils : {}\n".format(lv["advice_freq"]) +
            "Nombre de fichiers max : {}".format(lv["max_files"])
        )
        self._set_text(self.ia_instructions, instr)
        self._update_advice(key)

    def _update_advice(self, key):
        if key == "junior":
            advice = "Conseil : commence par la structure HTML de base (doctype, html, head, body). Ajoute un titre et un paragraphe."
        elif key == "facile":
            advice = "Conseil : pense a bien fermer toutes tes balises HTML et lie ton fichier CSS."
        elif key == "normale":
            advice = "Conseil : verifie que ton CSS cible les bons elements et que ton JS est sans erreur."
        elif key == "difficile":
            advice = "Conseil : aucun conseil supplementaire. Tu es presque autonome."
        elif key == "legendaire":
            advice = "Conseil : aucun droit a l'erreur. Sois parfait du premier coup."
        else:
            advice = "Conseil : niveau expert, tu es totalement autonome."
        self._set_text(self.ia_advice, advice)

    def _generate_subject(self):
        """Demande a l'IA de generer un sujet de projet precis avec des consignes structurees."""
        level = self.level.get()
        lv = LEARNING_LEVELS[level]
        # Historique des sujets deja proposes pour eviter les repetitions
        sujets_deja = self.app._learning_sujets if hasattr(self.app, "_learning_sujets") else []
        self.app._learning_sujets = sujets_deja
        historique = ""
        if sujets_deja:
            historique = "SUJETS DEJA PROPOSES (NE PAS les reprendre) :\n- {}\n\n".format("\n- ".join(sujets_deja[-10:]))
        difficulty_desc = {
            "junior": "simple, une seule page, basique",
            "facile": "une page avec quelques elements interactifs",
            "normale": "plusieurs sections, mise en page soignee, un peu de JavaScript",
            "difficile": "site multi-pages ou application web avec JavaScript significatif",
            "legendaire": "application web complete ou site e-commerce complexe, logique JS avancee",
            "senior": "projet professionnel complet avec architecture, design responsive et fonctionnalites avancees",
        }[level]
        prompt = (
            "Tu es un formateur en developpement web. Genere UN sujet de projet precis et concrete pour un apprenant au niveau {} ({}).\n"
            "IMPORTANT : varie le TYPE de site a chaque exercice. Ne propose PAS toujours un portfolio. Touche a tout : landing page, site de voyage, site e-commerce, blog, page de contact, CV en ligne, site restaurant, agence, page de formation, etc.\n"
            "Le sujet doit correspondre a la difficulté {}. Difficulte actuelle : {} ({}).\n"
            "Cela signifie : {}\n"
            "La difficulté ne doit PAS seulement signifier 'plus de pages' : elle doit signifier un type de site different et/ou plus complexe.\n"
            "{history}Donne les consignes suivantes de maniere claire et structuree :\n"
            "1. SUJET : le type exact de site a creer (sois varie, pas de portfolio a chaque fois)\n"
            "2. OBJECTIF : ce que le site doit permettre a l'utilisateur de faire\n"
            "3. PAGES OU SECTIONS : les elements obligatoires a inclure\n"
            "4. EXIGENCES TECHNIQUES : ce qui est attendu en HTML/CSS/JS selon le niveau\n"
            "5. CRITERES DE REUSSITE : ce qui sera verifie pour valider le projet\n"
            "Sois precis, direct et donne un seul sujet (pas de liste au choix). Ecris en francais.\n\nNiveau : {} ({}) - Tolerance : {}".format(
                lv["label"], level, level, lv["label"], difficulty_desc, historique, lv["label"], level, lv["tolerance"]
            )
        )
        try:
            model = self.app.model_var.get() or MODEL
            response = ollama.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.7, "num_predict": 700},
            )
            sujet = response["message"]["content"]
            # Extraire le titre du sujet pour l'historique (premiere ligne non vide)
            first_line = [l for l in sujet.splitlines() if l.strip()][0] if sujet else "Sujet inconnu"
            self.app._learning_sujets.append(first_line[:80])
            self.app.after(0, lambda: self._display_subject(sujet))
        except Exception as e:
            self.app.after(0, lambda: self.status_label.configure(text="Erreur generation sujet : {}".format(e), text_color="#c24141"))

    def _display_subject(self, sujet):
        """Affiche le sujet genere par l'IA dans la zone Instructions IA."""
        lv = LEARNING_LEVELS[self.level.get()]
        self.current_subject = sujet
        self.exercise_count += 1
        self.exercise_label.configure(text="Exercice {}".format(self.exercise_count))
        full = (
            "Niveau : {}\n\n".format(lv["label"]) +
            "SUJET DU PROJET (generé par l'IA) :\n{}\n\n".format(sujet) +
            "But : cree ce site web fonctionnel (HTML, CSS, JavaScript) sans aide exterieure.\n" +
            "Tu ne peux pas parler a l'IA, pas de copier-coller.\n" +
            "Seul le bouton 'Verifier le site' permet a l'IA de valider ou refuser ton travail.\n" +
            "Tolerance : {}\n".format(lv["tolerance"]) +
            "Conseils : {}\n".format(lv["advice_freq"]) +
            "Nombre de fichiers max : {}".format(lv["max_files"])
        )
        self._set_text(self.ia_instructions, full)
        self.status_label.configure(text="Sujet defini. Commence a coder !", text_color="#0d8a6a")

    def _set_text(self, widget, text):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _start_timer(self):
        self.start_time = time.time()
        self._tick_timer()

    def _tick_timer(self):
        if self.start_time is None:
            return
        elapsed = int(time.time() - self.start_time)
        h = elapsed // 3600
        m = (elapsed % 3600) // 60
        s = elapsed % 60
        self.timer_label.configure(text="{:02d}:{:02d}:{:02d}".format(h, m, s))
        self.timer_job = self.win.after(1000, self._tick_timer)

    def _stop_timer(self):
        if self.timer_job:
            self.win.after_cancel(self.timer_job)
            self.timer_job = None

    def _toggle_pause(self):
        self.paused = not self.paused
        if self.paused:
            self._stop_timer()
            self.code_editor.configure(state="disabled")
            self.pause_btn.configure(text="Reprendre", fg_color="#15803d", hover_color="#16a34a")
            self.verify_btn.configure(state="disabled")
            self.status_label.configure(text="En pause - editeur bloque", text_color="#b45309")
        else:
            self._start_timer()
            self.code_editor.configure(state="normal")
            self.pause_btn.configure(text="Pause", fg_color="#b45309", hover_color="#d97706")
            self.verify_btn.configure(state="normal")
            self.status_label.configure(text="Repris - codez !", text_color="#0d8a6a")

    def _set_editor_enabled(self, enabled):
        self.code_editor.configure(state="normal" if enabled else "disabled")

    def _on_code_change(self, event=None):
        self.files[self.current_file] = self.code_editor.get("1.0", "end-1c")

    def _refresh_files_ui(self):
        for btn in self.file_buttons.values():
            btn.destroy()
        self.file_buttons = {}
        for fname in self.files:
            b = ctk.CTkButton(self.files_list, text=fname, width=100, command=lambda f=fname: self._open_file(f), fg_color=BG_INPUT, hover_color="#4b4c54", font=ctk.CTkFont(size=10))
            b.pack(fill="x", pady=2, padx=2)
            self.file_buttons[fname] = b

    def _open_file(self, fname):
        self.current_file = fname
        self.editor_label.configure(text=fname)
        self.code_editor.delete("1.0", "end")
        self.code_editor.insert("1.0", self.files.get(fname, ""))

    def _add_file(self):
        if len(self.files) >= self.max_files:
            self.status_label.configure(text="Limite de fichiers atteinte ({})".format(self.max_files), text_color="#c24141")
            return
        base = "style"
        ext = ".css"
        i = 1
        while "{}{}".format(base, ext) in self.files:
            base = "style{}".format(i)
            i += 1
        fname = "{}{}".format(base, ext)
        self.files[fname] = ""
        self._refresh_files_ui()
        self._open_file(fname)

    def _abandon(self):
        self._stop_timer()
        self.win.destroy()

    def _verify(self):
        self._stop_timer()
        # Verification cote client : reject si le contenu est vide ou quasi inchange par rapport au squelette par defaut
        html_content = self.files.get("index.html", "")
        default_html = "<!DOCTYPE html>\n<html>\n<head>\n    <title>Mon site</title>\n</head>\n<body>\n    <h1>Bonjour</h1>\n</body>\n</html>"
        if not html_content.strip():
            self.status_label.configure(text="Refuse : aucun code saisi. Ecrivez du HTML avant de verifier.", text_color="#c24141")
            return
        if self._is_default_skeleton(html_content):
            self.status_label.configure(text="Refuse : le squelette par defaut n'est pas un site. Ajoutez du contenu reel.", text_color="#c24141")
            return
        all_code = ""
        for fname, content in self.files.items():
            all_code += "\n--- FICHIER : {} ---\n{}\n--- FIN ---".format(fname, content)
        level = self.level.get()
        lv = LEARNING_LEVELS[level]
        verify_prompt = (
            "Tu es un examinateur sever. Voici le code d'un apprenant au niveau {} ({}).\n"
            "Tolerance aux erreurs : {}.\n"
            "Le but est de creer un site web propre et fonctionnel (HTML, CSS, JS).\n"
            "Si le code est uniquement le squelette par defaut (DOCTYPE + titre + un h1 'Bonjour') sans contenu reel, reponds REFUSE.\n"
            "CONSIGNES DU PROJET A RESPECTER A LA LETTRE :\n{}\n"
            "Analyse si le code de l'apprenant correspond REELLEMENT a ces consignes. Si oui, reponds VALIDÉ. Si non, reponds REFUSE.\n"
            "Reponds UNIQUEMENT par 'VALIDÉ' ou 'REFUSE' suivi d'une courte explication en francais.\n"
            "Ne donne pas de conseil pour corriger, dis seulement si c'est accepte ou non.\n\n{}".format(lv["label"], level, lv["tolerance"], self.current_subject, all_code)
        )
        self.status_label.configure(text="Verification en cours...", text_color=TEXT_MAIN)
        threading.Thread(target=self._verify_thread, args=(verify_prompt,), daemon=True).start()

    @staticmethod
    def _is_default_skeleton(html):
        default = "<!DOCTYPE html>\n<html>\n<head>\n    <title>Mon site</title>\n</head>\n<body>\n    <h1>Bonjour</h1>\n</body>\n</html>"
        normal = " ".join(html.split())
        norm_default = " ".join(default.split())
        # Si le contenu normalise est identique ou ne contient pratiquement rien en plus
        return normal == norm_default or len(normal) < len(norm_default) + 50

    def _verify_thread(self, prompt):
        try:
            model = self.app.model_var.get() or MODEL
            response = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}], options={"temperature": 0.3, "num_predict": 512})
            content = response["message"]["content"]
            self.app.after(0, lambda: self._show_result(content))
        except Exception as e:
            self.app.after(0, lambda: self.status_label.configure(text="Erreur IA : {}".format(e), text_color="#c24141"))

    def _show_result(self, text):
        color = "#0d8a6a" if "VALIDÉ" in text.upper() else "#c24141"
        self.status_label.configure(text=text, text_color=color)
        elapsed = int(time.time() - self.start_time) if self.start_time else 0
        self._save_time(self.level.get(), elapsed)
        if "VALIDÉ" in text.upper():
            self.status_label.configure(text="Exercice reussi ! Generation d'un nouvel exercice...", text_color=ACCENT)
            # Reset les fichiers au squelette par defaut pour le nouvel exercice
            self.files = {"index.html": "<!DOCTYPE html>\n<html>\n<head>\n    <title>Mon site</title>\n</head>\n<body>\n    <h1>Bonjour</h1>\n</body>\n</html>"}
            self.current_file = "index.html"
            self._refresh_files_ui()
            self._open_file("index.html")
            self._set_level_instructions(self.level.get())
            threading.Thread(target=self._generate_subject, daemon=True).start()

    def _save_time(self, level, seconds):
        import json, os
        path = "learning_times.json"
        data = {}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        data.setdefault(level, []).append(seconds)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


if __name__ == "__main__":
    app = App()
    app.mainloop()
