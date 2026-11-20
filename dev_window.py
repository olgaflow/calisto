import customtkinter as ctk

from tkinter import filedialog, messagebox, colorchooser

import tkinter as tk

import os

import json

import re

import html

import time

import shutil

import threading

from pathlib import Path

import webbrowser
import unicodedata

import subprocess

import ollama

import base64

from urllib.parse import unquote, urlparse



try:

    from tkinterweb import HtmlFrame

except ImportError:

    HtmlFrame = None



BG_APP = "#0b1118"
BG_PANEL = "#111a24"
BG_EDITOR = "#0d1117"
TEXT_MAIN = "#e5edf5"
TEXT_MUTED = "#94a3b8"
ACCENT = "#22c58b"
ACCENT_HOVER = "#16a875"
IA_COLOR = "#22c58b"
IA_HOVER = "#16a875"



# Largeurs par defaut des colonnes de l'editeur

EXPLORER_WIDTH = 280

PREVIEW_PANEL_WIDTH = 260



LANG_EXTENSIONS = {
    ".py": "python",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "css",
    ".less": "css",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".json": "json",
    ".jsonc": "json",
    ".md": "markdown",
    ".markdown": "markdown",
    ".rst": "markdown",
    ".txt": "text",
    ".text": "text",
    ".cpp": "cpp",
    ".c": "c",
    ".java": "java",
    ".php": "php",
    ".rb": "ruby",
    ".go": "go",
    ".rs": "rust",
    ".sh": "shell",
    ".bash": "shell",
    ".ps1": "powershell",
    ".bat": "batch",
    ".cmd": "batch",
    ".xml": "xml",
    ".svg": "svg",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".toml": "toml",
    ".ini": "ini",
    ".cfg": "ini",
    ".conf": "ini",
    ".csv": "csv",
    ".sql": "sql",
    ".vue": "html",
    ".svelte": "html",
    ".tex": "tex",
    ".properties": "properties",
}

BINARY_PROJECT_FILE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf",
    ".zip", ".7z", ".rar", ".tar", ".gz", ".tgz", ".bz2", ".xz",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods", ".odp",
    ".sqlite", ".sqlite3", ".db",
    ".mp3", ".wav", ".ogg", ".mp4", ".webm",
    ".woff", ".woff2", ".ttf", ".otf", ".bin", ".exe", ".dll", ".msi",
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
    <title>Document</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>

</body>
</html>
"""

CSS_BOILERPLATE = "/* style.css */\nbody {\n    font-family: Arial, sans-serif;\n    margin: 0;\n    padding: 20px;\n    background: #f5f5f5;\n    color: #333;\n}\n\nh1 {\n    color: #333;\n}\n"



JS_BOILERPLATE = "// script.js\nconsole.log('Bonjour depuis Calisto');\n"



DEFAULT_TAG_COLORS = {

    "kw": "#4fc3f7",

    "str": "#ffb74d",

    "comment": "#81c784",

    "func": "#ffd54f",

    "number": "#ce93d8",

    "tag": "#64b5f6",

    "attr": "#4dd0e1",

    "bool": "#f48fb1",

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





_LARGEURS_HELVETICA = {
    " ": 278, "!": 278, '"': 355, "#": 556, "$": 556, "%": 889, "&": 667, "'": 191,
    "(": 333, ")": 333, "*": 389, "+": 584, ",": 278, "-": 333, ".": 278, "/": 278,
    "0": 556, "1": 556, "2": 556, "3": 556, "4": 556, "5": 556, "6": 556,
    "7": 556, "8": 556, "9": 556, ":": 278, ";": 278, "<": 584, "=": 584,
    ">": 584, "?": 556, "@": 1015,
    "A": 667, "B": 667, "C": 722, "D": 722, "E": 667, "F": 611, "G": 778,
    "H": 722, "I": 278, "J": 500, "K": 667, "L": 556, "M": 833, "N": 722,
    "O": 778, "P": 667, "Q": 778, "R": 722, "S": 667, "T": 611, "U": 722,
    "V": 667, "W": 944, "X": 667, "Y": 667, "Z": 611,
    "[": 278, "\\": 278, "]": 278, "^": 469, "_": 556, "`": 333,
    "a": 556, "b": 556, "c": 500, "d": 556, "e": 556, "f": 278, "g": 556,
    "h": 556, "i": 222, "j": 222, "k": 500, "l": 222, "m": 833, "n": 556,
    "o": 556, "p": 556, "q": 556, "r": 333, "s": 500, "t": 278, "u": 556,
    "v": 500, "w": 722, "x": 500, "y": 500, "z": 500,
    "{": 334, "|": 260, "}": 334, "~": 584,
}

_POLICES_PDF = {
    "F1": "Courier",
    "F2": "Helvetica-Bold",
    "F3": "Helvetica",
    "F4": "Helvetica-Oblique",
    "F5": "Courier-Bold",
}

_COULEURS_PDF = {
    "titre": (0.10, 0.28, 0.48),
    "texte": (0.13, 0.13, 0.15),
    "code": (0.62, 0.15, 0.15),
    "gris": (0.42, 0.45, 0.50),
    "tableau_entete": (0.88, 0.92, 0.97),
    "tableau_bord": (0.66, 0.70, 0.75),
    "code_fond": (0.95, 0.96, 0.97),
    "citation": (0.26, 0.42, 0.38),
    "trait": (0.72, 0.78, 0.86),
}

_MOTIF_INLINE_PDF = re.compile(
    r"\[c:#([0-9A-Fa-f]{6})\](.*?)\[/c\]"
    r"|\*\*(.+?)\*\*"
    r"|`([^`]+)`"
    r"|(?<!\*)\*([^*]+?)\*(?!\*)",
    re.DOTALL,
)


def _pdf_couleur(valeur):
    if isinstance(valeur, tuple):
        return valeur
    if isinstance(valeur, str) and valeur.startswith("#") and len(valeur) == 7:
        try:
            return (
                int(valeur[1:3], 16) / 255.0,
                int(valeur[3:5], 16) / 255.0,
                int(valeur[5:7], 16) / 255.0,
            )
        except ValueError:
            pass
    return _COULEURS_PDF.get(valeur, _COULEURS_PDF["texte"])


def _pdf_chaine(texte):
    return "<" + texte.encode("cp1252", errors="replace").hex().upper() + ">"


def _pdf_largeur(ch, police):
    if police in ("F1", "F5"):
        return 600
    base = unicodedata.normalize("NFKD", ch)
    base = "".join(x for x in base if not unicodedata.combining(x)) or ch
    valeur = _LARGEURS_HELVETICA.get(base[0], 556)
    if police in ("F2", "F5") and base[0] != " ":
        valeur = int(round(valeur * 1.06))
    return valeur


def _pdf_largeur_texte(texte, police, taille):
    return sum(_pdf_largeur(ch, police) for ch in texte) * taille / 1000.0


def _pdf_spans(texte, police="F3", taille=10.0, couleur="texte"):
    spans = []
    position = 0

    for trouve in _MOTIF_INLINE_PDF.finditer(texte):
        if trouve.start() > position:
            spans.append((texte[position:trouve.start()], police, taille, couleur))

        if trouve.group(1):
            spans.append((trouve.group(2), police, taille, "#" + trouve.group(1).upper()))
        elif trouve.group(3) is not None:
            spans.append((trouve.group(3), "F2", taille, couleur))
        elif trouve.group(4) is not None:
            spans.append((trouve.group(4), "F1", max(6.0, taille - 0.8), "code"))
        else:
            spans.append((trouve.group(5), "F4", taille, couleur))

        position = trouve.end()

    if position < len(texte):
        spans.append((texte[position:], police, taille, couleur))

    return [span for span in spans if span[0]]


def _pdf_mots(spans):
    mots = []

    for texte, police, taille, couleur in spans:
        fragments = texte.split(" ")

        for index, fragment in enumerate(fragments):
            if index > 0:
                if mots:
                    t, p, s, c = mots[-1]
                    mots[-1] = (t + " ", p, s, c)
                else:
                    mots.append((" ", police, taille, couleur))

            if fragment:
                mots.append((fragment, police, taille, couleur))

    return mots


def _pdf_decouper_mot(mot, largeur_max):
    resultat = []
    courant = ""

    for caractere in mot[0]:
        candidat = courant + caractere
        if courant and _pdf_largeur_texte(candidat, mot[1], mot[2]) > largeur_max:
            resultat.append((courant, mot[1], mot[2], mot[3]))
            courant = caractere
        else:
            courant = candidat

    if courant:
        resultat.append((courant, mot[1], mot[2], mot[3]))

    return resultat


def _pdf_lignes(spans, largeur_max):
    lignes = []
    ligne = []
    largeur = 0.0

    for mot in _pdf_mots(spans):
        if _pdf_largeur_texte(mot[0], mot[1], mot[2]) > largeur_max:
            morceaux = _pdf_decouper_mot(mot, largeur_max)
        else:
            morceaux = [mot]

        for morceau in morceaux:
            if ligne and largeur + _pdf_largeur_texte(morceau[0], morceau[1], morceau[2]) > largeur_max + 0.3:
                lignes.append(ligne)
                ligne = []
                largeur = 0.0
                if morceau[0].startswith(" ") and len(morceau[0]) > 1:
                    morceau = (morceau[0].lstrip(), morceau[1], morceau[2], morceau[3])

            ligne.append(morceau)
            largeur += _pdf_largeur_texte(morceau[0], morceau[1], morceau[2])

    if ligne:
        lignes.append(ligne)

    return lignes


def nettoyer_texte_document(texte):
    """Retire les artefacts de conversation en conservant la mise en forme Markdown."""

    if not texte:
        return ""

    texte = texte.replace("\r\n", "\n").replace("\r", "\n").replace("\ufeff", "")

    sortie = []
    dans_code = False

    for brute in texte.split("\n"):
        propre = brute.rstrip()
        depouillee = propre.strip()

        if depouillee.startswith("```"):
            dans_code = not dans_code
            sortie.append(propre)
            continue

        if dans_code:
            sortie.append(propre)
            continue

        if not depouillee:
            if sortie and sortie[-1] != "":
                sortie.append("")
            continue

        if re.match(r"^(utilisateur|user|human|assistant|ia|calisto|system)\s*:", depouillee, re.IGNORECASE):
            continue

        if re.match(
            r"^(voici|voila|bien sur|bien sûr|certainement|d'accord|parfait|"
            r"tres bien|très bien|a bientot|à bientôt|bien entendu|avec plaisir)\b",
            depouillee,
            re.IGNORECASE,
        ) and len(depouillee) < 110:
            continue

        if re.match(r"^(j'espere|j'espère|n'hesitez|n'hésitez)\s", depouillee, re.IGNORECASE):
            continue

        sortie.append(propre)

    while sortie and sortie[-1] == "":
        sortie.pop()

    return "\n".join(sortie)


def generer_pdf_minimal(titre, contenu, chemin):
    """Genere un PDF 1.4 multipage : titres, couleurs, styles, titres, listes, tableaux et code."""

    contenu = nettoyer_texte_document(contenu)
    titre = (titre or "Document").strip() or "Document"

    page_w, page_h = 612, 792
    marge = 54
    largeur_utile = page_w - 2 * marge
    bas_page = marge + 22

    tailles = {"titre": 18.0, "h1": 14.5, "h2": 12.5, "h3": 11.0, "corps": 10.0}

    pages = []
    operations = []
    position_y = [page_h - marge]

    def nouvelle_page():
        pages.append(operations[:])
        operations.clear()
        position_y[0] = page_h - marge

    def place(hauteur):
        if position_y[0] - hauteur < bas_page:
            nouvelle_page()

    def ecrire(jeton, x, base_y):
        for texte, police, taille, couleur in jeton:
            r, g, b = _pdf_couleur(couleur)
            operations.append(
                "BT /{} {:.2f} Tf {:.3f} {:.3f} {:.3f} rg {:.2f} {:.2f} Td {} Tj ET".format(
                    police, taille, r, g, b, x, base_y, _pdf_chaine(texte)
                )
            )
            x += _pdf_largeur_texte(texte, police, taille)

    def bloc(spans, largeur, hauteur_ligne, x=None, couleur="texte"):
        depart = marge if x is None else x
        for ligne in _pdf_lignes(spans, largeur):
            place(hauteur_ligne)
            ecrire(ligne, depart, position_y[0] - hauteur_ligne * 0.78)
            position_y[0] -= hauteur_ligne

    def dessiner_code(code):
        taille = 8.8
        hauteur_ligne = taille * 1.42
        largeur = largeur_utile - 18

        enveloppe = []
        for brute in code or [""]:
            propre = brute.replace("\t", "    ").rstrip()
            if propre:
                enveloppe.extend(_pdf_lignes([(propre, "F1", taille, "texte")], largeur))
            else:
                enveloppe.append([])

        if not enveloppe:
            enveloppe = [[]]

        while enveloppe:
            place(hauteur_ligne + 12)
            disponible = int((position_y[0] - bas_page - 12) // hauteur_ligne)
            maximum = max(1, disponible)
            segment = enveloppe[:maximum]
            enveloppe = enveloppe[maximum:]

            hauteur_segment = len(segment) * hauteur_ligne + 12
            r, g, b = _pdf_couleur("code_fond")
            operations.append(
                "{:.3f} {:.3f} {:.3f} rg {:.2f} {:.2f} {:.2f} {:.2f} re f".format(
                    r, g, b, marge, position_y[0] - hauteur_segment, largeur_utile, hauteur_segment
                )
            )

            position_y[0] -= 6

            for ligne in segment:
                ecrire(ligne, marge + 8, position_y[0] - hauteur_ligne * 0.78)
                position_y[0] -= hauteur_ligne

            position_y[0] -= 8

        position_y[0] -= 4

    def dessiner_tableau(lignes_brutes):
        rangees = []

        for brute in lignes_brutes:
            cellules = [cellule.strip() for cellule in brute.strip().strip("|").split("|")]
            if cellules and all(
                re.fullmatch(r":?-{2,}:?", cellule) for cellule in cellules if cellule
            ):
                continue
            rangees.append(cellules)

        if not rangees:
            return

        colonnes = max(len(rangee) for rangee in rangees)
        for rangee in rangees:
            while len(rangee) < colonnes:
                rangee.append("")

        taille = 9.2
        hauteur_ligne = taille * 1.35
        remplissage = 5.0

        naturelles = [30.0] * colonnes
        for rangee in rangees:
            for index, cellule in enumerate(rangee):
                naturelles[index] = max(
                    naturelles[index], _pdf_largeur_texte(cellule, "F3", taille) + 2 * remplissage
                )

        total = sum(naturelles)
        largeurs = [largeur * largeur_utile / total for largeur in naturelles]

        for index_rangee, rangee in enumerate(rangees):
            enveloppes = []
            for index, cellule in enumerate(rangee):
                if not cellule:
                    enveloppes.append([[]])
                    continue
                police = "F2" if index_rangee == 0 else "F3"
                spans = _pdf_spans(cellule, police, taille, "texte")
                enveloppes.append(_pdf_lignes(spans, largeurs[index] - 2 * remplissage))

            nb_lignes = max(len(enveloppe) for enveloppe in enveloppes) or 1
            hauteur = nb_lignes * hauteur_ligne + 2 * remplissage

            place(hauteur)

            if index_rangee == 0:
                r, g, b = _pdf_couleur("tableau_entete")
                operations.append(
                    "{:.3f} {:.3f} {:.3f} rg {:.2f} {:.2f} {:.2f} {:.2f} re f".format(
                        r, g, b, marge, position_y[0] - hauteur, largeur_utile, hauteur
                    )
                )

            x = marge
            for index in range(colonnes):
                for numero, ligne in enumerate(enveloppes[index]):
                    ecrire(
                        ligne,
                        x + remplissage,
                        position_y[0] - remplissage - hauteur_ligne * (numero + 0.78),
                    )
                x += largeurs[index]

            r, g, b = _pdf_couleur("tableau_bord")
            operations.append(
                "{:.3f} {:.3f} {:.3f} RG 0.7 w {:.2f} {:.2f} {:.2f} {:.2f} re S".format(
                    r, g, b, marge, position_y[0] - hauteur, largeur_utile, hauteur
                )
            )

            x = marge
            for index in range(colonnes - 1):
                x += largeurs[index]
                operations.append(
                    "{:.3f} {:.3f} {:.3f} RG 0.7 w {:.2f} {:.2f} m {:.2f} {:.2f} l S".format(
                        r, g, b, x, position_y[0], x, position_y[0] - hauteur
                    )
                )

            position_y[0] -= hauteur

        position_y[0] -= 6

    def dessiner_puce(spans, marqueur):
        taille = tailles["corps"]
        hauteur_ligne = taille * 1.45
        retrait = 20
        largeur = largeur_utile - retrait

        lignes = _pdf_lignes(spans, largeur)

        for index, ligne in enumerate(lignes):
            place(hauteur_ligne)
            if index == 0:
                r, g, b = _pdf_couleur("titre")
                operations.append(
                    "BT /F3 {:.2f} Tf {:.3f} {:.3f} {:.3f} rg {:.2f} {:.2f} Td {} Tj ET".format(
                        taille, r, g, b, marge + 2, position_y[0] - hauteur_ligne * 0.78,
                        _pdf_chaine(marqueur)
                    )
                )
            ecrire(ligne, marge + retrait, position_y[0] - hauteur_ligne * 0.78)
            position_y[0] -= hauteur_ligne

        position_y[0] -= 2

    def dessiner_citation(texte):
        taille = tailles["corps"]
        hauteur_ligne = taille * 1.45

        r, g, b = _pdf_couleur("citation")

        couleur = "citation"
        spans = _pdf_spans(texte, "F4", taille, couleur)
        largeur = largeur_utile - 24
        depart = marge + 16

        lignes = _pdf_lignes(spans, largeur)
        hauteur_totale = len(lignes) * hauteur_ligne

        place(hauteur_totale)

        operations.append(
            "{:.3f} {:.3f} {:.3f} rg {:.2f} {:.2f} 3.00 {:.2f} re f".format(
                r, g, b, marge, position_y[0] - hauteur_totale, hauteur_totale
            )
        )

        for ligne in lignes:
            ecrire(ligne, depart, position_y[0] - hauteur_ligne * 0.78)
            position_y[0] -= hauteur_ligne

        position_y[0] -= 6

    # --- Titre du document ---
    taille_titre = tailles["titre"]
    ecrire(
        _pdf_spans(titre, "F2", taille_titre, "titre") and _pdf_mots(
            _pdf_spans(titre, "F2", taille_titre, "titre")
        ),
        marge,
        position_y[0] - taille_titre * 0.82,
    )

    r, g, b = _pdf_couleur("trait")
    operations.append(
        "{:.3f} {:.3f} {:.3f} RG 1.2 w {:.2f} {:.2f} m {:.2f} {:.2f} l S".format(
            r, g, b, marge, position_y[0] - taille_titre * 1.15,
            page_w - marge, position_y[0] - taille_titre * 1.15
        )
    )

    position_y[0] -= taille_titre * 2.1

    # --- Analyse du contenu ---
    lignes_source = contenu.split("\n")
    index = 0

    while index < len(lignes_source):
        brute = lignes_source[index]
        depouillee = brute.strip()

        if depouillee.startswith("```"):
            index += 1
            code = []
            while index < len(lignes_source) and not lignes_source[index].strip().startswith("```"):
                code.append(lignes_source[index])
                index += 1
            index += 1
            dessiner_code(code)
            continue

        if depouillee.startswith("|") and depouillee.count("|") >= 2:
            bloc_tableau = []
            while index < len(lignes_source) and lignes_source[index].strip().startswith("|"):
                bloc_tableau.append(lignes_source[index].strip())
                index += 1
            dessiner_tableau(bloc_tableau)
            continue

        if not depouillee:
            if position_y[0] < page_h - marge - 2:
                position_y[0] -= 7
            index += 1
            continue

        entete = re.match(r"^(#{1,6})\s+(.*)$", depouillee)
        if entete:
            niveau = min(len(entete.group(1)), 3)
            style = "titre" if niveau == 1 else "h{}".format(niveau)
            taille = tailles[style]
            if position_y[0] < page_h - marge - 30:
                position_y[0] -= taille * 0.55
            spans = _pdf_spans(entete.group(2), "F2", taille, "titre")
            bloc(spans, largeur_utile, taille * 1.45)
            position_y[0] -= 3
            index += 1
            continue

        if re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", depouillee):
            place(14)
            r, g, b = _pdf_couleur("trait")
            operations.append(
                "{:.3f} {:.3f} {:.3f} RG 0.8 w {:.2f} {:.2f} m {:.2f} {:.2f} l S".format(
                    r, g, b, marge, position_y[0] - 6, page_w - marge, position_y[0] - 6
                )
            )
            position_y[0] -= 14
            index += 1
            continue

        puce = re.match(r"^([-*+])\s+(.*)$", depouillee)
        if puce:
            dessiner_puce(_pdf_spans(puce.group(2), "F3", tailles["corps"], "texte"), "•")
            index += 1
            continue

        numero = re.match(r"^(\d+[.)])\s+(.*)$", depouillee)
        if numero:
            dessiner_puce(
                _pdf_spans(numero.group(2), "F3", tailles["corps"], "texte"), numero.group(1)
            )
            index += 1
            continue

        if depouillee.startswith(">"):
            citation = depouillee.lstrip(">").strip()
            while index + 1 < len(lignes_source) and lignes_source[index + 1].strip().startswith(">"):
                index += 1
                citation += " " + lignes_source[index].strip().lstrip(">").strip()
            dessiner_citation(citation)
            index += 1
            continue

        paragraphe = [depouillee]
        index += 1

        while index < len(lignes_source):
            suivante = lignes_source[index].strip()
            if (
                not suivante
                or suivante.startswith(("```", "|", "#", ">"))
                or re.match(r"^([-*+]|\d+[.)])\s", suivante)
                or re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", suivante)
            ):
                break
            paragraphe.append(suivante)
            index += 1

        spans = _pdf_spans(" ".join(paragraphe), "F3", tailles["corps"], "texte")
        bloc(spans, largeur_utile, tailles["corps"] * 1.5)
        position_y[0] -= 4

    pages.append(operations[:])

    # --- Pied de page ---
    total_pages = len(pages)

    for numero_page, contenu_page in enumerate(pages):
        libelle = "Page {} / {}".format(numero_page + 1, total_pages)
        largeur_libelle = _pdf_largeur_texte(libelle, "F3", 9)
        r, g, b = _pdf_couleur("gris")
        contenu_page.append(
            "BT /F3 9 Tf {:.3f} {:.3f} {:.3f} rg {:.2f} 30 Td {} Tj ET".format(
                r, g, b, (page_w - largeur_libelle) / 2.0, _pdf_chaine(libelle)
            )
        )

    flux = ["\n".join(page) if page else "" for page in pages]

    # --- Objets PDF ---
    corps_objets = {}

    corps_objets[1] = b"<</Type /Catalog /Pages 2 0 R>>"

    enfants = " ".join("{} 0 R".format(8 + 2 * i) for i in range(len(flux)))

    corps_objets[2] = "<</Type /Pages /Kids [{}] /Count {}>>".format(enfants, len(flux)).encode("ascii")

    for decalage, nom_police in enumerate(_POLICES_PDF.values()):
        corps_objets[3 + decalage] = (
            "<</Type /Font /Subtype /Type1 /BaseFont /{} /Encoding /WinAnsiEncoding>>".format(nom_police)
        ).encode("ascii")

    ressources = " ".join(
        "/{} {} 0 R".format(code, 3 + decalage) for decalage, code in enumerate(_POLICES_PDF)
    )

    for index_page, contenu_page in enumerate(flux):
        id_page = 8 + 2 * index_page
        id_flux = id_page + 1

        donnees = contenu_page.encode("latin-1", errors="replace")

        corps_objets[id_page] = (
            "<</Type /Page /Parent 2 0 R /MediaBox [0 0 {} {}] "
            "/Resources << /Font << {} >> >> "
            "/Contents {} 0 R>>".format(page_w, page_h, ressources, id_flux)
        ).encode("ascii")

        corps_objets[id_flux] = (
            b"<</Length " + str(len(donnees)).encode("ascii") + b">>\nstream\n" + donnees + b"\nendstream"
        )

    total_objets = max(corps_objets) + 1

    sortie = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    decalages = {}

    for numero in range(1, total_objets):
        decalages[numero] = len(sortie)
        sortie += "{} 0 obj\n".format(numero).encode("ascii")
        sortie += corps_objets[numero]
        sortie += b"\nendobj\n"

    position_xref = len(sortie)

    sortie += "xref\n0 {}\n".format(total_objets).encode("ascii")
    sortie += b"0000000000 65535 f \n"

    for numero in range(1, total_objets):
        sortie += "{:010d} 00000 n \n".format(decalages[numero]).encode("ascii")

    sortie += (
        "trailer\n<</Size {} /Root 1 0 R>>\nstartxref\n{}\n%%EOF\n".format(total_objets, position_xref)
    ).encode("ascii")

    with open(chemin, "wb") as fichier:
        fichier.write(bytes(sortie))

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

        self._pane_layout_job = None

        self._manual_resize = False

        self._last_explorer_sash = None

        self._last_preview_sash = None

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



    # ---------- Dimensionnement des colonnes de l'editeur ----------



    def _ui_scale(self):

        """Facteur d'agrandissement de l'interface lie a la resolution de l'ecran."""

        try:

            from customtkinter.windows.widgets.scaling.scaling_tracker import ScalingTracker



            return float(ScalingTracker.get_window_scaling(self.winfo_toplevel()))

        except Exception:

            return 1.0



    def _sash_x(self, pane, index=0):

        """Position horizontale actuelle d'une separation."""

        try:

            return int(pane.sash_coord(index)[0])

        except Exception:

            return None



    def _set_sash_x(self, pane, index, x):

        """Deplace une separation (tk.PanedWindow n'a pas de methode sashpos)."""

        try:

            pane.sash_place(index, int(x), 0)

        except Exception:

            pass



    def _apply_explorer_layout(self):

        """Impose la largeur de la colonne Explorateur."""

        if self._manual_resize:

            return

        try:

            target = int(EXPLORER_WIDTH * self._ui_scale())

            self._set_sash_x(self._top_pane, 0, target)

            self._last_explorer_sash = target

        except Exception:

            pass



    def _apply_preview_layout(self):

        """Impose la largeur de la colonne Previsualisation."""

        if self._manual_resize:

            return

        try:

            total = self._pane.winfo_width()

            if total < 200:

                return

            target = max(200, total - int(PREVIEW_PANEL_WIDTH * self._ui_scale()))

            self._set_sash_x(self._pane, 0, target)

            self._last_preview_sash = target

        except Exception:

            pass



    def _apply_pane_layout(self):

        self._apply_explorer_layout()

        self.after_idle(self._apply_preview_layout)



    def _on_pane_configure(self, event=None):

        if self._pane_layout_job is None:

            self._pane_layout_job = self.after_idle(self._finish_pane_layout)



    def _finish_pane_layout(self):

        self._pane_layout_job = None

        self._apply_pane_layout()



    def _on_pane_drag(self, event=None):

        """Detecte un redimensionnement manuel des separateurs."""

        try:

            for pane in (self._top_pane, self._pane):

                x = self._sash_x(pane, 0)

                if x is not None and abs(event.x - x) <= 8:

                    self._manual_resize = True

                    return

        except Exception:

            pass



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

                    fill=TEXT_MUTED,

                    font=text_widget.cget("font"),

                )

                previous_line = line

            next_index = text_widget.index("{} + 1 display lines".format(index))

            if next_index == index:

                break

            index = next_index



    def _build_ui(self):

        # ========== LAYOUT PRINCIPAL : 3 colonnes distinctes et etirables ==========

        self.grid_columnconfigure(0, weight=1)

        self.grid_rowconfigure(1, weight=1)

        self.grid_rowconfigure(0, weight=0)                   # Header (hauteur fixe)

        self.grid_rowconfigure(1, weight=1)                   # Contenu (remplit tout l'espace)

        self.grid_rowconfigure(2, weight=0)                   # Barre d'etat (hauteur fixe)



        # ========== HEADER (ligne 0, pleine largeur) ==========

        header = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0)

        header.grid(row=0, column=0, columnspan=3, sticky="ew")

        header.grid_propagate(False)

        header.configure(height=40)



        header_left = ctk.CTkFrame(header, fg_color="transparent")

        header_left.pack(side="left", fill="y", padx=12, pady=6)

        ctk.CTkLabel(header_left, text="💻 Calisto Developpement", font=ctk.CTkFont(size=14, weight="bold"), text_color=ACCENT).pack(side="left")



        header_right = ctk.CTkFrame(header, fg_color="transparent")

        header_right.pack(side="right", padx=12, pady=4)

        ctk.CTkButton(header_right, text="📁 Ouvrir dossier", width=110, command=self.open_folder, fg_color=BG_EDITOR, hover_color="#263547").pack(side="right", padx=6, pady=2)
        ctk.CTkButton(header_right, text="📄 Nouveau fichier", width=110, command=self.new_file, fg_color=BG_EDITOR, hover_color="#263547").pack(side="right", padx=6, pady=2)

        ctk.CTkButton(header_right, text="💾 Enregistrer", width=100, command=self.save_file, fg_color=ACCENT, hover_color=ACCENT_HOVER).pack(side="right", padx=6, pady=2)

        ctk.CTkButton(header_right, text="🌐 Previsualiser", width=110, command=self.preview_open_browser, fg_color="#6366f1", hover_color="#4f46e5").pack(side="right", padx=6, pady=2)

        ctk.CTkButton(header_right, text="🎨 Reglages couleurs", width=120, command=self.open_color_settings, fg_color="#6b7280", hover_color="#4b5563").pack(side="right", padx=6, pady=2)



        # ========== COLONNE 0 : EXPLORATEUR (ligne 1) ==========

        import tkinter as tk

        self._top_pane = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=6, bg="#253446", bd=0)

        self._top_pane.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=3, pady=3)

        self._top_pane.bind("<Configure>", self._on_pane_configure, add="+")

        self._top_pane.bind("<B1-Motion>", self._on_pane_drag, add="+")



        self.explorer = ctk.CTkFrame(self, width=260, fg_color=BG_PANEL, corner_radius=0, border_width=1, border_color="#253446")

        self._top_pane.add(self.explorer, minsize=200, stretch="always")

        self.explorer.grid_propagate(False)



        explorer_header = ctk.CTkFrame(self.explorer, fg_color="transparent")

        explorer_header.pack(fill="x", padx=10, pady=(12, 4))

        ctk.CTkLabel(explorer_header, text="📂 Explorateur", font=ctk.CTkFont(size=15, weight="bold"), text_color=ACCENT).pack(side="left")

        ctk.CTkButton(

            explorer_header,

            text="🗑",

            width=32,

            height=28,

            command=self.delete_selected,

            fg_color=BG_EDITOR,

            hover_color="#263547",

            font=ctk.CTkFont(size=14),

        ).pack(side="right")

        ctk.CTkButton(

            explorer_header,

            text="Tout",

            width=46,

            height=28,

            command=self._import_project_files,

            fg_color=BG_EDITOR,

            hover_color="#263547",

            font=ctk.CTkFont(size=11),

        ).pack(side="right", padx=(0, 4))



        self.tree_frame = ctk.CTkScrollableFrame(self.explorer, fg_color=BG_APP)

        self.tree_frame.pack(fill="both", expand=True, padx=8, pady=(0, 6))



        ctk.CTkLabel(

            self.explorer,

            text="Clic droit sur un fichier : renommer, copier, supprimer…",

            font=ctk.CTkFont(size=10),

            text_color=TEXT_MUTED,

        ).pack(padx=12, pady=(0, 8), anchor="w")



        self.folder_label = ctk.CTkLabel(self.explorer, text="Aucun dossier ouvert", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED)

        self.folder_label.pack(padx=12, pady=(0, 10), anchor="w")



        self.proj_frame = ctk.CTkFrame(self.explorer, fg_color=BG_EDITOR, corner_radius=8)

        self.proj_frame.pack(fill="x", padx=8, pady=(0, 12))

        ctk.CTkLabel(self.proj_frame, text="Projet / Version", font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT_MUTED).pack(padx=8, pady=(8, 4), anchor="w")

        self.proj_var = ctk.StringVar(value="Aucun")

        self.proj_menu = ctk.CTkOptionMenu(self.proj_frame, variable=self.proj_var, values=["Aucun"], command=self.load_project_version, fg_color=BG_PANEL, button_color=ACCENT, button_hover_color=ACCENT_HOVER, dropdown_fg_color=BG_PANEL, font=ctk.CTkFont(size=11))

        self.proj_menu.pack(padx=8, pady=(0, 8), fill="x")



        # ========== COLONNES 1+2 : ZONE PRINCIPALE (ligne 1) ==========

        self.main_area = ctk.CTkFrame(self, fg_color=BG_APP, corner_radius=0, border_width=1, border_color="#253446")

        self._top_pane.add(self.main_area, minsize=400, stretch="always")

        self.main_area.grid_columnconfigure(0, weight=1)

        self.main_area.grid_rowconfigure(0, weight=1)



        import tkinter as tk

        self._pane = tk.PanedWindow(self.main_area, orient=tk.HORIZONTAL, sashwidth=6, bg="#253446", bd=0)

        self._pane.grid(row=0, column=0, sticky="nsew")

        self._pane.bind("<Configure>", self._on_pane_configure, add="+")

        self._pane.bind("<B1-Motion>", self._on_pane_drag, add="+")

        # Le bloc editeur n'a une taille reelle que quand l'onglet "Editeur de code" est visible

        self.after(600, self._apply_pane_layout)

        self.bind("<Map>", lambda event: self.after(150, self._apply_pane_layout), add="+")



        # ========== EDITEUR ==========

        self.editor_frame = ctk.CTkFrame(self.main_area, fg_color=BG_EDITOR, corner_radius=0, border_width=1, border_color="#253446")

        self.editor_frame.grid_columnconfigure(1, weight=1)

        self.editor_frame.grid_rowconfigure(1, weight=1)

        self.editor_frame.grid_rowconfigure(2, weight=0)

        self._pane.add(self.editor_frame, minsize=200, stretch="always")



        editor_header = ctk.CTkFrame(self.editor_frame, fg_color=BG_PANEL, corner_radius=0)

        editor_header.grid(row=0, column=0, columnspan=2, sticky="ew")



        editor_left = ctk.CTkFrame(editor_header, fg_color="transparent")

        editor_left.pack(side="left", fill="y", padx=12, pady=5)

        self.file_name_label = ctk.CTkLabel(editor_left, text="Aucun fichier", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED)

        self.file_name_label.pack(side="left")

        self.lang_label = ctk.CTkLabel(editor_left, text="", font=ctk.CTkFont(size=10), text_color=TEXT_MUTED)

        self.lang_label.pack(side="left", padx=(8, 0))



        editor_quick = ctk.CTkFrame(editor_header, fg_color="transparent")

        editor_quick.pack(side="right", padx=12, pady=5)



        actions = [

            ("📄 Nouveau", self.new_file),

            ("💾 Enregistrer", self.save_file),

            ("🌐 Navigateur", self.preview_open_browser),

            ("✨ Formater", self.format_code),

            ("🔍 Rechercher", self._show_find_replace),

            ("📍 Ligne", self._goto_line),

            ("💬 Commenter", self._toggle_comment),

            ("📄 Retour ligne", self._toggle_word_wrap),

            ("🤖 Demander a l'IA", self.ask_ai_help),

        ]

        def _dispatch(choice):

            for label, fn in actions:

                if label == choice:

                    fn()

                    break

            self._actions_menu.set("⚙ Actions")

        self._actions_menu = ctk.CTkOptionMenu(
            editor_quick,
            values=[a[0] for a in actions],
            command=_dispatch,
            width=150,
            fg_color=BG_PANEL,
            button_color=ACCENT,
            button_hover_color=ACCENT_HOVER,
            dropdown_fg_color=BG_PANEL,
        )

        self._actions_menu.set("⚙ Actions")

        self._actions_menu.pack(side="left", padx=4)



        self.line_numbers = tk.Canvas(

            self.editor_frame,

            width=44,

            bg=BG_PANEL,

            highlightthickness=0,

            bd=0,

        )

        self.line_numbers.grid(row=1, column=0, sticky="ns", padx=(5, 0), pady=5)

        self.line_numbers.bind("<Configure>", self._queue_line_number_redraw)

        self.editor = ctk.CTkTextbox(self.editor_frame, font=ctk.CTkFont(family="Consolas", size=14), fg_color=BG_EDITOR, text_color=TEXT_MAIN, border_width=0, wrap="none")

        self.editor.grid(row=1, column=1, sticky="nsew", padx=(0, 5), pady=5)
        self._text_widget().configure(insertbackground=TEXT_MAIN, selectbackground="#265343", selectforeground=TEXT_MAIN)

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

        self.editor.bind("<Control-d>", self._select_next_occurrence)

        self.editor.bind("<Control-l>", self._select_line)

        self.editor.bind("<Control-Shift-K>", self._delete_line)

        self.editor.bind("<Control-Return>", self._insert_line_below)

        self.editor.bind("<Control-Shift-Return>", self._insert_line_above)

        self.editor.bind("<Alt-Up>", self._move_line_up)

        self.editor.bind("<Alt-Down>", self._move_line_down)

        self.editor.bind("<Control-bracketright>", self._indent)

        self.editor.bind("<Control-bracketleft>", self._outdent)

        self.editor.bind("<Control-f>", lambda e: self._show_find_replace())

        self.editor.bind("<Control-g>", lambda e: self._goto_line())

        self.editor.bind("<Control-h>", lambda e: self._show_find_replace())

        self.editor.bind("<Control-s>", lambda e: self.save_file())

        self.editor.bind("<Right>", self._match_bracket)

        self.editor.bind("<Left>", self._match_bracket)

        self.editor.bind("<KeyRelease>", self._update_status_line_col, add="+")



        # Panneau droit : onglets previsualisation / IA

        self.right_panel = ctk.CTkFrame(self.main_area, fg_color=BG_PANEL, corner_radius=0, border_width=1, border_color="#253446")

        self.right_panel.grid_columnconfigure(0, weight=1)

        self.right_panel.grid_rowconfigure(1, weight=1)

        self._pane.add(self.right_panel, minsize=120, stretch="always")



        self.tab_frame = ctk.CTkFrame(self.right_panel, fg_color=BG_PANEL, corner_radius=0)

        self.tab_frame.grid(row=0, column=0, sticky="ew", pady=(0, 1))

        self.tab_frame.grid_propagate(False)

        self.tab_frame.configure(height=34)

        self.tab_frame.grid_columnconfigure(0, weight=1)

        self.tab_frame.grid_columnconfigure(1, weight=1)



        self.tab_preview = ctk.CTkButton(self.tab_frame, text="🌐 Previsualisation", fg_color=ACCENT, text_color="#ffffff", hover_color=ACCENT_HOVER, command=lambda: self.switch_tab("preview"), font=ctk.CTkFont(size=12, weight="bold"))

        self.tab_preview.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        self.tab_ia = ctk.CTkButton(self.tab_frame, text="Assistant IA", fg_color=BG_PANEL, text_color=TEXT_MAIN, hover_color="#202c39", command=lambda: self.switch_tab("ia"), font=ctk.CTkFont(size=12, weight="bold"))

        self.tab_ia.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)



        self.tab_content = ctk.CTkFrame(self.right_panel, fg_color=BG_PANEL, corner_radius=0)

        self.tab_content.grid(row=1, column=0, sticky="nsew")

        self.tab_content.grid_columnconfigure(0, weight=1)

        self.tab_content.grid_rowconfigure(0, weight=1)

        self.tab_content.grid_rowconfigure(1, weight=0)



        # Contenu Previsualisation (temps reel)

        self.preview_frame = ctk.CTkFrame(self.tab_content, fg_color=BG_EDITOR, corner_radius=0)

        self.preview_frame.grid(row=0, column=0, sticky="nsew")

        if HtmlFrame is not None:

            self.preview = HtmlFrame(self.preview_frame, messages_enabled=False)

            self.preview.pack(fill="both", expand=True)

        else:

            self.preview = ctk.CTkTextbox(

                self.preview_frame,

                font=ctk.CTkFont(family="Consolas", size=12),

                fg_color=BG_EDITOR,
                text_color=TEXT_MAIN,

                border_width=0,

                wrap="word",

            )

            self.preview.pack(fill="both", expand=True)

            self.preview.insert(

                "1.0",

                "L'apercu integre necessite tkinterweb. Fermez puis relancez l'application "

                "avec le lanceur pour installer les dependances.",

            )

            self.preview.configure(state="disabled")



        self.preview_bar = ctk.CTkFrame(self.tab_content, fg_color=BG_PANEL, corner_radius=0)

        self.preview_bar.grid(row=1, column=0, sticky="ew")

        self.preview_bar.grid_columnconfigure(0, weight=1)

        self.preview_open_btn = ctk.CTkButton(self.preview_bar, text="🌐 Ouvrir dans le navigateur", command=self.preview_open_browser, fg_color="#6366f1", hover_color="#4f46e5", font=ctk.CTkFont(size=11, weight="bold"), height=30)

        self.preview_open_btn.pack(padx=8, pady=6)

        ctk.CTkLabel(self.preview_bar, text="Apercu HTML/CSS integre. Le JavaScript complet s'ouvre dans le navigateur.", font=ctk.CTkFont(size=9), text_color=TEXT_MUTED, wraplength=220, justify="left").pack(padx=8, pady=(0, 6))



        # Contenu Assistant IA (zone agrandie)

        self.ia_panel = ctk.CTkFrame(self.tab_content, fg_color=BG_PANEL, corner_radius=0)

        self.ia_panel.grid_columnconfigure(0, weight=1)

        self.ia_panel.grid_rowconfigure(0, weight=3)

        self.ia_panel.grid_rowconfigure(1, weight=2)

        self.ia_panel.grid_rowconfigure(2, weight=0)

        self.ia_panel.grid_rowconfigure(3, weight=0)



        self.ia_chat = ctk.CTkTextbox(self.ia_panel, font=ctk.CTkFont(family="Consolas", size=12), fg_color=BG_EDITOR, text_color=TEXT_MAIN, border_width=0)

        self.ia_chat.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 4))

        self.ia_chat.insert("1.0", "Assistant IA Calisto\nPosez vos questions sur le code ici.\nTout est enregistre : l'IA se souvient de ce qu'elle a cree/modifie meme apres fermeture.\n---\n")



        proposal_section = ctk.CTkFrame(self.ia_panel, fg_color=BG_PANEL, corner_radius=0)

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

        ).pack(side="left", padx=2)

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

        self.proposals_container = ctk.CTkScrollableFrame(proposal_section, fg_color=BG_PANEL)

        self.proposals_container.grid(row=1, column=0, sticky="nsew")

        self.proposals_container.grid_columnconfigure(0, weight=1)



        # Saisie IA (agrandie, multiligne)

        self.ia_entry = ctk.CTkTextbox(self.ia_panel, height=100, font=ctk.CTkFont(size=12), fg_color=BG_EDITOR, border_color="#253446", text_color=TEXT_MAIN)

        self.ia_entry.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 4))

        self.ia_entry.insert("1.0", "Demandez a l'IA... (Ctrl+Entree pour envoyer)")

        self.ia_entry.bind("<Key>", self.ia_key_handler)



        btn_ia_frame = ctk.CTkFrame(self.ia_panel, fg_color="transparent")

        btn_ia_frame.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 8))

        ctk.CTkButton(btn_ia_frame, text="Envoyer a l'IA", command=self.ia_send, fg_color=IA_COLOR, hover_color=IA_HOVER, font=ctk.CTkFont(size=11, weight="bold")).pack(side="right")

        ctk.CTkButton(btn_ia_frame, text="Refactoriser + commenter", command=self.refactor_and_comment, fg_color="#6366f1", hover_color="#4f46e5", font=ctk.CTkFont(size=11)).pack(side="left")



        # Afficher preview par defaut

        self.preview_frame.grid(row=0, column=0, sticky="nsew")

        self.preview_bar.grid(row=1, column=0, sticky="ew")

        self.ia_panel.grid_remove()

        self.active_tab = "preview"



        # Barre d'etat (ligne 2, pleine largeur sur les 3 colonnes)

        self.status_var = ctk.StringVar(value="Pret")

        status_bar = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0)

        status_bar.grid(row=2, column=0, columnspan=3, sticky="ew")

        ctk.CTkLabel(status_bar, textvariable=self.status_var, font=ctk.CTkFont(size=11), text_color=TEXT_MUTED).pack(side="left", padx=12, pady=4)



    def switch_tab(self, name):

        if name == self.active_tab:

            return

        self.active_tab = name

        if name == "preview":

            self.tab_preview.configure(fg_color=BG_PANEL, text_color=TEXT_MAIN, font=ctk.CTkFont(size=12))

            self.tab_ia.configure(fg_color=ACCENT, text_color="#ffffff", font=ctk.CTkFont(size=12, weight="bold"))

            self.preview_frame.grid(row=0, column=0, sticky="nsew")

            self.preview_bar.grid(row=1, column=0, sticky="ew")

            self.ia_panel.grid_remove()

        else:

            self.tab_ia.configure(fg_color=BG_PANEL, text_color=TEXT_MAIN, font=ctk.CTkFont(size=12))

            self.tab_preview.configure(fg_color=ACCENT, text_color="#ffffff", font=ctk.CTkFont(size=12, weight="bold"))

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

    def get_current_editor_context(self):
        if not self.current_file or not self.editor.winfo_exists():
            return ""
        content = self.editor.get("1.0", "end-1c")
        if len(content) > 5000:
            content = content[:2500] + "\n...[contenu tronque]...\n" + content[-2500:]
        language = LANG_EXTENSIONS.get(self.current_file.suffix.lower(), "text")
        save_state = "modifications non enregistrees" if self.unsaved else "contenu actuel"
        return "Fichier ouvert : {} ({}, {}).\n```{}\n{}\n```".format(
            self.current_file.name,
            language,
            save_state,
            language,
            content,
        )

    def create_chat_proposal(self, code, lang, requested_filename=None):
        language_aliases = {"htm": "html", "js": "javascript", "py": "python"}
        lang = language_aliases.get(lang.lower().strip(), lang.lower().strip())
        requested_path = Path(requested_filename.replace("\\", "/")) if requested_filename else None
        if lang in ("", "text", "plain") and requested_path:
            lang = LANG_EXTENSIONS.get(requested_path.suffix.lower(), lang)
        if lang in ("", "text", "plain"):
            lang = self._detect_code_language(code, lang or "text")
        if not re.fullmatch(r"[a-z0-9][a-z0-9_+-]{0,20}", lang):
            return False

        target_path = None
        if requested_path:
            if requested_path.suffix.lower() in BINARY_PROJECT_FILE_EXTENSIONS:
                return False
            if self.current_folder and self.current_folder.is_dir():
                root = self.current_folder.resolve()
                target_path = (root / requested_path).resolve()
                try:
                    target_path.relative_to(root)
                except ValueError:
                    return False
            elif self.current_file and requested_path.name.casefold() == self.current_file.name.casefold():
                target_path = self.current_file
            else:
                return False

        valid_extensions = {
            extension
            for extension, file_language in LANG_EXTENSIONS.items()
            if file_language == lang
        }
        if not valid_extensions:
            valid_extensions = {"." + lang}
        active_file_matches = self.current_file and self.current_file.suffix.lower() in valid_extensions
        if target_path is None and active_file_matches:
            if self.current_file.is_file():
                target_path = self.current_file
        elif target_path is None:
            target_path = self._resolve_proposal_target(lang)

        self._create_proposal(code, lang, target_path=target_path, save_immediately=True)
        self.switch_tab("ia")
        return True

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

                text="Aucun fichier cree depuis Calisto.\nUtilisez « Nouveau fichier ».",

                font=ctk.CTkFont(size=11),

                text_color=TEXT_MUTED,

                justify="left",

            ).pack(pady=20, padx=8)

            return

        self._add_tree_items(self.tree_frame, p)



    def _relative_key(self, path):

        """Cle relative d'un fichier dans le projet (insensible a la casse).



        Retourne None si le fichier est en dehors du dossier du projet.

        """

        if not self.current_folder:

            return None

        try:

            dossier = Path(self.current_folder).resolve()

            cible = Path(path).resolve()

        except (OSError, ValueError, RuntimeError):

            return None

        try:

            return cible.relative_to(dossier).as_posix().casefold()

        except ValueError:

            pass

        parts_dossier = [p.casefold() for p in dossier.parts]

        parts_cible = [p.casefold() for p in cible.parts]

        if len(parts_cible) > len(parts_dossier) and parts_cible[: len(parts_dossier)] == parts_dossier:

            return Path(*parts_cible[len(parts_dossier):]).as_posix()

        return None



    def _is_managed_file(self, path):

        cle = self._relative_key(path)

        return cle is not None and cle in self._managed_files



    def _is_available_project_file(self, path):

        return self._is_managed_file(path) or (

            self.current_file is not None

            and Path(path).resolve() == self.current_file.resolve()

        )



    def _has_managed_descendant(self, path):

        cle = self._relative_key(path)

        if cle is None:

            return False

        prefix = "" if cle == "." else cle.rstrip("/") + "/"

        return any(item.startswith(prefix) for item in self._managed_files)



    def _register_managed_file(self, path):

        cle = self._relative_key(path)

        if cle is None:

            raise ValueError("Le fichier doit rester dans le dossier du projet.")

        self._managed_files.add(cle)

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

            lbl.bind("<Button-3>", lambda e, p=item: self._show_tree_menu(e, p))

            row.bind("<Button-3>", lambda e, p=item: self._show_tree_menu(e, p))

            if item.is_dir():

                self._add_tree_items(row, item, indent + 1)



    def on_tree_click(self, path):

        self.selected_tree_item = path

        self._refresh_tree()

        if not path.is_dir():

            self.open_file(path)



    # ---------- Menu contextuel de l'explorateur ----------



    def _show_tree_menu(self, event, path):

        """Menu clic droit sur un element de l'explorateur."""

        import tkinter as tk



        self.selected_tree_item = path

        menu = tk.Menu(self, tearoff=0)

        if path.is_dir():

            menu.add_command(label="📂 Ouvrir le dossier", command=lambda: self._reveal_in_explorer(path))

        else:

            menu.add_command(label="📂 Ouvrir dans l'editeur", command=lambda: self.on_tree_click(path))

            menu.add_command(label="✏️ Renommer", command=lambda: self._rename_tree_item(path))

            menu.add_command(label="📄 Copier le contenu", command=lambda: self._copy_tree_content(path))

            menu.add_command(label="⧉ Dupliquer", command=lambda: self._duplicate_tree_item(path))

        menu.add_command(label="📋 Copier le chemin", command=lambda: self._copy_tree_path(path))

        menu.add_command(label="👁 Tout afficher les fichiers du projet", command=self._import_project_files)

        menu.add_separator()

        menu.add_command(label="📁 Afficher dans l'Explorateur Windows", command=lambda: self._reveal_in_explorer(path))

        menu.add_command(label="🗑️ Supprimer", command=lambda: self._delete_tree_item(path))

        try:

            menu.tk_popup(event.x_root, event.y_root)

        finally:

            menu.grab_release()



    def _copy_tree_path(self, path):

        self.clipboard_clear()

        self.clipboard_append(str(path))

        self.status_var.set("Chemin copie : {}".format(path))



    def _copy_tree_content(self, path):

        try:

            content = path.read_text(encoding="utf-8-sig")

        except Exception as e:

            messagebox.showerror("Erreur", "Impossible de copier le contenu :\n{}".format(e))

            return

        self.clipboard_clear()

        self.clipboard_append(content)

        self.status_var.set("Contenu de {} copie dans le presse-papiers".format(path.name))



    def _duplicate_tree_item(self, path):

        if not path.is_file():

            return

        target = path.with_name("{}_copie{}".format(path.stem, path.suffix))

        index = 2

        while target.exists():

            target = path.with_name("{}_copie{}{}".format(path.stem, index, path.suffix))

            index += 1

        try:

            shutil.copy2(path, target)

        except Exception as e:

            messagebox.showerror("Erreur", "Impossible de dupliquer le fichier :\n{}".format(e))

            return

        try:

            self._register_managed_file(target)

        except ValueError:

            pass

        self.selected_tree_item = target

        self._refresh_tree()

        self._save_session()

        self.status_var.set("Copie creee : {}".format(target.name))



    def _rename_tree_item(self, path):

        new_name = ctk.CTkInputDialog(text="Nouveau nom pour '{}' :".format(path.name), title="Renommer").get_input()

        if not new_name or new_name == path.name:

            return

        target = path.with_name(new_name)

        if target.exists():

            messagebox.showwarning("Existe deja", "Un element nomme '{}' existe deja.".format(new_name))

            return

        etait_fichier = path.is_file()

        cle_avant = self._relative_key(path)

        try:

            path.rename(target)

        except OSError as e:

            messagebox.showerror("Erreur", "Renommage impossible :\n{}".format(e))

            return

        if cle_avant:

            self._managed_files.discard(cle_avant)

        cle_apres = self._relative_key(target)

        if etait_fichier and cle_apres:

            self._managed_files.add(cle_apres)

        self._file_buffers.pop(path.resolve(), None)

        self._file_buffers.pop(target.resolve(), None)

        if self.current_file and Path(self.current_file).resolve() == path.resolve():

            self.current_file = target

            self.file_name_label.configure(text=target.name)

        self.selected_tree_item = target

        self._refresh_tree()

        self._save_session()

        if etait_fichier and not cle_apres:

            messagebox.showwarning(

                "Fichier masque",

                "Le fichier a ete renomme sur le disque mais reste invisible dans l'explorateur.\n"

                "Utilisez « Tout afficher » dans l'en-tete de l'explorateur pour le reafficher.",

            )

            self.status_var.set("Renomme : {}".format(target.name))

        else:

            self.status_var.set("Renomme : {}".format(target.name))



    def _reveal_in_explorer(self, path):

        try:

            if path.is_dir():

                os.startfile(str(path))

            else:

                subprocess.Popen(["explorer", "/select,{}".format(path)])

        except Exception as e:

            messagebox.showerror("Erreur", "Impossible d'ouvrir l'Explorateur Windows :\n{}".format(e))



    def _delete_tree_item(self, path):

        if not path or not path.exists():

            return

        if path.is_dir():

            nb = sum(1 for element in path.rglob("*") if element.is_file())

            confirm = messagebox.askyesno(

                "Supprimer le dossier",

                "Supprimer le dossier '{}' et ses {} fichier(s) cree(s) depuis Calisto ?".format(path.name, nb),

            )

        else:

            confirm = messagebox.askyesno("Supprimer", "Supprimer le fichier '{}' ?".format(path.name))

        if not confirm:

            return

        self._remove_path(path)

        if self.current_file and Path(self.current_file).resolve() == path.resolve():

            self.current_file = None

            self.editor.delete("1.0", "end")

            self.file_name_label.configure(text="Aucun fichier")

            self.lang_label.configure(text="")

            self._update_preview()

        self.selected_tree_item = None

        self._refresh_tree()

        self._save_session()

        self.status_var.set("Supprime : {}".format(path.name))



    def _remove_path(self, path):

        """Supprime un fichier ou un dossier (uniquement les fichiers geres par Calisto)."""

        try:

            if path.is_file():

                self._file_buffers.pop(path.resolve(), None)

                path.unlink()

                self._forget_managed_file(path)

                return

            for element in sorted(path.rglob("*"), key=lambda p: len(p.parts), reverse=True):

                if element.is_file() and self._is_managed_file(element):

                    self._file_buffers.pop(element.resolve(), None)

                    element.unlink()

                    self._forget_managed_file(element)

            for folder in sorted((d for d in path.rglob("*") if d.is_dir()), key=lambda p: len(p.parts), reverse=True):

                try:

                    folder.rmdir()

                except OSError:

                    pass

            try:

                path.rmdir()

            except OSError:

                pass

        except OSError as e:

            messagebox.showerror("Erreur", "Suppression impossible :\n{}".format(e))



    def _forget_managed_file(self, path):

        cle = self._relative_key(path)

        if cle is not None:

            self._managed_files.discard(cle)



    def _import_project_files(self):

        """Affiche dans l'explorateur tous les fichiers de code du dossier du projet."""

        if not self.current_folder or not Path(self.current_folder).is_dir():

            messagebox.showwarning("Aucun dossier", "Ouvrez d'abord un dossier de projet.")

            return

        ajoutes = 0

        for element in Path(self.current_folder).rglob("*"):

            if element.is_file() and element.suffix.lower() in LANG_EXTENSIONS:

                cle = self._relative_key(element)

                if cle and cle not in self._managed_files:

                    self._managed_files.add(cle)

                    ajoutes += 1

        self._save_session()

        self._refresh_tree()

        self.status_var.set("{} fichier(s) affiche(s) dans l'explorateur".format(ajoutes))



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

            messagebox.showwarning("Nom invalide", "Le fichier doit etre cree dans le dossier du projet.")

            return

        if p.exists():

            if self._is_managed_file(p):

                messagebox.showwarning("Existe deja", "Le fichier '{}' existe deja.".format(name))

            elif messagebox.askyesno(

                "Fichier deja present",

                "Le fichier '{}' existe deja dans le dossier mais n'apparait pas dans l'explorateur.\n\nL'afficher ?".format(name),

            ):

                try:

                    self._register_managed_file(p)

                except ValueError:

                    pass

                self._refresh_tree()

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

        self.status_var.set("Fichier cree : {}".format(name))

        self._log_ia_action("creer_fichier", name)



    def delete_selected(self):

        if not self.selected_tree_item:

            messagebox.showwarning("Aucune selection", "Selectionnez un fichier dans l'explorateur.")

            return

        self._delete_tree_item(self.selected_tree_item)



    def open_file(self, path):

        p = Path(path)

        if not p.is_file():

            return

        if p.suffix.lower() in BINARY_PROJECT_FILE_EXTENSIONS:

            if self._open_external_file(p):

                self.status_var.set("Ouvert dans l'application systeme : {}".format(p.name))

            else:

                messagebox.showwarning(
                    "Apercu impossible",
                    "Aucune application n'est associee a ce type de fichier ({}).".format(p.suffix.lower()),
                )

            return

        self._invalidate_inline_completion()

        self._cache_current_buffer()

        try:

            content = self._file_buffers.get(p.resolve())

            if content is None:

                content = p.read_text(encoding="utf-8-sig")

        except UnicodeDecodeError:

            content = "[Fichier binaire, impossible a afficher]"

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

        # Expand only when the tag word is standalone: at line start or after whitespace or '<'
        if prev and not prev.isspace() and prev != '<':

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

        try:
            char = getattr(event, "char", "")
        except Exception:
            char = ""

        if char and char in pairs:

            # Ne pas auto-fermer si le caractere est deja present juste apres le curseur (evite les doublons)

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

        # Gerer la fermeture : si l'utilisateur tape )}], et que le char suivant est deja le meme, avancer seulement

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

        try:
            if char and self.current_file.suffix.lower() in (".html", ".htm") and char.isalpha():
                if self._auto_expand_html_tag():
                    return "break"
        except Exception:
            pass

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

            # Detecter si deja commente (premiere ligne non vide commence par le prefix)

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



    def _select_line(self, event=None):

        tw = self._text_widget()

        tw.tag_remove("sel", "1.0", "end")

        tw.tag_add("sel", "insert linestart", "insert lineend+1c")

        return "break"



    def _delete_line(self, event=None):

        tw = self._text_widget()

        tw.delete("insert linestart", "insert lineend+1c")

        return "break"



    def _insert_line_below(self, event=None):

        tw = self._text_widget()

        tw.insert("insert lineend", "\n")

        tw.mark_set("insert", "insert+1l linestart")

        return "break"



    def _insert_line_above(self, event=None):

        tw = self._text_widget()

        tw.insert("insert linestart", "\n")

        tw.mark_set("insert", "insert-1l linestart")

        return "break"



    def _move_line_up(self, event=None):

        tw = self._text_widget()

        cur = tw.index("insert")

        line = tw.get("insert linestart", "insert lineend")

        tw.delete("insert linestart", "insert lineend+1c")

        tw.insert("insert linestart-1l", line + "\n")

        tw.mark_set("insert", cur)

        return "break"



    def _move_line_down(self, event=None):

        tw = self._text_widget()

        cur = tw.index("insert")

        line = tw.get("insert linestart", "insert lineend")

        tw.delete("insert linestart", "insert lineend+1c")

        tw.insert("insert lineend+1c", "\n" + line)

        tw.mark_set("insert", cur)

        return "break"



    def _indent(self, event=None):

        tw = self._text_widget()

        tw.insert("insert", "    ")

        return "break"



    def _outdent(self, event=None):

        tw = self._text_widget()

        line_start = tw.index("insert linestart")

        line = tw.get(line_start, "insert lineend")

        if line.startswith("    "):

            tw.delete(line_start, "{}+4c".format(line_start))

        elif line.startswith("\t"):

            tw.delete(line_start, "{}+1c".format(line_start))

        return "break"



    def _select_next_occurrence(self, event=None):

        tw = self._text_widget()

        try:

            sel = tw.get("sel.first", "sel.last")

        except Exception:

            word = tw.get("insert wordstart", "insert wordend")

            if not word:

                return "break"

            sel = word

        # find next

        start = tw.index("sel.last" if tw.tag_ranges("sel") else "insert")

        idx = tw.search(sel, start, stopindex="end")

        if idx:

            tw.tag_remove("sel", "1.0", "end")

            tw.tag_add("sel", idx, "{}+{}c".format(idx, len(sel)))

            tw.mark_set("insert", "{}+{}c".format(idx, len(sel)))

            tw.see(idx)

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

                self.status_var.set("Remplacement termine")



        ctk.CTkButton(btns, text="Trouver suivant", command=lambda: do_find(1), fg_color=ACCENT, hover_color=ACCENT_HOVER, font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=6, pady=4)

        ctk.CTkButton(btns, text="Trouver precedent", command=lambda: do_find(-1), fg_color="#6b7280", hover_color="#4b5563", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=6, pady=4)

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

        dlg = ctk.CTkInputDialog(text="Numero de ligne :", title="Aller a la ligne")

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

        self.status_var.set("Retour a la ligne : {}".format("ON" if new == "char" else "OFF"))



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

        # Implementation simple : scan ligne par ligne (evite la recursion lourde)

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

            # chercher vers l'arriere

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

        self._completion_job = self.after(400, self._request_inline_completions)



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

                    "Si tu vois un debut de balise HTML partiel comme '<p' ou un mot-cle juste apres '<' incomplet, " \
                            "REMPLACE ce fragment partiel par la balise complete correcte (pas en l'ajoutant a cote). " \
                            "Si le mode demande de remplacer la ligne, retourne la ligne corrigee complete en "

                    "preservant l'indentation et ce que l'utilisateur a deja ecrit. Sinon, retourne "

                    "uniquement le suffixe a inserer au curseur. Ne repete pas du code existant. "

                    "REGLE OBLIGATOIRE : ecris toujours les caracteres en brut UTF-8 (apostrophe ', accent e/e/e, etc.). "

                    "N'utilise JAMAIS d'entites HTML (&#39;, &amp;, &eacute;, &egrave;, &ecirc;, &quot;, &lt;, &gt; ...). "

                    "Variante {}: propose une approche differente mais valide pour le meme contexte."

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
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except tk.TclError:
                return

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

            # Coordinates du curseur en coordonnees ecran (fiables pour un Toplevel)

            sx = text_widget.winfo_rootx() + x

            sy = text_widget.winfo_rooty() + y + line_height

            widget_width = max(1, text_widget.winfo_width())

            popup_width = min(400, max(220, widget_width - 40))

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

            self.status_var.set("Completion inline indisponible : {}".format(message))



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

            # Ne pas remplacer automatiquement les abreviations courtes (p, a, i, etc.)

            # pour eviter que taper "p" remplace directement par <p>. Proposer seulement.

            stripped = line.strip().lower().lstrip("<").rstrip()

            if line.lower().startswith("<") and stripped in KEYWORDS["html"] and len(stripped) > 1:

                return "completer l'abreviation HTML {} en element complet".format(stripped)

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

            self._preview_job = self.after(250, self._update_preview)



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

            self.status_var.set("Structure HTML inseree (!)")

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

        # Formateur HTML simple base sur l'indentation des balises

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

            # Balises d'ouverture -> augmenter l'indentation apres

            mopen = re.findall(r"<(\w+)([^>]*)>", line)

            for tag, attrs in mopen:

                tag = tag.lower()

                if tag in block_close and not line.rstrip().endswith("</{}>".format(tag)):

                    indent += 1

            # Balises auto-fermantes ou fermees sur la meme ligne ne font rien de plus

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

        for tag, label in [("kw", "Mots-cles"), ("str", "Chaines"), ("comment", "Commentaires"), ("func", "Fonctions"), ("number", "Nombres"), ("tag", "Balises HTML"), ("attr", "Attributs"), ("bool", "Booleens")]:

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

            ctk.CTkButton(row, text="🎨", width=30, command=pick, fg_color="#3a3a3e", hover_color="#4a4a4e").pack(side="left", padx=2)

            entries[tag] = var



        def save_colors():

            for tag, var in entries.items():

                TAG_COLORS[tag] = var.get()

            self._do_highlight()

            win.destroy()



        ctk.CTkButton(win, text="Enregistrer", command=save_colors, fg_color=ACCENT, hover_color=ACCENT_HOVER, font=ctk.CTkFont(size=12, weight="bold")).pack(pady=15)

        ctk.CTkButton(win, text="Reinitialiser", command=lambda: self._reset_colors(entries), fg_color="#6b7280", hover_color="#4b5563").pack(pady=(0, 20))



    def _reset_colors(self, entries):

        global TAG_COLORS

        TAG_COLORS = dict(DEFAULT_TAG_COLORS)

        for tag, variable in entries.items():

            variable.set(TAG_COLORS[tag])

        self._do_highlight()





    # ---------- Previsualisation instantanee ----------



    def _build_preview_html(self):

        if not self.current_file:

            return "<html><body><p>Ouvrez un fichier HTML, CSS ou JavaScript pour afficher l'apercu du projet.</p></body></html>"



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

                return "<html><body><p>Creez un fichier HTML dans ce dossier pour previsualiser ce projet.</p></body></html>"

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

            return "<html><body><p>La previsualisation est disponible pour les fichiers HTML, CSS et JavaScript.</p></body></html>"



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



            if extension == ".css":

                stylesheet = self._resolve_css_asset_urls(

                    self.editor.get("1.0", "end-1c"),

                    self.current_file.parent,

                    self.current_folder,

                )

                style = "<style data-calisto-css>\n{}\n</style>".format(stylesheet)

                content = re.sub(r"<style[^>]*data-calisto-css[^>]*>.*?</style>\s*", "", content, flags=re.IGNORECASE|re.DOTALL)

                if re.search(r"<head[^>]*>", content, re.IGNORECASE):
                    content = re.sub(r"<head[^>]*>", lambda m: m.group(0) + "\n" + style, content, count=1, flags=re.IGNORECASE)
                elif re.search(r"</head\s*>", content, re.IGNORECASE):
                    content = re.sub(r"</head\s*>", style + "\n</head>", content, count=1, flags=re.IGNORECASE)
                elif re.search(r"<body[^>]*>", content, re.IGNORECASE):
                    content = re.sub(r"<body[^>]*>", lambda m: m.group(0) + "\n" + style, content, count=1, flags=re.IGNORECASE)
                elif re.search(r"<html[^>]*>", content, re.IGNORECASE):
                    content = re.sub(r"<html[^>]*>", lambda m: m.group(0) + "\n<head>" + style + "</head>", content, count=1, flags=re.IGNORECASE)
                else:
                    content = "<!DOCTYPE html><html><head>" + style + "</head><body>" + content + "</body></html>"

            elif extension in (".html", ".htm"):

                content, stylesheet_path = self._prepare_html_stylesheet(html_file, content)

                try:
                    if stylesheet_path.is_file():

                        stylesheet = self._resolve_css_asset_urls(

                            self._read_project_file(stylesheet_path),

                            stylesheet_path.parent,

                            self.current_folder,

                        )

                        style = "<style data-calisto-css>\n{}\n</style>".format(stylesheet)
                        content = re.sub(r"<style[^>]*data-calisto-css[^>]*>.*?</style>\s*", "", content, flags=re.IGNORECASE|re.DOTALL)

                        if re.search(r"<head[^>]*>", content, re.IGNORECASE):

                            content = re.sub(r"<head[^>]*>", lambda m: m.group(0) + "\n" + style, content, count=1, flags=re.IGNORECASE)

                        elif re.search(r"</head\s*>", content, re.IGNORECASE):

                            content = re.sub(r"</head\s*>", style + "\n</head>", content, count=1, flags=re.IGNORECASE)

                        elif re.search(r"<body[^>]*>", content, re.IGNORECASE):

                            content = re.sub(r"<body[^>]*>", lambda m: m.group(0) + "\n" + style, content, count=1, flags=re.IGNORECASE)

                        else:

                            content = style + "\n" + content
                except Exception:
                    pass

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

                    "L'apercu rendu necessite tkinterweb. Fermez Calisto puis relancez-le avec « Lancer IA.bat » pour installer cette dependance.",

                )

                self.preview.configure(state="disabled")

        except Exception as error:

            self.status_var.set("Erreur de previsualisation : {}".format(error))



    def preview_html(self):

        if not self.current_file:

            messagebox.showwarning("Aucun fichier", "Ouvrez un fichier HTML d'abord.")

            return

        if self.current_file.suffix.lower() not in (".html", ".css", ".js"):

            messagebox.showwarning("Apercu indisponible", "La previsualisation est disponible pour les fichiers HTML, CSS et JavaScript.")

            return

        self._update_preview()

        self.status_var.set("Apercu du projet actualise")



    def _find_browser_exe(self):

        """Cherche un navigateur web installe sur Windows pour eviter d'ouvrir Acrobat PDF."""

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

            messagebox.showwarning("Apercu indisponible", "Ouvrez un fichier HTML, CSS ou JavaScript d'abord.")

            return

        content = self._build_preview_html()

        preview_file = self.current_file.parent / ("preview_" + self.current_file.name)

        try:

            preview_file.write_text(content, encoding="utf-8")

            url = preview_file.resolve().as_uri()

        except OSError as error:

            messagebox.showerror(

                "Erreur d'apercu",

                "Impossible d'enregistrer la page de previsualisation :\n{}".format(error),

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

                raise RuntimeError("Le navigateur par defaut n'a pas pu ouvrir la page.")

            self.status_var.set("Ouvert dans le navigateur par defaut")

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

        if (
            self.current_file.suffix.lower() in BINARY_PROJECT_FILE_EXTENSIONS
            and self.current_file.exists()
        ):

            messagebox.showwarning(
                "Fichier binaire",
                "Un fichier binaire ({}) ne peut pas etre modifie dans l'editeur. "
                "Generez-le avec l'IA ou ouvrez-le dans une application dediee.".format(
                    self.current_file.suffix.lower()
                ),
            )

            return

        self.selected_tree_item = self.current_file

        try:

            creating_file = not self.current_file.exists()

            # Creer le dossier parent si necessaire

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

        self.status_var.set("Version sauvegardee : {}".format(version_name))



    def load_project_version(self, selection):

        if selection == "Aucun" or selection not in self.versions:

            return

        vers_list = self.versions[selection]

        if not vers_list:

            return

        liste = "\n".join("- {} ({})".format(x["name"], x["date"]) for x in vers_list[:8])

        dlg = ctk.CTkInputDialog(text="Versions pour '{}' :\n{}\n\nNom de la version a charger :".format(selection, liste), title="Charger une version")

        choose = dlg.get_input()

        if not choose:

            return

        target = None

        for x in vers_list:

            if x["name"] == choose:

                target = x

                break

        if not target:

            messagebox.showwarning("Introuvable", "Version non trouvee.")

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

        self.status_var.set("Version '{}' chargee pour '{}'".format(choose, selection))

        self._save_session()



    # ---------- Assistant IA (connecte et persistant) ----------



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

        if not content or content == "Demandez a l'IA... (Ctrl+Entree pour envoyer)":

            return

        if not self.parent_app.begin_editor_exchange(content):

            messagebox.showinfo("IA occupee", "L'IA centrale traite deja une demande. Reessayez apres sa reponse.")

            return



        # Fenetre de progression

        prog = ctk.CTkToplevel(self)

        prog.title("Generation en cours")

        prog.geometry("400x150")

        prog.configure(fg_color=BG_PANEL)

        prog.transient(self)

        prog.grab_set()

        prog.resizable(False, False)



        ctk.CTkLabel(prog, text="L'IA genere votre code…", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT_MAIN).pack(pady=(20, 10))

        pb = ctk.CTkProgressBar(prog, width=300)

        pb.pack(pady=10)

        pb.set(0)

        lbl = ctk.CTkLabel(prog, text="0%", font=ctk.CTkFont(size=12), text_color=TEXT_MUTED)

        lbl.pack()



        # Animation simple de la barre

        def animate(i=0):

            if i <= 100:

                pb.set(i / 100)

                lbl.configure(text="{}%".format(i))

                prog.after(30, lambda: animate(i + 5))

            else:

                pb.set(1)

                lbl.configure(text="100%")



        animate()



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

        self.status_var.set("L'IA analyse les fichiers du projet et prepare une reponse…")



        def worker():

            try:

                texte = self.parent_app.ask_ai_central(content, context_files)

            except Exception as e:

                self.after(0, lambda error=str(e): (prog.destroy(), self._handle_ia_error(error)))

                return

            self.after(0, lambda: (prog.destroy(), self._handle_ia_response(texte)))

        threading.Thread(target=worker, daemon=True).start()

        return "break"



    def _handle_ia_response(self, texte):

        self.parent_app.finish_editor_exchange(response=texte)

        self.ia_append("Calisto : {}".format(texte))

        blocks = re.findall(r"```([^\n`]*)\n(.*?)```", texte, re.DOTALL)

        if not blocks:

            self.status_var.set(

                "Reponse recue sans proposition. Demandez le code complet dans un bloc avec son fichier cible."

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

                        self.ia_append("Aucune feuille CSS existante trouvee pour la proposition integree au HTML.")

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

                "{} bloc(s) redondant(s) pour le meme fichier ignore(s); une seule version, la plus complete, est conservee.".format(

                    duplicate_count

                )

            )

        created_files = []

        for code, lang, target in consolidated_proposals.values():

            if target and not target.exists():

                try:

                    created_files.append(self._create_ai_file(target, code, lang))

                except (OSError, ValueError) as error:

                    self.ia_append("Impossible de creer {} automatiquement : {}".format(target.name, error))

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

                "Fichier(s) cree(s) automatiquement : {}".format(

                    ", ".join(path.name for path in created_files)

                )

            )

            self.ia_append(

                "Fichier(s) cree(s) automatiquement : {}".format(

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

        normalized_lang = lang.lower()
        valid_extensions = {
            extension
            for extension, file_language in LANG_EXTENSIONS.items()
            if file_language == normalized_lang
        }
        if not valid_extensions and re.fullmatch(r"[a-z0-9][a-z0-9_+-]{0,20}", normalized_lang):
            valid_extensions = {"." + normalized_lang}
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
            "markdown": ("README.md",),
            "yaml": ("config.yml", "config.yaml"),
            "toml": ("pyproject.toml", "config.toml"),
            "xml": ("document.xml",),
            "sql": ("schema.sql", "database.sql"),
        }.get(lang.lower(), ())

        for preferred in preferred_names:

            match = next((path for path in candidates if path.name.lower() == preferred), None)

            if match:

                return match

        return candidates[0] if len(candidates) == 1 else None



    def _new_ai_file_path(self, lang, requested_filename=None):
        if not self.current_folder or not self.current_folder.is_dir():
            return None
        normalized_lang = lang.lower()
        extension = next(
            (suffix for suffix, file_language in LANG_EXTENSIONS.items() if file_language == normalized_lang),
            None,
        )
        if not extension and re.fullmatch(r"[a-z0-9][a-z0-9_+-]{0,20}", normalized_lang):
            extension = "." + normalized_lang
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

            if not candidate.suffix and not candidate.name.startswith("."):
                candidate = candidate.with_name(candidate.name + extension)
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
            candidate = root / default_names.get(normalized_lang, "nouveau_fichier" + extension)



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

            raise ValueError("Le fichier propose doit rester dans le dossier du projet.")

        path.parent.mkdir(parents=True, exist_ok=True)

        try:

            with path.open("x", encoding="utf-8", newline="") as output:

                output.write(code)

        except FileExistsError:

            raise FileExistsError("Le fichier {} existe deja; aucune donnee n'a ete ecrasee.".format(path.name))

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



    def _create_proposal(self, code, lang, target_path=None, save_immediately=False):

        lang = self._detect_code_language(code, lang)

        if target_path is None:

            target_path = self._resolve_proposal_target(lang)

        frame = ctk.CTkFrame(self.proposals_container, fg_color=BG_PANEL, corner_radius=8)

        frame.pack(fill="x", padx=6, pady=6)



        target_label = target_path.relative_to(self.current_folder).as_posix() if target_path and self.current_folder else "Fichier cible a choisir"

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

            text="Code propose — modifiable avant validation",

            font=ctk.CTkFont(size=10),

            text_color=TEXT_MUTED,

        ).pack(anchor="w", padx=8, pady=(0, 3))

        line_count = code.count("\n") + 1

        preview_height = min(360, max(150, line_count * 19))

        code_box = ctk.CTkTextbox(frame, height=preview_height, font=ctk.CTkFont(family="Consolas", size=12), fg_color=BG_EDITOR, text_color=TEXT_MAIN, border_width=0)

        code_box.insert("1.0", code)

        code_box.pack(fill="x", padx=8, pady=(0, 6))



        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")

        btn_frame.pack(anchor="e", padx=8, pady=(0, 8))



        if target_path and target_path.is_file():
            apply_label = (
                "✅ Accepter et enregistrer dans {}".format(target_path.name)
                if save_immediately
                else "✅ Valider dans {}".format(target_path.name)
            )
            if save_immediately:
                apply_command = lambda c=code_box, p=target_path, f=frame: self._apply_chat_proposal(
                    c.get("1.0", "end-1c"), p, f
                )
            else:
                apply_command = lambda c=code_box, p=target_path, f=frame: self._apply_proposal(
                    c.get("1.0", "end-1c"), p, f
                )
            ctk.CTkButton(
                btn_frame,
                text=apply_label,
                width=190 if save_immediately else 150,
                command=apply_command,
                fg_color=ACCENT,
                hover_color=ACCENT_HOVER,
                font=ctk.CTkFont(size=11, weight="bold"),

            ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(

            btn_frame,

            text="📄 Creer fichier",

            width=110,

            command=lambda c=code_box, l=lang, p=target_path, f=frame: self._create_file_proposal(

                c.get("1.0", "end-1c"), l, p, f

            ),

            fg_color="#6366f1",

            hover_color="#4f46e5",

            font=ctk.CTkFont(size=11, weight="bold"),

        ).pack(side="left", padx=(0, 6))



        self.proposals.append({"frame": frame, "code": code, "lang": lang, "target": target_path})

        self.status_var.set("Nouvelle proposition de code — Valider / Creer fichier / Refuser")
        self._save_session()

    def _apply_chat_proposal(self, code, target_path, proposal_frame):
        self._apply_proposal(code, target_path, proposal_frame=None)
        if self.unsaved:
            self.save_file()
        if not self.unsaved and proposal_frame:
            try:
                if proposal_frame.winfo_exists():
                    proposal_frame.destroy()
            except Exception:
                pass
            self.proposals = [p for p in self.proposals if p["frame"] is not proposal_frame]
            self.status_var.set("Code accepte et enregistre dans {}".format(target_path.name))
            self._save_session()

    def _apply_proposal(self, code, target_path=None, proposal_frame=None):

        if target_path is None:

            lang = self._detect_code_language(code, LANG_EXTENSIONS.get(self.current_file.suffix.lower(), "text") if self.current_file else "text")

            target_path = self._resolve_proposal_target(lang)

        if not target_path:

            messagebox.showwarning("Fichier cible", "Aucun fichier existant du bon type n'a ete trouve. Choisissez « Creer fichier » pour ne pas melanger les langages.")

            return

        if target_path.suffix.lower() == ".pdf":

            generer_pdf_minimal(target_path.stem.replace("_", " "), code, target_path)

            self._register_managed_file(target_path)

            self._refresh_tree()

            self.status_var.set("PDF mis a jour : {}".format(target_path.name))

            self._log_ia_action("appliquer_proposition", target_path.name)

            if proposal_frame:

                self._reject_proposal(proposal_frame)

            self._open_external_file(target_path)

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

        self.status_var.set("Code IA applique dans l'editeur (en attente d'enregistrement)")

        self._schedule_highlight()

        self._schedule_preview()

        self._refresh_tree()

        self._log_ia_action("appliquer_proposition", "code dans l'editeur")

        if proposal_frame:

            self._reject_proposal(proposal_frame)



    def _open_external_file(self, chemin):
        try:
            if hasattr(os, "startfile"):
                os.startfile(str(chemin))
                return True
        except Exception:
            pass
        try:
            return webbrowser.open(Path(chemin).resolve().as_uri())
        except Exception:
            return False

    def _create_file_proposal(self, code, lang, target_path=None, proposal_frame=None):

        if not self.current_folder:

            messagebox.showwarning("Aucun dossier", "Ouvrez d'abord un dossier de projet.")

            return

        normalized_lang = lang.lower()
        ext = target_path.suffix if target_path and target_path.suffix else next(
            (suffix for suffix, file_language in LANG_EXTENSIONS.items() if file_language == normalized_lang),
            "",
        )
        if not ext and re.fullmatch(r"[a-z0-9][a-z0-9_+-]{0,20}", normalized_lang):
            ext = "." + normalized_lang
        if target_path and self.current_folder:
            default_name = target_path.relative_to(Path(self.current_folder).resolve()).as_posix()
        else:
            default_name = "nouveau_fichier" + ext

        dlg = ctk.CTkInputDialog(text="Nom du nouveau fichier (ex: " + default_name + ") :", title="Creer fichier")

        name = dlg.get_input()

        if not name:

            return

        if ext and not Path(name).suffix and not Path(name).name.startswith("."):
            name = name + ext

        p = (Path(self.current_folder) / name).resolve()

        try:

            p.relative_to(Path(self.current_folder).resolve())

        except ValueError:

            messagebox.showwarning("Nom invalide", "Le fichier doit etre cree dans le dossier du projet.")

            return

        if p.exists():

            if not messagebox.askyesno("Existe deja", "Le fichier " + name + " existe deja. L'ecraser ?"):

                return

        try:

            p.parent.mkdir(parents=True, exist_ok=True)

            if p.suffix.lower() == ".pdf":

                generer_pdf_minimal(p.stem.replace("_", " "), code, p)

                self._register_managed_file(p)

                self._refresh_tree()

                if proposal_frame:

                    self._reject_proposal(proposal_frame)

                self.status_var.set("PDF cree : {}".format(name))

                self._log_ia_action("creer_fichier_ia", name)

                self._save_session()

                self._open_external_file(p)

                return

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

            self.status_var.set("Fichier cree : {}".format(name))

            self._log_ia_action("creer_fichier_ia", name)

            self._save_session()

        except Exception as e:

            messagebox.showerror("Erreur creation", str(e))



    def _reject_proposal(self, frame):

        try:

            if frame.winfo_exists():

                frame.destroy()

        except Exception:

            pass

        self.proposals = [p for p in self.proposals if p["frame"] is not frame]

        if not self.proposals:

            self.status_var.set("Proposition refusee")

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

            self.status_var.set("Toutes les propositions ont ete refusees")

            self._save_session()



    def ask_ai_help(self):

        code = self.editor.get("1.0", "end-1c")

        if not code.strip():

            messagebox.showwarning("Vide", "Il n'y a aucun code a analyser.")

            return

        self.switch_tab("ia")

        self.ia_entry.delete("1.0", "end")

        self.ia_entry.insert("1.0", "Analyse ce code et donne-moi des conseils d'amelioration avec des blocs de code corriges :")

        self.ia_entry.focus_set()

        self.status_var.set("Ecrivez votre demande, puis cliquez sur 'Envoyer a l'IA'")



    def on_close(self):

        self._invalidate_inline_completion()

        self._save_session()
