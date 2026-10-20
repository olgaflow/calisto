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
VERSION = "1.3.0"
GENERATED_DIR = "generated"
IA_CREATIONS_DIR = "ia_creations"
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

os.makedirs(GENERATED_DIR, exist_ok=True)
os.makedirs(IA_CREATIONS_DIR, exist_ok=True)


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


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Calisto - Assistant IA pour débutants")
        self.geometry("1200x800")
        self.minsize(900, 600)
        self.configure(fg_color=BG_APP)
        self.resizable(True, True)

        self.model_var = ctk.StringVar(value=MODEL)
        self.temp_var = ctk.DoubleVar(value=0.7)
        self.sys_text_var = ctk.StringVar(value="Tu es Calisoto, un professeur patient et encourageant pour débutants en développement web. Tu parles en français comme si tu discutais avec une personne qui apprend. Sois simple, direct et encourageant. N'utilise pas de ton robotique. Si tu ne comprends pas une question, dis-le et demande une précision. Ton rôle est d'aider les débutants à acquérir les bons réflexes de programmation. Réduis ton aide au minimum : ne donne pas de code complet, donne des indices et des explications. Encourage l'apprenant à chercher par lui-même. N'aide que si vraiment nécessaire.")
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

        self._build_ui()
        self._send_welcome_message()
        self._check_ollama()
        self.after(100, self._process_ui_queue)

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Tabs
        self.tabs = ctk.CTkTabview(self, fg_color=BG_APP)
        self.tabs.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.tabs.add("Discussion")
        self.tabs.add("Éditeur de code")
        self.tabs.add("Apprentissage")
        # Forcer l'etirement des onglets
        self.tabs._segmented_button.grid_columnconfigure(0, weight=1)
        self.tabs._segmented_button.grid_columnconfigure(1, weight=1)
        self.tabs._segmented_button.grid_columnconfigure(2, weight=1)

        self.chat_tab = self.tabs.tab("Discussion")
        self.code_tab = self.tabs.tab("Éditeur de code")
        self.learning_tab = self.tabs.tab("Apprentissage")

        self.chat_tab.grid_columnconfigure(0, weight=1)
        self.chat_tab.grid_rowconfigure(1, weight=1)
        self.code_tab.grid_columnconfigure(0, weight=1)
        self.code_tab.grid_rowconfigure(0, weight=1)
        self.learning_tab.grid_columnconfigure(0, weight=1)
        self.learning_tab.grid_rowconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(self.chat_tab, fg_color=BG_PANEL, corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 4))

        ctk.CTkLabel(header, text="💬 Discussion", font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT_MAIN).pack(side="left", padx=14, pady=8)

        right_btns = ctk.CTkFrame(header, fg_color="transparent")
        right_btns.pack(side="right", padx=10, pady=6)
        ctk.CTkButton(right_btns, text="⚙️ Réglages", width=95, command=self.open_settings, fg_color="#a855f7", hover_color="#9333ea", font=ctk.CTkFont(size=11)).pack(side="right", padx=3)
        ctk.CTkButton(right_btns, text="📎 Fichier", width=85, command=self.attach_file, fg_color=BG_INPUT, hover_color="#4b4c54", font=ctk.CTkFont(size=11)).pack(side="right", padx=3)

        # Chat area
        self.chat_container = ctk.CTkScrollableFrame(self.chat_tab, fg_color=BG_APP, corner_radius=12)
        self.chat_container.grid(row=1, column=0, sticky="nsew", padx=12, pady=(4, 8))
        self.chat_container.grid_columnconfigure(0, weight=1)

        # File chips
        self.file_chips_label = ctk.CTkLabel(self.chat_tab, text="", font=ctk.CTkFont(size=11), text_color="#a78bfa", anchor="w")
        self.file_chips_label.grid(row=2, column=0, sticky="w", padx=18, pady=(0, 4))

        # Input area - modern chat input bar
        bottom = ctk.CTkFrame(self.chat_tab, fg_color=BG_PANEL, corner_radius=16)
        bottom.grid(row=3, column=0, sticky="ew", padx=12, pady=(4, 8))
        bottom.grid_columnconfigure(0, weight=1)

        self.entry = ctk.CTkTextbox(bottom, height=100, font=ctk.CTkFont(size=13), fg_color=BG_INPUT, border_color="#4b4c54", text_color=TEXT_MAIN, corner_radius=12)
        self.entry.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        self.entry.bind("<Return>", self.on_enter)
        self.entry.bind("<Shift-Return>", self.on_shift_enter)

        right = ctk.CTkFrame(bottom, fg_color="transparent")
        right.grid(row=0, column=1, sticky="ns", padx=(0, 12), pady=12)
        self.send_btn = ctk.CTkButton(right, text="Envoyer ✈", width=100, height=38, command=self.send, fg_color=ACCENT, hover_color=ACCENT_HOVER, font=ctk.CTkFont(size=13, weight="bold"), corner_radius=10)
        self.send_btn.pack(pady=(0, 6))
        ctk.CTkButton(right, text="Effacer", width=100, height=28, command=self.clear_chat, fg_color=BG_INPUT, hover_color="#4b4c54", font=ctk.CTkFont(size=11), corner_radius=8).pack()

        self.status_var = ctk.StringVar(value="Prêt")
        ctk.CTkLabel(self.chat_tab, textvariable=self.status_var, font=ctk.CTkFont(size=11), text_color=TEXT_MUTED).grid(row=4, column=0, sticky="e", padx=18, pady=(0, 6))

        # Editor tab
        self.code_tab.grid_columnconfigure(0, weight=1)
        self.code_tab.grid_rowconfigure(0, weight=1)
        if DevWindow is not None:
            self.dev_window = DevWindow(self, master=self.code_tab)
            self.dev_window.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        else:
            ctk.CTkLabel(self.code_tab, text="L'éditeur de code n'a pas pu être chargé.", text_color=TEXT_MUTED).pack(pady=40)

        # Learning tab
        self.learning_tab.grid_columnconfigure(0, weight=1)
        self.learning_tab.grid_rowconfigure(0, weight=1)
        learn_frame = ctk.CTkFrame(self.learning_tab, fg_color=BG_PANEL, corner_radius=12)
        learn_frame.grid(row=0, column=0, sticky="nsew", padx=40, pady=40)
        ctk.CTkLabel(learn_frame, text="🎮 Mode Apprentissage", font=ctk.CTkFont(size=20, weight="bold"), text_color=TEXT_MAIN).pack(pady=25)
        ctk.CTkLabel(learn_frame, text="Apprenez à coder HTML/CSS/JS sans aide de l'IA.\nVous recevez un sujet, vous codez, l'IA vérifie.", font=ctk.CTkFont(size=13), text_color=TEXT_MUTED, justify="center").pack(pady=10)
        ctk.CTkButton(learn_frame, text="Ouvrir le mode Apprentissage", width=220, height=40, command=self.open_learning_mode, fg_color=ACCENT, hover_color=ACCENT_HOVER, font=ctk.CTkFont(size=13, weight="bold")).pack(pady=20)

    def _send_welcome_message(self):
        welcome = """Bienvenue dans Calisto ! 👋

Je suis Calisoto, votre professeur de développement web pour débutants. Mon rôle est de vous aider à acquérir les bons réflexes de programmation.

Voici ce que vous pouvez faire :

💬 **Discuter** – Posez-moi des questions, je vous guide et vous donne des indices plutôt que des solutions complètes.

📎 **Analyser des fichiers** – Joignez des fichiers texte, code ou PDF pour que je les lise et vous aide à les comprendre.

💻 **Éditeur de code** – Utilisez l'onglet "Éditeur de code" pour écrire du HTML, CSS, JavaScript, Python, etc. avec coloration syntaxique et prévisualisation.

🎮 **Mode Apprentissage** – Apprenez à coder en résolvant des exercices progressifs, sans aide de l'IA (sauf la vérification finale).

🌐 **Recherche web** – Activez-la dans les réglages pour chercher des informations en ligne.

⚠️ **Important** : Je suis un professeur, pas une solution. Je vous donne des indices et des explications, mais c'est à vous d'écrire le code. L'aide est réduite au minimum pour vous aider à progresser par vous-même.

Comment puis-je vous aider aujourd'hui ?"""
        self.messages.append({"role": "assistant", "content": welcome})
        self._add_bubble("Calisoto", welcome, "assistant", animate=False)

    # ---------- Chat ----------
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
        self.streaming = True
        self.send_btn.configure(state="disabled", fg_color="#4b4c54")
        self.status_var.set("L'IA répond…")
        threading.Thread(target=self._stream, daemon=True).start()

    def clear_chat(self):
        if self.streaming:
            return
        self.messages = []
        for w in self.chat_container.winfo_children():
            w.destroy()
        self._send_welcome_message()
        self.status_var.set("Conversation effacée")

    def _add_bubble(self, sender, text, role, animate=True):
        row = ctk.CTkFrame(self.chat_container, fg_color="transparent")
        row.pack(fill="x", pady=6, padx=12)
        if role == "user":
            row.pack_configure(anchor="e")
            bubble_color = BUBBLE_USER
            header_color = "#ffffff"
            side = "right"
            padx = (120, 8)
            avatar = "👤"
            avatar_bg = "#2563eb"
        else:
            row.pack_configure(anchor="w")
            bubble_color = BUBBLE_AI
            header_color = "#a78bfa"
            side = "left"
            padx = (8, 120)
            avatar = "🤖"
            avatar_bg = "#7c3aed"

        avatar_lbl = ctk.CTkLabel(row, text=avatar, font=ctk.CTkFont(size=18), width=40, height=40, fg_color=avatar_bg, corner_radius=20)
        avatar_lbl.pack(side=side, padx=(8, 6))

        bubble = ctk.CTkFrame(row, fg_color=bubble_color, corner_radius=16)
        bubble.pack(side=side, padx=padx)
        ctk.CTkLabel(bubble, text=sender, font=ctk.CTkFont(size=11, weight="bold"), text_color=header_color, anchor="w").pack(fill="x", padx=16, pady=(10, 2))
        lbl = ctk.CTkLabel(bubble, text=text, font=ctk.CTkFont(size=14), text_color=TEXT_MAIN, justify="left", wraplength=750, anchor="w")
        lbl.pack(fill="x", padx=16, pady=(0, 12))
        if role in ("user", "assistant"):
            ctk.CTkButton(bubble, text="📋", width=26, height=26, fg_color="transparent", hover_color=bubble_color, text_color=header_color, font=ctk.CTkFont(size=13), corner_radius=13, command=lambda t=text: self.copy_to_clipboard(t)).pack(side="right", padx=8, pady=8)
        self.after(30, self._scroll_bottom)
        return bubble, lbl

    def _scroll_bottom(self):
        try:
            self.update_idletasks()
            self.chat_container._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass

    def _stream(self):
        model = self.model_var.get() or MODEL
        temperature = self.temp_var.get()
        system = self.sys_text_var.get()
        now = time.strftime("%A %d %B %Y à %H:%M", time.localtime())
        system_with_context = "{}\n\nDate et heure actuelles : {}.\n".format(system, now)

        # Conversation naturelle
        system_with_context += (
            "\nRègles de conversation :"
            "\n- Tu es un professeur pour débutants. Réduis ton aide au minimum."
            "\n- Ne donne JAMAIS de code complet. Donne des indices, des explications et des pistes."
            "\n- Encourage l'apprenant à chercher par lui-même et à expérimenter."
            "\n- Si tu ne comprends pas la question, dis-le clairement et demande une précision."
            "\n- Évite le ton robotique et les listes à puces interminables."
        )
        
        # Code rules
        system_with_context += (
            "\n\nPour toute demande de code :"
            "\n- Ne fournis JAMAIS de code prêt à l'emploi. Donne des explications et des indices."
            "\n- Si l'utilisateur demande du code, explique la logique plutôt que de donner la solution."
            "\n- Encourage l'apprenant à écrire le code lui-même."
        )

        # Web search
        if self.web_search_var.get():
            system_with_context += (
                "\n\nLa recherche web est disponible mais ne l'utilisez JAMAIS pour répondre à une question sur du code local ou de la programmation hors ligne."
                "\nN'appelez rechercher_sur_internet QUE si l'utilisateur demande explicitement des informations en ligne."
            )

        # File creation
        if self.ai_can_create_files.get():
            system_with_context += "\n\nVous pouvez créer des fichiers. Utilisez le format [CREER_FICHIER: nom.ext] contenu [/CREER_FICHIER]."

        if self.ai_can_modify_app.get():
            system_with_context += "\n\nVous pouvez modifier l'application Calisto. Utilisez le format [MODIFIER_APP: chemin.py] contenu [/MODIFIER_APP]."

        if self._is_repeat_query:
            system_with_context += "\n\nNOTE : l'utilisateur repose exactement la même question. Ne répétez pas la même réponse. Approfondissez, changez d'angle ou demandez ce qui n'a pas été compris."
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
                full = chat_with_web_search(model, msgs, temperature, enabled=True, on_search=lambda q: self.after(0, lambda: self.status_var.set("Recherche web : {}".format(q))))
                bubble, lbl = self._add_bubble("IA", "", "assistant")
                self.ui_queue.put(("done", lbl, full, bubble))
                return
            last_err = None
            for attempt in range(2):
                try:
                    stream = ollama.chat(model=model, messages=msgs, stream=True, options={"temperature": temperature, "num_ctx": 8192, "num_predict": 2048})
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
        self.status_var.set("Prêt")

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
                self.status_var.set("Modification refusée")
                return
        elif command_type == "fichier" and not self.ai_can_create_files.get():
            resp = messagebox.askyesno("Autorisation IA", "L'IA propose de créer un fichier :\n{}\n\nAutoriser ?".format(filepath))
            if not resp:
                self.status_var.set("Création refusée")
                return
        else:
            resp = messagebox.askyesno("Confirmer", "L'IA propose de {} le fichier :\n{}\n\nConfirmer ?".format("modifier l'application" if command_type == "app" else "créer", filepath))
            if not resp:
                self.status_var.set("Action annulée")
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
            self.status_var.set("Fichier {} : {}".format("modifié" if command_type == "app" else "créé", filepath))
        except Exception as e:
            messagebox.showerror("Erreur", "Impossible d'écrire le fichier : {}".format(str(e)))

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
        if not self.attached_files:
            self.file_chips_label.configure(text="")
            return
        noms = " | ".join("📎 {}".format(p.name) for p in self.attached_files)
        self.file_chips_label.configure(text=noms)

    def copy_to_clipboard(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)

    def _check_ollama(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            result = s.connect_ex(("127.0.0.1", 11434))
            s.close()
            if result == 0:
                self.status_var.set("Ollama en ligne")
            else:
                self.status_var.set("Ollama hors ligne")
        except Exception:
            pass
        self.after(30000, self._check_ollama)

    # ---------- Settings ----------
    def open_settings(self):
        win = ctk.CTkToplevel(self)
        win.title("Réglages")
        win.geometry("700x850")
        win.configure(fg_color=BG_APP)
        win.transient(self)
        win.grab_set()
        win.resizable(True, True)

        ctk.CTkLabel(win, text="⚙️ Réglages", font=ctk.CTkFont(size=22, weight="bold"), text_color=TEXT_MAIN).pack(pady=(20, 15))

        # Scrollable body
        body = ctk.CTkScrollableFrame(win, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=30, pady=10)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=0)

        row_idx = [0]

        def section(title):
            ctk.CTkLabel(body, text=title, font=ctk.CTkFont(size=15, weight="bold"), text_color=ACCENT).grid(row=row_idx[0], column=0, columnspan=2, sticky="w", pady=(18, 8))
            row_idx[0] += 1

        def row(label, widget, pady=8):
            ctk.CTkLabel(body, text=label, font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_MAIN).grid(row=row_idx[0], column=0, sticky="w", pady=pady, padx=(0, 10))
            widget.grid(row=row_idx[0], column=1, sticky="e", pady=pady)
            row_idx[0] += 1

        section("Modèle IA")
        row("Modèle Ollama :", ctk.CTkEntry(body, textvariable=self.model_var, width=180, height=32, fg_color=BG_INPUT, border_color="#4b4c54", text_color=TEXT_MAIN))
        row("Température :", ctk.CTkSlider(body, from_=0.0, to=1.5, variable=self.temp_var, width=200))
        ctk.CTkLabel(body, textvariable=self.temp_var, font=ctk.CTkFont(size=12), text_color=TEXT_MUTED).grid(row=row_idx[0], column=1, sticky="e", pady=(0, 8))
        row_idx[0] += 1

        section("Personnalité de l'IA")
        ctk.CTkLabel(body, text="Instruction système (comment l'IA se comporte) :", font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_MAIN).grid(row=row_idx[0], column=0, columnspan=2, sticky="w", pady=(0, 5))
        row_idx[0] += 1
        sys_txt = ctk.CTkTextbox(body, height=120, font=ctk.CTkFont(size=12), fg_color=BG_INPUT, border_color="#4b4c54", text_color=TEXT_MAIN, corner_radius=8)
        sys_txt.grid(row=row_idx[0], column=0, columnspan=2, sticky="ew", pady=(0, 15))
        row_idx[0] += 1
        sys_txt.insert("1.0", self.sys_text_var.get())

        section("Options")
        for sw in [
            ctk.CTkSwitch(body, text="Autoriser la recherche web", variable=self.web_search_var, font=ctk.CTkFont(size=13), text_color=TEXT_MAIN),
            ctk.CTkSwitch(body, text="Suggestions de code IA en direct (éditeur)", variable=self.inline_completion_var, font=ctk.CTkFont(size=13), text_color=TEXT_MAIN),
            ctk.CTkSwitch(body, text="Autoriser l'IA à créer des fichiers", variable=self.ai_can_create_files, font=ctk.CTkFont(size=13), text_color=TEXT_MAIN),
            ctk.CTkSwitch(body, text="Autoriser l'IA à modifier l'application", variable=self.ai_can_modify_app, font=ctk.CTkFont(size=13), text_color=TEXT_MAIN),
        ]:
            sw.grid(row=row_idx[0], column=0, columnspan=2, sticky="w", pady=5)
            row_idx[0] += 1

        section("Aide / Raccourcis")
        help_txt = (
            "Raccourcis éditeur :\n"
            "  Ctrl+S : Sauvegarder   Ctrl+F : Rechercher   Ctrl+H : Remplacer\n"
            "  Ctrl+G : Aller à la ligne   Ctrl+/ : Commenter/Décommenter\n"
            "  Ctrl+D : Sélectionner occurrence suivante   Ctrl+L : Sélectionner ligne\n"
            "  Ctrl+Shift+K : Supprimer ligne   Ctrl+Entrée : Ligne en dessous\n"
            "  Ctrl+Shift+Entrée : Ligne au-dessus   Alt+↑/↓ : Déplacer ligne\n"
            "  Ctrl+] / Ctrl+[ : Indenter / Désindenter   Ctrl+Z/Y : Annuler/Refaire\n"
            "  Ctrl+Molette : Zoom   Ctrl+A : Tout sélectionner\n"
            "  Auto-fermeture : ( ) [ ] { } \" \" ' '\n\n"
            "Chat IA :\n"
            "  Réponse directe, sans recherche web inutile.\n"
            "  La recherche web ne se déclenche que si vous la demandez.\n"
            "  Personnalisez la personnalité dans l'instruction système."
        )
        ctk.CTkLabel(body, text=help_txt, font=ctk.CTkFont(size=11), text_color=TEXT_MUTED, justify="left").grid(row=row_idx[0], column=0, columnspan=2, sticky="w", pady=(0, 15))
        row_idx[0] += 1

        def save_close():
            self.sys_text_var.set(sys_txt.get("1.0", "end").strip())
            self.status_var.set("Réglages enregistrés")
            win.destroy()

        btns = ctk.CTkFrame(win, fg_color="transparent")
        btns.pack(fill="x", padx=30, pady=20)
        ctk.CTkButton(btns, text="Annuler", width=100, command=win.destroy, fg_color=BG_INPUT, hover_color="#4b4c54", font=ctk.CTkFont(size=12)).pack(side="right", padx=10)
        ctk.CTkButton(btns, text="Enregistrer", width=100, command=save_close, fg_color=ACCENT, hover_color=ACCENT_HOVER, font=ctk.CTkFont(size=13, weight="bold")).pack(side="right")

    # ---------- Learning mode ----------
    def open_learning_mode(self):
        if self.streaming:
            self.status_var.set("Attendez la fin de la réponse avant d'ouvrir le mode Apprentissage.")
            return
        # Clear the learning tab and build the learning UI inside it
        for w in self.learning_tab.winfo_children():
            w.destroy()
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
        self.win = parent_app.learning_tab
        for w in self.win.winfo_children():
            w.destroy()

        self.level = ctk.StringVar(value="junior")
        self.start_time = None
        self.timer_job = None
        self.files = {}
        self.max_files = 5
        self.current_file = "index.html"
        self.paused = False
        self.current_subject = ""
        self.exercise_count = 0
        self.started = False
        self.subject_ready = False

        self._build_ui()
        threading.Thread(target=self._generate_subject, daemon=True).start()

    def _build_ui(self):
        header = ctk.CTkFrame(self.win, fg_color=BG_PANEL, height=50)
        header.pack(fill="x", padx=10, pady=10)
        header.pack_propagate(False)

        ctk.CTkLabel(header, text="🎮 Mode Apprentissage", font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT_MAIN).pack(side="left", padx=15, pady=10)
        self.exercise_label = ctk.CTkLabel(header, text="Exercice 0", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_MUTED)
        self.exercise_label.pack(side="left", padx=15, pady=10)
        self.level_btn = ctk.CTkOptionMenu(header, values=[LEARNING_LEVELS[k]["label"] for k in LEARNING_LEVELS], command=self._on_level_change, width=140)
        self.level_btn.set("Junior")
        self.level_btn.pack(side="right", padx=15, pady=10)

        self.timer_label = ctk.CTkLabel(self.win, text="00:00:00", font=ctk.CTkFont(size=22, weight="bold"), text_color=ACCENT)
        self.timer_label.pack(pady=(0, 10))

        # Barre de progression stylisée pour la génération du sujet
        self.progress_frame = ctk.CTkFrame(self.win, fg_color=BG_PANEL, corner_radius=8)
        self.progress_frame.pack(fill="x", padx=20, pady=(0, 8))
        ctk.CTkLabel(self.progress_frame, text="⏳ Génération du sujet :", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_MAIN).pack(side="left", padx=(12, 8), pady=8)
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, width=300, height=20, corner_radius=10, fg_color=BG_INPUT, progress_color="#22c55e")
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=8)
        self.progress_bar.set(0)
        self.progress_label = ctk.CTkLabel(self.progress_frame, text="0%", font=ctk.CTkFont(size=12, weight="bold"), text_color="#22c55e", width=50)
        self.progress_label.pack(side="right", padx=(0, 12), pady=8)

        body = ctk.CTkFrame(self.win, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=10, pady=5)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=2)
        body.grid_columnconfigure(2, weight=1)
        body.grid_rowconfigure(0, weight=1)

        # Files
        files_frame = ctk.CTkFrame(body, fg_color=BG_PANEL)
        files_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        ctk.CTkLabel(files_frame, text="Fichiers", font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_MAIN).pack(pady=8)
        self.files_list = ctk.CTkScrollableFrame(files_frame, fg_color="transparent")
        self.files_list.pack(fill="both", expand=True, padx=5, pady=5)
        self.file_buttons = {}
        self._refresh_files_ui()
        ctk.CTkButton(files_frame, text="+ Nouveau fichier", width=120, command=self._add_file, fg_color="#6366f1", hover_color="#4f46e5", font=ctk.CTkFont(size=11)).pack(pady=5)

        # Editor
        editor_frame = ctk.CTkFrame(body, fg_color="#1e1e1e")
        editor_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        editor_frame.grid_rowconfigure(1, weight=1)
        editor_frame.grid_columnconfigure(0, weight=1)

        self.editor_label = ctk.CTkLabel(editor_frame, text="index.html", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_MUTED)
        self.editor_label.grid(row=0, column=0, sticky="w", padx=10, pady=5)

        self.code_editor = ctk.CTkTextbox(editor_frame, font=ctk.CTkFont(family="Consolas", size=13), fg_color="#1e1e1e", text_color="#d4d4d4", border_width=0)
        self.code_editor.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.code_editor.bind("<Control-c>", lambda e: "break")
        self.code_editor.bind("<Control-v>", lambda e: "break")
        self.code_editor.bind("<Control-x>", lambda e: "break")
        self.code_editor.bind("<Button-3>", lambda e: "break")
        self.code_editor.bind("<KeyRelease>", self._on_code_change)
        self.code_editor.configure(state="disabled")

        # IA panel
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
        self.verify_btn = ctk.CTkButton(btn_frame, text="Vérifier le site", command=self._verify, fg_color=ACCENT, hover_color=ACCENT_HOVER, font=ctk.CTkFont(size=12, weight="bold"))
        self.verify_btn.pack(side="right", padx=10)

        self.start_btn = ctk.CTkButton(btn_frame, text="Démarrer l'exercice", command=self._start_exercise, fg_color=ACCENT, hover_color=ACCENT_HOVER, font=ctk.CTkFont(size=12, weight="bold"))
        self.start_btn.pack(side="right", padx=10)
        self.start_btn.configure(state="disabled")

        self.status_label = ctk.CTkLabel(self.win, text="", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED)
        self.status_label.pack(pady=(0, 5))

        self.files["index.html"] = "<!DOCTYPE html>\n<html>\n<head>\n    <title>Mon site</title>\n</head>\n<body>\n    <h1>Bonjour</h1>\n</body>\n</html>"
        self._open_file("index.html")
        self.status_label.configure(text="Génération du sujet en cours…", text_color=TEXT_MAIN)
        self._set_level_instructions("junior")

    def _on_level_change(self, value):
        for k, v in LEARNING_LEVELS.items():
            if v["label"] == value:
                self.level.set(k)
                self.max_files = v["max_files"]
                self._set_level_instructions(k)
                self._refresh_files_ui()
                self.status_label.configure(text="Génération du sujet en cours…", text_color=TEXT_MAIN)
                self.subject_ready = False
                if hasattr(self, "start_btn"):
                    self.start_btn.configure(state="disabled")
                if hasattr(self, "progress_bar"):
                    self.progress_bar.set(0)
                    self.progress_label.configure(text="0%")
                threading.Thread(target=self._generate_subject, daemon=True).start()
                break

    def _set_text(self, widget, text):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

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

    def _schedule_advice(self):
        if hasattr(self, "_advice_job") and self._advice_job:
            try:
                self.app.after_cancel(self._advice_job)
            except Exception:
                pass
        self._advice_job = self.app.after(5000, self._give_advice)

    def _give_advice(self):
        self._advice_job = None
        if not self.started or self.paused:
            return
        level = self.level.get()
        if level not in ("junior", "facile"):
            return
        code = self.code_editor.get("1.0", "end-1c")
        if not code.strip():
            return
        threading.Thread(target=self._advice_thread, args=(code, level), daemon=True).start()

    def _advice_thread(self, code, level):
        try:
            model = self.app.model_var.get() or MODEL
            prompt = (
                "Tu es un formateur bienveillant en développement web. Un apprenant au niveau {} est en train de coder. "
                "Voici son code actuel :\n```\n{}\n```\n"
                "Donne UN seul conseil court et encourageant (1-2 phrases max) pour l'aider à progresser. "
                "Ne donne pas la solution complète. Sois pédagogique et positif. Réponds en français."
            ).format(level, code[:2000])
            response = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}], options={"temperature": 0.6, "num_predict": 120})
            advice = response["message"]["content"]
            self.app.after(0, lambda: self._set_text(self.ia_advice, advice))
        except Exception as e:
            pass

    def _start_exercise(self):
        if not self.subject_ready:
            self.status_label.configure(text="Attendez que le sujet soit généré.", text_color="#c24141")
            return
        self.started = True
        self.code_editor.configure(state="normal")
        self.start_btn.configure(state="disabled")
        self._start_timer()
        self.status_label.configure(text="Exercice démarré. Codez !", text_color="#0d8a6a")

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
        self.timer_job = self.app.after(1000, self._tick_timer)

    def _stop_timer(self):
        if self.timer_job:
            self.app.after_cancel(self.timer_job)
            self.timer_job = None

    def _on_code_change(self, event=None):
        if not self.paused:
            self.files[self.current_file] = self.code_editor.get("1.0", "end-1c")
        # Conseils IA automatiques pour les 2 niveaux les plus bas (junior, facile)
        level = self.level.get()
        if level in ("junior", "facile") and self.started and not self.paused:
            self._schedule_advice()

    def _toggle_pause(self):
        self.paused = not self.paused
        if self.paused:
            self._paused_elapsed = int(time.time() - self.start_time) if self.start_time else 0
            self._stop_timer()
            self.code_editor.configure(state="disabled")
            self.pause_btn.configure(text="Reprendre", fg_color="#15803d", hover_color="#16a34a")
            self.verify_btn.configure(state="disabled")
            self.status_label.configure(text="En pause – éditeur bloqué", text_color="#b45309")
        else:
            # Reprendre depuis le temps écoulé avant la pause
            elapsed_before = getattr(self, "_paused_elapsed", 0)
            self.start_time = time.time() - elapsed_before
            self._tick_timer()
            self.code_editor.configure(state="normal")
            self.pause_btn.configure(text="Pause", fg_color="#b45309", hover_color="#d97706")
            self.verify_btn.configure(state="normal")
            self.status_label.configure(text="Repris – codez !", text_color="#0d8a6a")

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
        # Reset to welcome screen
        for w in self.app.learning_tab.winfo_children():
            w.destroy()
        learn_frame = ctk.CTkFrame(self.app.learning_tab, fg_color=BG_PANEL, corner_radius=12)
        learn_frame.grid(row=0, column=0, sticky="nsew", padx=40, pady=40)
        ctk.CTkLabel(learn_frame, text="🎮 Mode Apprentissage", font=ctk.CTkFont(size=20, weight="bold"), text_color=TEXT_MAIN).pack(pady=25)
        ctk.CTkLabel(learn_frame, text="Apprenez à coder HTML/CSS/JS sans aide de l'IA.\nVous recevez un sujet, vous codez, l'IA vérifie.", font=ctk.CTkFont(size=13), text_color=TEXT_MUTED, justify="center").pack(pady=10)
        ctk.CTkButton(learn_frame, text="Ouvrir le mode Apprentissage", width=220, height=40, command=self.app.open_learning_mode, fg_color=ACCENT, hover_color=ACCENT_HOVER, font=ctk.CTkFont(size=13, weight="bold")).pack(pady=20)

    def _verify(self):
        self._stop_timer()
        html_content = self.files.get("index.html", "")
        default_html = "<!DOCTYPE html>\n<html>\n<head>\n    <title>Mon site</title>\n</head>\n<body>\n    <h1>Bonjour</h1>\n</body>\n</html>"
        if not html_content.strip():
            self.status_label.configure(text="Refusé : aucun code saisi. Écrivez du HTML avant de vérifier.", text_color="#c24141")
            return
        if self._is_default_skeleton(html_content):
            self.status_label.configure(text="Refusé : le squelette par défaut n'est pas un site. Ajoutez du contenu réel.", text_color="#c24141")
            return
        all_code = ""
        for fname, content in self.files.items():
            all_code += "\n--- FICHIER : {} ---\n{}\n--- FIN ---".format(fname, content)
        level = self.level.get()
        lv = LEARNING_LEVELS[level]
        verify_prompt = (
            "Tu es un examinateur sévère mais pédagogue. Voici le code d'un apprenant au niveau {} ({}).\n"
            "Tolérance aux erreurs : {}.\n"
            "Le but est de créer un site web propre et fonctionnel (HTML, CSS, JS).\n"
            "Si le code est uniquement le squelette par défaut, réponds REFUSE.\n"
            "CONSIGNES DU PROJET À RESPECTER À LA LETTRE :\n{}\n"
            "Analyse si le code de l'apprenant correspond RÉELLEMENT à ces consignes. Si oui, réponds VALIDÉ. Sinon, réponds REFUSE.\n"
            "Dans ta réponse, explique :\n"
            "1. Ce qui est BIEN dans le code (points positifs)\n"
            "2. Ce qui est INCORRECT ou MANQUANT (erreurs)\n"
            "3. Des CONSEILS pour améliorer (sans donner le code complet)\n"
            "Réponds UNIQUEMENT par 'VALIDÉ' ou 'REFUSE' suivi de l'explication en français.\n"
            "Ne donne pas de code prêt à l'emploi, seulement des conseils.\n\n{}".format(lv["label"], level, lv["tolerance"], self.current_subject, all_code)
        )
        self.status_label.configure(text="Vérification en cours…", text_color=TEXT_MAIN)
        threading.Thread(target=self._verify_thread, args=(verify_prompt,), daemon=True).start()

    @staticmethod
    def _is_default_skeleton(html):
        default = "<!DOCTYPE html>\n<html>\n<head>\n    <title>Mon site</title>\n</head>\n<body>\n    <h1>Bonjour</h1>\n</body>\n</html>"
        normal = " ".join(html.split())
        norm_default = " ".join(default.split())
        return normal == norm_default or len(normal) < len(norm_default) + 50

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
            "Donne les consignes suivantes de manière claire et structurée :\n"
            "1. SUJET : le type exact de site à créer (sois varié, pas de portfolio à chaque fois)\n"
            "2. OBJECTIF : ce que le site doit permettre à l'utilisateur de faire\n"
            "3. PAGES OU SECTIONS : les éléments obligatoires à inclure\n"
            "4. EXIGENCES TECHNIQUES : ce qui est attendu en HTML/CSS/JS selon le niveau\n"
            "5. CRITÈRES DE RÉUSSITE : ce qui sera vérifié pour valider le projet\n"
            "Sois précis, direct et donne un seul sujet (pas de liste au choix). Écris en français.\n\nNiveau : {} ({}) - Tolérance : {}".format(
                lv["label"], level, level, lv["label"], difficulty_desc, historique, lv["label"], level, lv["tolerance"]
            )
        )
        # Afficher un indicateur de chargement
        self.app.after(0, lambda: self.status_label.configure(text="⏳ Génération du sujet en cours…", text_color=TEXT_MAIN))
        self._loading_dots = 0
        self._loading_progress = 0
        self.app.after(0, lambda: self.progress_bar.set(0))
        self.app.after(0, lambda: self.progress_label.configure(text="0%"))
        self.app.after(0, lambda: self._start_loading_animation())
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
            self.app.after(0, lambda: self._finish_loading(sujet))
        except Exception as e:
            self._stop_loading()
            self.app.after(0, lambda: self.status_label.configure(text="Erreur génération sujet : {}".format(e), text_color="#c24141"))

    def _start_loading_animation(self):
        self._loading_job = self.app.after(500, self._animate_loading)

    def _animate_loading(self):
        if not hasattr(self, "_loading_job") or self._loading_job is None:
            print("DEBUG: _animate_loading called but _loading_job is None")
            return
        self._loading_dots = (self._loading_dots + 1) % 4
        dots = "." * (self._loading_dots + 1)
        # Augmenter la progression de manière progressive (jusqu'à ~90%)
        if self._loading_progress < 0.9:
            self._loading_progress = min(0.9, self._loading_progress + 0.05)
        try:
            self.status_label.configure(text="⏳ Génération du sujet en cours{}".format(dots), text_color=TEXT_MAIN)
            self.progress_bar.set(self._loading_progress)
            self.progress_label.configure(text="{}%".format(int(self._loading_progress * 100)))
        except Exception as e:
            print("ANIMATE ERROR:", e)
        self._loading_job = self.app.after(500, self._animate_loading)

    def _finish_loading(self, sujet):
        self._stop_loading()
        self.progress_bar.set(1.0)
        self.progress_label.configure(text="100%")
        self._display_subject(sujet)

    def _stop_loading(self):
        if hasattr(self, "_loading_job") and self._loading_job:
            try:
                self.app.after_cancel(self._loading_job)
            except Exception:
                pass
            self._loading_job = None

    def _display_subject(self, sujet):
        self._stop_loading()
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
        self.subject_ready = True
        if hasattr(self, "start_btn"):
            self.start_btn.configure(state="normal")
        self.status_label.configure(text="Sujet prêt. Cliquez sur 'Démarrer l'exercice' pour commencer.", text_color="#0d8a6a")

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
        # Verrouiller l'éditeur après vérification
        self.code_editor.configure(state="disabled")
        self.verify_btn.configure(state="disabled")
        self.pause_btn.configure(state="disabled")
        self._stop_timer()
        # Afficher le résultat détaillé dans la zone de conseil
        self._set_text(self.ia_advice, text)
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
            # Réactiver l'éditeur pour le nouvel exercice
            self.code_editor.configure(state="normal")
            self.verify_btn.configure(state="normal")
            self.pause_btn.configure(state="normal")
            self.started = False
            self.subject_ready = False
            if hasattr(self, "start_btn"):
                self.start_btn.configure(state="disabled")
            threading.Thread(target=self._generate_subject, daemon=True).start()

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
