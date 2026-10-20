import customtkinter as ctk
from tkinter import filedialog, messagebox, colorchooser
import tkinter as tk
import os
import json
import re
import html
import time
import threading
from pathlib import Path
import webbrowser
import subprocess
import ollama
import base64
from urllib.parse import unquote, urlparse

try:
    from tkinterweb import HtmlFrame
except ImportError:
    HtmlFrame = None

BG_APP = "#0a0a0b"
BG_PANEL = "#1a1a1b"
BG_EDITOR = "#1e1e1e"
TEXT_MAIN = "#d1d5db"
TEXT_MUTED = "#9ca3af"
ACCENT = "#10a37f"
ACCENT_HOVER = "#0d8a6a"
IA_COLOR = "#a855f7"
IA_HOVER = "#9333ea"

LANG_EXTENSIONS = {
    ".py": "python",
    ".html": "html",
    ".css": "css",
    ".js": "javascript",
    ".ts": "typescript",
    ".json": "json",
    ".md": "markdown",
    ".txt": "text",
    ".cpp": "cpp",
    ".c": "c",
    ".java": "java",
    ".php": "php",
    ".rb": "ruby",
    ".go": "go",
    ".rs": "rust",
    ".sh": "shell",
    ".xml": "xml",
    ".yml": "yaml",
    ".yaml": "yaml",
}

FILE_ICONS = {
    ".html": "🌐",
    ".css": "🎨",
    ".js": "📜",
    ".ts": "📘",
    ".py": "🐍",
    ".json": "📋",
    ".md": "📝",
    ".txt": "📄",
    ".cpp": "⚙️",
    ".c": "⚙️",
    ".java": "☕",
    ".php": "🐘",
    ".rb": "💎",
    ".go": "🐹",
    ".rs": "🦀",
    ".sh": "🐚",
    ".xml": "📎",
    ".yml": "📦",
    ".yaml": "📦",
}

HTML_BOILERPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nouvelle page</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <h1>Bonjour le monde</h1>
    <p>Ceci est une page HTML créée par Calisto.</p>
</body>
</html>"""

CSS_BOILERPLATE = "/* style.css */\nbody {\n    font-family: Arial, sans-serif;\n    margin: 0;\n    padding: 20px;\n    background: #f5f5f5;\n    color: #333;\n}\n\nh1 {\n    color: #333;\n}\n"

JS_BOILERPLATE = "// script.js\nconsole.log('Bonjour depuis Calisto');\n"

DEFAULT_TAG_COLORS = {
    "kw": "#569cd6",
    "str": "#ce9178",
    "comment": "#6a9955",
    "func": "#dcdcaa",
    "number": "#b5cea8",
    "tag": "#569cd6",
    "attr": "#9cdcfe",
    "bool": "#569cd6",
}

KEYWORDS = {
    "python": ["def", "class", "if", "else", "elif", "for", "while", "try", "except", "finally",
               "import", "from", "as", "return", "True", "False", "None", "with", "lambda",
               "yield", "async", "await", "break", "continue", "pass", "raise", "assert",
               "del", "global", "nonlocal", "in", "is", "not", "and", "or"],
    "javascript": ["function", "const", "let", "var", "if", "else", "for", "while", "try",
                   "catch", "finally", "return", "true", "false", "null", "undefined", "this",
                   "new", "class", "extends", "import", "export", "from", "async", "await",
                   "switch", "case", "break", "continue", "delete", "in", "instanceof",
                   "typeof", "void", "with", "debugger"],
    "html": ["html", "head", "body", "title", "meta", "link", "script", "style", "div", "span",
             "p", "a", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "table", "tr", "td",
             "th", "form", "input", "button", "select", "option", "textarea", "img", "br", "hr"],
    "css": ["color", "background", "font", "margin", "padding", "border", "display", "position",
            "width", "height", "flex", "grid", "align", "justify", "text", "float", "clear",
            "overflow", "z-index", "opacity", "transition", "animation", "hover", "active",
            "focus", "before", "after"],
}

TAG_COLORS = dict(DEFAULT_TAG_COLORS)


def generer_pdf_minimal(titre, contenu, chemin):
    """Genere un fichier PDF valide (PDF 1.4) sans dependance externe."""
    def echappe_pdf(texte):
        texte = texte.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        return texte

    lignes = contenu.splitlines()
    # Limite a 60 lignes pour garder un PDF lisible
    lignes = lignes[:60]
    texte_pdf = ""
    y = 740
    for ligne in lignes:
        texte_pdf += "BT /F1 12 Tf 50 {} Td ({}) Tj ET\n".format(y, echappe_pdf(ligne))
        y -= 18
        if y < 60:
            break

    pdf = (
        "%PDF-1.4\n"
        "1 0 obj\n"
        "<< /Type /Catalog /Pages 2 0 R >>\n"
        "endobj\n"
        "2 0 obj\n"
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
        "endobj\n"
        "3 0 obj\n"
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\n"
        "endobj\n"
        "4 0 obj\n"
        "<< /Length {} >>\n"
        "stream\n"
        "BT /F1 12 Tf 50 760 Td ({}) Tj ET\n"
        "{}"
        "endstream\n"
        "endobj\n"
        "xref\n"
        "0 5\n"
        "0000000000 65535 f \n"
        "0000000015 00000 n \n"
        "0000000064 00000 n \n"
        "0000000123 00000 n \n"
        "0000000212 00000 n \n"
        "trailer\n"
        "<< /Size 5 /Root 1 0 R >>\n"
        "startxref\n"
        "{}\n"
        "%%EOF\n"
    ).format(len(texte_pdf) + len(echappe_pdf(titre)) + 40, echappe_pdf(titre), texte_pdf, len(pdf) if False else 0)

    # Recalculer le startxref correctement
    header_len = len("%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length {} >>\nstream\nBT /F1 12 Tf 50 760 Td ({}) Tj ET\n{}endstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000015 00000 n \n0000000064 00000 n \n0000000123 00000 n \n0000000212 00000 n \ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n".format(len(texte_pdf) + len(echappe_pdf(titre)) + 40, echappe_pdf(titre), texte_pdf))
    xref_pos = len(header_len.encode("latin-1", errors="replace")) if False else None

    # Construction finale simple
    obj4_stream = "BT /F1 12 Tf 50 760 Td ({}) Tj ET\n{}endstream\nendobj\n".format(echappe_pdf(titre), texte_pdf)
    obj4_len = len(obj4_stream.encode("latin-1", errors="replace"))
    obj4 = "4 0 obj\n<< /Length {} >>\nstream\n{}endobj\n".format(obj4_len, obj4_stream)

    xref_start = (
        len(b"%PDF-1.4\n") +
        len(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n") +
        len(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n") +
        len(b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n") +
        len(obj4.encode("latin-1", errors="replace"))
    )

    pdf_final = (
        "%PDF-1.4\n"
        "1 0 obj\n"
        "<< /Type /Catalog /Pages 2 0 R >>\n"
        "endobj\n"
        "2 0 obj\n"
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
        "endobj\n"
        "3 0 obj\n"
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\n"
        "endobj\n"
        + obj4 +
        "xref\n"
        "0 5\n"
        "0000000000 65535 f \n"
        "0000000009 00000 n \n"
        "0000000058 00000 n \n"
        "0000000115 00000 n \n"
        "0000000{:010d} 00000 n \n".format(9 + 49 + 49 + 49 + obj4_len)[:1] + "0000000{:010d} 00000 n \n".format(0)  # placeholder
    )

    # Reconstruire proprement avec les offsets corrects
    parts = []
    parts.append(b"%PDF-1.4\n")
    p1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    parts.append(p1)
    p2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    parts.append(p2)
    p3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n"
    parts.append(p3)
    p4 = obj4.encode("latin-1", errors="replace")
    parts.append(p4)

    offsets = []
    acc = 0
    for p in parts:
        offsets.append(acc)
        acc += len(p)

    xref_lines = b"xref\n0 5\n"
    for i, off in enumerate(offsets):
        xref_lines += "{:010d} 00000 n \n".format(off).encode("ascii")

    trailer = b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n{}\n%%EOF\n".format(acc).encode("ascii")

    pdf_final = b"".join(parts) + xref_lines + trailer

    with open(chemin, "wb") as f:
        f.write(pdf_final)
    return chemin



class DevWindow(ctk.CTkFrame):
    def __init__(self, parent_app, master=None, ollama_client=None):
        super().__init__(master or parent_app, fg_color=BG_APP, corner_radius=0)
        self.parent_app = parent_app
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.current_file = None
        self.current_folder = None
        self._managed_files = set()
        self._file_buffers = {}
        self.versions = {}
        self.current_project = None
        self.unsaved = False
        self.ia_history = []
        self.proposals = []
        self.selected_tree_item = None
        self._highlight_job = None
        self._preview_job = None
        self._autosave_job = None
        self._completion_job = None
        self._completion_generation = 0
        self._inline_suggestion = ""
        self._inline_completion_label = None
        self._inline_replacement_range = None
        self._multi_completion_popup = None
        self._pending_completions = {}
        self._completion_expected = 0
        self._completion_received = 0
        self._line_number_redraw_job = None
        self._recent_inline_suggestions = []
        self.autosave_enabled = True
        self.session_file = None  # chemin du dev_session.json du projet courant

        self._build_ui()
        self._load_projects()
        self.after_idle(self._update_preview)

    def toggle_maximize(self):
        window = self.winfo_toplevel()
        if window.state() == "zoomed":
            window.state("normal")
            self.maximize_button.configure(text="⛶ Agrandir")
        else:
            window.state("zoomed")
            self.maximize_button.configure(text="❐ Restaurer")

    def _text_widget(self):
        return getattr(self.editor, "_textbox", self.editor)

    def _on_editor_scroll(self, first, last):
        self.editor._y_scrollbar.set(first, last)
        self._queue_line_number_redraw()

    def _on_editor_modified(self, event=None):
        if self._line_number_redraw_job is None:
            self._line_number_redraw_job = self.after_idle(self._finish_editor_modified)

    def _finish_editor_modified(self):
        self._line_number_redraw_job = None
        text_widget = self._text_widget()
        if text_widget.edit_modified():
            text_widget.edit_modified(False)
        self._redraw_line_numbers()

    def _queue_line_number_redraw(self, event=None):
        if self._line_number_redraw_job is None:
            self._line_number_redraw_job = self.after_idle(self._finish_line_number_redraw)

    def _finish_line_number_redraw(self):
        self._line_number_redraw_job = None
        self._redraw_line_numbers()

    def _redraw_line_numbers(self):
        if not hasattr(self, "line_numbers") or not self.line_numbers.winfo_exists():
            return
        canvas = self.line_numbers
        canvas.delete("all")
        text_widget = self._text_widget()
        index = text_widget.index("@0,0")
        previous_line = None
        while True:
            line = int(index.split(".")[0])
            if line != previous_line:
                info = text_widget.dlineinfo(index)
                if info is None or info[1] > canvas.winfo_height():
                    break
                canvas.create_text(
                    canvas.winfo_width() - 8,
                    info[1] + info[3] / 2,
                    text=str(line),
                    anchor="e",
                    fill="#858585",
                    font=text_widget.cget("font"),
                )
                previous_line = line
            next_index = text_widget.index("{} + 1 display lines".format(index))
            if next_index == index:
                break
            index = next_index

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1, minsize=250)
        self.grid_columnconfigure(1, weight=2, minsize=400)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")

        header_left = ctk.CTkFrame(header, fg_color="transparent")
        header_left.pack(side="left", fill="y", padx=12, pady=4)
        ctk.CTkLabel(header_left, text="💻 Calisto Développement", font=ctk.CTkFont(size=14, weight="bold"), text_color=ACCENT).pack(side="left")

        header_right = ctk.CTkFrame(header, fg_color="transparent")
        header_right.pack(side="right", padx=10, pady=4)
        self.maximize_button = ctk.CTkButton(
            header_right,
            text="⛶ Agrandir",
            width=90,
            command=self.toggle_maximize,
            fg_color="#6b7280",
            hover_color="#4b5563",
        )
        self.maximize_button.pack(side="right", padx=4, pady=2)
        ctk.CTkButton(header_right, text="📁 Ouvrir dossier", width=105, command=self.open_folder, fg_color=BG_EDITOR, hover_color="#2a2a3e").pack(side="right", padx=4, pady=2)
        ctk.CTkButton(header_right, text="📄 Nouveau fichier", width=105, command=self.new_file, fg_color=BG_EDITOR, hover_color="#2a2a3e").pack(side="right", padx=4, pady=2)
        ctk.CTkButton(header_right, text="🗑️ Supprimer", width=95, command=self.delete_selected, fg_color="#c24141", hover_color="#a33434").pack(side="right", padx=4, pady=2)
        ctk.CTkButton(header_right, text="💾 Enregistrer", width=95, command=self.save_file, fg_color=ACCENT, hover_color=ACCENT_HOVER).pack(side="right", padx=4, pady=2)
        ctk.CTkButton(header_right, text="🌐 Prévisualiser", width=105, command=self.preview_open_browser, fg_color="#6366f1", hover_color="#4f46e5").pack(side="right", padx=4, pady=2)
        ctk.CTkButton(header_right, text="🎨 Réglages couleurs", width=115, command=self.open_color_settings, fg_color="#6b7280", hover_color="#4b5563").pack(side="right", padx=4, pady=2)

        # Sidebar explorateur
        self.explorer = ctk.CTkFrame(self, width=300, fg_color="#252526", corner_radius=0, border_width=2, border_color="#333336")
        self.explorer.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
        self.explorer.grid_propagate(False)

        ctk.CTkLabel(self.explorer, text="📂 Explorateur", font=ctk.CTkFont(size=14, weight="bold"), text_color=ACCENT).pack(pady=(15, 8), padx=12, anchor="w")

        self.tree_frame = ctk.CTkScrollableFrame(self.explorer, fg_color="transparent")
        self.tree_frame.pack(fill="both", expand=True, padx=8, pady=(0, 10))

        self.folder_label = ctk.CTkLabel(self.explorer, text="Aucun dossier ouvert", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED)
        self.folder_label.pack(padx=12, pady=(0, 10), anchor="w")

        self.proj_frame = ctk.CTkFrame(self.explorer, fg_color=BG_EDITOR, corner_radius=8)
        self.proj_frame.pack(fill="x", padx=8, pady=(0, 12))
        ctk.CTkLabel(self.proj_frame, text="Projet / Version", font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT_MUTED).pack(padx=8, pady=(8, 4), anchor="w")
        self.proj_var = ctk.StringVar(value="Aucun")
        self.proj_menu = ctk.CTkOptionMenu(self.proj_frame, variable=self.proj_var, values=["Aucun"], command=self.load_project_version, fg_color="#2a2a3e", button_color=ACCENT, button_hover_color=ACCENT_HOVER, font=ctk.CTkFont(size=11))
        self.proj_menu.pack(padx=8, pady=(0, 8), fill="x")

        # Zone principale
        self.main_area = ctk.CTkFrame(self, fg_color="#1a1a1b", corner_radius=0, border_width=2, border_color="#333336")
        self.main_area.grid(row=1, column=1, sticky="nsew", padx=2, pady=2)
        self.main_area.grid_columnconfigure(0, weight=2)
        self.main_area.grid_columnconfigure(1, weight=1)
        self.main_area.grid_rowconfigure(0, weight=1)

        # Éditeur
        self.editor_frame = ctk.CTkFrame(self.main_area, fg_color=BG_EDITOR, corner_radius=0, border_width=2, border_color="#333336")
        self.editor_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        self.editor_frame.grid_columnconfigure(1, weight=1)
        self.editor_frame.grid_rowconfigure(1, weight=1)
        self.editor_frame.grid_rowconfigure(2, weight=0)

        editor_header = ctk.CTkFrame(self.editor_frame, fg_color="#2a2a2e", corner_radius=0)
        editor_header.grid(row=0, column=0, columnspan=2, sticky="ew")

        # Gauche : nom du fichier
        editor_left = ctk.CTkFrame(editor_header, fg_color="transparent")
        editor_left.pack(side="left", fill="y", padx=10, pady=4)
        self.file_name_label = ctk.CTkLabel(editor_left, text="Aucun fichier", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED)
        self.file_name_label.pack(side="left")
        self.lang_label = ctk.CTkLabel(editor_left, text="", font=ctk.CTkFont(size=10), text_color=TEXT_MUTED)
        self.lang_label.pack(side="left", padx=(8, 0))

        # Boutons rapides dans l'editeur (centre-droit, styles propres, pas de compression)
        editor_quick = ctk.CTkFrame(editor_header, fg_color="transparent")
        editor_quick.pack(side="right", padx=8, pady=4)

        btn_style = {"font": ctk.CTkFont(size=10, weight="bold"), "width": 88, "height": 26, "corner_radius": 6}
        ctk.CTkButton(editor_quick, text="📄 Nouveau", command=self.new_file, fg_color=BG_EDITOR, hover_color="#2a2a3e", **btn_style).pack(side="left", padx=3)
        ctk.CTkButton(editor_quick, text="💾 Enregistrer", command=self.save_file, fg_color=ACCENT, hover_color=ACCENT_HOVER, **btn_style).pack(side="left", padx=3)
        ctk.CTkButton(editor_quick, text="🌐 Navigateur", command=self.preview_open_browser, fg_color="#6366f1", hover_color="#4f46e5", **btn_style).pack(side="left", padx=3)
        ctk.CTkButton(editor_quick, text="✨ Formater", command=self.format_code, fg_color="#9333ea", hover_color="#7e22ce", **btn_style).pack(side="left", padx=3)
        ctk.CTkButton(editor_quick, text="🔍 Rechercher", command=self._show_find_replace, fg_color="#6366f1", hover_color="#4f46e5", **btn_style).pack(side="left", padx=3)
        ctk.CTkButton(editor_quick, text="📍 Ligne", command=self._goto_line, fg_color="#6b7280", hover_color="#4b5563", **btn_style).pack(side="left", padx=3)
        ctk.CTkButton(editor_quick, text="💬 Commenter", command=self._toggle_comment, fg_color="#a855f7", hover_color="#9333ea", **btn_style).pack(side="left", padx=3)
        ctk.CTkButton(editor_quick, text="📄 Retour ligne", command=self._toggle_word_wrap, fg_color="#6b7280", hover_color="#4b5563", **btn_style).pack(side="left", padx=3)

        self.line_numbers = tk.Canvas(
            self.editor_frame,
            width=44,
            bg="#252526",
            highlightthickness=0,
            bd=0,
        )
        self.line_numbers.grid(row=1, column=0, sticky="ns", padx=(5, 0), pady=5)
        self.line_numbers.bind("<Configure>", self._queue_line_number_redraw)
        self.editor = ctk.CTkTextbox(self.editor_frame, font=ctk.CTkFont(family="Consolas", size=13), fg_color=BG_EDITOR, text_color=TEXT_MAIN, border_width=0, wrap="none")
        self.editor.grid(row=1, column=1, sticky="nsew", padx=(0, 5), pady=5)
        self._text_widget().configure(yscrollcommand=self._on_editor_scroll)
        # Horizontal scrollbar pour deplacer de gauche a droite
        self.editor_xscroll = tk.Scrollbar(self.editor_frame, orient="horizontal", command=self._text_widget().xview)
        self.editor_xscroll.grid(row=2, column=1, sticky="ew", padx=(0, 5))
        self._text_widget().configure(xscrollcommand=self.editor_xscroll.set)
        self._text_widget().bind("<<Modified>>", self._on_editor_modified, add="+")
        self._text_widget().bind("<Configure>", self._queue_line_number_redraw, add="+")
        self.editor.bind("<KeyRelease>", self.on_key_release)
        self.editor.bind("<Return>", self.on_editor_return)
        self.editor.bind("<Tab>", self.on_tab)
        self.editor.bind("<Escape>", self._reject_inline_completion_key)
        self.editor.bind("<Key>", self._on_auto_close_key)
        self.editor.bind("<Control-MouseWheel>", self._on_ctrl_wheel_zoom)
        self.editor.bind("<Control-slash>", self._toggle_comment)
        self.editor.bind("<Control-f>", lambda e: self._show_find_replace())
        self.editor.bind("<Control-g>", lambda e: self._goto_line())
        self.editor.bind("<Control-h>", lambda e: self._show_find_replace())
        self.editor.bind("<Control-s>", lambda e: self.save_file())
        self.editor.bind("<Right>", self._match_bracket)
        self.editor.bind("<Left>", self._match_bracket)
        self.editor.bind("<KeyRelease>", self._update_status_line_col, add="+")

        # Panneau droit : onglets prévisualisation / IA
        self.right_panel = ctk.CTkFrame(self.main_area, fg_color="#2a2a2e", corner_radius=0, border_width=2, border_color="#333336")
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)
        self.right_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.grid_rowconfigure(1, weight=1)

        self.tab_frame = ctk.CTkFrame(self.right_panel, fg_color="#2a2a2e", height=32, corner_radius=0)
        self.tab_frame.grid(row=0, column=0, sticky="ew")
        self.tab_frame.grid_propagate(False)
        self.tab_frame.grid_columnconfigure(0, weight=1)
        self.tab_frame.grid_columnconfigure(1, weight=1)

        self.tab_preview = ctk.CTkButton(self.tab_frame, text="🌐 Prévisualisation (temps réel)", fg_color="transparent", text_color=TEXT_MAIN, hover_color="#3a3a3e", command=lambda: self.switch_tab("preview"), font=ctk.CTkFont(size=12))
        self.tab_preview.grid(row=0, column=0, sticky="nsew")
        self.tab_ia = ctk.CTkButton(self.tab_frame, text="🤖 Assistant IA", fg_color="#2a2a3e", text_color="#ffffff", hover_color="#3a3a3e", command=lambda: self.switch_tab("ia"), font=ctk.CTkFont(size=12, weight="bold"))
        self.tab_ia.grid(row=0, column=1, sticky="nsew")

        self.tab_content = ctk.CTkFrame(self.right_panel, fg_color="#161b22", corner_radius=0)
        self.tab_content.grid(row=1, column=0, sticky="nsew")
        self.tab_content.grid_columnconfigure(0, weight=1)
        self.tab_content.grid_rowconfigure(0, weight=1)
        self.tab_content.grid_rowconfigure(1, weight=0)

        # Contenu Prévisualisation (temps réel)
        self.preview_frame = ctk.CTkFrame(self.tab_content, fg_color="#0d1117", corner_radius=0)
        self.preview_frame.grid(row=0, column=0, sticky="nsew")
        if HtmlFrame is not None:
            self.preview = HtmlFrame(self.preview_frame, messages_enabled=False)
            self.preview.pack(fill="both", expand=True)
        else:
            self.preview = ctk.CTkTextbox(
                self.preview_frame,
                font=ctk.CTkFont(family="Consolas", size=12),
                fg_color="#0d1117",
                text_color="#c9d1d9",
                border_width=0,
                wrap="word",
            )
            self.preview.pack(fill="both", expand=True)
            self.preview.insert(
                "1.0",
                "L'aperçu intégré nécessite tkinterweb. Fermez puis relancez l'application "
                "avec le lanceur pour installer les dépendances.",
            )
            self.preview.configure(state="disabled")

        self.preview_bar = ctk.CTkFrame(self.tab_content, fg_color="#161b22", corner_radius=0)
        self.preview_bar.grid(row=1, column=0, sticky="ew")
        self.preview_bar.grid_columnconfigure(0, weight=1)
        self.preview_open_btn = ctk.CTkButton(self.preview_bar, text="🌐 OUVRIR DANS LE NAVIGATEUR (page rendue)", command=self.preview_open_browser, fg_color="#6366f1", hover_color="#4f46e5", font=ctk.CTkFont(size=12, weight="bold"), height=40)
        self.preview_open_btn.pack(padx=12, pady=10)
        ctk.CTkLabel(self.preview_bar, text="L'aperçu intégré suit le HTML/CSS. Ouvrez dans le navigateur pour les fonctions JavaScript complètes.", font=ctk.CTkFont(size=10), text_color=TEXT_MUTED).pack(pady=(0, 8))

        # Contenu Assistant IA (zone agrandie)
        self.ia_panel = ctk.CTkFrame(self.tab_content, fg_color="#161b22", corner_radius=0)
        self.ia_panel.grid_columnconfigure(0, weight=1)
        self.ia_panel.grid_rowconfigure(0, weight=3)
        self.ia_panel.grid_rowconfigure(1, weight=2)

        self.ia_chat = ctk.CTkTextbox(self.ia_panel, font=ctk.CTkFont(family="Consolas", size=12), fg_color="#0d1117", text_color="#c9d1d9", border_width=0)
        self.ia_chat.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 4))
        self.ia_chat.insert("1.0", "Assistant IA Calisto\nPosez vos questions sur le code ici.\nTout est enregistré : l'IA se souvient de ce qu'elle a créé/modifié même après fermeture.\n---\n")

        proposal_section = ctk.CTkFrame(self.ia_panel, fg_color="#161b22", corner_radius=0)
        proposal_section.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 4))
        proposal_section.grid_columnconfigure(0, weight=1)
        proposal_section.grid_rowconfigure(1, weight=1)
        proposal_header = ctk.CTkFrame(proposal_section, fg_color="transparent")
        proposal_header.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        ctk.CTkLabel(
            proposal_header,
            text="Propositions de code",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#c9d1d9",
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            proposal_header,
            text="Tout refuser",
            width=92,
            height=28,
            command=self._clear_proposals,
            fg_color="#8f3333",
            hover_color="#a33434",
            font=ctk.CTkFont(size=10, weight="bold"),
        ).pack(side="right", padx=4)
        self.proposals_container = ctk.CTkScrollableFrame(proposal_section, fg_color="#161b22", height=200)
        self.proposals_container.grid(row=1, column=0, sticky="nsew")
        self.proposals_container.grid_columnconfigure(0, weight=1)

        # Saisie IA (agrandie, multiligne)
        self.ia_entry = ctk.CTkTextbox(self.ia_panel, height=90, font=ctk.CTkFont(size=12), fg_color=BG_EDITOR, border_color="#4b4c54", text_color=TEXT_MAIN)
        self.ia_entry.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 4))
        self.ia_entry.insert("1.0", "Demandez à l'IA... (Ctrl+Entrée pour envoyer)")
        self.ia_entry.bind("<Key>", self.ia_key_handler)

        btn_ia_frame = ctk.CTkFrame(self.ia_panel, fg_color="transparent")
        btn_ia_frame.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 8))
        ctk.CTkButton(btn_ia_frame, text="Envoyer à l'IA", command=self.ia_send, fg_color=IA_COLOR, hover_color=IA_HOVER, font=ctk.CTkFont(size=11, weight="bold")).pack(side="right")
        ctk.CTkButton(btn_ia_frame, text="Refactoriser + commenter", command=self.refactor_and_comment, fg_color="#6366f1", hover_color="#4f46e5", font=ctk.CTkFont(size=11)).pack(side="left")

        # Afficher preview par défaut
        self.preview_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.preview_bar.place(relx=0, rely=1.0, relwidth=1, anchor="sw", y=-4)
        self.ia_panel.place_forget()
        self.active_tab = "preview"

        # Barre d'état
        self.status_var = ctk.StringVar(value="Prêt")
        status_bar = ctk.CTkFrame(self, fg_color=BG_PANEL, height=28, corner_radius=0)
        status_bar.grid(row=2, column=0, columnspan=2, sticky="ew")
        status_bar.grid_propagate(False)
        ctk.CTkLabel(status_bar, textvariable=self.status_var, font=ctk.CTkFont(size=11), text_color=TEXT_MUTED).pack(side="left", padx=12, pady=4)

        self.ai_btn = ctk.CTkButton(self.editor_frame, text="🤖 Demander à l'IA", width=120, command=self.ask_ai_help, fg_color=IA_COLOR, hover_color=IA_HOVER, font=ctk.CTkFont(size=11, weight="bold"))
        self.ai_btn.place(relx=1.0, rely=1.0, x=-10, y=-10, anchor="se")

    def switch_tab(self, name):
        if name == self.active_tab:
            return
        self.active_tab = name
        if name == "preview":
            self.tab_preview.configure(fg_color="#2a2a2e", text_color=TEXT_MAIN, font=ctk.CTkFont(size=12))
            self.tab_ia.configure(fg_color="#2a2a3e", text_color="#ffffff", font=ctk.CTkFont(size=12, weight="bold"))
            self.preview_frame.grid(row=0, column=0, sticky="nsew")
            self.preview_bar.grid(row=1, column=0, sticky="ew")
            self.ia_panel.grid_remove()
        else:
            self.tab_ia.configure(fg_color="#2a2a2e", text_color=TEXT_MAIN, font=ctk.CTkFont(size=12))
            self.tab_preview.configure(fg_color="#2a2a3e", text_color="#ffffff", font=ctk.CTkFont(size=12, weight="bold"))
            self.ia_panel.grid(row=0, column=0, sticky="nsew")
            self.preview_frame.grid_remove()
            self.preview_bar.grid_remove()

    # ---------- Session persistante ----------

    def _session_path(self):
        if not self.current_folder:
            return None
        return Path(self.current_folder) / ".calisto_session.json"

    def _save_session(self):
        if not self.current_folder:
            return
        try:
            session = {
                "folder": str(self.current_folder),
                "current_file": str(self.current_file) if self.current_file else None,
                "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
                "ia_history": self.ia_history[-50:],
                "managed_files": sorted(self._managed_files),
            }
            sp = self._session_path()
            sp.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print("Erreur sauvegarde session:", e)

    def _load_session(self):
        sp = self._session_path()
        if not sp or not sp.exists():
            self._managed_files = set()
            return
        try:
            data = json.loads(sp.read_text(encoding="utf-8"))
            self.ia_history = data.get("ia_history", [])
            managed_files = set()
            for relative_path in data.get("managed_files", []):
                candidate = (self.current_folder / relative_path).resolve()
                try:
                    normalized = candidate.relative_to(self.current_folder.resolve()).as_posix().casefold()
                except ValueError:
                    continue
                if candidate.is_file():
                    managed_files.add(normalized)
            if "managed_files" not in data:
                for entry in self.ia_history:
                    if not isinstance(entry, dict) or entry.get("action") not in ("creer_fichier", "creer_fichier_ia"):
                        continue
                    candidate = Path(entry.get("detail", ""))
                    if not candidate.is_absolute():
                        candidate = self.current_folder / candidate
                    candidate = candidate.resolve()
                    try:
                        normalized = candidate.relative_to(self.current_folder.resolve()).as_posix().casefold()
                    except ValueError:
                        continue
                    if candidate.is_file():
                        managed_files.add(normalized)
            self._managed_files = managed_files
            cf = data.get("current_file")
            if cf and Path(cf).is_file():
                self.open_file(Path(cf))
            self._refresh_tree()
        except Exception as e:
            print("Erreur chargement session:", e)

    def _log_ia_action(self, action, detail):
        entry = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "action": action,
            "detail": detail,
            "file": str(self.current_file) if self.current_file else None,
        }
        self.ia_history.append(entry)
        self._save_session()

    def get_ai_context_files(self):
        code_files = {}
        context_errors = []
        total_chars = 0
        max_context_files = 20
        max_file_chars = 5000
        max_current_file_chars = 24000
        max_total_chars = 32000
        ignored_directories = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build", "versions"}
        current_path = self.current_file.resolve() if self.current_file else None
        candidates = []
        current_content = self.editor.get("1.0", "end-1c") if current_path else ""
        if current_path:
            self._file_buffers[current_path] = current_content
        current_content_limit = min(len(current_content), max_current_file_chars)
        other_context_budget = max_total_chars - current_content_limit

        if self.current_folder and self.current_folder.is_dir():
            for root, directories, filenames in os.walk(self.current_folder):
                directories[:] = sorted(
                    name for name in directories
                    if name not in ignored_directories and not name.startswith(".")
                )
                for name in sorted(filenames):
                    path = Path(root) / name
                    if path.suffix.lower() not in LANG_EXTENSIONS:
                        continue
                    if not self._is_managed_file(path):
                        continue
                    candidates.append(path.resolve())

        candidates = [path for path in candidates if path != current_path]
        candidates.sort(key=lambda path: str(path).casefold())
        for path in candidates:
            if len(code_files) >= max_context_files:
                context_errors.append("Le contexte est limite aux {} fichiers de code.".format(max_context_files))
                break
            try:
                relative = path.relative_to(self.current_folder.resolve()).as_posix() if self.current_folder else path.name
                content = self._file_buffers.get(path)
                if content is None:
                    content = path.read_text(encoding="utf-8-sig")
            except (OSError, UnicodeError, ValueError) as error:
                context_errors.append("Fichier ignore ({}): {}".format(path.name, error))
                continue

            remaining = other_context_budget - total_chars
            if remaining <= 0:
                context_errors.append(
                    "Le contexte des fichiers associes est limite a {} caracteres.".format(other_context_budget)
                )
                break
            content_limit = min(max_file_chars, remaining)
            if len(content) > content_limit:
                context_errors.append(
                    "{} est tronque a {} caracteres pour tenir dans le contexte.".format(relative, content_limit)
                )
            code_files[relative] = content[:content_limit]
            total_chars += min(len(content), content_limit)

        if self.current_file:
            current_path = self.current_file.resolve()
            current_content = self.editor.get("1.0", "end-1c")
            self._file_buffers[current_path] = current_content
            try:
                current_name = current_path.relative_to(self.current_folder.resolve()).as_posix() if self.current_folder else current_path.name
            except ValueError:
                current_name = current_path.name
            current_content_limit = min(max_current_file_chars, max_total_chars - total_chars)
            if len(current_content) > current_content_limit:
                context_errors.append(
                    "{} (fichier ouvert) est tronque a {} caracteres.".format(
                        current_name, current_content_limit
                    )
                )
            code_files[current_name + " (fichier ouvert, modifications incluses)"] = current_content[:current_content_limit]
            total_chars += min(len(current_content), current_content_limit)

        folder = str(self.current_folder) if self.current_folder else "Aucun dossier"
        recent_actions = "\n".join(
            "- {} : {} ({})".format(item["time"], item["action"], item["detail"])
            for item in self.ia_history[-10:]
        )
        code_files["Projet de l'editeur : {}".format(folder)] = "\n".join(
            ["Fichiers transmis a l'IA :"] +
            ["- {}".format(name) for name in code_files] +
            context_errors
        )
        code_files["Actions recentes de l'editeur"] = recent_actions or "Aucune action recente."
        return code_files

    def get_ai_context(self):
        context = self.get_ai_context_files()
        return "\n\n".join(
            "--- {} ---\n{}\n--- fin ---".format(name, content)
            for name, content in context.items()
        )

    # ---------- Projets / fichiers ----------

    def _load_projects(self):
        projects_dir = Path("projects")
        if not projects_dir.exists():
            projects_dir.mkdir()
        self.versions = {}
        for p in projects_dir.iterdir():
            if p.is_dir():
                versions_dir = p / "versions"
                versions_dir.mkdir(exist_ok=True)
                vers_list = []
                for v in sorted(versions_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
                    try:
                        with open(v, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        vers_list.append({
                            "name": v.stem,
                            "date": data.get("date", ""),
                            "desc": data.get("desc", ""),
                            "files": data.get("files", {}),
                        })
                    except Exception:
                        continue
                if vers_list:
                    self.versions[p.name] = vers_list
        self._refresh_proj_menu()
        self._refresh_tree()

    def _refresh_proj_menu(self):
        values = ["Aucun"] + list(self.versions.keys())
        self.proj_menu.configure(values=values)
        self.proj_var.set("Aucun")

    def _refresh_tree(self):
        for w in self.tree_frame.winfo_children():
            w.destroy()
        if not self.current_folder:
            ctk.CTkLabel(self.tree_frame, text="Ouvrez un dossier pour commencer", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED).pack(pady=20)
            return
        p = Path(self.current_folder)
        self.folder_label.configure(text=p.name)
        if not self._managed_files:
            ctk.CTkLabel(
                self.tree_frame,
                text="Aucun fichier créé depuis Calisto.\nUtilisez « Nouveau fichier ».",
                font=ctk.CTkFont(size=11),
                text_color=TEXT_MUTED,
                justify="left",
            ).pack(pady=20, padx=8)
            return
        self._add_tree_items(self.tree_frame, p)

    def _is_managed_file(self, path):
        try:
            relative = Path(path).resolve().relative_to(self.current_folder.resolve()).as_posix().casefold()
        except (ValueError, AttributeError):
            return False
        return relative in self._managed_files

    def _is_available_project_file(self, path):
        return self._is_managed_file(path) or (
            self.current_file is not None
            and Path(path).resolve() == self.current_file.resolve()
        )

    def _has_managed_descendant(self, path):
        try:
            relative = Path(path).resolve().relative_to(self.current_folder.resolve()).as_posix().casefold()
        except (ValueError, AttributeError):
            return False
        prefix = "" if relative == "." else relative.rstrip("/") + "/"
        return any(item.startswith(prefix) for item in self._managed_files)

    def _register_managed_file(self, path):
        try:
            relative = Path(path).resolve().relative_to(self.current_folder.resolve()).as_posix().casefold()
        except ValueError:
            raise ValueError("Le fichier doit rester dans le dossier du projet.")
        self._managed_files.add(relative)
        self._save_session()

    def _icon_for(self, path):
        if path.is_dir():
            return "📁"
        return FILE_ICONS.get(path.suffix.lower(), "📄")

    def _add_tree_items(self, parent, path, indent=0):
        visible_items = []
        try:
            for item in path.iterdir():
                if item.is_dir() and self._has_managed_descendant(item):
                    visible_items.append(item)
                elif item.is_file() and self._is_managed_file(item):
                    visible_items.append(item)
        except OSError:
            return
        for item in sorted(visible_items, key=lambda x: (not x.is_dir(), x.name.lower()))[:100]:
            prefix = "    " * indent
            icon = self._icon_for(item)
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=1)
            row.item_path = item
            if item == self.selected_tree_item:
                row.configure(fg_color="#2a4a6e")
            lbl = ctk.CTkLabel(row, text=prefix + icon + " " + item.name, font=ctk.CTkFont(size=11), text_color=TEXT_MAIN, anchor="w", cursor="hand2")
            lbl.pack(fill="x", padx=5, pady=1)
            lbl.bind("<Button-1>", lambda e, p=item: self.on_tree_click(p))
            row.bind("<Button-1>", lambda e, p=item: self.on_tree_click(p))
            if item.is_dir():
                self._add_tree_items(row, item, indent + 1)

    def on_tree_click(self, path):
        self.selected_tree_item = path
        self._refresh_tree()
        if not path.is_dir():
            self.open_file(path)

    def open_folder(self):
        path = filedialog.askdirectory(title="Choisir un dossier de projet")
        if not path:
            return
        self._cache_current_buffer()
        self.current_folder = Path(path)
        self._managed_files = set()
        self.current_file = None
        self.editor.delete("1.0", "end")
        self.file_name_label.configure(text="Aucun fichier")
        self.lang_label.configure(text="")
        self.selected_tree_item = None
        self._load_session()
        self._refresh_tree()
        if not self.current_file:
            self._update_preview()
        self.status_var.set("Dossier ouvert : {}".format(path))
        self._do_highlight()

    def new_file(self):
        if not self.current_folder:
            messagebox.showwarning("Aucun dossier", "Ouvrez d'abord un dossier de projet.")
            return
        dlg = ctk.CTkInputDialog(text="Nom du fichier (ex: index.html, style.css, script.js) :", title="Nouveau fichier")
        name = dlg.get_input()
        if not name:
            return
        p = (Path(self.current_folder) / name).resolve()
        try:
            p.relative_to(Path(self.current_folder).resolve())
        except ValueError:
            messagebox.showwarning("Nom invalide", "Le fichier doit être créé dans le dossier du projet.")
            return
        if p.exists():
            messagebox.showwarning("Existe déjà", "Ce fichier existe déjà.")
            return
        ext = p.suffix.lower()
        content = ""
        if ext in (".html", ".htm"):
            content = HTML_BOILERPLATE
        elif ext == ".css":
            content = CSS_BOILERPLATE
        elif ext == ".js":
            content = JS_BOILERPLATE
        elif ext == ".py":
            content = "# Nouveau fichier Python\nprint('Bonjour Calisto')\n"
        p.parent.mkdir(parents=True, exist_ok=True)
        if ext in (".html", ".htm"):
            content, stylesheet_path = self._prepare_html_stylesheet(p, content, managed_only=True)
        p.write_text(content, encoding="utf-8")
        self._register_managed_file(p)
        if ext in (".html", ".htm") and not stylesheet_path.exists():
            stylesheet_path.write_text(CSS_BOILERPLATE, encoding="utf-8")
            self._register_managed_file(stylesheet_path)
        elif ext == ".css":
            self._link_css_to_open_html(p)
        self.open_file(p)
        self._refresh_tree()
        self.status_var.set("Fichier créé : {}".format(name))
        self._log_ia_action("creer_fichier", name)

    def delete_selected(self):
        if not self.selected_tree_item:
            messagebox.showwarning("Aucune sélection", "Sélectionnez un fichier dans l'explorateur.")
            return
        if self.selected_tree_item.is_dir():
            messagebox.showwarning("Dossier", "La suppression de dossier n'est pas supportée ici.")
            return
        confirm = messagebox.askyesno("Supprimer", "Supprimer le fichier '{}' ?".format(self.selected_tree_item.name))
        if not confirm:
            return
        try:
            self._file_buffers.pop(self.selected_tree_item.resolve(), None)
            self.selected_tree_item.unlink()
            try:
                relative = self.selected_tree_item.resolve().relative_to(self.current_folder.resolve()).as_posix().casefold()
                self._managed_files.discard(relative)
            except ValueError:
                pass
            if self.current_file and self.current_file == self.selected_tree_item:
                self.current_file = None
                self.editor.delete("1.0", "end")
                self.file_name_label.configure(text="Aucun fichier")
                self.lang_label.configure(text="")
                self._update_preview()
            self.selected_tree_item = None
            self._save_session()
            self._refresh_tree()
            self.status_var.set("Fichier supprimé")
            self._save_session()
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def open_file(self, path):
        p = Path(path)
        if not p.is_file():
            return
        self._invalidate_inline_completion()
        self._cache_current_buffer()
        try:
            content = self._file_buffers.get(p.resolve())
            if content is None:
                content = p.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            content = "[Fichier binaire, impossible à afficher]"
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
            return
        self.current_file = p
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", content)
        self.unsaved = False
        try:
            self.unsaved = content != p.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError):
            pass
        self._file_buffers[p.resolve()] = content
        self.file_name_label.configure(text=p.name)
        ext = p.suffix.lower()
        lang = LANG_EXTENSIONS.get(ext, "texte")
        self.lang_label.configure(text=lang)
        self.status_var.set("Ouvert : {}".format(p.name))
        self._log_ia_action("ouvrir_fichier", str(p))
        self.selected_tree_item = p
        self._refresh_tree()
        self._schedule_highlight()
        self._update_preview()

    def _cache_current_buffer(self):
        if self.current_file and self.editor.winfo_exists():
            self._file_buffers[self.current_file.resolve()] = self.editor.get("1.0", "end-1c")

    def _auto_expand_html_tag(self):
        if not self.current_file:
            return False
        if self.current_file.suffix.lower() not in (".html", ".htm"):
            return False
        text_widget = self._text_widget()
        try:
            before = text_widget.get("insert linestart", "insert")
        except Exception:
            return False
        m = re.search(r"([A-Za-z][A-Za-z0-9]*)$", before)
        if not m:
            return False
        tag = m.group(1).lower()
        html_tags = {
            "p", "div", "span", "a", "h1", "h2", "h3", "h4", "h5", "h6",
            "ul", "ol", "li", "table", "tr", "td", "th", "thead", "tbody",
            "header", "footer", "nav", "section", "article", "aside", "main",
            "form", "input", "button", "select", "option", "textarea", "label",
            "img", "br", "hr", "meta", "link", "script", "style", "title",
            "small", "strong", "em", "b", "i", "u", "code", "pre", "blockquote",
            "dl", "dt", "dd", "figure", "figcaption", "details", "summary",
            "menu", "fieldset", "legend", "datalist", "output", "progress",
            "canvas", "audio", "video", "source", "track", "map", "area",
        }
        self_closing = {"img", "br", "hr", "input", "meta", "link", "source", "track", "area", "col"}
        if tag not in html_tags:
            return False
        # Only expand when the tag word is standalone (preceded by whitespace/start/>/< or nothing)
        start = m.start(1)
        prev = before[start - 1] if start > 0 else ""
        # Expand only when the tag word is standalone: at line start or after whitespace.
        if prev and not prev.isspace():
            return False
        start_idx = "insert linestart + {} chars".format(m.start(1))
        end_idx = "insert linestart + {} chars".format(m.end(1))
        if tag in self_closing:
            replacement = "<{}>".format(tag)
            text_widget.delete(start_idx, end_idx)
            text_widget.insert(start_idx, replacement)
            text_widget.mark_set("insert", "{} + {} chars".format(start_idx, len(replacement)))
        else:
            replacement = "<{}></{}>".format(tag, tag)
            text_widget.delete(start_idx, end_idx)
            text_widget.insert(start_idx, replacement)
            text_widget.mark_set("insert", "{} + {} chars".format(start_idx, len("<{}>".format(tag))))
        self._schedule_highlight()
        self._schedule_preview()
        return True

    # ---------- Auto-fermeture des paires ----------
    def _on_auto_close_key(self, event=None):
        if not self.current_file:
            return None
        text_widget = self._text_widget()
        pairs = {"(": ")", "{": "}", "[": "]", '"': '"', "'": "'"}
        char = event.char
        if char in pairs:
            # Ne pas auto-fermer si le caractère est déjà présent juste après le curseur (évite les doublons)
            try:
                after = text_widget.get("insert", "insert + 1c")
            except Exception:
                after = ""
            if after == pairs[char]:
                return None
            text_widget.insert("insert", char + pairs[char])
            text_widget.mark_set("insert", "insert + 1c")
            self._schedule_highlight()
            return "break"
        # Gérer la fermeture : si l'utilisateur tape )}], et que le char suivant est déjà le même, avancer seulement
        closers = {")", "}", "]", '"', "'"}
        if char in closers:
            try:
                after = text_widget.get("insert", "insert + 1c")
            except Exception:
                after = ""
            if after == char:
                text_widget.mark_set("insert", "insert + 1c")
                self._schedule_highlight()
                return "break"
        return None

    # ---------- Zoom Ctrl + molette ----------
    def _on_ctrl_wheel_zoom(self, event=None):
        try:
            delta = event.delta
        except Exception:
            return None
        current = int(self.editor.cget("font").split(" ")[-1]) if self.editor.cget("font") else 13
        step = 1 if delta > 0 else -1
        new_size = max(8, min(24, current + step))
        self.editor.configure(font=ctk.CTkFont(family="Consolas", size=new_size))
        self._text_widget().configure(font=ctk.CTkFont(family="Consolas", size=new_size))
        self._redraw_line_numbers()
        return "break"

    # ---------- Toggle comment Ctrl+/
    def _toggle_comment(self, event=None):
        if not self.current_file:
            return "break"
        text_widget = self._text_widget()
        try:
            sel_ranges = text_widget.tag_ranges("sel")
        except Exception:
            sel_ranges = []
        language = LANG_EXTENSIONS.get(self.current_file.suffix.lower(), "text")
        comment_prefix = self._comment_prefix_for(language)
        if sel_ranges:
            start = sel_ranges[0]
            end = sel_ranges[-1]
            lines = text_widget.get(start, end).splitlines()
            # Détecter si déjà commenté (première ligne non vide commence par le prefix)
            already = all((ln.strip().startswith(comment_prefix) or ln.strip() == "") for ln in lines if ln.strip())
            new_lines = []
            for ln in lines:
                if ln.strip() == "":
                    new_lines.append(ln)
                elif already:
                    if ln.startswith(comment_prefix):
                        new_lines.append(ln[len(comment_prefix):])
                    else:
                        new_lines.append(ln)
                else:
                    new_lines.append(comment_prefix + ln)
            replacement = "\n".join(new_lines)
            text_widget.delete(start, end)
            text_widget.insert(start, replacement)
            text_widget.tag_remove("sel", "1.0", "end")
            text_widget.tag_add("sel", start, "{} + {} chars".format(start, len(replacement)))
        else:
            # Ligne courante
            line_start = text_widget.index("insert linestart")
            line_end = text_widget.index("insert lineend")
            ln = text_widget.get(line_start, line_end)
            if ln.strip() == "":
                return "break"
            if ln.strip().startswith(comment_prefix):
                new_ln = ln[len(comment_prefix):] if ln.startswith(comment_prefix) else ln
            else:
                new_ln = comment_prefix + ln
            text_widget.delete(line_start, line_end)
            text_widget.insert(line_start, new_ln)
        self.on_key_release()
        return "break"

    @staticmethod
    def _comment_prefix_for(language):
        if language in ("python", "ruby", "shell", "yaml", "sh", "makefile"):
            return "# "
        if language in ("javascript", "typescript", "js", "ts", "java", "c", "cpp", "cs", "go", "rust", "php", "dart", "swift", "kotlin"):
            return "// "
        if language in ("css", "scss", "less"):
            return "/* */"
        if language == "html":
            return "<!-- -->"
        return "# "

    # ---------- Find / Replace ----------
    def _show_find_replace(self):
        win = ctk.CTkToplevel(self)
        win.title("Rechercher / Remplacer")
        win.geometry("420x190")
        win.configure(fg_color=BG_PANEL)
        win.transient(self)
        win.grab_set()
        ctk.CTkLabel(win, text="Rechercher :", font=ctk.CTkFont(size=12), text_color=TEXT_MAIN).pack(pady=(14, 4), padx=14, anchor="w")
        find_var = ctk.StringVar()
        find_entry = ctk.CTkEntry(win, textvariable=find_var, width=360, fg_color=BG_EDITOR, border_color="#4b4c54", text_color=TEXT_MAIN)
        find_entry.pack(padx=14, pady=(0, 10))
        ctk.CTkLabel(win, text="Remplacer par :", font=ctk.CTkFont(size=12), text_color=TEXT_MAIN).pack(pady=(0, 4), padx=14, anchor="w")
        replace_var = ctk.StringVar()
        replace_entry = ctk.CTkEntry(win, textvariable=replace_var, width=360, fg_color=BG_EDITOR, border_color="#4b4c54", text_color=TEXT_MAIN)
        replace_entry.pack(padx=14, pady=(0, 14))
        btns = ctk.CTkFrame(win, fg_color="transparent")
        btns.pack()
        text_widget = self._text_widget()

        def do_find(direction=1):
            needle = find_var.get()
            if not needle:
                return
            text_widget.tag_remove("sel", "1.0", "end")
            start = text_widget.index("insert")
            if direction > 0:
                pos = text_widget.search(needle, start, stopindex="end", nocase=True)
            else:
                pos = text_widget.search(needle, start, stopindex="1.0", backwards=True, nocase=True)
            if pos:
                end = "{} + {} chars".format(pos, len(needle))
                text_widget.tag_add("sel", pos, end)
                text_widget.mark_set("insert", end)
                text_widget.see(pos)
            else:
                self.status_var.set("Aucune correspondance pour '{}'".format(needle))

        def do_replace():
            needle = find_var.get()
            repl = replace_var.get()
            if not needle:
                return
            try:
                pos = text_widget.index("sel.first")
                end = text_widget.index("sel.last")
            except Exception:
                return
            if text_widget.get(pos, end) == needle:
                text_widget.delete(pos, end)
                text_widget.insert(pos, repl)
                text_widget.tag_remove("sel", "1.0", "end")
                text_widget.tag_add("sel", pos, "{} + {} chars".format(pos, len(repl)))
                text_widget.mark_set("insert", "{} + {} chars".format(pos, len(repl)))
            do_find(1)

        def do_replace_all():
            needle = find_var.get()
            repl = replace_var.get()
            if not needle:
                return
            content = text_widget.get("1.0", "end-1c")
            new_content = content.replace(needle, repl)
            if new_content != content:
                text_widget.delete("1.0", "end")
                text_widget.insert("1.0", new_content)
                self.on_key_release()
                self.status_var.set("Remplacement terminé")

        ctk.CTkButton(btns, text="Trouver suivant", command=lambda: do_find(1), fg_color=ACCENT, hover_color=ACCENT_HOVER, font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=6, pady=4)
        ctk.CTkButton(btns, text="Trouver précédent", command=lambda: do_find(-1), fg_color="#6b7280", hover_color="#4b5563", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=6, pady=4)
        ctk.CTkButton(btns, text="Remplacer", command=do_replace, fg_color="#a855f7", hover_color="#9333ea", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=6, pady=4)
        ctk.CTkButton(btns, text="Tout remplacer", command=do_replace_all, fg_color="#6366f1", hover_color="#4f46e5", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=6, pady=4)
        ctk.CTkButton(btns, text="Fermer", command=win.destroy, fg_color="#4b5563", hover_color="#3a3a3e", font=ctk.CTkFont(size=11)).pack(side="left", padx=6, pady=4)
        find_entry.focus()
        win.bind("<Return>", lambda e: do_find(1))
        win.bind("<Control-Return>", lambda e: do_replace())
        win.bind("<Escape>", lambda e: win.destroy())

    # ---------- Goto Line ----------
    def _goto_line(self):
        if not self.current_file:
            messagebox.showwarning("Aucun fichier", "Ouvrez un fichier d'abord.")
            return
        dlg = ctk.CTkInputDialog(text="Numéro de ligne :", title="Aller à la ligne")
        val = dlg.get_input()
        if not val:
            return
        try:
            n = int(val)
        except ValueError:
            return
        text_widget = self._text_widget()
        total = int(text_widget.index("end-1c").split(".")[0])
        if n < 1:
            n = 1
        if n > total:
            n = total
        idx = "{}.0".format(n)
        text_widget.mark_set("insert", idx)
        text_widget.see(idx)
        text_widget.tag_remove("sel", "1.0", "end")
        self.status_var.set("Ligne {}".format(n))

    # ---------- Word wrap ----------
    def _toggle_word_wrap(self):
        wrap = self.editor.cget("wrap")
        new = "none" if wrap == "char" else "char"
        self.editor.configure(wrap=new)
        self.status_var.set("Retour à la ligne : {}".format("ON" if new == "char" else "OFF"))

    # ---------- Status line/col ----------
    def _update_status_line_col(self, event=None):
        if not self.current_file:
            return
        text_widget = self._text_widget()
        try:
            index = text_widget.index("insert")
            line, col = index.split(".")
            total_lines = int(text_widget.index("end-1c").split(".")[0])
            self.status_var.set("Ligne {}, Colonne {} / {}".format(line, int(col) + 1, total_lines))
        except Exception:
            pass

    # ---------- Bracket matching ----------
    def _match_bracket(self, event=None):
        if not self.current_file:
            return None
        text_widget = self._text_widget()
        for tag in ("bracket_match",):
            try:
                text_widget.tag_remove(tag, "1.0", "end")
            except Exception:
                pass
        pairs = {"(": ")", ")": "(", "{": "}", "}": "{", "[": "]", "]": "["}
        try:
            index = text_widget.index("insert")
            char = text_widget.get(index)
            if char not in pairs:
                return None
            # chercher le correspondant
            target = pairs[char]
            found = self._find_matching(text_widget, index, char, target)
            if found:
                text_widget.tag_add("bracket_match", index, "{} + 1c".format(index))
                text_widget.tag_add("bracket_match", found, "{} + 1c".format(found))
                try:
                    text_widget.tag_config("bracket_match", background="#4a4a4e", foreground="#ffffff")
                except Exception:
                    pass
        except Exception:
            pass
        return None

    @staticmethod
    def _find_matching(text_widget, start, open_char, close_char):
        # Implémentation simple : scan ligne par ligne (évite la récursion lourde)
        try:
            start_index = text_widget.index(start)
            line, col = start_index.split(".")
            line = int(line)
            col = int(col)
            content = text_widget.get("{} linestart".format(start_index), "{} lineend".format(start_index))
        except Exception:
            return None
        # Direction selon qu'on est sur un ouvrant ou fermant
        opens = {"(", "{", "["}
        if open_char in opens:
            # chercher vers l'avant
            stack = 1
            idx = text_widget.index(start)
            text_all = text_widget.get(start, "end")
            pos = 0
            while pos < len(text_all):
                c = text_all[pos]
                if c == open_char:
                    stack += 1
                elif c == close_char:
                    stack -= 1
                    if stack == 0:
                        return "{} + {} chars".format(start, pos)
                pos += 1
        else:
            # chercher vers l'arrière
            stack = 1
            idx = text_widget.index(start)
            text_all = text_widget.get("1.0", start)
            pos = len(text_all) - 1
            while pos >= 0:
                c = text_all[pos]
                if c == close_char:
                    stack += 1
                elif c == open_char:
                    stack -= 1
                    if stack == 0:
                        return "1.0 + {} chars".format(pos)
                pos -= 1
        return None

    def _expand_emmet(self):
        if not self.current_file:
            return False
        if self.current_file.suffix.lower() not in (".html", ".htm"):
            return False
        text_widget = self._text_widget()
        try:
            line = text_widget.get("insert linestart", "insert lineend")
        except Exception:
            return False
        cursor_col = int(text_widget.index("insert").split(".")[1])
        before = line[:cursor_col]
        m = re.search(r"([A-Za-z][A-Za-z0-9\-]*(?:[.#][A-Za-z0-9\-_]+)*)(?:\*(\d+))?$", before)
        if not m:
            return False
        token = m.group(1)
        count = int(m.group(2) or 1)
        has_mod = (count > 1) or ("." in token) or ("#" in token) or (">" in token) or ("+" in token)
        if not has_mod:
            return False
        start_idx = "insert linestart + {} chars".format(m.start(1))
        end_idx = "insert linestart + {} chars".format(cursor_col)
        try:
            expansion = self._emmet_build(token, count)
        except Exception:
            return False
        text_widget.delete(start_idx, end_idx)
        text_widget.insert(start_idx, expansion)
        text_widget.mark_set("insert", "{} + {} chars".format(start_idx, len(expansion)))
        self._schedule_highlight()
        self._schedule_preview()
        return True

    @staticmethod
    def _emmet_build(token, count):
        def build_one(tok):
            # tag.class#id
            m = re.match(r"^([A-Za-z][A-Za-z0-9\-]*)((?:\.[A-Za-z0-9\-_]+)?(?:\#[A-Za-z0-9\-_]+)?)$", tok)
            if not m:
                return "<{}></{}>".format(tok, tok)
            tag = m.group(1)
            mods = m.group(2) or ""
            classes = re.findall(r"\.([A-Za-z0-9\-_]+)", mods)
            ids = re.findall(r"\#([A-Za-z0-9\-_]+)", mods)
            attrs = ""
            if classes:
                attrs += ' class="{}"'.format(" ".join(classes))
            if ids:
                attrs += ' id="{}"'.format(ids[0])
            self_closing = {"img", "br", "hr", "input", "meta", "link", "source", "track", "area", "col"}
            if tag.lower() in self_closing:
                return "<{}{}>".format(tag, attrs)
            return "<{}{}></{}>".format(tag, attrs, tag)

        # Handle sibling +
        parts = [p for p in token.split("+") if p]
        if len(parts) > 1:
            return "\n".join(build_one(p) for p in parts)

        # Handle child >
        if ">" in token:
            parent, child = token.split(">", 1)
            cm = re.match(r"^(.+?)(?:\*(\d+))?$", child)
            child_tok = cm.group(1)
            child_count = int(cm.group(2) or 1)
            parent_one = build_one(parent)
            child_one = build_one(child_tok)
            if child_count > 1:
                child_block = "\n".join("    " + child_one for _ in range(child_count))
            else:
                child_block = "    " + child_one
            ptag = re.match(r"^([A-Za-z][A-Za-z0-9\-]*)", parent).group(1)
            return "<{}>{}\n</{}>".format(ptag, child_block, ptag)

        one = build_one(token)
        if count <= 1:
            return one
        return "\n".join(one for _ in range(count))

    def on_key_release(self, event=None):
        self.unsaved = True
        self._cache_current_buffer()
        self.file_name_label.configure(text=(self.current_file.name if self.current_file else "Sans titre") + " ●")
        self._invalidate_inline_completion()
        self._check_emmet()
        if self._expand_emmet():
            return
        if self._auto_expand_html_tag():
            return
        self._schedule_highlight()
        self._schedule_preview()
        if self.autosave_enabled and self.current_file:
            self._schedule_autosave()
        if event and self.current_file and self._inline_completion_is_enabled() and (
            event.char and event.char.isprintable()
            or event.keysym in ("BackSpace", "Delete", "Return")
            or event.state & 0x4 and event.keysym.lower() in ("v", "x", "z", "y")
        ):
            self._schedule_inline_completion()

    def _inline_completion_is_enabled(self):
        setting = getattr(self.parent_app, "inline_completion_var", None)
        return bool(setting.get()) if setting is not None else True

    def set_inline_completion_enabled(self, enabled):
        if enabled:
            return
        if self._completion_job:
            try:
                self.after_cancel(self._completion_job)
            except Exception:
                pass
            self._completion_job = None
        self._invalidate_inline_completion()

    def _invalidate_inline_completion(self):
        self._completion_generation += 1
        self._inline_suggestion = ""
        self._inline_replacement_range = None
        if self._inline_completion_label is not None:
            self._inline_completion_label.place_forget()

    def _schedule_inline_completion(self):
        if not self._inline_completion_is_enabled():
            return
        if self._completion_job:
            try:
                self.after_cancel(self._completion_job)
            except Exception:
                pass
        self._completion_job = self.after(600, self._request_inline_completions)

    def _request_inline_completions(self):
        self._completion_job = None
        if not self._inline_completion_is_enabled() or not self.current_file:
            return
        self._dismiss_multi_popup()
        text_widget = self._text_widget()
        before_cursor = text_widget.get("1.0", "insert")
        after_cursor = text_widget.get("insert", "end-1c")
        if not before_cursor.strip():
            return

        generation = self._completion_generation
        self._completion_generation += 1
        content = text_widget.get("1.0", "end-1c")
        line_start = text_widget.index("insert linestart")
        line_end = text_widget.index("insert lineend")
        current_line = text_widget.get(line_start, line_end)
        line_suffix = text_widget.get("insert", "insert lineend")
        language = LANG_EXTENSIONS.get(self.current_file.suffix.lower(), "text")
        replacement_mode = self._inline_completion_replacement_mode(
            language, current_line, content, line_suffix
        )
        replace_line = replacement_mode is not None
        replacement_range = (line_start, line_end) if replace_line else None
        model = self.parent_app.model_var.get() or "llama3.2"
        file_name = self.current_file.name
        prefix = before_cursor[-3000:]
        suffix = after_cursor[:1500]
        file_context = content[:8000]
        if len(content) > 8000:
            file_context += "\n...[contenu intermediaire tronque; prefixe et suffixe du curseur transmis separement]..."
        existing_html_structure = ", ".join(
            "<{}>".format(tag)
            for tag in ("html", "head", "body")
            if re.search(r"<\s*{}\b".format(tag), content, re.IGNORECASE)
        ) or "aucune balise html/head/body"
        recent_suggestions = "\n".join(
            "- {}".format(item) for item in self._recent_inline_suggestions[-6:]
        ) or "Aucune"

        self._pending_completions = {}
        self._completion_expected = 2
        self._completion_received = 0

        def worker(variant_idx, temperature):
            try:
                variant_system = (
                    "Tu es un assistant de programmation inline rigoureux. Avant toute suggestion, inspecte "
                    "le code existant dans son ensemble, le contexte autour du curseur et les structures "
                    "deja declarees. N'ajoute que le code strictement necessaire a l'endroit du curseur. "
                    "N'enveloppe jamais un fragment dans une deuxieme page ou une structure parente deja "
                    "presente : si html, head ou body existent, ne propose ni ces balises ni leur contenu "
                    "global une seconde fois. Ne recree pas de document complet pour completer une liste, "
                    "un paragraphe, une regle CSS ou une fonction. Aide dans tout le fichier, pas seulement "
                    "dans un langage ou une balise : HTML, CSS, JavaScript, Python et les autres langages "
                    "indiques. Analyse les deux cotes du curseur et le code environnant. "
                    "Retourne uniquement du code, sans explication ni Markdown. Complete ou corrige "
                    "l'intention de l'utilisateur avec une proposition utile et coherente. Analyse les "
                    "syntaxes incompletes et les structures deja presentes. "
                    "Apres une balise HTML ouverte comme <p>, propose une ligne complete et utile. "
                    "Apres un selecteur CSS ou une declaration incomplete, propose une regle exploitable; "
                    "dans JavaScript, Python et les autres langages, complete l'expression ou le bloc. "
                    "Si le mode demande de remplacer la ligne, retourne la ligne corrigee complete en "
                    "preservant l'indentation et ce que l'utilisateur a deja ecrit. Sinon, retourne "
                    "uniquement le suffixe a inserer au curseur. Ne repete pas du code existant. "
                    "REGLE OBLIGATOIRE : ecris toujours les caracteres en brut UTF-8 (apostrophe ', accent e/è/é, etc.). "
                    "N'utilise JAMAIS d'entites HTML (&#39;, &amp;, &eacute;, &egrave;, &ecirc;, &quot;, &lt;, &gt; ...). "
                    "Variante {}: propose une approche differente mais valide pour le même contexte."
                ).format(variant_idx + 1)
                response = ollama.chat(
                    model=model,
                    messages=[
                        {"role": "system", "content": variant_system},
                        {
                            "role": "user",
                            "content": (
                                "Langage : {}\nFichier : {}\nMode : {}\nLigne actuelle complete :\n{}\n"
                                "Code avant curseur :\n{}\n\nCode apres curseur :\n{}\n\n"
                                "Contexte du fichier :\n{}\n\n"
                                "Balises globales deja presentes : {}\n"
                                "Regle obligatoire : n'inclus pas ces balises dans la suggestion. "
                                "En mode remplacement, reecris la ligne complete et utile; en mode completion, "
                                "renvoie seulement le suffixe necessaire a la position du curseur.\n\n"
                                "Suggestions de texte deja acceptees recemment (ne pas repeter leur formulation) :\n{}"
                            ).format(
                                language,
                                file_name,
                                "remplacer la ligne incomplete ({})".format(replacement_mode)
                                if replace_line else "completer au curseur",
                                current_line,
                                prefix,
                                suffix,
                                file_context,
                                existing_html_structure,
                                recent_suggestions,
                            ),
                        },
                    ],
                    options={"temperature": temperature, "num_ctx": 8192, "num_predict": 160},
                )
                completion = response.get("message", {}).get("content", "")
                suggestion = completion.strip()
                if suggestion.startswith("```") and suggestion.endswith("```"):
                    suggestion = re.sub(r"^```[^\n]*\n|```$", "", suggestion).strip()
                if not suggestion or suggestion.startswith("```"):
                    suggestion = None
                else:
                    suggestion = self._filter_duplicate_completion(suggestion, content)
                    if not suggestion:
                        suggestion = None
                    elif replace_line:
                        suggestion = self._normalize_inline_replacement(
                            suggestion, current_line, language, replacement_mode
                        )
            except Exception as error:
                suggestion = None
            self.after(0, lambda g=generation, v=variant_idx, s=suggestion: self._on_one_completion(g, v, s, before_cursor, replacement_range))

        for i in range(2):
            threading.Thread(target=worker, args=(i, 0.1 + 0.05 * i), daemon=True).start()

    def _on_one_completion(self, generation, variant_idx, suggestion, before_cursor, replacement_range):
        if generation != self._completion_generation - 1:
            return
        if suggestion:
            suggestion = self._sanitize_suggestion(suggestion)
            self._pending_completions[variant_idx] = suggestion
        self._completion_received += 1
        if self._completion_received >= self._completion_expected:
            self._show_multi_completions(before_cursor, replacement_range)

    def _show_multi_completions(self, before_cursor, replacement_range):
        self._dismiss_multi_popup()
        if not self._pending_completions:
            return
        popup = tk.Toplevel(self)
        popup.wm_overrideredirect(True)
        popup.configure(bg="#1f2937")
        popup.attributes("-topmost", True)
        self._multi_completion_popup = popup

        header = tk.Label(popup, text="Choisissez une suggestion :", bg="#374151", fg="#ffffff",
                          font=("Consolas", 10, "bold"), padx=8, pady=6, anchor="w")
        header.pack(fill="x")

        list_frame = tk.Frame(popup, bg="#1f2937")
        list_frame.pack(fill="both", expand=True)

        canvas = tk.Canvas(list_frame, bg="#1f2937", highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, bg="#1f2937")

        scrollable.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        ordered = sorted(self._pending_completions.items())
        self._multi_options = ordered

        def make_inserter(suggestion, repl_range):
            def insert_one():
                self._insert_selected_completion(suggestion, repl_range, before_cursor)
                self._dismiss_multi_popup()
            return insert_one

        for idx, (variant, suggestion) in enumerate(ordered):
            row = tk.Frame(scrollable, bg="#1f2937")
            row.pack(fill="x", padx=4, pady=2)
            num_lbl = tk.Label(row, text="Option {}".format(variant + 1), bg="#374151", fg="#a1a1aa",
                               font=("Consolas", 9, "bold"), padx=6, pady=2, width=14, anchor="w")
            num_lbl.pack(side="left")
            preview = suggestion.replace("\n", " \\ ")
            if len(preview) > 70:
                preview = preview[:70] + "..."
            btn = tk.Button(row, text=preview, bg="#374151", fg="#d1d5db",
                            font=("Consolas", 10), bd=0, padx=6, pady=4, anchor="w",
                            cursor="hand2", relief="flat",
                            command=make_inserter(suggestion, replacement_range))
            btn.pack(side="left", fill="x", expand=True)

        footer = tk.Frame(popup, bg="#1f2937")
        footer.pack(fill="x")
        tk.Button(footer, text="Fermer (Echap)", bg="#4b5563", fg="#ffffff",
                  font=("Consolas", 10), bd=0, padx=8, pady=4,
                  command=self._dismiss_multi_popup).pack(side="right", padx=6, pady=4)
        popup.bind("<Escape>", lambda e: self._dismiss_multi_popup())

        text_widget = self._text_widget()
        cursor_box = text_widget.bbox("insert")
        if cursor_box:
            x, y, _, line_height = cursor_box
            # Coordinates du curseur en coordonnées écran (fiables pour un Toplevel)
            sx = text_widget.winfo_rootx() + x
            sy = text_widget.winfo_rooty() + y + line_height
            widget_width = max(1, text_widget.winfo_width())
            popup_width = min(560, max(300, widget_width - 20))
            popup.update_idletasks()
            popup_height = popup.winfo_reqheight()
            screen_w = popup.winfo_screenwidth()
            screen_h = popup.winfo_screenheight()
            sx = min(max(4, sx), max(4, screen_w - popup_width - 4))
            if sy + popup_height > screen_h:
                sy = max(4, text_widget.winfo_rooty() + y - popup_height)
            popup.geometry("+{}+{}".format(sx, sy))

    def _dismiss_multi_popup(self):
        if self._multi_completion_popup is not None:
            try:
                self._multi_completion_popup.destroy()
            except Exception:
                pass
            self._multi_completion_popup = None
        self._multi_options = []
        try:
            self.editor.unbind_all("<MouseWheel>")
        except Exception:
            pass

    def _insert_selected_completion(self, suggestion, replacement_range, before_cursor):
        if not suggestion:
            return
        text_widget = self._text_widget()
        if text_widget.get("1.0", "insert") != before_cursor:
            return
        normalized = " ".join(suggestion.split())
        if normalized:
            self._recent_inline_suggestions.append(normalized)
            self._recent_inline_suggestions = self._recent_inline_suggestions[-8:]
        if replacement_range:
            text_widget.delete(*replacement_range)
            text_widget.insert(replacement_range[0], suggestion)
            text_widget.mark_set(
                "insert", "{} + {} chars".format(replacement_range[0], len(suggestion))
            )
        else:
            self.editor.insert("insert", suggestion)
        self.on_key_release()

    def _show_completion_error(self, generation, message):
        if generation == self._completion_generation - 1:
            self.status_var.set("Complétion inline indisponible : {}".format(message))

    @staticmethod
    def _sanitize_suggestion(suggestion):
        """Decode les entites HTML (&#39;, &amp;, &eacute; ...) en caracteres bruts UTF-8."""
        if not suggestion:
            return suggestion
        cleaned = html.unescape(suggestion)
        # Collapse any leftover numeric/named entities html.unescape missed
        cleaned = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))) if int(m.group(1)) < 0x110000 else m.group(0), cleaned)
        cleaned = re.sub(r"&#x([0-9a-fA-F]+);", lambda m: chr(int(m.group(1), 16)) if int(m.group(1), 16) < 0x110000 else m.group(0), cleaned)
        return cleaned

    @staticmethod
    def _normalize_inline_replacement(suggestion, current_line, language, replacement_mode):
        original = current_line.strip()
        result = suggestion.strip()
        if language == "html":
            closing = re.fullmatch(r"</\s*([A-Za-z][\w:-]*)\s*>", result)
            if closing:
                tag = closing.group(1)
                opening = re.search(
                    r"<\s*{}\b[^>]*>".format(re.escape(tag)), original, re.IGNORECASE
                )
                if opening:
                    result = original + closing.group(0) if original[opening.end():].strip() else (
                        opening.group(0) + closing.group(0)
                    )
                elif original.lower() == tag.lower():
                    result = "<{}></{}>".format(tag, tag)
            elif re.fullmatch(r"<\s*([A-Za-z][\w:-]*)\b[^>]*>", result):
                opening = re.fullmatch(r"<\s*([A-Za-z][\w:-]*)\b[^>]*>", result)
                if opening and not re.search(
                    r"</\s*{}\s*>".format(re.escape(opening.group(1))), result, re.IGNORECASE
                ):
                    result += "</{}>".format(opening.group(1))
        elif replacement_mode.startswith("terminer l'expression") and original:
            if not result.startswith(original) and re.search(
                r"(?:=|=>|\+|-|\*|/|%|\.|,|:|&&|\|\||\?\?|->|:=|\(|\[)\s*$",
                original,
            ):
                separator = "" if original.endswith(("(", "[", ".", "->")) else " "
                result = original + separator + result

        indentation = re.match(r"^[ \t]*", current_line).group(0)
        if indentation and result and not result.startswith(indentation):
            result = indentation + result
        return result

    @staticmethod
    def _inline_completion_replacement_mode(language, current_line, content, line_suffix):
        if line_suffix.strip():
            return None
        line = current_line.strip()
        if not line:
            return None

        if language == "html":
            if line.lower() in KEYWORDS["html"]:
                return "completer l'abreviation HTML {} en element complet".format(line.lower())
            if re.search(r"<\s*[A-Za-z][\w:-]*(?:\s[^<>]*)?$", line):
                return "terminer une balise HTML commencee"
            void_tags = {
                "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
                "meta", "param", "source", "track", "wbr",
            }
            for match in re.finditer(r"<\s*([A-Za-z][\w:-]*)\b[^>]*>", line):
                tag = match.group(1).lower()
                if tag in void_tags or match.group(0).rstrip().endswith("/>"):
                    continue
                opening_count = len(re.findall(
                    r"<\s*{}\b[^>]*>".format(re.escape(tag)), content, re.IGNORECASE
                ))
                closing_count = len(re.findall(
                    r"</\s*{}\s*>".format(re.escape(tag)), content, re.IGNORECASE
                ))
                if opening_count > closing_count:
                    return "completer la balise <{}> sans ajouter seulement sa fermeture".format(tag)
            return None

        if language == "css":
            if line.startswith((".", "#", ":", "*", "[")) and "{" not in line:
                return "completer le selecteur CSS en une regle exploitable"
            if re.match(r"^[A-Za-z][\w-]*(?:[\s>+~:#.\[\]=\"'-].*)?$", line) and (
                "{" not in line and not re.match(r"^[\w-]+\s*:", line)
            ):
                return "completer le selecteur CSS en une regle exploitable"
            if re.match(r"^[\w-]+\s*:\s*[^;{}]*$", line) and not line.endswith(";"):
                return "terminer la declaration CSS"

        if language == "python" and re.match(
            r"^(?:def|class|if|elif|else|for|while|try|except|finally|with|async|match|case)\b",
            line,
        ):
            if not line.endswith(":") or line in ("try", "else", "finally"):
                return "completer le bloc Python"

        if re.search(
            r"(?:=|=>|\+|-|\*|/|%|\.|,|:|&&|\|\||\?\?|->|:=|\bis|\bin|\band|\bor|\bnot|\bas|\bawait|\breturn|\byield|\braise)\s*$",
            line,
        ):
            return "terminer l'expression ou l'instruction incomplete"
        if line.count("(") > line.count(")") or line.count("[") > line.count("]"):
            return "terminer l'expression ou l'instruction incomplete"
        return None

    @staticmethod
    def _filter_duplicate_completion(suggestion, existing_content):
        for tag in ("html", "head", "body"):
            if not re.search(r"<\s*{}\b".format(tag), existing_content, re.IGNORECASE):
                continue
            suggestion = re.sub(
                r"</?\s*{}\b[^>]*>".format(tag),
                "",
                suggestion,
                flags=re.IGNORECASE,
            )
        if re.search(r"<!doctype\s+html\b", existing_content, re.IGNORECASE):
            suggestion = re.sub(
                r"<!doctype\s+html\b[^>]*>",
                "",
                suggestion,
                flags=re.IGNORECASE,
            )
        suggestion = suggestion.strip()
        if len(suggestion) >= 32:
            normalized_suggestion = re.sub(r"\s+", " ", suggestion).strip().casefold()
            normalized_existing = re.sub(r"\s+", " ", existing_content).casefold()
            if normalized_suggestion in normalized_existing:
                return ""
        return suggestion

    def _reject_inline_completion_key(self, event=None):
        self._dismiss_multi_popup()
        self._invalidate_inline_completion()
        return "break"

    def _schedule_autosave(self):
        if self._autosave_job:
            try:
                self.after_cancel(self._autosave_job)
            except Exception:
                pass
        self._autosave_job = self.after(30000, self._auto_save)

    def _auto_save(self):
        if not self.current_file or not self.unsaved:
            return
        try:
            self.current_file.parent.mkdir(parents=True, exist_ok=True)
            content = self.editor.get("1.0", "end-1c")
            ext = self.current_file.suffix.lower()
            lang = LANG_EXTENSIONS.get(ext, "text")
            content = self._format_content(content, lang)
            self.current_file.write_text(content, encoding="utf-8")
            self._file_buffers[self.current_file.resolve()] = content
            self.editor.delete("1.0", "end")
            self.editor.insert("1.0", content)
            self.unsaved = False
            self.file_name_label.configure(text=self.current_file.name)
            self.status_var.set("Auto-save (formate) : {}".format(self.current_file.name))
            self._update_preview()
            self.auto_version()
            self._save_session()
        except Exception as e:
            print("Erreur auto-save:", e)

    def toggle_autosave(self):
        self.autosave_enabled = not self.autosave_enabled
        etat = "ON" if self.autosave_enabled else "OFF"
        self.status_var.set("Auto-save : {}".format(etat))
        # Mettre a jour l'affichage du bouton (reconstruit simplement le texte via status)

    def restore_from_disk(self):
        if not self.current_file or not self.current_file.exists():
            messagebox.showwarning("Restaurer", "Aucun fichier a restaurer.")
            return
        try:
            content = self.current_file.read_text(encoding="utf-8")
            self.editor.delete("1.0", "end")
            self.editor.insert("1.0", content)
            self.unsaved = False
            self.file_name_label.configure(text=self.current_file.name)
            self.status_var.set("Restaure depuis le disque : {}".format(self.current_file.name))
            self._schedule_highlight()
            self._schedule_preview()
        except Exception as e:
            messagebox.showerror("Erreur restauration", str(e))

    def on_tab(self, event=None):
        self._dismiss_multi_popup()
        self.editor.insert("insert", "    ")
        return "break"

    def on_editor_return(self, event=None):
        text_widget = self._text_widget()
        if text_widget.tag_ranges("sel"):
            text_widget.delete("sel.first", "sel.last")

        line_start = text_widget.index("insert linestart")
        line_end = text_widget.index("insert lineend")
        current_line = text_widget.get(line_start, line_end)
        before_cursor = text_widget.get(line_start, "insert")
        after_cursor = text_widget.get("insert", line_end)
        indent = self._automatic_indentation(
            current_line,
            before_cursor,
            after_cursor,
            LANG_EXTENSIONS.get(self.current_file.suffix.lower(), "text")
            if self.current_file else "text",
        )
        text_widget.insert("insert", "\n" + indent)
        self.on_key_release()
        return "break"

    @staticmethod
    def _automatic_indentation(current_line, before_cursor, after_cursor, language):
        indentation = re.match(r"^[ \t]*", current_line).group(0)
        unit = "\t" if "\t" in indentation else "    "
        stripped_before = before_cursor.rstrip()
        stripped_after = after_cursor.lstrip()
        if (
            language == "html"
            and re.match(r"^</\s*[A-Za-z][\w:-]*\s*>", stripped_after) is not None
        ):
            return indentation
        dedent_before = (
            re.match(r"^[}\])]", stripped_after) is not None
            or re.fullmatch(r"[}\]]\s*;?", stripped_before.strip()) is not None
            or (
                language == "python"
                and re.match(r"^(?:elif|else|except|finally|case)\b", stripped_after) is not None
            )
        )
        if dedent_before:
            return indentation[:-1] if indentation.endswith("\t") else indentation[:-4]

        opens_block = stripped_before.endswith(("{", "[", "("))
        if language == "python":
            code_before_comment = stripped_before.split("#", 1)[0].rstrip()
            opens_block = opens_block or (
                code_before_comment.endswith(":")
                and re.match(
                    r"^(?:async\s+)?(?:def|class|if|elif|else|for|while|try|except|finally|with|match|case)\b",
                    code_before_comment.lstrip(),
                ) is not None
            )
        elif language == "html":
            void_tags = {
                "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
                "meta", "param", "source", "track", "wbr",
            }
            opening_tags = list(re.finditer(r"<\s*([A-Za-z][\w:-]*)\b[^>]*>", stripped_before))
            opening_tag = re.search(r"<\s*([A-Za-z][\w:-]*)\b[^>]*>\s*$", stripped_before)
            if opening_tag:
                tag_name = opening_tag.group(1).lower()
                opens_block = (
                    tag_name not in void_tags
                    and not opening_tag.group(0).rstrip().endswith("/>")
                )
        if opens_block:
            return indentation + unit
        return indentation

    def _schedule_highlight(self):
        if self._highlight_job:
            try:
                self.after_cancel(self._highlight_job)
            except Exception:
                pass
        self._highlight_job = self.after(700, self._do_highlight)

    def _do_highlight(self):
        if not self.current_file:
            return
        lang = LANG_EXTENSIONS.get(self.current_file.suffix.lower(), "text")
        self.apply_syntax_highlighting(lang)

    def _schedule_preview(self):
        if self._preview_job:
            try:
                self.after_cancel(self._preview_job)
            except Exception:
                pass
        if self.current_file and self.current_file.suffix.lower() in (".html", ".css", ".js"):
            self._preview_job = self.after(500, self._update_preview)

    def _check_emmet(self):
        if not self.current_file:
            return
        if self.current_file.suffix.lower() != ".html":
            return
        content = self.editor.get("1.0", "end-1c")
        if content.strip() == "!":
            self.editor.delete("1.0", "end")
            content, stylesheet_path = self._prepare_html_stylesheet(
                self.current_file,
                HTML_BOILERPLATE,
                managed_only=True,
            )
            self.editor.insert("1.0", content)
            if not stylesheet_path.exists():
                stylesheet_path.write_text(CSS_BOILERPLATE, encoding="utf-8")
                self._register_managed_file(stylesheet_path)
            self.status_var.set("Structure HTML insérée (!)")
            self._schedule_highlight()
            self._schedule_preview()

    def format_code(self):
        if not self.current_file:
            messagebox.showwarning("Formater", "Ouvrez un fichier d'abord.")
            return
        content = self.editor.get("1.0", "end-1c")
        if not content.strip():
            return
        ext = self.current_file.suffix.lower()
        lang = LANG_EXTENSIONS.get(ext, "text")
        try:
            formatted = self._format_content(content, lang)
            self.editor.delete("1.0", "end")
            self.editor.insert("1.0", formatted)
            self.unsaved = True
            self.file_name_label.configure(text=self.current_file.name + " ●")
            self.status_var.set("Code formate : {}".format(lang))
            self._schedule_highlight()
            self._schedule_preview()
        except Exception as e:
            messagebox.showerror("Erreur formatage", str(e))

    def _format_content(self, content, lang):
        if lang == "python":
            return self._format_python(content)
        if lang in ("html",):
            return self._format_html(content)
        if lang in ("css",):
            return self._format_css(content)
        if lang in ("javascript", "typescript", "js", "ts", "cpp", "c", "java", "go", "rust", "php"):
            return self._format_braces(content)
        return content

    def _format_python(self, content):
        lines = content.splitlines()
        out = []
        indent = 0
        for line in lines:
            stripped = line.strip()
            if not stripped:
                out.append("")
                continue
            if stripped.startswith(("return ", "break", "continue", "raise ", "pass", "yield ")) or stripped in ("return", "break", "continue", "pass"):
                out.append("    " * indent + stripped)
                continue
            # Diminuer l'indentation avant certains mots
            if stripped.startswith(("return ", "break", "continue", "raise ", "pass", "else:", "elif ", "except", "finally:")):
                indent = max(0, indent - 1)
            out.append("    " * indent + stripped)
            if stripped.endswith(":") and not stripped.startswith("#"):
                indent += 1
        return "\n".join(out)

    def _format_html(self, content):
        # Formateur HTML simple basé sur l'indentation des balises
        lines = content.splitlines()
        out = []
        indent = 0
        self_closing = {"br", "hr", "img", "input", "meta", "link", "area", "base", "col", "embed", "source", "track", "wbr"}
        block_close = {"html", "head", "body", "div", "p", "ul", "ol", "li", "table", "tr", "td", "th", "thead", "tbody", "tfoot", "section", "article", "header", "footer", "nav", "aside", "main", "form", "fieldset", "dl", "dt", "dd", "figure", "figcaption", "blockquote", "pre", "code", "details", "summary", "menu"}
        for raw in lines:
            line = raw.strip()
            if not line:
                out.append("")
                continue
            # Balises de fermeture -> diminuer l'indentation avant d'afficher
            mclose = re.match(r"</(\w+)", line)
            if mclose:
                tag = mclose.group(1).lower()
                if tag in block_close:
                    indent = max(0, indent - 1)
            out.append("    " * indent + line)
            # Balises d'ouverture -> augmenter l'indentation après
            mopen = re.findall(r"<(\w+)([^>]*)>", line)
            for tag, attrs in mopen:
                tag = tag.lower()
                if tag in block_close and not line.rstrip().endswith("</{}>".format(tag)):
                    indent += 1
            # Balises auto-fermantes ou fermées sur la meme ligne ne font rien de plus
        return "\n".join(out)

    def _format_css(self, content):
        lines = content.splitlines()
        out = []
        indent = 0
        for raw in lines:
            line = raw.strip()
            if not line:
                out.append("")
                continue
            if line.startswith("}"):
                indent = max(0, indent - 1)
            out.append("    " * indent + line)
            if line.endswith("{"):
                indent += 1
        return "\n".join(out)

    def _format_braces(self, content):
        lines = content.splitlines()
        out = []
        indent = 0
        for raw in lines:
            line = raw.strip()
            if not line:
                out.append("")
                continue
            if line.startswith("}") or line.startswith(")"):
                indent = max(0, indent - 1)
            out.append("    " * indent + line)
            if line.endswith("{") or line.endswith("(") or line.endswith("["):
                indent += 1
        return "\n".join(out)

    # ---------- Coloration syntaxique ----------

    def apply_syntax_highlighting(self, lang=None):
        tw = self._text_widget()
        for tag in ("kw", "str", "comment", "func", "number", "tag", "attr", "bool"):
            try:
                tw.tag_delete(tag)
            except Exception:
                pass
        for tag, color in TAG_COLORS.items():
            try:
                tw.tag_config(tag, foreground=color)
            except Exception:
                pass

        content = self.editor.get("1.0", "end-1c")
        if not content:
            return

        def add_matches(pattern, tag):
            for m in re.finditer(pattern, content, re.MULTILINE):
                start = "1.0 + {} chars".format(m.start())
                end = "1.0 + {} chars".format(m.end())
                try:
                    tw.tag_add(tag, start, end)
                except Exception:
                    pass

        if lang in KEYWORDS:
            kw_regex = r"\b(" + "|".join(re.escape(k) for k in KEYWORDS[lang]) + r")\b"
            add_matches(kw_regex, "kw")

        add_matches(r'"(?:[^"\\]|\\.)*"', "str")
        add_matches(r"'(?:[^'\\]|\\.)*'", "str")

        if lang in ("python", "ruby", "shell", "yaml"):
            add_matches(r"#.*$", "comment")
        if lang in ("javascript", "css", "cpp", "c", "java", "go", "rust", "ts", "php"):
            add_matches(r"//.*$", "comment")
            add_matches(r"/\*.*?\*/", "comment")

        add_matches(r"\b\d+(?:\.\d+)?\b", "number")

        if lang == "html":
            add_matches(r"<[^>]+>", "tag")
            add_matches(r"\b([a-zA-Z-]+)=(\"[^\"]*\"|'[^']*')", "attr")

    def open_color_settings(self):
        win = ctk.CTkToplevel(self.winfo_toplevel())
        win.title("Couleurs du code - Calisto")
        win.geometry("500x540")
        win.configure(fg_color=BG_PANEL)
        win.transient(self.winfo_toplevel())
        win.grab_set()

        ctk.CTkLabel(win, text="🎨 Personnaliser les couleurs de code", font=ctk.CTkFont(size=14, weight="bold"), text_color=ACCENT).pack(pady=15)

        entries = {}
        for tag, label in [("kw", "Mots-clés"), ("str", "Chaînes"), ("comment", "Commentaires"), ("func", "Fonctions"), ("number", "Nombres"), ("tag", "Balises HTML"), ("attr", "Attributs"), ("bool", "Booléens")]:
            row = ctk.CTkFrame(win, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=6)
            ctk.CTkLabel(row, text=label, width=130, font=ctk.CTkFont(size=12), text_color=TEXT_MAIN).pack(side="left")
            var = ctk.StringVar(value=TAG_COLORS.get(tag, "#ffffff"))
            ent = ctk.CTkEntry(row, textvariable=var, width=120, fg_color=BG_EDITOR, border_color="#4b4c54", text_color=TEXT_MAIN)
            ent.pack(side="left", padx=5)

            def pick(t=tag, v=var):
                col = colorchooser.askcolor(color=v.get(), title="Choisir couleur pour " + t)
                if col and col[1]:
                    v.set(col[1])
            ctk.CTkButton(row, text="🎨", width=30, command=pick, fg_color="#3a3a3e", hover_color="#4a4a4e").pack(side="left", padx=4)
            entries[tag] = var

        def save_colors():
            for tag, var in entries.items():
                TAG_COLORS[tag] = var.get()
            self._do_highlight()
            win.destroy()

        ctk.CTkButton(win, text="Enregistrer", command=save_colors, fg_color=ACCENT, hover_color=ACCENT_HOVER, font=ctk.CTkFont(size=12, weight="bold")).pack(pady=15)
        ctk.CTkButton(win, text="Réinitialiser", command=lambda: self._reset_colors(entries), fg_color="#6b7280", hover_color="#4b5563").pack(pady=(0, 20))

    def _reset_colors(self, entries):
        global TAG_COLORS
        TAG_COLORS = dict(DEFAULT_TAG_COLORS)
        for tag, variable in entries.items():
            variable.set(TAG_COLORS[tag])
        self._do_highlight()


    # ---------- Prévisualisation instantanée ----------

    def _build_preview_html(self):
        if not self.current_file:
            return "<html><body><p>Ouvrez un fichier HTML, CSS ou JavaScript pour afficher l'aperçu du projet.</p></body></html>"

        extension = self.current_file.suffix.lower()
        html_file = self.current_file
        if extension == ".html":
            content = self.editor.get("1.0", "end-1c").lstrip("\ufeff")
        elif extension in (".css", ".js") and self.current_folder:
            html_files = sorted(
                path for path in self.current_folder.rglob("*.html")
                if not any(part in {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build"} for part in path.parts)
            )
            html_file = next(
                (path for path in html_files if path.name.lower() == "index.html"),
                html_files[0] if html_files else None,
            )
            if not html_file:
                return "<html><body><p>Créez un fichier HTML dans ce dossier pour prévisualiser ce projet.</p></body></html>"
            try:
                content = self._read_project_file(html_file)
            except (OSError, UnicodeError) as error:
                raise RuntimeError("Impossible de lire la page HTML du projet : {}".format(error))
            code = self.editor.get("1.0", "end-1c").lstrip("\ufeff")
            if extension == ".css":
                self._file_buffers[self.current_file.resolve()] = code
            else:
                script = "<script>\n{}\n</script>".format(code)
                script_pattern = re.compile(
                    r"<script\b(?=[^>]*\bsrc\s*=\s*(['\"])(.*?)\1)[^>]*>\s*</script\s*>",
                    re.IGNORECASE | re.DOTALL,
                )

                def replace_active_script(match):
                    source = urlparse(match.group(2)).path
                    return script if Path(source).name.lower() == self.current_file.name.lower() else match.group(0)

                content, replaced = script_pattern.subn(replace_active_script, content)
                if not replaced:
                    if re.search(r"</body\s*>", content, re.IGNORECASE):
                        content = re.sub(r"</body\s*>", script + "\n</body>", content, count=1, flags=re.IGNORECASE)
                    else:
                        content += "\n" + script
        else:
            return "<html><body><p>La prévisualisation est disponible pour les fichiers HTML, CSS et JavaScript.</p></body></html>"

        if html_file:
            link_pattern = re.compile(r"<link\b[^>]*>", re.IGNORECASE)
            linked_stylesheets = set()

            def inline_stylesheet(match):
                tag = match.group(0)
                rel_match = re.search(r"\brel\s*=\s*(?:(['\"])(.*?)\1|([^\s>]+))", tag, re.IGNORECASE)
                href_match = re.search(r"\bhref\s*=\s*(?:(['\"])(.*?)\1|([^\s>]+))", tag, re.IGNORECASE)
                rel = (rel_match.group(2) or rel_match.group(3)) if rel_match else ""
                href = (href_match.group(2) or href_match.group(3)) if href_match else ""
                if not rel_match or "stylesheet" not in rel.lower().split() or not href_match:
                    return tag

                url = urlparse(href.strip())
                if url.scheme or url.netloc or not url.path:
                    return tag
                stylesheet_path = self._resolve_local_project_path(html_file, href, self.current_folder)
                if stylesheet_path is None:
                    return tag
                if not stylesheet_path.is_file() or stylesheet_path.suffix.lower() != ".css":
                    return tag
                try:
                    stylesheet = self._read_project_file(stylesheet_path)
                except (OSError, UnicodeError) as error:
                    raise RuntimeError("Impossible de charger la feuille CSS {} : {}".format(stylesheet_path.name, error))
                stylesheet = self._resolve_css_asset_urls(
                    stylesheet,
                    stylesheet_path.parent,
                    self.current_folder,
                )
                linked_stylesheets.add(stylesheet_path)
                return "<style>\n{}\n</style>".format(stylesheet)

            content = link_pattern.sub(inline_stylesheet, content)

            if extension == ".css" and self.current_file.resolve() not in linked_stylesheets:
                stylesheet = self._resolve_css_asset_urls(
                    self.editor.get("1.0", "end-1c"),
                    self.current_file.parent,
                    self.current_folder,
                )
                style = "<style>\n{}\n</style>".format(stylesheet)
                if re.search(r"</head\s*>", content, re.IGNORECASE):
                    content = re.sub(r"</head\s*>", style + "\n</head>", content, count=1, flags=re.IGNORECASE)
                else:
                    content = style + "\n" + content
            elif extension in (".html", ".htm") and not linked_stylesheets:
                content, stylesheet_path = self._prepare_html_stylesheet(html_file, content)
                if stylesheet_path.is_file():
                    stylesheet = self._resolve_css_asset_urls(
                        self._read_project_file(stylesheet_path),
                        stylesheet_path.parent,
                        self.current_folder,
                    )
                    style = "<style>\n{}\n</style>".format(stylesheet)
                    if re.search(r"</head\s*>", content, re.IGNORECASE):
                        content = re.sub(r"</head\s*>", style + "\n</head>", content, count=1, flags=re.IGNORECASE)
                    else:
                        content = style + "\n" + content
        return content

    def _read_project_file(self, path):
        resolved = path.resolve()
        if resolved in self._file_buffers:
            return self._file_buffers[resolved].lstrip("\ufeff")
        return resolved.read_text(encoding="utf-8-sig")

    @staticmethod
    def _resolve_local_project_path(base_file, reference, project_root=None):
        parsed = urlparse(reference.strip())
        if parsed.scheme or parsed.netloc or not parsed.path:
            return None
        asset_path = unquote(parsed.path).replace("\\", "/")
        if asset_path.startswith("/") and project_root:
            return (Path(project_root) / asset_path.lstrip("/")).resolve()
        return (Path(base_file).parent / asset_path.lstrip("/")).resolve()

    def _prepare_html_stylesheet(self, html_path, html, managed_only=False):
        html_path = Path(html_path).resolve()
        css_candidates = []
        for tag in re.findall(r"<link\b[^>]*>", html, re.IGNORECASE):
            rel_match = re.search(r"\brel\s*=\s*(?:(['\"])(.*?)\1|([^\s>]+))", tag, re.IGNORECASE)
            href_match = re.search(r"\bhref\s*=\s*(?:(['\"])(.*?)\1|([^\s>]+))", tag, re.IGNORECASE)
            rel = (rel_match.group(2) or rel_match.group(3)) if rel_match else ""
            href = (href_match.group(2) or href_match.group(3)) if href_match else ""
            if not rel_match or "stylesheet" not in rel.lower().split() or not href_match:
                continue
            parsed = urlparse(href.strip())
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            candidate = self._resolve_local_project_path(html_path, href, self.current_folder)
            if candidate is None:
                continue
            if (
                candidate.suffix.lower() == ".css"
                and candidate.is_file()
                and (not managed_only or self._is_managed_file(candidate))
            ):
                css_candidates.append(candidate)

        if css_candidates:
            stylesheet_path = css_candidates[0]
        else:
            existing_css = sorted(
                path.resolve()
                for path in html_path.parent.glob("*.css")
                if path.is_file()
                and (not managed_only or self._is_managed_file(path))
            )
            preferred_names = ("style.css", "styles.css", "main.css")
            stylesheet_path = next(
                (path for name in preferred_names for path in existing_css if path.name.lower() == name),
                existing_css[0] if len(existing_css) == 1 else None,
            )
            if stylesheet_path is None and self.current_folder:
                ignored_directories = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build"}
                project_css = sorted(
                    path.resolve()
                    for path in self.current_folder.rglob("*.css")
                    if path.is_file()
                    and not any(part in ignored_directories for part in path.relative_to(self.current_folder).parts)
                    and (not managed_only or self._is_managed_file(path))
                )
                stylesheet_path = next(
                    (path for name in preferred_names for path in project_css if path.name.lower() == name),
                    project_css[0] if len(project_css) == 1 else html_path.parent / "style.css",
                )
            elif stylesheet_path is None:
                stylesheet_path = html_path.parent / "style.css"
            if managed_only and stylesheet_path.exists() and not self._is_managed_file(stylesheet_path):
                stylesheet_path = html_path.parent / "style-2.css"
                suffix = 3
                while stylesheet_path.exists() and not self._is_managed_file(stylesheet_path):
                    stylesheet_path = html_path.parent / "style-{}.css".format(suffix)
                    suffix += 1

        return self._link_stylesheet(html, stylesheet_path, html_path, self.current_folder), stylesheet_path

    @staticmethod
    def _resolve_css_asset_urls(stylesheet, base_folder, project_root=None):
        url_pattern = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.IGNORECASE)

        def resolve_url(match):
            value = match.group(2).strip()
            parsed = urlparse(value)
            if not value or parsed.scheme or parsed.netloc or value.startswith("#"):
                return match.group(0)
            asset_url_path = unquote(parsed.path).replace("\\", "/")
            asset_folder = project_root if asset_url_path.startswith("/") and project_root else base_folder
            asset_path = (asset_folder / asset_url_path.lstrip("/")).resolve()
            if not asset_path.is_file():
                return match.group(0)
            asset_url = asset_path.as_uri()
            if parsed.query:
                asset_url += "?" + parsed.query
            if parsed.fragment:
                asset_url += "#" + parsed.fragment
            return 'url("{}")'.format(asset_url.replace('"', '\\"'))

        return url_pattern.sub(resolve_url, stylesheet)

    def _update_preview(self):
        try:
            content = self._build_preview_html()
            if HtmlFrame is not None:
                base_folder = self.current_folder or (
                    self.current_file.parent if self.current_file else Path.cwd()
                )
                preview_folder = self.current_file.parent if self.current_file and self.current_file.suffix.lower() == ".html" else base_folder
                self.preview.load_html(content, base_url=preview_folder.resolve().as_uri() + "/")
            else:
                self.preview.configure(state="normal")
                self.preview.delete("1.0", "end")
                self.preview.insert(
                    "1.0",
                    "L'aperçu rendu nécessite tkinterweb. Fermez Calisto puis relancez-le avec « Lancer IA.bat » pour installer cette dépendance.",
                )
                self.preview.configure(state="disabled")
        except Exception as error:
            self.status_var.set("Erreur de prévisualisation : {}".format(error))

    def preview_html(self):
        if not self.current_file:
            messagebox.showwarning("Aucun fichier", "Ouvrez un fichier HTML d'abord.")
            return
        if self.current_file.suffix.lower() not in (".html", ".css", ".js"):
            messagebox.showwarning("Aperçu indisponible", "La prévisualisation est disponible pour les fichiers HTML, CSS et JavaScript.")
            return
        self._update_preview()
        self.status_var.set("Aperçu du projet actualisé")

    def _find_browser_exe(self):
        """Cherche un navigateur web installé sur Windows pour eviter d'ouvrir Acrobat PDF."""
        candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Mozilla Firefox\firefox.exe",
            r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files\Opera\opera.exe",
            r"C:\Program Files (x86)\Opera\opera.exe",
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return None

    def preview_open_browser(self):
        if not self.current_file or self.current_file.suffix.lower() not in (".html", ".css", ".js"):
            messagebox.showwarning("Aperçu indisponible", "Ouvrez un fichier HTML, CSS ou JavaScript d'abord.")
            return
        content = self._build_preview_html()
        preview_file = self.current_file.parent / ("preview_" + self.current_file.name)
        try:
            preview_file.write_text(content, encoding="utf-8")
            url = preview_file.resolve().as_uri()
        except OSError as error:
            messagebox.showerror(
                "Erreur d'aperçu",
                "Impossible d'enregistrer la page de prévisualisation :\n{}".format(error),
            )
            return

        browser = self._find_browser_exe()
        if browser:
            try:
                subprocess.Popen([browser, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.status_var.set("Ouvert dans le navigateur web")
                return
            except Exception:
                pass
        # Dernier recours : webbrowser (peut ouvrir l'associe par defaut)
        try:
            if not webbrowser.open(url):
                raise RuntimeError("Le navigateur par défaut n'a pas pu ouvrir la page.")
            self.status_var.set("Ouvert dans le navigateur par défaut")
        except Exception as e:
            messagebox.showerror("Erreur", "Impossible d'ouvrir le navigateur :\n{}".format(e))

    # ---------- Sauvegarde fiable ----------

    def save_file(self):
        if not self.current_file:
            if not self.current_folder:
                messagebox.showwarning("Aucun dossier", "Ouvrez d'abord un dossier de projet.")
                return
            path = filedialog.asksaveasfilename(
                title="Enregistrer le fichier",
                initialdir=str(self.current_folder),
                defaultextension=".html",
                filetypes=[
                    ("Fichiers du projet", "*.html *.css *.js *.py *.json *.txt"),
                    ("Tous les fichiers", "*.*"),
                ],
            )
            if not path:
                return
            selected_path = Path(path).resolve()
            try:
                selected_path.relative_to(Path(self.current_folder).resolve())
            except ValueError:
                messagebox.showwarning("Dossier invalide", "Le fichier doit rester dans le dossier du projet.")
                return
            self.current_file = selected_path
            self.current_file.parent.mkdir(parents=True, exist_ok=True)
        self.selected_tree_item = self.current_file
        try:
            creating_file = not self.current_file.exists()
            # Créer le dossier parent si nécessaire
            self.current_file.parent.mkdir(parents=True, exist_ok=True)
            content = self.editor.get("1.0", "end-1c")
            ext = self.current_file.suffix.lower()
            stylesheet_path = None
            if ext in (".html", ".htm"):
                content, stylesheet_path = self._prepare_html_stylesheet(
                    self.current_file,
                    content,
                    managed_only=True,
                )
            lang = LANG_EXTENSIONS.get(ext, "text")
            content = self._format_content(content, lang)
            self.editor.delete("1.0", "end")
            self.editor.insert("1.0", content)
            self.current_file.write_text(content, encoding="utf-8")
            self._file_buffers[self.current_file.resolve()] = content
            if creating_file:
                self._register_managed_file(self.current_file)
            if stylesheet_path and not stylesheet_path.exists():
                stylesheet_path.write_text(CSS_BOILERPLATE, encoding="utf-8")
                self._register_managed_file(stylesheet_path)
            self.unsaved = False
            self.file_name_label.configure(text=self.current_file.name)
            self.status_var.set("Enregistre et formate : {}".format(self.current_file.name))
            self._refresh_tree()
            self._update_preview()
            self.auto_version()
            self._log_ia_action("sauvegarder", self.current_file.name)
            self._save_session()
        except Exception as e:
            messagebox.showerror("Erreur enregistrement", str(e))

    def auto_version(self):
        if not self.current_file or not self.current_folder:
            return
        projects_dir = Path("projects")
        projects_dir.mkdir(exist_ok=True)
        proj_name = self.current_folder.name
        proj_dir = projects_dir / proj_name
        proj_dir.mkdir(exist_ok=True)
        vers_dir = proj_dir / "versions"
        vers_dir.mkdir(exist_ok=True)
        version_name = "v_{}".format(time.strftime("%Y%m%d_%H%M%S"))
        data = {
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "desc": "Sauvegarde automatique",
            "files": {},
        }
        for f in Path(self.current_folder).rglob("*"):
            if f.is_file() and not f.name.startswith("."):
                try:
                    data["files"][str(f.relative_to(self.current_folder))] = f.read_text(encoding="utf-8")
                except Exception:
                    data["files"][str(f.relative_to(self.current_folder))] = "[binaire]"
        vers_path = vers_dir / (version_name + ".json")
        with open(vers_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if proj_name in self.versions:
            self.versions[proj_name].insert(0, {
                "name": version_name,
                "date": data["date"],
                "desc": data["desc"],
                "files": data["files"],
            })
        else:
            self.versions[proj_name] = [{
                "name": version_name,
                "date": data["date"],
                "desc": data["desc"],
                "files": data["files"],
            }]
        self._refresh_proj_menu()
        self.status_var.set("Version sauvegardée : {}".format(version_name))

    def load_project_version(self, selection):
        if selection == "Aucun" or selection not in self.versions:
            return
        vers_list = self.versions[selection]
        if not vers_list:
            return
        liste = "\n".join("- {} ({})".format(x["name"], x["date"]) for x in vers_list[:8])
        dlg = ctk.CTkInputDialog(text="Versions pour '{}' :\n{}\n\nNom de la version à charger :".format(selection, liste), title="Charger une version")
        choose = dlg.get_input()
        if not choose:
            return
        target = None
        for x in vers_list:
            if x["name"] == choose:
                target = x
                break
        if not target:
            messagebox.showwarning("Introuvable", "Version non trouvée.")
            return
        if not self.current_folder:
            self.current_folder = Path("projects") / selection
            self.current_folder.mkdir(parents=True, exist_ok=True)
        for rel, content in target["files"].items():
            fp = self.current_folder / rel
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(content, encoding="utf-8")
            self._register_managed_file(fp)
        self._refresh_tree()
        self.current_project = selection
        self.status_var.set("Version '{}' chargée pour '{}'".format(choose, selection))
        self._save_session()

    # ---------- Assistant IA (connecté et persistant) ----------

    def ia_key_handler(self, event=None):
        if event and (event.state & 0x4) and event.keysym.lower() == "return":
            self.ia_send()
            return "break"
        return None

    def ia_append(self, text):
        self.ia_chat.configure(state="normal")
        self.ia_chat.insert("end", text + "\n")
        self.ia_chat.see("end")
        self.ia_chat.configure(state="disabled")

    def ia_send(self, event=None):
        content = self.ia_entry.get("1.0", "end-1c").strip()
        if not content or content == "Demandez à l'IA... (Ctrl+Entrée pour envoyer)":
            return
        if not self.parent_app.begin_editor_exchange(content):
            messagebox.showinfo("IA occupee", "L'IA centrale traite deja une demande. Reessayez apres sa reponse.")
            return

        self.ia_entry.delete("1.0", "end")
        self.ia_append(">> {}".format(content))
        context_files = self.get_ai_context_files()
        truncation_notes = [
            line
            for name, details in context_files.items()
            if name.startswith("Projet de l'editeur : ")
            for line in details.splitlines()
            if "tronque" in line.lower()
        ]
        if truncation_notes:
            self.ia_append("⚠️ Contexte code incomplet : " + " ".join(truncation_notes))
        self.status_var.set("L'IA analyse les fichiers du projet et prépare une réponse...")

        def worker():
            try:
                texte = self.parent_app.ask_ai_central(content, context_files)
            except Exception as e:
                self.after(0, lambda error=str(e): self._handle_ia_error(error))
                return
            self.after(0, lambda: self._handle_ia_response(texte))
        threading.Thread(target=worker, daemon=True).start()
        return "break"

    def _handle_ia_response(self, texte):
        self.parent_app.finish_editor_exchange(response=texte)
        self.ia_append("IA : {}".format(texte))
        blocks = re.findall(r"```([^\n`]*)\n(.*?)```", texte, re.DOTALL)
        if not blocks:
            self.status_var.set(
                "Réponse reçue sans proposition. Demandez le code complet dans un bloc avec son fichier cible."
            )
            self._save_session()
            return
        unique_blocks = {}
        duplicate_count = 0
        for info, code in blocks:
            info = info.strip()
            lang_match = re.match(r"([^\s]+)", info)
            lang = lang_match.group(1).lower() if lang_match else "text"
            filename_match = re.search(r"(?:filename|file)=([^\s]+)", info, re.IGNORECASE)
            filename = filename_match.group(1).strip("\"'") if filename_match else None
            lang = self._detect_code_language(code, lang)
            target = self._resolve_proposal_target(lang, filename)

            if lang == "html":
                html_target = self._resolve_proposal_target("html", filename)
                if html_target is None:
                    html_target = self._new_ai_file_path("html", filename)
                target = html_target
            elif target is None:
                target = self._new_ai_file_path(lang, filename)

            identity = (
                lang,
                str(target.resolve()).casefold() if target else (filename or "").casefold(),
            )
            previous = unique_blocks.get(identity)
            if previous is None:
                unique_blocks[identity] = (code, lang, target)
            else:
                duplicate_count += 1
                if len(code.strip()) > len(previous[0].strip()):
                    unique_blocks[identity] = (code, lang, target)

        prepared_proposals = []
        for code, lang, target in unique_blocks.values():
            if lang == "html":
                code, inline_css = self._split_inline_css(code)
                if target:
                    code, css_target = self._prepare_html_stylesheet(
                        target,
                        code,
                        managed_only=True,
                    )
                else:
                    css_target = self._resolve_proposal_target("css")
                if inline_css:
                    if css_target:
                        prepared_proposals.append((inline_css, "css", css_target))
                    else:
                        self.ia_append("Aucune feuille CSS existante trouvée pour la proposition intégrée au HTML.")
                elif css_target and not css_target.exists():
                    prepared_proposals.append((CSS_BOILERPLATE, "css", css_target))

            prepared_proposals.append((code, lang, target))

        consolidated_proposals = {}
        for code, lang, target in prepared_proposals:
            identity = (
                lang,
                str(target.resolve()).casefold() if target else "",
            )
            previous = consolidated_proposals.get(identity)
            if previous is None:
                consolidated_proposals[identity] = (code, lang, target)
            else:
                duplicate_count += 1
                if len(code.strip()) > len(previous[0].strip()):
                    consolidated_proposals[identity] = (code, lang, target)

        if duplicate_count:
            self.ia_append(
                "{} bloc(s) redondant(s) pour le même fichier ignoré(s); une seule version, la plus complète, est conservée.".format(
                    duplicate_count
                )
            )
        created_files = []
        for code, lang, target in consolidated_proposals.values():
            if target and not target.exists():
                try:
                    created_files.append(self._create_ai_file(target, code, lang))
                except (OSError, ValueError) as error:
                    self.ia_append("Impossible de créer {} automatiquement : {}".format(target.name, error))
                    self._create_proposal(code, lang, None)
            else:
                self._create_proposal(code, lang, target)

        if created_files:
            self._refresh_tree()
            html_file = next(
                (path for path in created_files if path.suffix.lower() in (".html", ".htm")),
                created_files[0],
            )
            self.open_file(html_file)
            self.status_var.set(
                "Fichier(s) créé(s) automatiquement : {}".format(
                    ", ".join(path.name for path in created_files)
                )
            )
            self.ia_append(
                "Fichier(s) créé(s) automatiquement : {}".format(
                    ", ".join(str(path.relative_to(self.current_folder)) for path in created_files)
                )
            )
            self._save_session()

    def _handle_ia_error(self, error):
        self.parent_app.finish_editor_exchange(error=error)
        self.ia_append("Erreur IA : {}".format(error))
        self.status_var.set("Echec de la requete a l'IA centrale")
        self._save_session()

    def refactor_and_comment(self):
        if not self.editor.get("1.0", "end-1c").strip():
            messagebox.showwarning("Code vide", "Ouvrez ou saisissez du code avant de demander une refactorisation.")
            return
        self.ia_entry.delete("1.0", "end")
        self.ia_entry.insert(
            "1.0",
            "Refactorise le code ouvert pour ameliorer sa lisibilite sans changer son comportement. "
            "Ajoute des commentaires en francais uniquement pour expliquer les parties non evidentes. "
            "Presente le code complet dans un bloc Markdown avec le langage adapte. "
            "Ne modifie pas le fichier automatiquement.",
        )
        self.ia_send()

    @staticmethod
    def _detect_code_language(code, declared_language):
        aliases = {
            "js": "javascript",
            "jsx": "javascript",
            "ts": "typescript",
            "tsx": "typescript",
            "py": "python",
            "htm": "html",
        }
        language = aliases.get(declared_language.lower(), declared_language.lower())
        stripped = code.strip()
        if language in ("html", "xml") and not re.search(r"<(?:!doctype|/?[a-z][^>]*)\b", stripped, re.IGNORECASE):
            if re.search(r"(?:^|[;}])\s*(?:[.#][\w-]+|[a-z][\w-]*)\s*[,:{]", stripped, re.IGNORECASE) and "{" in stripped:
                return "css"
        if language == "text":
            if re.search(r"<(?:!doctype|html|head|body|div|main|section)\b", stripped, re.IGNORECASE):
                return "html"
            if re.search(r"(?:^|[;}])\s*(?:[.#][\w-]+|[a-z][\w-]*)\s*[,:{]", stripped, re.IGNORECASE) and "{" in stripped:
                return "css"
        return language

    @staticmethod
    def _split_inline_css(html):
        styles = []

        def remove_style(match):
            styles.append(match.group(1).strip())
            return ""

        html = re.sub(
            r"<style\b[^>]*>(.*?)</style\s*>",
            remove_style,
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        inline_index = 0

        def move_inline_style(match):
            nonlocal inline_index
            tag = match.group(0)
            style_match = re.search(
                r"\s+style\s*=\s*(['\"])(.*?)\1",
                tag,
                re.IGNORECASE | re.DOTALL,
            )
            if not style_match:
                return tag
            css = style_match.group(2).strip()
            if not css:
                return tag[:style_match.start()] + tag[style_match.end():]
            inline_index += 1
            class_name = "calisto-inline-{}".format(inline_index)
            styles.append(".{} {{ {} }}".format(class_name, css))
            tag = tag[:style_match.start()] + tag[style_match.end():]
            class_match = re.search(
                r"\bclass\s*=\s*(?:(['\"])(.*?)\1|([^\s>]+))",
                tag,
                re.IGNORECASE | re.DOTALL,
            )
            if class_match:
                quote = class_match.group(1) or '"'
                classes = (class_match.group(2) or class_match.group(3)).split()
                classes.append(class_name)
                replacement = 'class={}{}{}'.format(quote, " ".join(classes), quote)
                return tag[:class_match.start()] + replacement + tag[class_match.end():]
            insertion_point = tag.rfind("/>")
            if insertion_point < 0:
                insertion_point = tag.rfind(">")
            return tag[:insertion_point] + ' class="{}"'.format(class_name) + tag[insertion_point:]

        html = re.sub(
            r"<[a-z][^<>]*>",
            move_inline_style,
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        return html, "\n\n".join(style for style in styles if style)

    def _resolve_proposal_target(self, lang, requested_filename=None):
        if not self.current_folder or not self.current_folder.is_dir():
            return None
        extensions = {
            "html": {".html", ".htm"},
            "css": {".css"},
            "javascript": {".js"},
            "typescript": {".ts"},
            "python": {".py"},
            "json": {".json"},
        }
        valid_extensions = extensions.get(lang.lower(), set())
        if not valid_extensions:
            return None

        root = self.current_folder.resolve()
        if requested_filename:
            requested_path = (root / requested_filename.replace("\\", "/")).resolve()
            try:
                requested_path.relative_to(root)
            except ValueError:
                return None
            if (
                requested_path.suffix.lower() in valid_extensions
                and requested_path.is_file()
                and self._is_available_project_file(requested_path)
            ):
                return requested_path
            return None

        candidates = sorted(
            path.resolve()
            for path in root.rglob("*")
            if path.is_file()
            and path.suffix.lower() in valid_extensions
            and self._is_available_project_file(path)
            and not any(
                part in {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build"}
                for part in path.relative_to(root).parts
            )
        )
        if self.current_file and self.current_file.suffix.lower() in valid_extensions:
            return self.current_file.resolve()

        if lang.lower() == "css":
            html_candidates = sorted(
                path for path in root.rglob("*.html")
                if path.is_file()
                and self._is_available_project_file(path)
                and not any(
                    part in {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build"}
                    for part in path.relative_to(root).parts
                )
            )
            if self.current_file and self.current_file.suffix.lower() in (".html", ".htm"):
                html_candidates = [self.current_file] + [path for path in html_candidates if path.resolve() != self.current_file.resolve()]
            for html_path in html_candidates:
                try:
                    html = self._read_project_file(html_path)
                except (OSError, UnicodeError):
                    continue
                for link_tag in re.findall(r"<link\b[^>]*>", html, re.IGNORECASE):
                    href_match = re.search(r"\bhref\s*=\s*(?:(['\"])(.*?)\1|([^\s>]+))", link_tag, re.IGNORECASE)
                    rel_match = re.search(r"\brel\s*=\s*(?:(['\"])(.*?)\1|([^\s>]+))", link_tag, re.IGNORECASE)
                    href = (href_match.group(2) or href_match.group(3)) if href_match else ""
                    rel = (rel_match.group(2) or rel_match.group(3)) if rel_match else ""
                    if not href or "stylesheet" not in rel.lower().split():
                        continue
                    linked = self._resolve_local_project_path(html_path, href, root)
                    if linked in candidates:
                        return linked

        preferred_names = {
            "html": ("index.html",),
            "css": ("style.css", "styles.css", "main.css"),
            "javascript": ("script.js", "main.js", "app.js"),
            "typescript": ("main.ts", "app.ts"),
            "python": (),
            "json": (),
        }.get(lang.lower(), ())
        for preferred in preferred_names:
            match = next((path for path in candidates if path.name.lower() == preferred), None)
            if match:
                return match
        return candidates[0] if len(candidates) == 1 else None

    def _new_ai_file_path(self, lang, requested_filename=None):
        if not self.current_folder or not self.current_folder.is_dir():
            return None
        extensions = {
            "html": ".html",
            "htm": ".htm",
            "css": ".css",
            "javascript": ".js",
            "typescript": ".ts",
            "python": ".py",
            "json": ".json",
            "markdown": ".md",
            "text": ".txt",
            "xml": ".xml",
            "yaml": ".yml",
        }
        extension = extensions.get(lang.lower())
        if not extension:
            return None

        root = self.current_folder.resolve()
        if requested_filename:
            normalized_name = requested_filename.strip().strip("\"'").replace("\\", "/")
            candidate = (root / normalized_name).resolve()
            try:
                candidate.relative_to(root)
            except ValueError:
                candidate = root / Path(normalized_name).name
            if candidate.suffix.lower() != extension:
                candidate = candidate.with_suffix(extension)
        else:
            default_names = {
                "html": "index.html",
                "css": "style.css",
                "javascript": "script.js",
                "typescript": "main.ts",
                "python": "main.py",
                "json": "data.json",
                "markdown": "README.md",
                "text": "notes.txt",
                "xml": "document.xml",
                "yaml": "config.yml",
            }
            candidate = root / default_names[lang.lower()]

        if not candidate.name or candidate.name == extension:
            candidate = candidate.with_name("nouveau_fichier" + extension)
        original = candidate
        suffix = 2
        while candidate.exists() or self._is_managed_file(candidate):
            candidate = original.with_name(
                "{}-{}{}".format(original.stem, suffix, original.suffix)
            )
            suffix += 1
        return candidate

    def _create_ai_file(self, path, code, lang):
        root = self.current_folder.resolve()
        path = Path(path).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            raise ValueError("Le fichier proposé doit rester dans le dossier du projet.")
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("x", encoding="utf-8", newline="") as output:
                output.write(code)
        except FileExistsError:
            raise FileExistsError("Le fichier {} existe déjà; aucune donnée n'a été écrasée.".format(path.name))
        self._register_managed_file(path)
        self._file_buffers[path] = code
        self._log_ia_action("creer_fichier_ia", str(path.relative_to(root)))
        return path

    @staticmethod
    def _link_stylesheet(html, css_target, html_filename=None, project_root=None):
        html_path = Path(html_filename) if html_filename else css_target
        html_folder = html_path.parent
        href = os.path.relpath(css_target, html_folder).replace("\\", "/")

        for tag in re.findall(r"<link\b[^>]*>", html, re.IGNORECASE):
            rel_match = re.search(r"\brel\s*=\s*(?:(['\"])(.*?)\1|([^\s>]+))", tag, re.IGNORECASE)
            href_match = re.search(r"\bhref\s*=\s*(?:(['\"])(.*?)\1|([^\s>]+))", tag, re.IGNORECASE)
            rel = (rel_match.group(2) or rel_match.group(3)) if rel_match else ""
            existing_href = (href_match.group(2) or href_match.group(3)) if href_match else ""
            if not rel_match or "stylesheet" not in rel.lower().split() or not href_match:
                continue
            existing_path = DevWindow._resolve_local_project_path(
                html_path,
                existing_href,
                project_root,
            )
            if existing_path is None:
                continue
            if existing_path == css_target.resolve():
                return html
            if not existing_path.is_file():
                updated_tag = re.sub(
                    r"\bhref\s*=\s*(?:(['\"]).*?\1|[^\s>]+)",
                    'href="{}"'.format(href),
                    tag,
                    count=1,
                    flags=re.IGNORECASE,
                )
                return html.replace(tag, updated_tag, 1)

        link = '<link rel="stylesheet" href="{}">'.format(href)
        if re.search(r"</head\s*>", html, re.IGNORECASE):
            return re.sub(r"</head\s*>", link + "\n</head>", html, count=1, flags=re.IGNORECASE)
        return link + "\n" + html

    def _link_css_to_open_html(self, css_path):
        if not self.current_file or self.current_file.suffix.lower() not in (".html", ".htm"):
            return False
        html = self.editor.get("1.0", "end-1c")
        linked_html = self._link_stylesheet(
            html,
            css_path,
            self.current_file,
            self.current_folder,
        )
        if linked_html == html:
            return False
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", linked_html)
        self._file_buffers[self.current_file.resolve()] = linked_html
        self.unsaved = True
        self.file_name_label.configure(text=self.current_file.name + " ●")
        self._schedule_preview()
        return True

    def _create_proposal(self, code, lang, target_path=None):
        lang = self._detect_code_language(code, lang)
        if target_path is None:
            target_path = self._resolve_proposal_target(lang)
        frame = ctk.CTkFrame(self.proposals_container, fg_color="#2a2a2e", corner_radius=6)
        frame.pack(fill="x", padx=6, pady=6)

        target_label = target_path.relative_to(self.current_folder).as_posix() if target_path and self.current_folder else "Fichier cible à choisir"
        proposal_header = ctk.CTkFrame(frame, fg_color="transparent")
        proposal_header.pack(fill="x", padx=8, pady=(6, 2))
        ctk.CTkLabel(
            proposal_header,
            text="📋 Proposition {} → {}".format(lang, target_label),
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#c9d1d9",
        ).pack(side="left", anchor="w", expand=True)
        ctk.CTkButton(
            proposal_header,
            text="❌ Refuser",
            width=84,
            height=26,
            command=lambda f=frame: self._reject_proposal(f),
            fg_color="#c24141",
            hover_color="#a33434",
            font=ctk.CTkFont(size=10, weight="bold"),
        ).pack(side="right", padx=(6, 0))

        ctk.CTkLabel(
            frame,
            text="Code proposé — modifiable avant validation",
            font=ctk.CTkFont(size=10),
            text_color=TEXT_MUTED,
        ).pack(anchor="w", padx=8, pady=(0, 3))
        line_count = code.count("\n") + 1
        preview_height = min(360, max(150, line_count * 19))
        code_box = ctk.CTkTextbox(frame, height=preview_height, font=ctk.CTkFont(family="Consolas", size=12), fg_color="#0d1117", text_color="#c9d1d9", border_width=0)
        code_box.insert("1.0", code)
        code_box.pack(fill="x", padx=8, pady=(0, 6))

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(anchor="e", padx=8, pady=(0, 8))

        if target_path and target_path.is_file():
            ctk.CTkButton(
                btn_frame,
                text="✅ Valider dans {}".format(target_path.name),
                width=150,
                command=lambda c=code_box, p=target_path, f=frame: self._apply_proposal(
                    c.get("1.0", "end-1c"), p, f
                ),
                fg_color=ACCENT,
                hover_color=ACCENT_HOVER,
                font=ctk.CTkFont(size=11, weight="bold"),
            ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            btn_frame,
            text="📄 Créer fichier",
            width=110,
            command=lambda c=code_box, l=lang, p=target_path, f=frame: self._create_file_proposal(
                c.get("1.0", "end-1c"), l, p, f
            ),
            fg_color="#6366f1",
            hover_color="#4f46e5",
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(side="left", padx=(0, 6))

        self.proposals.append({"frame": frame, "code": code, "lang": lang, "target": target_path})
        self.status_var.set("Nouvelle proposition de code — Valider / Créer fichier / Refuser")
        self._save_session()

    def _apply_proposal(self, code, target_path=None, proposal_frame=None):
        if target_path is None:
            lang = self._detect_code_language(code, LANG_EXTENSIONS.get(self.current_file.suffix.lower(), "text") if self.current_file else "text")
            target_path = self._resolve_proposal_target(lang)
        if not target_path:
            messagebox.showwarning("Fichier cible", "Aucun fichier existant du bon type n'a été trouvé. Choisissez « Créer fichier » pour ne pas mélanger les langages.")
            return
        if target_path.suffix.lower() == ".css":
            self._link_css_to_open_html(target_path)
        if self.current_file is None or target_path.resolve() != self.current_file.resolve():
            self.open_file(target_path)
        if target_path.suffix.lower() in (".html", ".htm"):
            code, stylesheet_path = self._prepare_html_stylesheet(
                target_path,
                code,
                managed_only=True,
            )
            if not stylesheet_path.exists():
                stylesheet_path.parent.mkdir(parents=True, exist_ok=True)
                stylesheet_path.write_text(CSS_BOILERPLATE, encoding="utf-8")
                self._register_managed_file(stylesheet_path)
        self._invalidate_inline_completion()
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", code)
        self._cache_current_buffer()
        self.unsaved = True
        self.file_name_label.configure(text=(self.current_file.name if self.current_file else "Sans titre") + " ●")
        self.status_var.set("Code IA appliqué dans l'éditeur (en attente d'enregistrement)")
        self._schedule_highlight()
        self._schedule_preview()
        self._refresh_tree()
        self._log_ia_action("appliquer_proposition", "code dans l'editeur")
        if proposal_frame:
            self._reject_proposal(proposal_frame)

    def _create_file_proposal(self, code, lang, target_path=None, proposal_frame=None):
        if not self.current_folder:
            messagebox.showwarning("Aucun dossier", "Ouvrez d'abord un dossier de projet.")
            return
        ext_map = {"html": ".html", "css": ".css", "javascript": ".js", "js": ".js", "python": ".py", "text": ".txt"}
        ext = ext_map.get(lang.lower(), ".txt")
        default_name = target_path.name if target_path else "nouveau_fichier" + ext
        dlg = ctk.CTkInputDialog(text="Nom du nouveau fichier (ex: " + default_name + ") :", title="Créer fichier")
        name = dlg.get_input()
        if not name:
            return
        if not name.endswith(ext):
            name = name + ext
        p = (Path(self.current_folder) / name).resolve()
        try:
            p.relative_to(Path(self.current_folder).resolve())
        except ValueError:
            messagebox.showwarning("Nom invalide", "Le fichier doit être créé dans le dossier du projet.")
            return
        if p.exists():
            if not messagebox.askyesno("Existe deja", "Le fichier " + name + " existe deja. L'ecraser ?"):
                return
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            stylesheet_path = None
            if lang.lower() in ("html", "htm"):
                code, stylesheet_path = self._prepare_html_stylesheet(
                    p,
                    code,
                    managed_only=True,
                )
            p.write_text(code, encoding="utf-8")
            self._register_managed_file(p)
            if stylesheet_path and not stylesheet_path.exists():
                stylesheet_path.write_text(CSS_BOILERPLATE, encoding="utf-8")
                self._register_managed_file(stylesheet_path)
            elif lang.lower() in ("css", "stylesheet"):
                self._link_css_to_open_html(p)
            self._refresh_tree()
            self.open_file(p)
            if proposal_frame:
                self._reject_proposal(proposal_frame)
            self.status_var.set("Fichier créé : {}".format(name))
            self._log_ia_action("creer_fichier_ia", name)
            self._save_session()
        except Exception as e:
            messagebox.showerror("Erreur creation", str(e))

    def _reject_proposal(self, frame):
        frame.destroy()
        self.proposals = [p for p in self.proposals if p["frame"] is not frame]
        if not self.proposals:
            self.status_var.set("Proposition refusée")
        self._save_session()

    def _clear_proposals(self):
        had_proposals = bool(self.proposals)
        for p in self.proposals:
            try:
                p["frame"].destroy()
            except Exception:
                pass
        self.proposals = []
        if had_proposals:
            self.status_var.set("Toutes les propositions ont été refusées")
            self._save_session()

    def ask_ai_help(self):
        code = self.editor.get("1.0", "end-1c")
        if not code.strip():
            messagebox.showwarning("Vide", "Il n'y a aucun code à analyser.")
            return
        self.switch_tab("ia")
        self.ia_entry.delete("1.0", "end")
        self.ia_entry.insert("1.0", "Analyse ce code et donne-moi des conseils d'amélioration avec des blocs de code corrigés :")
        self.ia_send()

    def on_close(self):
        self._invalidate_inline_completion()
        self._save_session()
