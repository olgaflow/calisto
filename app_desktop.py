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
        "description": "Recherche des informations actualisées sur le web avec DuckDuckGo.",
        "parameters": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Les mots-clés précis à rechercher sur internet.",
                }
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


def web_search(query, max_results=5):
    query = str(query).strip()
    if not query:
        raise ValueError("La recherche web nécessite une requête non vide.")
    if len(query) > 500:
        raise ValueError("La requête de recherche web ne peut pas dépasser 500 caractères.")
    max_results = max(1, min(int(max_results), 5))
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
    except Exception as e:
        raise RuntimeError("La recherche web a échoué : {}".format(e)) from e
    if not results:
        return "Aucun résultat trouvé pour cette requête."
    out = []
    for index, result in enumerate(results[:max_results], start=1):
        title = str(result.get("title", "")).strip()
        snippet = str(result.get("body", "")).strip()
        url = str(result.get("href", "")).strip()
        out.append(
            "{}. {}\n{}\nSource : {}".format(
                index,
                title or "Résultat sans titre",
                snippet[:800],
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
                        result = web_search(query)
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
        self.sys_text_var = ctk.StringVar(value="Tu es un assistant utile, amical et tu reponds en francais. Sois clair et concis.")
        self.web_search_var = ctk.BooleanVar(value=True)
        self.inline_completion_var = ctk.BooleanVar(value=True)
        self.last_user_prompt = ""

        self.mode_var = ctk.StringVar(value="aucun")
        self.mode_timer_running = False
        self.mode_start_time = 0

        # Autorisations IA
        self.ai_can_create_files = ctk.BooleanVar(value=False)
        self.ai_can_modify_app = ctk.BooleanVar(value=False)

        # Fenêtre de développement
        self.dev_window = None

        os.makedirs(CONVERSATIONS_DIR, exist_ok=True)
        os.makedirs(GENERATED_DIR, exist_ok=True)
        os.makedirs(IA_CREATIONS_DIR, exist_ok=True)
        self._build_ui()
        self._refresh_conversation_list()
        self._refresh_mode_panel()
        self._update_clock()
        self.after(100, self._process_ui_queue)
        self.after(1000, self._tick_mode_timer)

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar gauche
        self.sidebar = ctk.CTkFrame(self, width=300, fg_color=BG_PANEL, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        ctk.CTkLabel(self.sidebar, text="Conversations", font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT_MAIN).pack(pady=(18, 8), padx=16, anchor="w")
        ctk.CTkButton(self.sidebar, text="Nouvelle conversation", height=34, fg_color=ACCENT, hover_color=ACCENT_HOVER, font=ctk.CTkFont(size=12, weight="bold"), command=self.new_conversation).pack(padx=16, pady=(0, 12), fill="x")

        self.conv_list = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.conv_list.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        sep = ctk.CTkFrame(self.sidebar, fg_color="#2a2a2e", height=1)
        sep.pack(fill="x", padx=16, pady=(6, 14))

        ctk.CTkLabel(self.sidebar, text="Modes d'activite", font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT_MAIN).pack(pady=(0, 8), padx=16, anchor="w")
        self.mode_panel = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.mode_panel.pack(fill="x", padx=16, pady=(0, 16))

        # Contenu principal
        self.main = ctk.CTkFrame(self, fg_color=BG_APP, corner_radius=0)
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
            if self.dev_window:
                self.dev_window.destroy()
                self.dev_window = None
            return
        if self.activity.is_active():
            self.activity.stop()
        self.mode_var.set(key)
        self.activity.start(key, label)
        self.mode_timer_running = True
        self.mode_start_time = time.time()
        self.status_var.set("Mode '{}' demarre.".format(label))
        self._refresh_mode_panel()

        # Ouvrir la fenêtre de développement si mode Travail
        if key == "travail" and DevWindow is not None:
            if self.dev_window is None or not self.dev_window.winfo_exists():
                self.dev_window = DevWindow(self)
                self.dev_window.focus()

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
            ctk.CTkButton(row, text="🗑️", width=24, height=24, fg_color="transparent", text_color="#c24141", hover_color="#c24141", command=lambda c=c: self.delete_conversation(c)).pack(side="right", padx=4)
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
            self.current_conv = None
            self.messages = []
            self.conv_title_label.configure(text="Aucune conversation")
            for w in self.chat_container.winfo_children():
                w.destroy()
            self.tools_bar.grid_remove()
        else:
            if not messagebox.askyesno("Confirmer", "Supprimer cette conversation ?"):
                return
        try:
            Path(CONVERSATIONS_DIR, conv["file"]).unlink()
        except Exception:
            pass
        self._refresh_conversation_list()

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
        now = time.strftime("%A %d %B %Y — %H:%M", time.localtime())
        system = "{}\n\nTu es Calisto, l'assistant central de l'application. Reponds en francais. "
        system += "Pour toute demande sur le projet ouvert, analyse d'abord les noms, liens et contenus des fichiers transmis. "
        system += "Pour une demande de code, produis une seule version finale par fichier, sans variantes ni blocs dupliques. "
        system += "Indique le fichier cible et utilise un seul bloc Markdown complet par fichier, avec son langage "
        system += "et un nom de fichier explicite, par exemple ```css filename=style.css. Respecte les fichiers existants et leurs liens. "
        system += "Si une nouvelle cible est necessaire, choisis un nom de fichier adapte et inclus-le dans filename=...; l'editeur cree automatiquement les fichiers manquants. "
        system += "Si l'utilisateur demande de corriger, reparer ou modifier du code, ne te contente pas de conseils : "
        system += "fournis le code complet corrige de chaque fichier modifie dans des blocs distincts avec filename=chemin/relatif. "
        system += "Lis jusqu'a la fin le fichier ouvert et les fichiers lies transmis; s'ils sont tronques, dis-le et ne pretend pas fournir un fichier complet. "
        system += "Base-toi sur le contenu integral des fichiers transmis et conserve tout ce qui n'a pas besoin d'etre change. "
        system += "Ne fournis pas un simple extrait de quelques lignes pour une demande de modification, sauf si l'utilisateur demande explicitement un extrait. "
        system += "N'utilise jamais de points de suspension, de texte fictif ou de marqueurs comme 'code existant' a la place du code. "
        system += "Avant de repondre, verifie que chaque bloc est complet, coherent et directement utilisable dans le fichier cible. "
        system += "Le fichier marque comme ouvert dans le contexte est la cible principale, sauf si la correction concerne une dependance. "
        system += "Ne mets jamais du CSS ou du JavaScript dans un fichier HTML si un fichier CSS ou JavaScript dedie existe. "
        system += "Ne modifie jamais directement les fichiers : chaque proposition devra etre validee."
        system = system.format(self._editor_request_system or "Tu es un assistant utile et clair.")
        system += "\nDate et heure actuelles : {}.".format(now)
        web_search_enabled = self.web_search_var.get()
        if web_search_enabled:
            system += (
                "\nTu peux utiliser l'outil de recherche web pour les informations récentes ou lorsque des sources sont nécessaires. "
                "Appuie les affirmations issues du web sur les URL retournées et indique clairement si la recherche échoue."
            )

        file_ctx = ""
        if context_files:
            file_ctx += "\n\nContexte actuel du projet ouvert dans l'editeur. Analyse ces fichiers avant de proposer une modification. "
            file_ctx += "Conserve les liens entre HTML, CSS et JavaScript et cible le bon fichier existant :\n"
            for fname, fcontent in context_files.items():
                file_ctx += "\n--- FICHIER : {} ---\n{}\n--- FIN DU FICHIER ---\n".format(fname, fcontent)

        history = [
            dict(message)
            for message in self.messages[-8:]
            if message.get("role") in ("user", "assistant")
        ]
        for message in history[:-1]:
            if message["role"] == "assistant":
                message["content"] = re.sub(
                    r"```.*?```",
                    "[ancienne proposition de code omise]",
                    message.get("content", ""),
                    flags=re.DOTALL,
                )
            message["content"] = message.get("content", "")[:1200]
        if not history or history[-1].get("role") != "user" or history[-1].get("content") != prompt:
            raise RuntimeError("La conversation centrale a change pendant la demande de l'editeur.")
        history[-1]["content"] += file_ctx
        msgs = [{"role": "system", "content": system}] + history
        reponse = chat_with_web_search(
            self._editor_request_model,
            msgs,
            self._editor_request_temperature,
            enabled=web_search_enabled,
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
        system = self.sys_text_var.get()
        memory_ctx = self.memory.get_context()
        now = time.strftime("%A %d %B %Y à %H:%M", time.localtime())
        stats_txt = self._activity_stats_text()
        mode = self.mode_var.get()
        active = self.activity.is_active()
        mode_label = self.mode_var.get() if active else "Aucun"
        system_with_context = "{}\n\nDate et heure actuelles : {}.\nMode d'activité actuel : {} ({}).\nStatistiques d'activité :\n{}".format(system, now, mode_label, mode, stats_txt)
        if mode == "travail" and active:
            system_with_context += "\n\nTu es en mode TRAVAIL / FORMATION DEVELOPPEUR WEB. L'utilisateur est en train de travailler. Propose activement ton aide sur HTML, CSS, JavaScript, React, Node.js, ou tout sujet de developpement web, sans qu'il ait a te le demander. Sois pedagogique et encourageant."
        if self._pending_editor_context:
            system_with_context += "\n\nL'utilisateur travaille dans l'editeur. Pour les changements de code, "
            system_with_context += "analyse les noms et liens des fichiers du projet fournis avec sa question. "
            system_with_context += "produis une seule version finale et un seul bloc complet par fichier cible, sans variantes ni doublons. "
            system_with_context += "Indique le fichier cible; separe HTML, CSS et JavaScript en blocs distincts "
            system_with_context += "et utilise un nom de fichier explicite dans la balise, ex. ```css filename=style.css. "
            system_with_context += "Si un fichier cible manque, choisis son nom; l'editeur le cree automatiquement. "
            system_with_context += "Pour une demande de correction, donne le code complet corrige dans ces blocs, pas seulement des conseils. "
            system_with_context += "Ne donne pas un extrait de quelques lignes, de points de suspension ou un marqueur a la place du code complet. "
            system_with_context += "Ne mets pas du CSS dans le HTML si une feuille CSS existe."
        web_search_enabled = self.web_search_var.get()
        if web_search_enabled:
            system_with_context += (
                "\n\nTu peux utiliser l'outil de recherche web pour les informations récentes ou lorsque des sources sont nécessaires. "
                "Cite les URL fournies par les résultats et indique clairement si la recherche échoue."
            )

        if self.ai_can_create_files.get():
            system_with_context += "\n\nTu as l'autorisation de creer des fichiers pour l'utilisateur. Pour creer un fichier, utilise ce format exact dans ta reponse :\n[CREER_FICHIER: nom_du_fichier.ext]\ncontenu du fichier\n[/CREER_FICHIER]\nLe fichier sera enregistre dans le dossier ia_creations/. Tu peux creer des scripts, des pages web, des documents, etc. Tu peux aussi creer des fichiers PDF (.pdf)."

        if self.ai_can_modify_app.get():
            system_with_context += "\n\nTu as l'autorisation de modifier le code de l'application Calisto elle-même. Pour modifier un fichier de l'application, utilise ce format exact :\n[MODIFIER_APP: chemin_du_fichier.py]\nnouveau contenu du fichier\n[/MODIFIER_APP]\nUne demande de confirmation s'affichera a l'utilisateur avant chaque modification."
        conversation = self.messages.copy()
        if self._pending_editor_context:
            conversation = [dict(message) for message in conversation[-8:]]
            for message in conversation[:-1]:
                if message.get("role") == "assistant":
                    message["content"] = re.sub(
                        r"```.*?```",
                        "[ancienne proposition de code omise]",
                        message.get("content", ""),
                        flags=re.DOTALL,
                    )
                message["content"] = message.get("content", "")[:1200]
        if self._pending_editor_context and conversation and conversation[-1].get("role") == "user":
            conversation[-1] = dict(conversation[-1])
            conversation[-1]["content"] += (
                "\n\nFichiers et etat actuels de l'editeur (analyse-les avant de repondre) :\n"
                + self._pending_editor_context
            )
        msgs = [{"role": "system", "content": system_with_context + memory_ctx}] + conversation
        full = ""
        try:
            if web_search_enabled:
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
            stream = ollama.chat(
                model=model,
                messages=msgs,
                stream=True,
                options={"temperature": temperature, "num_ctx": 24576, "num_predict": 8192},
            )
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


if __name__ == "__main__":
    app = App()
    app.mainloop()
