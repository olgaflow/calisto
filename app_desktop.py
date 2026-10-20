import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk
import ollama
import threading
import os
import json
import re
import queue
import time
import socket
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
VERSION = "1.4.0"
GENERATED_DIR = "generated"
IA_CREATIONS_DIR = "ia_creations"
CONVERSATIONS_DIR = "conversations"
MAX_WEB_SEARCH_ROUNDS = 3
MAX_WEB_SEARCH_CALLS = 3

WEB_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "rechercher_sur_internet",
        "description": "Recherche des pages web ou des actualités récentes avec DuckDuckGo. Utilisez uniquement quand l'utilisateur demande des informations en ligne.",
        "parameters": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string", "description": "Une requête de mots-clés précise."},
                "region": {"type": "string", "enum": ["fr-fr", "wt-wt", "us-en"], "description": "Région et langue."},
                "timelimit": {"type": "string", "enum": ["d", "w", "m", "y"], "description": "Ancienneté max."},
                "search_type": {"type": "string", "enum": ["text", "news"], "description": "text ou news."},
                "max_results": {"type": "integer", "description": "Nombre de résultats (1-10)."},
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
IA_COLOR = "#a855f7"
IA_HOVER = "#9333ea"

os.makedirs(GENERATED_DIR, exist_ok=True)
os.makedirs(IA_CREATIONS_DIR, exist_ok=True)
os.makedirs(CONVERSATIONS_DIR, exist_ok=True)


def web_search(query, max_results=5, region="fr-fr", timelimit=None, search_type="text"):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, region=region, timelimit=timelimit, safesearch="moderate", max_results=max_results))
        lines = []
        for r in results:
            lines.append("- {} : {}".format(r.get("title", ""), r.get("href", "")))
        return "\n".join(lines) if lines else "Aucun résultat trouvé."
    except Exception as e:
        return "Erreur de recherche : {}".format(str(e))


def read_file_content(path):
    p = Path(path)
    if not p.exists():
        return ""
    try:
        if p.suffix.lower() == ".pdf":
            reader = PdfReader(str(p))
            text = []
            for page in reader.pages:
                text.append(page.extract_text() or "")
            return "\n".join(text)
        return p.read_text(encoding="utf-8")
    except Exception:
        return ""


def chat_with_web_search(model, messages, temperature, enabled, on_search=None):
    conversation = [dict(message) for message in messages]
    search_count = 0
    for round_index in range(MAX_WEB_SEARCH_ROUNDS + 1):
        can_call_tools = enabled and round_index < MAX_WEB_SEARCH_ROUNDS
        request = {
            "model": model,
            "messages": conversation,
            "options": {"temperature": temperature, "num_ctx": 8192, "num_predict": 4096},
        }
        if can_call_tools:
            request["tools"] = [WEB_SEARCH_TOOL]
        response = ollama.chat(**request)
        assistant_message = response.get("message", {})
        tool_calls = assistant_message.get("tool_calls", []) or []
        if not tool_calls:
            content = assistant_message.get("content", "")
            if content:
                return content
            raise RuntimeError("Réponse vide de l'IA.")
        if not can_call_tools:
            raise RuntimeError("Limite de recherches atteinte.")
        conversation.append(assistant_message)
        for tool_call in tool_calls:
            function = tool_call.get("function", {})
            name = function.get("name", "")
            arguments = function.get("arguments", {})
            if name != "rechercher_sur_internet":
                result = "Erreur : outil non autorisé."
            else:
                query = arguments.get("query", "")
                if search_count >= MAX_WEB_SEARCH_CALLS:
                    result = "Limite de recherches atteinte."
                else:
                    search_count += 1
                    if on_search:
                        on_search(query)
                    result = web_search(query)
            conversation.append({"role": "tool", "content": result})
    raise RuntimeError("Trop de tours de recherche.")


# =====================================================================
# FENETRE DE PROGRESSION (pour generation IA / exercice)
# =====================================================================
class ProgressWindow:
    def __init__(self, parent, title="Generation en cours", message="L'IA travaille…"):
        self.win = ctk.CTkToplevel(parent)
        self.win.title(title)
        self.win.geometry("400x160")
        self.win.configure(fg_color="#1a1a1b")
        self.win.transient(parent)
        self.win.grab_set()
        self.win.resizable(False, False)

        ctk.CTkLabel(self.win, text=message, font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT_MAIN).pack(pady=(20, 10))
        self.pb = ctk.CTkProgressBar(self.win, width=300)
        self.pb.pack(pady=10)
        self.pb.set(0)
        self.lbl = ctk.CTkLabel(self.win, text="0%", font=ctk.CTkFont(size=12), text_color=TEXT_MUTED)
        self.lbl.pack()
        self._animating = True
        self._animate(0)

    def _animate(self, i=0):
        if not self._animating:
            return
        if i <= 100:
            self.pb.set(i / 100)
            self.lbl.configure(text="{}%".format(i))
            self.win.after(40, lambda: self._animate(i + 4))
        else:
            self.pb.set(1)
            self.lbl.configure(text="100%")

    def close(self):
        self._animating = False
        try:
            self.win.destroy()
        except Exception:
            pass


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Calisto - Assistant IA pour débutants")
        self.geometry("1300x850")
        self.minsize(1000, 650)
        self.configure(fg_color=BG_APP)
        self.resizable(True, True)

        self.model_var = ctk.StringVar(value=MODEL)
        self.temp_var = ctk.DoubleVar(value=0.7)
        self.sys_text_var = ctk.StringVar(value="Tu es Calisto, un assistant chaleureux et naturel. Tu parles en français comme si tu discutais avec une personne. Sois simple, direct et encourageant. N'utilise pas de ton robotique. Si tu ne comprends pas une question, dis-le et demande une précision.")
        self.web_search_var = ctk.BooleanVar(value=False)
        self.inline_completion_var = ctk.BooleanVar(value=True)
        self.ai_can_create_files = ctk.BooleanVar(value=False)
        self.ai_can_modify_app = ctk.BooleanVar(value=False)

        self.dev_window = None
        self.messages = []
        self.streaming = False
        self.attached_files = []
        self.ui_queue = queue.Queue()
        self.last_user_prompt = ""
        self._is_repeat_query = False
        self._pending_editor_context = ""
        self._learning_sujets = []

        # Conversation management
        self.current_conv_id = None
        self.conversations = []  # list of dicts: id, title, created_at, updated_at

        self._build_ui()
        self._load_conversations()
        self._send_welcome_message()
        self._check_ollama()
        self.after(100, self._process_ui_queue)

    # =====================================================================
    # UI CONSTRUCTION - STYLE CHATGPT
    # =====================================================================
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=0, minsize=320)  # Sidebar conversations
        self.grid_columnconfigure(1, weight=1)               # Main chat
        self.grid_rowconfigure(0, weight=1)

        # ---------------- SIDEBAR CONVERSATIONS ----------------
        self.sidebar = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0, border_width=1, border_color="#333336")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(2, weight=1)

        # Header sidebar
        s_header = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        s_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(12, 8))
        ctk.CTkLabel(s_header, text="💬 Conversations", font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT_MAIN).pack(side="left")
        ctk.CTkButton(s_header, text="+", width=32, height=32, command=self.new_conversation, fg_color=ACCENT, hover_color=ACCENT_HOVER, font=ctk.CTkFont(size=16, weight="bold")).pack(side="right", padx=4)
        ctk.CTkButton(s_header, text="🔍", width=32, height=32, command=self._focus_search, fg_color=BG_INPUT, hover_color="#4b4c54", font=ctk.CTkFont(size=14)).pack(side="right", padx=4)

        # Search bar
        self.conv_search = ctk.CTkEntry(self.sidebar, placeholder_text="Rechercher une conversation…", fg_color=BG_INPUT, border_color="#4b4c54", text_color=TEXT_MAIN, height=30)
        self.conv_search.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 8))
        self.conv_search.bind("<KeyRelease>", lambda e: self._filter_conversations())

        # Conversations list
        self.conv_list_frame = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.conv_list_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=(0, 8))
        self.conv_list_frame.grid_columnconfigure(0, weight=1)

        # Settings button at bottom of sidebar
        ctk.CTkButton(self.sidebar, text="⚙️ Réglages", width=200, command=self.open_settings, fg_color=BG_INPUT, hover_color="#4b4c54", font=ctk.CTkFont(size=12)).grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 12))

        # ---------------- MAIN CHAT ----------------
        self.main = ctk.CTkFrame(self, fg_color=BG_APP, corner_radius=0)
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(1, weight=1)

        # Chat header
        self.chat_header = ctk.CTkFrame(self.main, fg_color=BG_APP, height=50, corner_radius=0)
        self.chat_header.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        self.chat_header.grid_propagate(False)
        self.chat_header.grid_columnconfigure(1, weight=1)
        self.conv_title_label = ctk.CTkLabel(self.chat_header, text="Nouvelle conversation", font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT_MAIN)
        self.conv_title_label.grid(row=0, column=0, sticky="w", padx=20, pady=12)
        self.status_label = ctk.CTkLabel(self.chat_header, text="● Prêt", font=ctk.CTkFont(size=11), text_color="#10a37f")
        self.status_label.grid(row=0, column=2, sticky="e", padx=20, pady=12)

        # Messages area
        self.chat_container = ctk.CTkScrollableFrame(self.main, fg_color=BG_APP)
        self.chat_container.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.chat_container.grid_columnconfigure(0, weight=1)

        # Input area
        self.input_area = ctk.CTkFrame(self.main, fg_color=BG_PANEL, height=130, corner_radius=0)
        self.input_area.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
        self.input_area.grid_propagate(False)
        self.input_area.grid_columnconfigure(0, weight=1)

        self.entry = ctk.CTkTextbox(self.input_area, height=80, font=ctk.CTkFont(size=13), fg_color=BG_INPUT, border_color="#4b4c54", text_color=TEXT_MAIN)
        self.entry.grid(row=0, column=0, sticky="nsew", padx=15, pady=12)
        self.entry.bind("<Return>", self.on_enter)
        self.entry.bind("<Shift-Return>", self.on_shift_enter)

        right = ctk.CTkFrame(self.input_area, fg_color="transparent")
        right.grid(row=0, column=1, sticky="ns", padx=10, pady=10)
        self.send_btn = ctk.CTkButton(right, text="Envoyer", width=100, height=34, command=self.send, fg_color=ACCENT, hover_color=ACCENT_HOVER, font=ctk.CTkFont(size=13, weight="bold"))
        self.send_btn.pack(pady=(0, 6))
        ctk.CTkButton(right, text="Effacer", width=100, height=28, command=self.clear_chat, fg_color=BG_INPUT, hover_color="#4b4c54", font=ctk.CTkFont(size=11)).pack()

        # File chips
        self.file_chips_label = ctk.CTkLabel(self.main, text="", font=ctk.CTkFont(size=11), text_color="#a78bfa", anchor="w")
        self.file_chips_label.grid(row=3, column=0, sticky="w", padx=20, pady=(6, 0))

        # ---------------- EDITOR TAB (via dev_window) ----------------
        # The editor is accessed via the Tabs in the original design, but here we keep
        # a simple button in settings to open dev_window. The dev_window is embedded
        # when needed.

    # =====================================================================
    # CONVERSATION MANAGEMENT
    # =====================================================================
    def _load_conversations(self):
        self.conversations = []
        try:
            files = sorted(Path(CONVERSATIONS_DIR).glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        except Exception:
            files = []
        for f in files:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                self.conversations.append({
                    "id": data.get("id", f.stem),
                    "file": f.name,
                    "title": data.get("title", "Sans titre"),
                    "created_at": data.get("created_at", 0),
                    "updated_at": data.get("updated_at", 0),
                    "messages": data.get("messages", []),
                })
            except Exception:
                continue
        self._refresh_conversation_list()
        if self.conversations and not self.current_conv_id:
            self.select_conversation(self.conversations[0]["id"])
        elif not self.conversations:
            self.new_conversation()

    def _refresh_conversation_list(self):
        for w in self.conv_list_frame.winfo_children():
            w.destroy()
        term = self.conv_search.get().lower() if hasattr(self, "conv_search") else ""
        filtered = [c for c in self.conversations if term in c["title"].lower()] if term else self.conversations
        for c in filtered:
            row = ctk.CTkFrame(self.conv_list_frame, fg_color="transparent")
            row.pack(fill="x", pady=2, padx=4)
            is_active = (self.current_conv_id == c["id"])
            row.configure(fg_color=BG_INPUT if is_active else "transparent")
            title = c["title"]
            if len(title) > 26:
                title = title[:23] + "..."
            btn = ctk.CTkButton(row, text=title, anchor="w", fg_color="transparent",
                               text_color=TEXT_MAIN if is_active else TEXT_MUTED,
                               hover_color=BG_INPUT, height=30, font=ctk.CTkFont(size=12),
                               command=lambda cid=c["id"]: self.select_conversation(cid))
            btn.pack(side="left", fill="x", expand=True, padx=(4, 4), pady=2)
            ctk.CTkButton(row, text="🗑️", width=28, height=28, fg_color="#8f3030", hover_color="#c24141",
                          text_color="#ffffff", font=ctk.CTkFont(size=12),
                          command=lambda cid=c["id"]: self.delete_conversation(cid)).pack(side="right", padx=4, pady=2)

    def _filter_conversations(self):
        self._refresh_conversation_list()

    def _focus_search(self):
        self.conv_search.focus_set()

    def new_conversation(self):
        if self.streaming:
            self.status_label.configure(text="⏳ Attendez la fin de la réponse…", text_color="#f59e0b")
            return
        cid = str(int(time.time() * 1000))
        conv = {
            "id": cid, "file": "conv_{}.json".format(cid),
            "title": "Nouvelle conversation",
            "created_at": time.time(), "updated_at": time.time(),
            "messages": [],
        }
        path = Path(CONVERSATIONS_DIR) / conv["file"]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(conv, f, ensure_ascii=False, indent=2)
        self.conversations.insert(0, conv)
        self._refresh_conversation_list()
        self.select_conversation(cid)

    def select_conversation(self, cid):
        if self.streaming:
            return
        conv = next((c for c in self.conversations if c["id"] == cid), None)
        if not conv:
            return
        self.current_conv_id = cid
        self.messages = list(conv.get("messages", []))
        self.conv_title_label.configure(text=conv["title"])
        self.status_label.configure(text="● Prêt", text_color="#10a37f")
        self._render_chat()
        self._refresh_conversation_list()

    def delete_conversation(self, cid):
        if self.streaming:
            return
        conv = next((c for c in self.conversations if c["id"] == cid), None)
        if not conv:
            return
        if not messagebox.askyesno("Supprimer", "Supprimer cette conversation ?"):
            return
        try:
            (Path(CONVERSATIONS_DIR) / conv["file"]).unlink()
        except OSError as e:
            messagebox.showerror("Erreur", "Impossible de supprimer : {}".format(e))
            return
        self.conversations = [c for c in self.conversations if c["id"] != cid]
        if self.current_conv_id == cid:
            self.current_conv_id = None
            self.messages = []
            self.conv_title_label.configure(text="Nouvelle conversation")
            for w in self.chat_container.winfo_children():
                w.destroy()
        self._refresh_conversation_list()
        if self.conversations and not self.current_conv_id:
            self.select_conversation(self.conversations[0]["id"])
        elif not self.conversations:
            self.new_conversation()

    def _save_current(self):
        if not self.current_conv_id:
            return
        conv = next((c for c in self.conversations if c["id"] == self.current_conv_id), None)
        if not conv:
            return
        conv["messages"] = self.messages
        conv["updated_at"] = time.time()
        if conv["title"] == "Nouvelle conversation" and self.messages:
            for m in self.messages:
                if m.get("role") == "user":
                    conv["title"] = m["content"][:40]
                    break
        self.conv_title_label.configure(text=conv["title"])
        path = Path(CONVERSATIONS_DIR) / conv["file"]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(conv, f, ensure_ascii=False, indent=2)
        self._refresh_conversation_list()

    def _render_chat(self):
        for w in self.chat_container.winfo_children():
            w.destroy()
        if not self.messages:
            self._send_welcome_message(animate=False)
            return
        for m in self.messages:
            role = m.get("role", "user")
            sender = "Vous" if role == "user" else ("Système" if role == "system" else "IA")
            self._add_bubble(sender, m.get("content", ""), role, animate=False)

    def _send_welcome_message(self, animate=True):
        welcome = """Bienvenue dans Calisto ! 👋

Je suis votre assistant IA local (Ollama). Vous pouvez :

💬 **Discuter** – Posez-moi n'importe quelle question
📎 **Analyser des fichiers** – Joignez des fichiers texte, code ou PDF
💻 **Éditeur de code** – Utilisez le bouton Éditeur dans les réglages
🎮 **Mode Apprentissage** – Apprenez à coder HTML/CSS/JS par la pratique

Comment puis-je vous aider aujourd'hui ?"""
        self.messages.append({"role": "assistant", "content": welcome})
        self._add_bubble("IA", welcome, "assistant", animate=animate)
        self._save_current()

    # =====================================================================
    # CHAT
    # =====================================================================
    def on_enter(self, event):
        if self.streaming:
            return "break"
        if event.state & 0x1:
            return None
        self.send()
        return "break"

    def on_shift_enter(self, event):
        return None

    def send(self):
        if self.streaming:
            return
        prompt = self.entry.get("1.0", "end").strip()
        if not prompt and not self.attached_files:
            return
        self._is_repeat_query = (prompt == self.last_user_prompt)
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
        self._add_bubble("Vous", prompt if prompt else "[Fichier(s)]", "user", animate=False)
        self._save_current()
        self.streaming = True
        self.send_btn.configure(state="disabled", fg_color="#4b4c54")
        self.status_label.configure(text="● L'IA répond…", text_color="#f59e0b")
        threading.Thread(target=self._stream, daemon=True).start()

    def clear_chat(self):
        if self.streaming:
            return
        self.messages = []
        for w in self.chat_container.winfo_children():
            w.destroy()
        self._send_welcome_message()
        self.status_label.configure(text="● Prêt", text_color="#10a37f")
        self._save_current()

    def _add_bubble(self, sender, text, role, animate=True):
        row = ctk.CTkFrame(self.chat_container, fg_color="transparent")
        row.pack(fill="x", pady=6, padx=10)
        if role == "user":
            row.pack_configure(anchor="e")
            bubble_color = BUBBLE_USER
            header_color = "#ffffff"
            side = "right"
            padx = (80, 10)
        else:
            row.pack_configure(anchor="w")
            bubble_color = BUBBLE_AI
            header_color = "#a78bfa"
            side = "left"
            padx = (10, 80)

        bubble = ctk.CTkFrame(row, fg_color=bubble_color, corner_radius=14)
        bubble.pack(side=side, padx=padx)
        ctk.CTkLabel(bubble, text=sender, font=ctk.CTkFont(size=11, weight="bold"), text_color=header_color, anchor="w").pack(fill="x", padx=14, pady=(10, 4))
        lbl = ctk.CTkLabel(bubble, text=text, font=ctk.CTkFont(size=14), text_color=TEXT_MAIN, justify="left", wraplength=750, anchor="w")
        lbl.pack(fill="x", padx=14, pady=(0, 12))
        if role in ("user", "assistant"):
            ctk.CTkButton(bubble, text="📋", width=22, height=22, fg_color="transparent", hover_color=bubble_color, text_color=header_color, font=ctk.CTkFont(size=11), command=lambda t=text: self.copy_to_clipboard(t)).pack(side="right", padx=8, pady=8)
        self.after(30, self._scroll_bottom)
        return bubble, lbl

    def _scroll_bottom(self):
        try:
            self.update_idletasks()
            self.chat_container._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass

    def _refresh_file_chips(self):
        if not self.attached_files:
            self.file_chips_label.configure(text="")
            return
        noms = " | ".join("📎 {}".format(p.name) for p in self.attached_files)
        self.file_chips_label.configure(text=noms)

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
            self.status_label.configure(text="● Fichier joint : {}".format(p.name), text_color="#f59e0b")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def copy_to_clipboard(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)

    # =====================================================================
    # IA STREAM
    # =====================================================================
    def _stream(self):
        model = self.model_var.get() or MODEL
        temperature = self.temp_var.get()
        system = self.sys_text_var.get()
        now = time.strftime("%A %d %B %Y à %H:%M", time.localtime())
        system_with_context = "{}\n\nDate et heure actuelles : {}.\n".format(system, now)

        system_with_context += (
            "\nRègles de conversation :"
            "\n- Parlez de façon naturelle, chaleureuse et directe, comme à l'oral."
            "\n- Si vous ne comprenez pas la question, dites-le clairement et demandez une précision."
            "\n- Si l'utilisateur repose la même question, ne répétez pas exactement la même réponse."
            "\n- Évitez le ton robotique, les listes à puces interminables."
        )
        system_with_context += (
            "\n\nPour toute demande de code :"
            "\n- Produisez une seule version finale par fichier, sans variantes."
            "\n- Indiquez le fichier cible dans un bloc Markdown complet, ex. ```css filename=style.css."
            "\n- Ne fournissez jamais un simple extrait de quelques lignes."
        )
        if self.web_search_var.get():
            system_with_context += (
                "\n\nLa recherche web est disponible mais ne l'utilisez JAMAIS pour du code local."
                "\nN'appelez rechercher_sur_internet QUE si l'utilisateur demande explicitement des informations en ligne."
            )
        if self.ai_can_create_files.get():
            system_with_context += "\n\nVous pouvez créer des fichiers. Utilisez [CREER_FICHIER: nom.ext] contenu [/CREER_FICHIER]."
        if self.ai_can_modify_app.get():
            system_with_context += "\n\nVous pouvez modifier l'application Calisto. Utilisez [MODIFIER_APP: chemin.py] contenu [/MODIFIER_APP]."
        if self._is_repeat_query:
            system_with_context += "\n\nNOTE : l'utilisateur repose la même question. Ne répétez pas la même réponse."
            self._is_repeat_query = False

        history = [dict(m) for m in self.messages[-10:]]
        for m in history:
            m["content"] = m.get("content", "")[:2500]
        if self._pending_editor_context and history and history[-1].get("role") == "user":
            history[-1] = dict(history[-1])
            history[-1]["content"] += "\n\nContenu de l'éditeur :\n" + self._pending_editor_context

        msgs = [{"role": "system", "content": system_with_context}] + history
        full = ""
        try:
            if self.web_search_var.get():
                full = chat_with_web_search(model, msgs, temperature, enabled=True,
                                            on_search=lambda q: self.after(0, lambda: self.status_label.configure(text="● Recherche web : {}".format(q), text_color="#f59e0b")))
                bubble, lbl = self._add_bubble("IA", "", "assistant")
                self.ui_queue.put(("done", lbl, full, bubble))
                return
            last_err = None
            for attempt in range(2):
                try:
                    stream = ollama.chat(model=model, messages=msgs, stream=True,
                                         options={"temperature": temperature, "num_ctx": 8192, "num_predict": 2048})
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
                elif ev[0] == "done":
                    _, lbl, full, bubble = ev
                    if lbl.winfo_exists():
                        lbl.configure(text=full)
                    self.messages.append({"role": "assistant", "content": full})
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
        self.status_label.configure(text="● Prêt", text_color="#10a37f")

    def _get_editor_context(self):
        if self.dev_window is not None and self.dev_window.winfo_exists():
            return self.dev_window.get_ai_context()
        return ""

    def check_ai_creation_commands(self, text):
        pattern = r"\[CREER_FICHIER: ([^\]]+)\](.*?)\[/CREER_FICHIER\]"
        for filepath, content in re.findall(pattern, text, re.DOTALL):
            self.handle_ai_creation_request("fichier", filepath.strip(), content.strip())
        pattern2 = r"\[MODIFIER_APP: ([^\]]+)\](.*?)\[/MODIFIER_APP\]"
        for filepath, content in re.findall(pattern2, text, re.DOTALL):
            self.handle_ai_creation_request("app", filepath.strip(), content.strip())

    def handle_ai_creation_request(self, command_type, filepath, content):
        if command_type == "app" and not self.ai_can_modify_app.get():
            resp = messagebox.askyesno("Autorisation IA", "L'IA propose de modifier le fichier de l'application :\n{}\n\nAutoriser ?".format(filepath))
            if not resp:
                self.status_label.configure(text="● Modification refusée", text_color="#c24141")
                return
        elif command_type == "fichier" and not self.ai_can_create_files.get():
            resp = messagebox.askyesno("Autorisation IA", "L'IA propose de créer un fichier :\n{}\n\nAutoriser ?".format(filepath))
            if not resp:
                self.status_label.configure(text="● Création refusée", text_color="#c24141")
                return
        else:
            resp = messagebox.askyesno("Confirmer", "L'IA propose de {} le fichier :\n{}\n\nConfirmer ?".format("modifier l'application" if command_type == "app" else "créer", filepath))
            if not resp:
                self.status_label.configure(text="● Action annulée", text_color="#c24141")
                return

        try:
            if command_type == "app":
                target_path = Path(filepath)
            else:
                target_path = Path(IA_CREATIONS_DIR) / filepath
            target_path.parent.mkdir(parents=True, exist_ok=True)
            if str(filepath).lower().endswith(".pdf"):
                try:
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Helvetica", "", 12)
                    for line in str(content).splitlines():
                        pdf.multi_cell(0, 10, line)
                    pdf.output(str(target_path))
                    messagebox.showinfo("Succès", "PDF créé :\n{}".format(filepath))
                    return
                except Exception as e:
                    messagebox.showerror("Erreur PDF", str(e))
                    return
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("Succès", "Fichier {} avec succès :\n{}".format("modifié" if command_type == "app" else "créé", filepath))
            self.status_label.configure(text="● Fichier {} : {}".format("modifié" if command_type == "app" else "créé", filepath), text_color="#10a37f")
        except Exception as e:
            messagebox.showerror("Erreur", "Impossible d'écrire le fichier : {}".format(str(e)))

    def open_settings(self):
        win = ctk.CTkToplevel(self)
        win.title("Réglages")
        win.geometry("620x750")
        win.configure(fg_color=BG_APP)
        win.transient(self)
        win.grab_set()
        win.resizable(True, True)

        ctk.CTkLabel(win, text="⚙️ Réglages", font=ctk.CTkFont(size=20, weight="bold"), text_color=TEXT_MAIN).pack(pady=(20, 15))

        body = ctk.CTkFrame(win, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=30, pady=10)

        def row(label, widget, pady=12):
            r = ctk.CTkFrame(body, fg_color="transparent")
            r.pack(fill="x", pady=pady)
            ctk.CTkLabel(r, text=label, font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_MAIN).pack(side="left")
            widget.pack(side="right")

        row("Modèle Ollama :", ctk.CTkEntry(body, textvariable=self.model_var, width=170))
        row("Température :", ctk.CTkSlider(body, from_=0.0, to=1.5, variable=self.temp_var, width=200))
        ctk.CTkLabel(body, textvariable=self.temp_var, font=ctk.CTkFont(size=12), text_color=TEXT_MUTED).pack()

        ctk.CTkLabel(body, text="Instruction système (personnalité de l'IA) :", font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_MAIN).pack(anchor="w", pady=(15, 5))
        sys_txt = ctk.CTkTextbox(body, height=100, font=ctk.CTkFont(size=12), fg_color=BG_INPUT, border_color="#4b4c54", text_color=TEXT_MAIN)
        sys_txt.pack(fill="x", pady=(0, 15))
        sys_txt.insert("1.0", self.sys_text_var.get())

        ctk.CTkSwitch(body, text="Autoriser la recherche web", variable=self.web_search_var, font=ctk.CTkFont(size=13)).pack(anchor="w", pady=5)
        ctk.CTkSwitch(body, text="Suggestions de code IA en direct (éditeur)", variable=self.inline_completion_var, font=ctk.CTkFont(size=13)).pack(anchor="w", pady=5)
        ctk.CTkSwitch(body, text="Autoriser l'IA à créer des fichiers", variable=self.ai_can_create_files, font=ctk.CTkFont(size=13)).pack(anchor="w", pady=5)
        ctk.CTkSwitch(body, text="Autoriser l'IA à modifier l'application", variable=self.ai_can_modify_app, font=ctk.CTkFont(size=13)).pack(anchor="w", pady=15)

        ctk.CTkLabel(body, text="Éditeur de code", font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_MAIN).pack(anchor="w", pady=(15, 5))
        ctk.CTkButton(body, text="Ouvrir l'éditeur de code", width=200, command=self.open_editor, fg_color=ACCENT, hover_color=ACCENT_HOVER, font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=5)

        ctk.CTkLabel(body, text="Aide / Raccourcis", font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_MAIN).pack(anchor="w", pady=(15, 5))
        help_txt = (
            "Éditeur de code :\n"
            "  Ctrl+S : Sauvegarder  |  Ctrl+F : Rechercher  |  Ctrl+G : Aller à la ligne\n"
            "  Ctrl+/ : Commenter  |  Ctrl+Molette : Zoom\n"
            "  Auto-fermeture : ( ) [ ] { } \" \" ' '\n\n"
            "Chat IA :\n"
            "  Réponse directe, sans recherche web inutile.\n"
            "  La recherche web ne se déclenche que si vous l'activez dans les réglages."
        )
        ctk.CTkLabel(body, text=help_txt, font=ctk.CTkFont(size=11), text_color=TEXT_MUTED, justify="left").pack(anchor="w", pady=(0, 15))

        def save_close():
            self.sys_text_var.set(sys_txt.get("1.0", "end").strip())
            self.status_label.configure(text="● Réglages enregistrés", text_color="#10a37f")
            win.destroy()

        btns = ctk.CTkFrame(win, fg_color="transparent")
        btns.pack(fill="x", padx=30, pady=20)
        ctk.CTkButton(btns, text="Annuler", width=100, command=win.destroy, fg_color=BG_INPUT, hover_color="#4b4c54").pack(side="right", padx=10)
        ctk.CTkButton(btns, text="Enregistrer", width=100, command=save_close, fg_color=ACCENT, hover_color=ACCENT_HOVER, font=ctk.CTkFont(size=13, weight="bold")).pack(side="right")

    def open_editor(self):
        if self.dev_window is not None and self.dev_window.winfo_exists():
            self.dev_window.focus_set()
            return
        win = ctk.CTkToplevel(self)
        win.title("Éditeur de code - Calisto")
        win.geometry("1300x850")
        win.configure(fg_color=BG_APP)
        win.transient(self)
        win.resizable(True, True)
        self.dev_window = DevWindow(self, master=win)
        self.dev_window.pack(fill="both", expand=True)
        win.protocol("WM_DELETE_WINDOW", lambda: self._on_editor_close(win))

    def _on_editor_close(self, win):
        self.dev_window = None
        win.destroy()

    def _check_ollama(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            result = s.connect_ex(("127.0.0.1", 11434))
            s.close()
            if result == 0:
                self.status_label.configure(text="● Ollama en ligne", text_color="#10a37f")
            else:
                self.status_label.configure(text="● Ollama hors ligne", text_color="#c24141")
        except Exception:
            self.status_label.configure(text="● Ollama inconnu", text_color="#c24141")
        self.after(30000, self._check_ollama)


# =====================================================================
# MODE APPRENTISSAGE / JEUX
# =====================================================================
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
        self.win.geometry("1200x800")
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
        self.exercise_ready = False  # True quand l'exercice est genere et pret a commencer
        self.progress = None

        self._build_ui()
        self.status_label.configure(text="Génération du sujet en cours…", text_color=TEXT_MUTED)
        threading.Thread(target=self._generate_subject, daemon=True).start()

    def _build_ui(self):
        self.win.grid_columnconfigure(0, weight=1, minsize=260)
        self.win.grid_columnconfigure(1, weight=2)
        self.win.grid_columnconfigure(2, weight=1)
        self.win.grid_rowconfigure(0, weight=0)  # Header
        self.win.grid_rowconfigure(1, weight=1)  # Content

        # Header
        header = ctk.CTkFrame(self.win, fg_color=BG_PANEL, corner_radius=0)
        header.grid(row=0, column=0, columnspan=3, sticky="ew", padx=3, pady=3)
        header.grid_propagate(False)
        header.configure(height=44)

        ctk.CTkLabel(header, text="🎮 Mode Apprentissage", font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT_MAIN).pack(side="left", padx=15, pady=8)
        self.exercise_label = ctk.CTkLabel(header, text="Exercice 0", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_MUTED)
        self.exercise_label.pack(side="left", padx=15, pady=8)
        self.level_btn = ctk.CTkOptionMenu(header, values=[LEARNING_LEVELS[k]["label"] for k in LEARNING_LEVELS], command=self._on_level_change, width=140)
        self.level_btn.set("Junior")
        self.level_btn.pack(side="right", padx=15, pady=8)

        self.timer_label = ctk.CTkLabel(self.win, text="00:00:00", font=ctk.CTkFont(size=22, weight="bold"), text_color=ACCENT)
        self.timer_label.grid(row=0, column=1, columnspan=2, sticky="e", padx=15, pady=(8, 0))

        # Files (col 0)
        files_frame = ctk.CTkFrame(self.win, fg_color="#252526", corner_radius=0, border_width=2, border_color="#44444a")
        files_frame.grid(row=1, column=0, sticky="nsew", padx=3, pady=3)
        files_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(files_frame, text="📂 Fichiers", font=ctk.CTkFont(size=14, weight="bold"), text_color=ACCENT).pack(pady=(10, 8))
        self.files_list = ctk.CTkScrollableFrame(files_frame, fg_color="#1a1a1b")
        self.files_list.pack(fill="both", expand=True, padx=5, pady=5)
        self.file_buttons = {}
        self._refresh_files_ui()
        ctk.CTkButton(files_frame, text="+ Nouveau fichier", width=140, command=self._add_file, fg_color="#6366f1", hover_color="#4f46e5", font=ctk.CTkFont(size=11)).pack(pady=6)

        # Editor (col 1)
        editor_frame = ctk.CTkFrame(self.win, fg_color=BG_EDITOR, corner_radius=0, border_width=2, border_color="#44444a")
        editor_frame.grid(row=1, column=1, sticky="nsew", padx=3, pady=3)
        editor_frame.grid_rowconfigure(1, weight=1)
        editor_frame.grid_columnconfigure(0, weight=1)

        self.editor_label = ctk.CTkLabel(editor_frame, text="index.html", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_MUTED)
        self.editor_label.grid(row=0, column=0, sticky="w", padx=12, pady=6)

        self.code_editor = ctk.CTkTextbox(editor_frame, font=ctk.CTkFont(family="Consolas", size=13), fg_color="#1e1e1e", text_color="#d4d4d4", border_width=0, wrap="none")
        self.code_editor.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 5))
        self.code_editor.bind("<Control-c>", lambda e: "break")
        self.code_editor.bind("<Control-v>", lambda e: "break")
        self.code_editor.bind("<Control-x>", lambda e: "break")
        self.code_editor.bind("<Button-3>", lambda e: "break")
        self.code_editor.bind("<KeyRelease>", self._on_code_change)

        # Horizontal scrollbar
        hscroll = ctk.CTkFrame(editor_frame, fg_color="transparent")
        hscroll.grid(row=2, column=0, sticky="ew", padx=10)
        hscrollbar = tk.Scrollbar(hscroll, orient="horizontal", command=self.code_editor._text_widget().xview)
        hscrollbar.pack(fill="x")
        self.code_editor._text_widget().configure(xscrollcommand=hscrollbar.set)

        # IA panel (col 2)
        ia_frame = ctk.CTkFrame(self.win, fg_color="#2a2a2e", corner_radius=0, border_width=2, border_color="#44444a")
        ia_frame.grid(row=1, column=2, sticky="nsew", padx=3, pady=3)
        ia_frame.grid_rowconfigure(1, weight=1)
        ia_frame.grid_rowconfigure(3, weight=1)
        ia_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(ia_frame, text="📋 Instructions IA", font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_MAIN).pack(pady=(10, 5))
        self.ia_instructions = ctk.CTkTextbox(ia_frame, font=ctk.CTkFont(size=11), fg_color="#161b22", border_color="#4b4c54", text_color=TEXT_MAIN)
        self.ia_instructions.pack(fill="both", expand=True, padx=8, pady=5)
        self.ia_instructions.configure(state="disabled")

        ctk.CTkLabel(ia_frame, text="💡 Conseils IA", font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_MAIN).pack(pady=(10, 5))
        self.ia_advice = ctk.CTkTextbox(ia_frame, font=ctk.CTkFont(size=11), fg_color="#161b22", border_color="#4b4c54", text_color=TEXT_MAIN)
        self.ia_advice.pack(fill="both", expand=True, padx=8, pady=5)
        self.ia_advice.configure(state="disabled")

        # Bottom buttons (full width)
        btn_frame = ctk.CTkFrame(self.win, fg_color="transparent")
        btn_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=15, pady=12)

        self.start_btn = ctk.CTkButton(btn_frame, text="▶ Commencer l'exercice", width=180, command=self._start_exercise, fg_color="#10a37f", hover_color="#0d8a6a", font=ctk.CTkFont(size=12, weight="bold"), state="disabled")
        self.start_btn.pack(side="left", padx=8)

        self.pause_btn = ctk.CTkButton(btn_frame, text="⏸ Pause", width=120, command=self._toggle_pause, fg_color="#b45309", hover_color="#d97706", font=ctk.CTkFont(size=12, weight="bold"), state="disabled")
        self.pause_btn.pack(side="left", padx=8)

        self.abandon_btn = ctk.CTkButton(btn_frame, text="❌ Abandonner", width=120, command=self._abandon, fg_color="#c24141", hover_color="#a33434", font=ctk.CTkFont(size=12, weight="bold"))
        self.abandon_btn.pack(side="left", padx=8)

        self.verify_btn = ctk.CTkButton(btn_frame, text="✅ Vérifier le site", width=160, command=self._verify, fg_color=ACCENT, hover_color=ACCENT_HOVER, font=ctk.CTkFont(size=12, weight="bold"), state="disabled")
        self.verify_btn.pack(side="right", padx=8)

        self.status_label = ctk.CTkLabel(self.win, text="", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED)
        self.status_label.grid(row=3, column=0, columnspan=3, sticky="w", padx=15, pady=(0, 8))

        self.files["index.html"] = "<!DOCTYPE html>\n<html>\n<head>\n    <title>Mon site</title>\n</head>\n<body>\n    <h1>Bonjour</h1>\n</body>\n</html>"
        self._open_file("index.html")
        self._set_level_instructions("junior")

    def _on_level_change(self, value):
        for k, v in LEARNING_LEVELS.items():
            if v["label"] == value:
                self.level.set(k)
                self.max_files = v["max_files"]
                self._set_level_instructions(k)
                self._refresh_files_ui()
                self.exercise_ready = False
                self.start_btn.configure(state="disabled", text="▶ Commencer l'exercice")
                self.verify_btn.configure(state="disabled")
                self.status_label.configure(text="Génération d'un nouvel exercice…", text_color=TEXT_MUTED)
                threading.Thread(target=self._generate_subject, daemon=True).start()
                break

    def _set_level_instructions(self, key):
        lv = LEARNING_LEVELS[key]
        instr = (
            "Niveau : {}\n\n".format(lv["label"]) +
            "But : créez un site web fonctionnel (HTML, CSS, JavaScript) sans aide extérieure.\n" +
            "Vous ne pouvez pas parler à l'IA, pas de copier-coller.\n" +
            "Seul le bouton 'Vérifier le site' permet à l'IA de valider ou refuser votre travail.\n" +
            "Tolérance : {}\n".format(lv["tolerance"]) +
            "Conseils : {}\n".format(lv["advice_freq"]) +
            "Nombre de fichiers max : {}".format(lv["max_files"])
        )
        self._set_text(self.ia_instructions, instr)
        self._update_advice(key)

    def _update_advice(self, key):
        if key == "junior":
            advice = "Conseil : commencez par la structure HTML de base (doctype, html, head, body). Ajoutez un titre et un paragraphe."
        elif key == "facile":
            advice = "Conseil : pensez à bien fermer toutes vos balises HTML et liez votre fichier CSS."
        elif key == "normale":
            advice = "Conseil : vérifiez que votre CSS cible les bons éléments et que votre JavaScript est sans erreur."
        elif key == "difficile":
            advice = "Conseil : aucun conseil supplémentaire. Vous êtes presque autonome."
        elif key == "legendaire":
            advice = "Conseil : aucun droit à l'erreur. Soyez parfait du premier coup."
        else:
            advice = "Conseil : niveau expert, vous êtes totalement autonome."
        self._set_text(self.ia_advice, advice)

    def _set_text(self, widget, text):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _generate_subject(self):
        level = self.level.get()
        lv = LEARNING_LEVELS[level]
        sujets_deja = self.app._learning_sujets if hasattr(self.app, "_learning_sujets") else []
        self.app._learning_sujets = sujets_deja
        historique = ""
        if sujets_deja:
            historique = "SUJETS DÉJÀ PROPOSÉS (NE PAS les reprendre) :\n- {}\n\n".format("\n- ".join(sujets_deja[-10:]))
        difficulty_desc = {
            "junior": "simple, une seule page, basique",
            "facile": "une page avec quelques éléments interactifs",
            "normale": "plusieurs sections, mise en page soignée, un peu de JavaScript",
            "difficile": "site multi-pages ou application web avec JavaScript significatif",
            "legendaire": "application web complète ou site e-commerce complexe",
            "senior": "projet professionnel complet avec architecture, design responsive et fonctionnalités avancées",
        }[level]
        prompt = (
            "Tu es un formateur en développement web. Génère UN sujet de projet précis et concret pour un apprenant au niveau {} ({}).\n"
            "IMPORTANT : varie le TYPE de site à chaque exercice. Ne propose PAS toujours un portfolio. Touche à tout : landing page, site de voyage, site e-commerce, blog, page de contact, CV en ligne, site restaurant, agence, page de formation, etc.\n"
            "Le sujet doit correspondre à la difficulté {}. Difficulté actuelle : {} ({}).\n"
            "Cela signifie : {}\n"
            "La difficulté ne doit PAS seulement signifier 'plus de pages' : elle doit signifier un type de site différent et/ou plus complexe.\n"
            "{history}Donne les consignes suivantes de manière claire et structurée :\n"
            "1. SUJET : le type exact de site à créer (sois varié, pas de portfolio à chaque fois)\n"
            "2. OBJECTIF : ce que le site doit permettre à l'utilisateur de faire\n"
            "3. PAGES OU SECTIONS : les éléments obligatoires à inclure\n"
            "4. EXIGENCES TECHNIQUES : ce qui est attendu en HTML/CSS/JS selon le niveau\n"
            "5. CRITÈRES DE RÉUSSITE : ce qui sera vérifié pour valider le projet\n"
            "Sois précis, direct et donne un seul sujet (pas de liste au choix). Écris en français.\n\nNiveau : {} ({}) - Tolérance : {}".format(
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
            first_line = [l for l in sujet.splitlines() if l.strip()][0] if sujet else "Sujet inconnu"
            self.app._learning_sujets.append(first_line[:80])
            self.app.after(0, lambda: self._display_subject(sujet))
        except Exception as e:
            self.app.after(0, lambda: self.status_label.configure(text="Erreur génération sujet : {}".format(e), text_color="#c24141"))

    def _display_subject(self, sujet):
        lv = LEARNING_LEVELS[self.level.get()]
        self.current_subject = sujet
        self.exercise_count += 1
        self.exercise_label.configure(text="Exercice {}".format(self.exercise_count))
        full = (
            "Niveau : {}\n\n".format(lv["label"]) +
            "SUJET DU PROJET (généré par l'IA) :\n{}\n\n".format(sujet) +
            "But : créez ce site web fonctionnel (HTML, CSS, JavaScript) sans aide extérieure.\n" +
            "Vous ne pouvez pas parler à l'IA, pas de copier-coller.\n" +
            "Seul le bouton 'Vérifier le site' permet à l'IA de valider ou refuser votre travail.\n" +
            "Tolérance : {}\n".format(lv["tolerance"]) +
            "Conseils : {}\n".format(lv["advice_freq"]) +
            "Nombre de fichiers max : {}".format(lv["max_files"])
        )
        self._set_text(self.ia_instructions, full)
        self.status_label.configure(text="Sujet généré. Cliquez sur 'Commencer l'exercice' pour démarrer le chronomètre.", text_color="#10a37f")
        self.exercise_ready = True
        self.start_btn.configure(state="normal", text="▶ Commencer l'exercice")
        self.verify_btn.configure(state="disabled")

    def _start_exercise(self):
        if not self.exercise_ready:
            return
        self.start_time = time.time()
        self.exercise_ready = False
        self.start_btn.configure(state="disabled")
        self.verify_btn.configure(state="normal")
        self.pause_btn.configure(state="normal")
        self.status_label.configure(text="Exercice en cours. Codez !", text_color="#10a37f")
        self._tick_timer()

    def _tick_timer(self):
        if self.start_time is None or self.paused:
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
            self.pause_btn.configure(text="▶ Reprendre", fg_color="#15803d", hover_color="#16a34a")
            self.verify_btn.configure(state="disabled")
            self.status_label.configure(text="⏸ En pause – éditeur bloqué", text_color="#b45309")
        else:
            self._tick_timer()
            self.code_editor.configure(state="normal")
            self.pause_btn.configure(text="⏸ Pause", fg_color="#b45309", hover_color="#d97706")
            self.verify_btn.configure(state="normal")
            self.status_label.configure(text="Exercice en cours. Codez !", text_color="#10a37f")

    def _refresh_files_ui(self):
        for btn in self.file_buttons.values():
            btn.destroy()
        self.file_buttons = {}
        for fname in self.files:
            b = ctk.CTkButton(self.files_list, text=fname, width=140, command=lambda f=fname: self._open_file(f), fg_color=BG_INPUT, hover_color="#4b4c54", font=ctk.CTkFont(size=10))
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

    def _on_code_change(self, event=None):
        if not self.paused and self.exercise_ready is False and self.start_time is not None:
            self.files[self.current_file] = self.code_editor.get("1.0", "end-1c")
        elif not self.paused and self.start_time is not None:
            self.files[self.current_file] = self.code_editor.get("1.0", "end-1c")

    def _verify(self):
        self._stop_timer()
        html_content = self.files.get("index.html", "")
        default_html = "<!DOCTYPE html>\n<html>\n<head>\n    <title>Mon site</title>\n</head>\n<body>\n    <h1>Bonjour</h1>\n</body>\n</html>"
        if not html_content.strip():
            self.status_label.configure(text="Refusé : aucun code saisi. Écrivez du HTML avant de vérifier.", text_color="#c24141")
            self._tick_timer()
            return
        if self._is_default_skeleton(html_content):
            self.status_label.configure(text="Refusé : le squelette par défaut n'est pas un site. Ajoutez du contenu réel.", text_color="#c24141")
            self._tick_timer()
            return
        all_code = ""
        for fname, content in self.files.items():
            all_code += "\n--- FICHIER : {} ---\n{}\n--- FIN ---".format(fname, content)
        level = self.level.get()
        lv = LEARNING_LEVELS[level]
        verify_prompt = (
            "Tu es un examinateur sévère. Voici le code d'un apprenant au niveau {} ({}).\n"
            "Tolérance aux erreurs : {}.\n"
            "Le but est de créer un site web propre et fonctionnel (HTML, CSS, JS).\n"
            "Si le code est uniquement le squelette par défaut, réponds REFUSE.\n"
            "CONSIGNES DU PROJET À RESPECTER À LA LETTRE :\n{}\n"
            "Analyse si le code de l'apprenant correspond RÉELLEMENT à ces consignes. Si oui, réponds VALIDÉ. Sinon, réponds REFUSE.\n"
            "Réponds UNIQUEMENT par 'VALIDÉ' ou 'REFUSE' suivi d'une courte explication en français.\n"
            "Ne donne pas de conseil pour corriger, dis seulement si c'est accepté ou non.\n\n{}".format(lv["label"], level, lv["tolerance"], self.current_subject, all_code)
        )
        self.status_label.configure(text="Vérification en cours…", text_color=TEXT_MAIN)
        self.verify_btn.configure(state="disabled")
        threading.Thread(target=self._verify_thread, args=(verify_prompt,), daemon=True).start()

    @staticmethod
    def _is_default_skeleton(html):
        default = "<!DOCTYPE html>\n<html>\n<head>\n    <title>Mon site</title>\n</head>\n<body>\n    <h1>Bonjour</h1>\n</body>\n</html>"
        normal = " ".join(html.split())
        norm_default = " ".join(default.split())
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
            self.status_label.configure(text="Exercice réussi ! Génération d'un nouvel exercice…", text_color=ACCENT)
            self.files = {"index.html": "<!DOCTYPE html>\n<html>\n<head>\n    <title>Mon site</title>\n</head>\n<body>\n    <h1>Bonjour</h1>\n</body>\n</html>"}
            self.current_file = "index.html"
            self._refresh_files_ui()
            self._open_file("index.html")
            self._set_level_instructions(self.level.get())
            self.start_btn.configure(state="normal", text="▶ Commencer l'exercice")
            self.verify_btn.configure(state="disabled")
            self.pause_btn.configure(state="disabled")
            threading.Thread(target=self._generate_subject, daemon=True).start()
        else:
            self._tick_timer()

    def _save_time(self, level, seconds):
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
