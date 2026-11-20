import ast
import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
import ollama
import threading
import os
import shutil
import tempfile
import hashlib
import base64
import binascii
import json
import re
import queue
import random
import time
import unicodedata
import html
from pathlib import Path
from ddgs import DDGS
from PyPDF2 import PdfReader
from fpdf import FPDF
import pypdfium2 as pdfium
import urllib.request
import ctypes
import sys
import traceback
import webbrowser
import subprocess

try:
    from dev_window import DevWindow
except Exception:
    DevWindow = None

LEARNING_HTML_BOILERPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Document</title>
</head>
<body>

</body>
</html>"""

try:
    import ai_runtime
except Exception:
    ai_runtime = None

try:
    import image_generation
except Exception:
    image_generation = None

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

MODEL = "qwen2.5:7b"
VERSION = "1.3.0"
MAX_WEB_SEARCH_ROUNDS = 3
MAX_WEB_SEARCH_CALLS = 3
MAX_GENERATED_FILE_BYTES = 5 * 1024 * 1024
PDF_CREATION_START_PATTERN = r"\[CREER_FICHIER(?:_BASE64)?:\s*[^\]\r\n]+\.pdf\]"
PDF_CREATION_BLOCK_PATTERN = (
    r"\[CREER_FICHIER(?:_BASE64)?:\s*[^\]\r\n]+\.pdf\]"
    r".*?\[/CREER_FICHIER(?:_BASE64)?\]"
)
PDF_ALIAS_TAG_PATTERN = r"\[(?:TAG(?:É|E)?|FICHIER)\s*:\s*([^\]\r\n]+\.pdf)\]"
PDF_RESPONSE_HINT_PATTERN = (
    r"(?im)(?:^\s*(?:(?:voici|voilà)\s+(?:le|un|une)?\s*pdf"
    r"(?:\s+(?:cr[eé][eé]|g[eé]n[eé]r[eé]|simple|t[eé]l[eé]chargeable))?"
    r"|je vais\s+(?:cr[eé]er|g[eé]n[eé]rer)\s+(?:le|un|une)?\s*pdf)\b"
    r"|\bfichier\s+t[eé]l[eé]chargeable\b|\bcode source du pdf\b)"
)
PDF_CREATION_ACTION_PATTERN = (
    r"creer|cree|creez|creation|faire|fait|fais|fasse|fabriquer|fabrique|"
    r"produire|produis|produisez|generer|genere|generez|ecrire|ecris|ecrivez|"
    r"rediger|redige|redigez|preparer|prepare|preparez|convertir|convertis|"
    r"exporter|exporte|exportez|donner|donne|donnez|telecharger|telecharge|"
    r"realiser|realise|realisez|mettre|mets|mettez|transformer|transforme|"
    r"transformez|obtenir|veux|voudrais|souhaite|aimerais|besoin|"
    r"create|creates|make|makes|"
    r"generate|generates|write|download"
)
BINARY_FILE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico",
    ".zip", ".7z", ".rar", ".tar", ".gz", ".tgz", ".bz2", ".xz",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods", ".odp",
    ".sqlite", ".sqlite3", ".db",
    ".mp3", ".wav", ".ogg", ".mp4", ".webm",
    ".woff", ".woff2", ".ttf", ".otf", ".bin", ".exe", ".dll", ".msi",
}


def _is_pdf_creation_request(prompt):
    normalized = (
        unicodedata.normalize("NFKD", str(prompt))
        .encode("ascii", "ignore")
        .decode("ascii")
        .casefold()
    )
    return bool(
        re.search(
            r"\b(?:" + PDF_CREATION_ACTION_PATTERN + r")\b.{0,600}\bpdf\b"
            r"|\bpdf\b.{0,600}\b(?:" + PDF_CREATION_ACTION_PATTERN + r")\b",
            normalized,
            re.DOTALL,
        )
    )


def _is_image_creation_request(prompt):
    normalized = (
        unicodedata.normalize("NFKD", str(prompt))
        .encode("ascii", "ignore")
        .decode("ascii")
        .casefold()
    )
    actions = (
        r"creer|cree|creez|faire|fais|fait|fabriquer|fabrique|generer|genere|"
        r"dessiner|dessine|dessinez|illustrer|illustre|peindre|"
        r"produire|produis|produisez|realiser|realise|realisez|create|generate|"
        r"draw|paint|make|veux|voudrais|souhaite|aimerais|montre|imagine|visualise"
    )
    subjects = (
        r"image|illustration|dessin|logo|affiche|portrait|photo|icone|visuel|picture|"
        r"oiseau|chat|chien|personne|femme|homme|enfant|arbre|fleur|maison|voiture|"
        r"paysage|dessin anime|bande dessinee|coloriage|personnage"
    )
    return bool(
        re.search(r"\b(?:" + actions + r")\b.{0,400}\b(?:" + subjects + r")\b", normalized, re.S)
        or re.search(r"\b(?:" + subjects + r")\b.{0,300}\b(?:genere|creer|faire|dessine|create|draw)\b", normalized, re.S)
        or re.search(r"\b(?:" + subjects + r")\s+(?:de|d')\b", normalized, re.S)
        or re.search(r"\b(?:une|un|des|quelques)\s+(?:" + subjects + r")\b", normalized, re.S)
        or re.search(r"\b(?:image|photo|dessin)\s+(?:de|d')\b", normalized, re.S)
        or re.search(r"\b(?:fais|genere|cree|dessine)\s+(?:une|un|des)\s+(?:" + subjects + r")\b", normalized, re.S)
    )


IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")


def _is_image_edit_request(prompt):
    normalized = (
        unicodedata.normalize("NFKD", str(prompt))
        .encode("ascii", "ignore")
        .decode("ascii")
        .casefold()
    )
    return bool(
        re.search(
            r"\b(?:ameliore|ameliorer|ameliorez|retouche|retoucher|modifie|modifier|"
            r"transforme|transformer|refais|refaire|embellis|change|changer|ajoute|"
            r"improve|enhance|edit|modify|redo|upgrade)\b",
            normalized,
        )
    )


CODE_PROJECT_ACTION_PATTERN = (
    r"creer|cree|creez|creation|faire|fait|fais|fasse|fabriquer|fabrique|"
    r"construire|construis|construis|developper|developpe|developpez|"
    r"coder|code|codons|programmer|programme|programmez|"
    r"realiser|realise|realisez|mettre|mets|mettez|"
    r"aide|aider|aidez|guide|guidez|montre|montrez|apprendre|apprends|"
    r"build|create|make|code|program|develop|help|guide|show|learn"
)

CODE_PROJECT_SUBJECT_PATTERN = (
    r"site|page|page web|application|appli|projet|script|programme|"
    r"html|css|javascript|python|fichier|fichiers|dossier|"
    r"formulaire|bouton|menu|navbar|carte|cards|galerie|"
    r"jeu|jeux|animation|template|modele|exemple|demo|démo|"
    r"portfolio|blog|boutique|ecommerce|landing|"
    r"page|page html|page web|page internet|"
    r"un site|un projet|un script|un programme|un exemple|un demo|un modèle|un modèle"
)


def _is_code_project_request(prompt):
    """Detecte une demande d'aide au codage / creation de projet."""
    normalized = (
        unicodedata.normalize("NFKD", str(prompt))
        .encode("ascii", "ignore")
        .decode("ascii")
        .casefold()
    )
    return bool(
        re.search(
            r"\b(?:" + CODE_PROJECT_ACTION_PATTERN + r")\b.{0,400}\b(?:" + CODE_PROJECT_SUBJECT_PATTERN + r")\b",
            normalized,
            re.S,
        )
        or re.search(
            r"\b(?:" + CODE_PROJECT_SUBJECT_PATTERN + r")\b.{0,300}\b(?:" + CODE_PROJECT_ACTION_PATTERN + r")\b",
            normalized,
            re.S,
        )
        or re.search(r"\b(?:site|page|application|projet|script|html|css|javascript)\b", normalized, re.S)
    )




def _ask_project_folder(prompt_text):
    """Demande a l'utilisateur de creer ou choisir un dossier de projet."""
    from tkinter import simpledialog

    default_name = "mon_projet"
    nom = simpledialog.askstring(
        "Nouveau projet de code",
        "Nom du dossier de projet (sera cree dans ia_creations/projets/) :",
        initialvalue=default_name,
    )
    if not nom or not nom.strip():
        return None
    nom = nom.strip()
    # Nettoyer le nom
    nom = re.sub(r'[<>:"/\\|?*]', "_", nom)
    target = CODE_PROJECT_DIR / nom
    if target.exists():
        if not messagebox.askyesno(
            "Dossier existant",
            "Le dossier '{}' existe deja.\nVoulez-vous l'utiliser pour ce projet ?".format(nom),
        ):
            return None
    else:
        if not messagebox.askyesno(
            "Creer le dossier",
            "L'IA propose de creer le dossier de projet :\n{}\n\nAutoriser ?".format(target),
        ):
            return None
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        messagebox.showerror("Erreur", "Impossible de creer le dossier : {}".format(error))
        return None
    return target


def _is_within_project(path, project_dir):
    try:
        Path(path).resolve().relative_to(Path(project_dir).resolve())
        return True
    except ValueError:
        return False



def _nom_fichier_image(prompt, staging_dir=None):
    """Genere un nom de fichier lisible a partir du prompt, sans hash moche."""
    base = str(prompt).strip().lower()
    base = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode("ascii")
    base = re.sub(r"[^a-z0-9\s-]", "", base)
    base = re.sub(r"\s+", "_", base).strip("_")
    base = re.sub(r"_+", "_", base)
    base = base[:50]
    if not base:
        base = "image"

    # Verifier l'unicite dans le dossier de destination pour eviter l'ecrasement
    if staging_dir is None:
        staging_dir = IA_CREATIONS_DIR / ".pending"
    candidate = staging_dir / ("{}.png".format(base))
    counter = 1
    while candidate.exists():
        candidate = staging_dir / ("{}_{}.png".format(base, counter))
        counter += 1
    return candidate.name


def base_dir():
    """Dossier de l'application (fonctionne aussi une fois l'exe Windows compile)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


GENERATED_DIR = base_dir() / "generated"
IA_CREATIONS_DIR = base_dir() / "ia_creations"

CODE_PROJECT_DIR = Path.home() / "Desktop" / "Calisto_Projets"


def resolve_generated_file_path(filepath, output_dir=None):
    """Resolve un chemin relatif dans le dossier des creations IA uniquement."""
    relative = Path(str(filepath).strip().replace("\\", os.sep).replace("/", os.sep))
    if (
        not relative.name
        or relative.is_absolute()
        or relative.drive
        or ".." in relative.parts
        or any(":" in part for part in relative.parts)
    ):
        raise ValueError("Le nom doit rester dans le dossier ia_creations.")

    try:
        root = Path(output_dir if output_dir is not None else IA_CREATIONS_DIR).resolve()
        target = (root / relative).resolve()
        target.relative_to(root)
    except (OSError, RuntimeError, ValueError) as error:
        raise ValueError("Le fichier doit rester dans le dossier ia_creations.") from error
    if target == root:
        raise ValueError("Un nom de fichier est requis.")
    return target


def decode_generated_binary(content):
    """Decode un petit fichier binaire produit en Base64 par l'IA."""
    encoded = re.sub(r"\s+", "", str(content))
    max_encoded_length = ((MAX_GENERATED_FILE_BYTES + 2) // 3) * 4
    if len(encoded) > max_encoded_length:
        raise ValueError("Le fichier depasse la limite de 5 Mo.")
    try:
        decoded = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError("Le contenu Base64 du fichier est invalide.") from error
    if not decoded:
        raise ValueError("Le fichier Base64 est vide.")
    if len(decoded) > MAX_GENERATED_FILE_BYTES:
        raise ValueError("Le fichier depasse la limite de 5 Mo.")
    return decoded


WEB_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "rechercher_sur_internet",
        "description": "Recherche des pages web ou des actualites recentes avec DuckDuckGo. Utilisez uniquement quand l'utilisateur demande des informations en ligne.",
        "parameters": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string", "description": "Une requete de mots-cles precise."},
                "region": {"type": "string", "enum": ["fr-fr", "wt-wt", "us-en"], "description": "Region et langue."},
                "timelimit": {"type": "string", "enum": ["d", "w", "m", "y"], "description": "Anciennete max."},
                "search_type": {"type": "string", "enum": ["text", "news"], "description": "text ou news."},
                "max_results": {"type": "integer", "description": "Nombre de resultats (1-10)."},
            },
        },
    },
}

BG_APP = "#0b1118"
BG_PANEL = "#111a24"
BG_INPUT = "#182331"
TEXT_MAIN = "#e5edf5"
TEXT_MUTED = "#94a3b8"
BUBBLE_USER = "#12372a"
BUBBLE_AI = "#141f2b"
ACCENT = "#22c58b"
ACCENT_HOVER = "#16a875"

os.makedirs(GENERATED_DIR, exist_ok=True)
os.makedirs(IA_CREATIONS_DIR, exist_ok=True)


def web_search(query, max_results=5, region="fr-fr", timelimit=None, search_type="text"):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, region=region, timelimit=timelimit, safesearch="moderate", max_results=max_results))
        lines = []
        for r in results:
            lines.append("- {} : {}".format(r.get("title", ""), r.get("href", "")))
        return "\n".join(lines) if lines else "Aucun resultat trouve."
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


def _safe_pdf_text(value):
    text = (
        str(value)
        .replace("’", "'")
        .replace("‘", "'")
        .replace("“", '"')
        .replace("”", '"')
        .replace("–", "-")
        .replace("—", "-")
        .replace("…", "...")
        .replace("•", "-")
    )
    return text.encode("latin-1", "replace").decode("latin-1")


def _strip_pdf_chat_text(content):
    chat_pattern = (
        r"voici le pdf(?: cr[eé]e)?|"
        r"voici le contenu(?: du pdf)?|"
        r"je vous invite|"
        r"n['’]h[eé]sitez pas|"
        r"je reste [àa] votre disposition|"
        r"dites[- ]moi si|"
        r"j['’]esp[eè]re que|"
        r"souhaitez-vous|"
        r"si vous souhaitez"
    )
    lines = []
    for line in str(content).splitlines():
        if re.match(r"(?i)^\s*(?:{})\b".format(chat_pattern), line):
            continue
        line = re.sub(r"(?i)\s+(?:{})\b.*$".format(chat_pattern), "", line)
        lines.append(line)
    return "\n".join(lines)


def _clean_pdf_markdown(content):
    text = str(content).replace("\r\n", "\n").replace("\r", "\n").strip()
    text = re.sub(
        r"(?im)^[ \t]*\*\*titre\*\*[ \t]*\n[ \t]*=+[ \t]*\n(?:[ \t]*\n)*[ \t]*([^\n]+)[ \t]*$",
        r"# \1",
        text,
    )
    text = re.sub(
        r"(?m)^([^\n]+)\n[ \t]*([=-]{3,})[ \t]*$",
        lambda match: "{} {}".format("#" if match.group(2).startswith("=") else "##", match.group(1).strip()),
        text,
    )
    heading = re.search(r"(?m)^\s{0,3}#{1,6}\s+\S.*$", text)
    if heading:
        text = text[heading.start():]
    else:
        text = re.sub(
            r"(?im)^\s*(?:bien s[uû]r[,! ]*|voici le contenu(?: du pdf)?[^:\n]*:|je vais (?:cr[eé]er|g[eé]n[eé]rer) (?:le|un|une)?\s*pdf[^.\n]*\.?)\s*",
            "",
            text,
        )
    return _strip_pdf_chat_text(text).strip()


def _clean_markdown_inline(text):
    value = html.unescape(str(text))
    value = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", value)
    value = re.sub(r"(\*\*|__)(.+?)\1", r"\2", value)
    value = re.sub(r"(?<!\w)([*_`])(.+?)\1(?!\w)", r"\2", value)
    return _safe_pdf_text(value)


def _is_code_like_line(line):
    stripped = line.strip()
    return bool(
        re.match(
            r"(?:import\s+\w|from\s+\w+\s+import\b|def\s+\w|class\s+\w|"
            r"try\s*:|except\b|finally\s*:|if\s+.+:|elif\s+.+:|else\s*:|"
            r"for\s+.+:|while\s+.+:|with\s+.+:|return\b|pass$|break$|continue$|"
            r"raise\b|[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*\s*(?:=|\+=|-=)|"
            r"(?:GPIO|pygame|time|window|sr)\.|print\s*\()",
            stripped,
        )
    )


def _append_code_or_warning(blocks, code, language="python"):
    code = str(code).strip()
    if not code:
        return
    if language.lower() in ("python", "py"):
        lines = []
        for line in code.splitlines():
            if not line.lstrip().startswith("from "):
                line = re.sub(r"\s+(?=import\s+[A-Za-z_])", "\n", line)
            line = re.sub(
                r"(?<=\))\s+(?=(?:(?:GPIO|pygame|time|window|sr)\.|print\s*\())",
                "\n",
                line,
            )
            line = re.sub(r"(?<=\))\s+(?=[A-Za-z_]\w*\s*=)", "\n", line)
            lines.extend(line.splitlines())
        code = "\n".join(lines)
        try:
            ast.parse(code)
        except SyntaxError:
            chunks = []
            current_chunk = []
            for line in lines:
                if line.strip() and not line[0].isspace() and current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = []
                current_chunk.append(line)
            if current_chunk:
                chunks.append(current_chunk)

            valid_lines = []
            warning_pending = False
            for chunk in chunks:
                try:
                    ast.parse("\n".join(chunk))
                except SyntaxError:
                    if valid_lines:
                        blocks.append(("code", language, _safe_pdf_text("\n".join(valid_lines))))
                        valid_lines = []
                    if not warning_pending:
                        blocks.append(
                            ("warning", "", "Exemple de code omis : sa syntaxe est incomplète ou incorrecte.")
                        )
                        warning_pending = True
                else:
                    valid_lines.extend(chunk)
                    warning_pending = False
            if valid_lines:
                blocks.append(("code", language, _safe_pdf_text("\n".join(valid_lines))))
            return
    blocks.append(("code", language, _safe_pdf_text(code)))


def _parse_pdf_markdown(content):
    lines = _clean_pdf_markdown(content).splitlines()
    blocks = []
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            index += 1
            continue
        if stripped.startswith("```"):
            language = stripped[3:].strip()
            code_lines = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            if index < len(lines):
                index += 1
            _append_code_or_warning(blocks, "\n".join(code_lines), language or "text")
            continue
        heading = re.match(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if heading:
            blocks.append(("heading", len(heading.group(1)), _clean_markdown_inline(heading.group(2))))
            index += 1
            continue
        if re.match(r"^\s*(?:[-*_]\s*){3,}$", line):
            blocks.append(("rule", "", ""))
            index += 1
            continue
        if re.match(r"^\s*\|.*\|\s*$", line):
            rows = []
            while index < len(lines) and re.match(r"^\s*\|.*\|\s*$", lines[index]):
                cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                    rows.append([_clean_markdown_inline(cell) for cell in cells])
                index += 1
            if rows:
                blocks.append(("table", rows, ""))
            continue
        ordered = re.match(r"^(\s*)(\d+)[.)]\s+(.+)$", line)
        bullet = re.match(r"^(\s*)[-*+]\s+(.+)$", line)
        if ordered or bullet:
            match = ordered or bullet
            indent = min(12, (len(match.group(1).expandtabs(4)) // 2) * 4)
            prefix = "{}. ".format(match.group(2)) if ordered else ""
            item_text = ordered.group(3) if ordered else bullet.group(2)
            blocks.append(("list", indent, _clean_markdown_inline(prefix + item_text)))
            index += 1
            continue
        quote = re.match(r"^\s*>\s?(.*)$", line)
        if quote:
            quote_lines = []
            while index < len(lines):
                quote_line = re.match(r"^\s*>\s?(.*)$", lines[index])
                if not quote_line:
                    break
                quote_lines.append(_clean_markdown_inline(quote_line.group(1)))
                index += 1
            blocks.append(("quote", "", " ".join(quote_lines)))
            continue

        paragraph = [stripped]
        index += 1
        while index < len(lines):
            next_line = lines[index]
            next_stripped = next_line.strip()
            if (
                not next_stripped
                or next_stripped.startswith("```")
                or re.match(r"^\s{0,3}#{1,6}\s+", next_line)
                or re.match(r"^\s*(?:[-*_]\s*){3,}$", next_line)
                or re.match(r"^\s*(?:[-*+]\s+|\d+[.)]\s+|>\s?)", next_line)
            ):
                break
            paragraph.append(next_stripped)
            index += 1
        grouped_lines = []
        for paragraph_line in paragraph:
            kind = "code" if _is_code_like_line(paragraph_line) else "paragraph"
            if grouped_lines and grouped_lines[-1][0] == kind:
                grouped_lines[-1][1].append(paragraph_line)
            else:
                grouped_lines.append((kind, [paragraph_line]))
        for kind, grouped in grouped_lines:
            if kind == "code":
                _append_code_or_warning(blocks, "\n".join(grouped))
            else:
                blocks.append(
                    ("paragraph", "", _clean_markdown_inline(" ".join(grouped)))
                )
    return blocks


def _wrap_pdf_cell(text, pdf, max_width):
    lines = []
    for paragraph in str(text).splitlines() or [""]:
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = ""
        for word in words:
            if not current:
                current = word
                continue
            candidate = "{} {}".format(current, word)
            if pdf.get_string_width(candidate) <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def _extract_pdf_document_text(response):
    text = str(response)
    tagged_blocks = re.findall(
        r"\[CREER_FICHIER:\s*([^\]\r\n]+\.pdf)\](.*?)\[/CREER_FICHIER\]",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if tagged_blocks:
        return _clean_pdf_markdown(max(tagged_blocks, key=lambda item: len(item[1]))[1])

    unclosed_tag = re.search(
        r"\[CREER_FICHIER:\s*[^\]\r\n]+\.pdf\](.*)$",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if unclosed_tag:
        return _clean_pdf_markdown(
            re.sub(r"\[/CREER_FICHIER\].*$", "", unclosed_tag.group(1), flags=re.I | re.S)
        )

    alias_tag = re.search(PDF_ALIAS_TAG_PATTERN, text, re.IGNORECASE)
    if alias_tag:
        text = text[alias_tag.end():]

    fenced_blocks = re.findall(r"```([^\r\n`]*)\r?\n(.*?)```", text, re.DOTALL)
    markdown_blocks = [
        body
        for language, body in fenced_blocks
        if language.strip().lower() in ("", "md", "markdown")
    ]
    document_blocks = [
        body
        for body in markdown_blocks or [body for _, body in fenced_blocks]
        if re.search(r"(?m)^\s{0,3}#{1,6}\s+\S", body)
    ]
    if document_blocks:
        return _clean_pdf_markdown(max(document_blocks, key=len))
    if markdown_blocks:
        return _clean_pdf_markdown(max(markdown_blocks, key=len))
    return _clean_pdf_markdown(text)


def _is_complete_pdf_document(content):
    blocks = _parse_pdf_markdown(content)
    body_parts = []
    for kind, detail, text in blocks:
        if kind in ("paragraph", "list", "quote", "code"):
            body_parts.append(str(text))
        elif kind == "table":
            body_parts.extend(str(cell) for row in detail for cell in row)
    body = " ".join(body_parts).strip()
    nb_body_blocks = sum(
        1 for kind, _, _ in blocks
        if kind in ("paragraph", "list", "quote", "table", "code")
    )
    return len(body) >= 500 and nb_body_blocks >= 3


def _pdf_filename_from_content(content, fallback="document.pdf"):
    if fallback and fallback.lower() != "document.pdf":
        return fallback
    title = re.search(r"(?m)^\s*#\s+(.+?)\s*$", str(content))
    if not title:
        return fallback or "document.pdf"
    slug = unicodedata.normalize("NFKD", title.group(1))
    slug = slug.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")[:80]
    return "{}.pdf".format(slug) if slug else (fallback or "document.pdf")


class GeneratedDocumentPDF(FPDF):
    def __init__(self, title):
        super().__init__()
        self.document_title = _safe_pdf_text(title)
        self.set_margins(18, 20, 18)
        self.set_auto_page_break(auto=True, margin=18)

    def header(self):
        if self.page_no() <= 1:
            return
        self.set_y(9)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(104, 119, 137)
        self.cell(0, 5, self.document_title[:100], align="R")
        self.set_draw_color(218, 226, 234)
        self.line(self.l_margin, 16, self.w - self.r_margin, 16)
        self.set_y(21)

    def footer(self):
        self.set_y(-14)
        self.set_draw_color(218, 226, 234)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(104, 119, 137)
        self.cell(0, 8, "CALISTO  |  {}".format(self.page_no()), align="C")


PDF_INLINE_PATTERN = re.compile(
    r"\[c:#([0-9A-Fa-f]{6})\](.*?)\[/c\]"
    r"|\*\*(.+?)\*\*"
    r"|`([^`]+)`"
    r"|(?<!\*)\*([^*]+?)\*(?!\*)"
    r"|__(.+?)__",
    re.DOTALL,
)

PDF_BROWSER_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
]


def _pdf_rgb(valeur):
    if isinstance(valeur, tuple):
        return valeur
    if isinstance(valeur, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", valeur):
        try:
            return (int(valeur[1:3], 16), int(valeur[3:5], 16), int(valeur[5:7], 16))
        except ValueError:
            return None
    return None


def _pdf_style_fusion(style, extra):
    lettres = set(style or "") | set(extra or "")
    return "".join(lettre for lettre in "BI" if lettre in lettres)


def _pdf_inline_runs(texte, style="", couleur=None):
    """Decoupe un texte Markdown en segments (texte, style, couleur)."""

    valeur = html.unescape(str(texte))
    valeur = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", valeur)
    valeur = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", valeur)

    runs = []
    position = 0

    for trouve in PDF_INLINE_PATTERN.finditer(valeur):
        if trouve.start() > position:
            runs.append((_safe_pdf_text(valeur[position:trouve.start()]), style, couleur))

        if trouve.group(1):
            runs.extend(_pdf_inline_runs(trouve.group(2), style, "#" + trouve.group(1).upper()))
        elif trouve.group(3) is not None:
            runs.extend(_pdf_inline_runs(trouve.group(3), _pdf_style_fusion(style, "B"), couleur))
        elif trouve.group(4) is not None:
            runs.append((_safe_pdf_text(trouve.group(4)), "C", couleur))
        elif trouve.group(5) is not None:
            runs.extend(_pdf_inline_runs(trouve.group(5), _pdf_style_fusion(style, "I"), couleur))
        else:
            runs.extend(_pdf_inline_runs(trouve.group(6), _pdf_style_fusion(style, "B"), couleur))

        position = trouve.end()

    if position < len(valeur):
        runs.append((_safe_pdf_text(valeur[position:]), style, couleur))

    return [run for run in runs if run[0]]


def _pdf_write_runs(
    pdf,
    texte,
    taille,
    interligne,
    couleur=(45, 58, 72),
    style="",
    interligne_apres=0.35,
):
    runs = _pdf_inline_runs(texte, style, None) if isinstance(texte, str) else texte

    if not runs:
        pdf.ln(interligne)
        return

    if pdf.get_x() < pdf.l_margin:
        pdf.set_x(pdf.l_margin)

    if pdf.get_y() + interligne > pdf.h - pdf.b_margin - 1:
        pdf.add_page()

    page_depart = pdf.page_no()
    y_depart = pdf.get_y()

    for morceau, style_morceau, couleur_morceau in runs:
        police = "Courier" if style_morceau == "C" else "Helvetica"
        graisse = "" if style_morceau == "C" else style_morceau
        pdf.set_font(police, graisse, taille - 0.6 if style_morceau == "C" else taille)
        pdf.set_text_color(*(_pdf_rgb(couleur_morceau) or couleur))
        pdf.write(interligne, morceau)

    y_fin = pdf.get_y()

    if pdf.page_no() != page_depart:
        pdf.set_y(y_fin + interligne * (1.0 + interligne_apres))
    else:
        pdf.set_y(max(y_fin, y_depart) + interligne * (1.0 + interligne_apres))

    pdf.set_x(pdf.l_margin)


def _pdf_browser_executable():
    for chemin in PDF_BROWSER_CANDIDATES:
        if os.path.exists(chemin):
            return chemin
    return None


def _looks_like_html(content):
    """Vrai seulement pour un document HTML complet, pas pour du Markdown qui parle de HTML."""
    return bool(
        re.match(r"\s*(?:<!doctype\s+html|<html\b)", str(content), re.IGNORECASE)
    )


def write_html_pdf(target_path, html_content):
    """Rend un document HTML/CSS en PDF via Edge ou Chrome (rendu fidele)."""

    navigateur = _pdf_browser_executable()
    if not navigateur:
        return False

    contenu = str(html_content)

    if "<html" not in contenu.lower():
        contenu = (
            '<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">'
            "<style>@page{size:A4;margin:18mm}"
            "body{font-family:Helvetica,Arial,sans-serif;color:#2d3a48;line-height:1.55;font-size:11pt}"
            "h1{color:#192d44;font-size:22pt}h2{color:#188462;font-size:15pt}h3{font-size:12.5pt}"
            "table{border-collapse:collapse;width:100%;margin:10px 0}"
            "th,td{border:1px solid #dae2ea;padding:6px 8px;text-align:left}"
            "th{background:#188462;color:#fff}"
            "code,pre{font-family:Consolas,monospace;background:#eef2f6}"
            "pre{padding:10px;border-radius:4px;overflow:auto}"
            "blockquote{border-left:3px solid #188462;margin:10px 0;padding:2px 12px;color:#3b536a}"
            "img{max-width:100%}</style></head><body>"
            + contenu
            + "</body></html>"
        )

    cible = Path(target_path)
    cible.parent.mkdir(parents=True, exist_ok=True)

    temporaire = tempfile.NamedTemporaryFile(suffix=".html", delete=False)
    temporaire.close()
    chemin_html = Path(temporaire.name)

    try:
        chemin_html.write_text(contenu, encoding="utf-8")

        commande = [
            navigateur,
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--no-pdf-header-footer",
            "--print-to-pdf={}".format(cible.resolve()),
            chemin_html.resolve().as_uri(),
        ]

        subprocess.run(commande, capture_output=True, timeout=90)

        return cible.exists() and cible.stat().st_size > 800
    except Exception:
        return False
    finally:
        try:
            chemin_html.unlink()
        except OSError:
            pass


def write_markdown_pdf(target_path, content):
    if _looks_like_html(content) and write_html_pdf(target_path, content):
        return
    if not _is_complete_pdf_document(content):
        raise ValueError("Le contenu du PDF est incomplet ou ne contient qu'un titre.")
    blocks = _parse_pdf_markdown(content)
    if not blocks:
        raise ValueError("Le contenu du PDF est vide.")

    title = Path(target_path).stem.replace("-", " ").replace("_", " ").strip()
    first_heading = next(
        (index for index, block in enumerate(blocks) if block[0] == "heading" and block[1] == 1),
        None,
    )
    if first_heading is not None:
        title = blocks.pop(first_heading)[2]
    if not title:
        title = "Document"

    pdf = GeneratedDocumentPDF(title)
    pdf.set_title(title)
    pdf.set_author("Calisto")
    pdf.add_page()
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_text_color(25, 45, 68)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 11, _safe_pdf_text(title))
    pdf.set_draw_color(34, 197, 139)
    pdf.set_line_width(1.1)
    pdf.line(pdf.l_margin, pdf.get_y() + 2, pdf.w - pdf.r_margin, pdf.get_y() + 2)
    pdf.ln(6)

    body_width = pdf.w - pdf.l_margin - pdf.r_margin
    for kind, detail, text in blocks:
        if kind == "heading":
            level = detail
            pdf.ln(2 if level == 2 else 1)
            taille_titre = 19 if level == 1 else 15 if level == 2 else 12
            couleur_titre = (25, 45, 68) if level == 1 else (24, 132, 98)
            if pdf.get_y() + (8 if level == 1 else 7) + 12 > pdf.h - pdf.b_margin:
                pdf.add_page()
            pdf.set_x(pdf.l_margin)
            _pdf_write_runs(
                pdf,
                text,
                taille_titre,
                8 if level == 1 else 7,
                couleur=couleur_titre,
                style="B",
                interligne_apres=0.12,
            )
            if level == 1:
                pdf.set_draw_color(218, 226, 234)
                pdf.line(pdf.l_margin, pdf.get_y() + 1, pdf.w - pdf.r_margin, pdf.get_y() + 1)
                pdf.ln(3)
        elif kind == "paragraph":
            pdf.set_x(pdf.l_margin)
            _pdf_write_runs(pdf, text, 10.5, 6.0, couleur=(45, 58, 72), interligne_apres=0.18)
        elif kind == "list":
            x = pdf.l_margin + detail
            numerotee = bool(re.match(r"^\d+[.)]\s", str(text).strip()))
            if not numerotee:
                y = pdf.get_y()
                pdf.set_fill_color(34, 197, 139)
                pdf.ellipse(x + 1, y + 2.6, 1.2, 1.2, style="F")
            pdf.set_x(x + 5)
            _pdf_write_runs(pdf, text, 10.5, 5.8, couleur=(45, 58, 72), interligne_apres=0.06)
        elif kind == "quote":
            debut = pdf.get_y()
            pdf.set_x(pdf.l_margin + 6)
            _pdf_write_runs(
                pdf,
                text,
                10,
                6.3,
                couleur=(59, 83, 106),
                style="I",
                interligne_apres=0.2,
            )
            pdf.set_draw_color(24, 132, 98)
            pdf.set_line_width(0.9)
            pdf.line(pdf.l_margin + 1, debut, pdf.l_margin + 1, max(debut + 1, pdf.get_y() - 3.0))
            pdf.set_line_width(0.2)
            pdf.ln(1.6)
        elif kind == "table":
            column_count = max(len(row) for row in detail)
            column_width = body_width / column_count
            for row_index, row in enumerate(detail):
                cells = row + [""] * (column_count - len(row))
                pdf.set_font("Helvetica", "B" if row_index == 0 else "", 9)
                wrapped = [
                    _wrap_pdf_cell(cell, pdf, column_width - 6)
                    for cell in cells
                ]
                row_height = max(8, max(len(cell_lines) for cell_lines in wrapped) * 5.2 + 4)
                if pdf.get_y() + row_height > pdf.h - pdf.b_margin:
                    pdf.add_page()
                y = pdf.get_y()
                for column_index, cell_lines in enumerate(wrapped):
                    x = pdf.l_margin + column_index * column_width
                    if row_index == 0:
                        pdf.set_fill_color(24, 132, 98)
                        pdf.set_text_color(255, 255, 255)
                    else:
                        if row_index % 2:
                            pdf.set_fill_color(247, 249, 251)
                        else:
                            pdf.set_fill_color(255, 255, 255)
                        pdf.set_text_color(45, 58, 72)
                    pdf.set_draw_color(218, 226, 234)
                    pdf.rect(x, y, column_width, row_height, style="DF")
                    pdf.set_xy(x + 3, y + 2)
                    pdf.multi_cell(
                        column_width - 6,
                        5.2,
                        "\n".join(cell_lines),
                    )
                pdf.set_y(y + row_height)
        elif kind == "code":
            if detail and detail.lower() not in ("markdown", "md", "text"):
                pdf.set_font("Helvetica", "B", 8)
                pdf.set_text_color(24, 132, 98)
                pdf.cell(0, 5, _safe_pdf_text(detail.upper()))
                pdf.ln(5)
            pdf.set_fill_color(30, 41, 59)
            pdf.set_text_color(236, 242, 248)
            pdf.set_font("Courier", "", 8.5)
            pdf.set_x(pdf.l_margin + 2)
            pdf.multi_cell(body_width - 4, 5.2, text or " ", fill=True)
            pdf.ln(2)
        elif kind == "warning":
            pdf.set_fill_color(255, 247, 220)
            pdf.set_text_color(130, 86, 20)
            pdf.set_font("Helvetica", "I", 9.5)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 6, text, fill=True)
            pdf.ln(2)
        elif kind == "rule":
            pdf.ln(2)
            pdf.set_draw_color(218, 226, 234)
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
            pdf.ln(4)

    target_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        suffix=".pdf",
        dir=str(target_path.parent),
        delete=False,
    ) as temporary_file:
        temporary_path = Path(temporary_file.name)
    try:
        pdf.output(str(temporary_path))
        os.replace(str(temporary_path), str(target_path))
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def chat_with_web_search(
    model,
    messages,
    temperature,
    enabled,
    on_search=None,
    num_ctx=4096,
    num_predict=768,
):
    conversation = [dict(message) for message in messages]
    search_count = 0
    for round_index in range(MAX_WEB_SEARCH_ROUNDS + 1):
        can_call_tools = enabled and round_index < MAX_WEB_SEARCH_ROUNDS
        request = {
            "model": model,
            "messages": conversation,
            "options": {"temperature": temperature, "num_ctx": num_ctx, "num_predict": num_predict},
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
            raise RuntimeError("Reponse vide de l'IA.")
        if not can_call_tools:
            raise RuntimeError("Limite de recherches atteinte.")
        conversation.append(assistant_message)
        for tool_call in tool_calls:
            function = tool_call.get("function", {})
            name = function.get("name", "")
            arguments = function.get("arguments", {})
            if name != "rechercher_sur_internet":
                result = "Erreur : outil non autorise."
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
    def __init__(self, profil=None):
        super().__init__()
        self.profil = profil
        self.title("Calisto - Assistant IA pour debutants")
        self.geometry(self._initial_geometry())
        self.minsize(900, 600)
        self.configure(fg_color=BG_APP)
        self.resizable(True, True)

        self.model_var = ctk.StringVar(value=MODEL)
        self.temp_var = ctk.DoubleVar(value=0.7)
        self.sys_text_var = ctk.StringVar(value="Tu es Calisto, un professeur patient et encourageant pour debutants en developpement web. Tu parles en francais comme si tu discutais avec une personne qui apprend. Sois simple, direct et encourageant. N'utilise pas de ton robotique. Si tu ne comprends pas une question, dis-le et demande une precision. Ton role est d'aider les debutants a acquerir les bons reflexes de programmation. Pour les questions d'apprentissage, guide d'abord avec des indices. Si l'utilisateur demande explicitement du code ou une correction, fournis le code demande dans un bloc Markdown avec son langage et, si possible, son nom de fichier.")
        self.web_search_var = ctk.BooleanVar(value=False)
        self.inline_completion_var = ctk.BooleanVar(value=True)
        self.ai_can_create_files = ctk.BooleanVar(value=False)
        self.ai_can_modify_app = ctk.BooleanVar(value=False)
        self._image_generation_busy = False
        self._image_generation_active = False
        self._pending_generated_artifacts = {}
        self._image_setup_label = None
        self._image_progress_frame = None
        self._image_progress_bar = None
        self._image_progress_label = None
        self._image_progress_pct = None
        self._image_progress_job = None
        self._image_progress_value = 0
        self._current_project_dir = None

        self.dev_window = None
        self.messages = []
        self.streaming = False
        self._suppress_streaming = False
        self._pdf_generation_requested = False
        self._requested_pdf_filename = "document.pdf"
        self.conversation_summary = ""
        self._chat_project_key = None
        self._chat_memory_notice = ""
        self._memory_compaction_in_progress = set()
        self._chat_memory_generations = {}
        self._last_chat_activity = time.monotonic()
        self.attached_files = []
        self.ui_queue = queue.Queue()
        self.last_user_prompt = ""
        self._is_repeat_query = False
        self._pending_editor_context = ""
        self._learning_sujets = []
        self.learning_mode_window = None

        self._build_ui()
        self._send_welcome_message()
        self._check_ollama()
        self._start_ai()
        self.after(100, self._process_ui_queue)

    def _initial_geometry(self):
        """Taille de la fenetre : 92% de l'ecran, exprimee en unites de l'interface."""
        try:
            screen_w = ctypes.windll.user32.GetSystemMetrics(0)
            screen_h = ctypes.windll.user32.GetSystemMetrics(1)
        except Exception:
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()
        scale = 1.0
        try:
            from customtkinter.windows.widgets.scaling.scaling_tracker import ScalingTracker

            scale = float(ScalingTracker.get_window_scaling(self))
        except Exception:
            pass
        target_w = max(1000, min(1766, int(screen_w * 0.92)))
        target_h = max(640, min(1000, int(screen_h * 0.92)))
        return "{}x{}".format(int(target_w / scale), int(target_h / scale))

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Tabs
        self.tabs = ctk.CTkTabview(
            self,
            fg_color=BG_APP,
            segmented_button_fg_color=BG_PANEL,
            segmented_button_selected_color=ACCENT,
            segmented_button_selected_hover_color=ACCENT_HOVER,
            segmented_button_unselected_color=BG_PANEL,
            segmented_button_unselected_hover_color="#202c39",
            text_color=TEXT_MAIN,
        )
        self.tabs.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.tabs.add("Discussion")
        self.tabs.add("Editeur de code")
        self.tabs.add("Apprentissage")
        self.tabs.add("Bibliotheque")
        # Forcer l'etirement des onglets
        self.tabs._segmented_button.grid_columnconfigure(0, weight=1)
        self.tabs._segmented_button.grid_columnconfigure(1, weight=1)
        self.tabs._segmented_button.grid_columnconfigure(2, weight=1)
        self.tabs._segmented_button.grid_columnconfigure(3, weight=1)

        self.chat_tab = self.tabs.tab("Discussion")
        self.code_tab = self.tabs.tab("Editeur de code")
        self.learning_tab = self.tabs.tab("Apprentissage")
        self.library_tab = self.tabs.tab("Bibliotheque")

        self.chat_tab.grid_columnconfigure(0, weight=1)
        self.chat_tab.grid_rowconfigure(1, weight=1)
        self.code_tab.grid_columnconfigure(0, weight=1)
        self.code_tab.grid_rowconfigure(0, weight=1)
        self.learning_tab.grid_columnconfigure(0, weight=1)
        self.learning_tab.grid_rowconfigure(0, weight=1)
        self.library_tab.grid_columnconfigure(0, weight=1)
        self.library_tab.grid_rowconfigure(1, weight=1)

        self.build_library_tab()

        # Header
        header = ctk.CTkFrame(self.chat_tab, fg_color=BG_PANEL, corner_radius=14)
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 8))

        title_block = ctk.CTkFrame(header, fg_color="transparent")
        title_block.pack(side="left", padx=18, pady=10)
        ctk.CTkLabel(title_block, text="Calisto", font=ctk.CTkFont(size=19, weight="bold"), text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(title_block, text="Votre assistant IA, directement sur votre ordinateur", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED).pack(anchor="w", pady=(1, 0))

        right_btns = ctk.CTkFrame(header, fg_color="transparent")
        right_btns.pack(side="right", padx=10, pady=6)
        ctk.CTkButton(right_btns, text="Reglages", width=100, height=34, command=self.open_settings, fg_color="#263547", hover_color="#34475c", font=ctk.CTkFont(size=11), corner_radius=9).pack(side="right", padx=4)
        ctk.CTkButton(right_btns, text="Joindre un fichier", width=126, height=34, command=self.attach_file, fg_color="#263547", hover_color="#34475c", font=ctk.CTkFont(size=11), corner_radius=9).pack(side="right", padx=4)
        ctk.CTkButton(right_btns, text="Fichiers IA", width=92, height=34, command=self.open_ai_creations_folder, fg_color="#263547", hover_color="#34475c", font=ctk.CTkFont(size=11), corner_radius=9).pack(side="right", padx=4)

        # Chat area
        self.chat_container = ctk.CTkScrollableFrame(self.chat_tab, fg_color=BG_APP, corner_radius=14)
        self.chat_container.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 6))
        self.chat_container.grid_columnconfigure(0, weight=1)

        # File chips
        self.file_chips_label = ctk.CTkLabel(self.chat_tab, text="", font=ctk.CTkFont(size=11), text_color=ACCENT, anchor="w")
        self.file_chips_label.grid(row=2, column=0, sticky="w", padx=24, pady=(0, 4))

        # Input area - modern chat input bar
        bottom = ctk.CTkFrame(self.chat_tab, fg_color=BG_PANEL, corner_radius=16, border_width=1, border_color="#263547")
        bottom.grid(row=3, column=0, sticky="ew", padx=18, pady=(4, 8))
        bottom.grid_columnconfigure(0, weight=1)

        self.entry = ctk.CTkTextbox(bottom, height=82, font=ctk.CTkFont(size=13), fg_color=BG_INPUT, border_width=0, text_color=TEXT_MAIN, corner_radius=11, wrap="word")
        self.entry.grid(row=0, column=0, sticky="nsew", padx=(12, 8), pady=12)
        self.entry.bind("<Return>", self.on_enter)
        self.entry.bind("<Shift-Return>", self.on_shift_enter)

        right = ctk.CTkFrame(bottom, fg_color="transparent")
        right.grid(row=0, column=1, sticky="ns", padx=(0, 12), pady=12)
        self.send_btn = ctk.CTkButton(right, text="Envoyer", width=112, height=40, command=self.send, fg_color=ACCENT, hover_color=ACCENT_HOVER, font=ctk.CTkFont(size=13, weight="bold"), corner_radius=10)
        self.send_btn.pack(pady=(0, 6))
        ctk.CTkLabel(right, text="Entree pour envoyer\nMaj + Entree pour une ligne", font=ctk.CTkFont(size=9), text_color=TEXT_MUTED, justify="center").pack(pady=(1, 5))
        ctk.CTkButton(right, text="Effacer", width=112, height=27, command=self.clear_chat, fg_color="transparent", hover_color="#263547", text_color=TEXT_MUTED, font=ctk.CTkFont(size=10), corner_radius=8).pack()

        self.status_var = ctk.StringVar(value="Pret")
        ctk.CTkLabel(self.chat_tab, textvariable=self.status_var, font=ctk.CTkFont(size=11), text_color=TEXT_MUTED).grid(row=4, column=0, sticky="e", padx=18, pady=(0, 6))

        # Editor tab
        self.code_tab.grid_columnconfigure(0, weight=1)
        self.code_tab.grid_rowconfigure(0, weight=1)
        if DevWindow is not None:
            self.dev_window = DevWindow(self, master=self.code_tab)
            self.dev_window.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        else:
            ctk.CTkLabel(self.code_tab, text="L'editeur de code n'a pas pu etre charge.", text_color=TEXT_MUTED).pack(pady=40)

        # Learning tab
        self.learning_tab.grid_columnconfigure(0, weight=1)
        self.learning_tab.grid_rowconfigure(0, weight=1)
        self._show_learning_landing()

    def _send_welcome_message(self):
        welcome = """Bonjour ! Je suis Calisto, votre assistant IA local.

Posez une question, joignez un fichier ou ouvrez l'editeur pour parler de votre code. Je vous guide pas a pas, sans donner la solution toute faite.

Par quoi souhaitez-vous commencer ?"""
        self._welcome_message = welcome
        self.messages.append({"role": "assistant", "content": welcome})
        self._add_bubble("Calisto", welcome, "assistant", animate=False)

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

    def _current_chat_project_key(self):
        if self.dev_window is not None:
            folder = self.dev_window.current_folder
            current_file = self.dev_window.current_file
            if folder:
                project_path = Path(folder)
            elif current_file:
                project_path = Path(current_file).parent
            else:
                project_path = None
        else:
            project_path = None
        if project_path is None:
            return "global"
        resolved = str(project_path.resolve())
        return resolved.casefold() if os.name == "nt" else resolved

    def _chat_memory_path(self, project_key):
        if os.name == "nt":
            state_root = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
        else:
            state_root = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state")))
        digest = hashlib.sha256(project_key.encode("utf-8")).hexdigest()
        return state_root / "Calisto" / "chat_memory" / (digest + ".json")

    def _save_chat_memory(self, project_key=None, summary=None, messages=None):
        project_key = project_key or self._chat_project_key or "global"
        summary = self.conversation_summary if summary is None else summary
        messages = self.messages if messages is None else messages
        path = self._chat_memory_path(project_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "project_key": project_key,
            "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": str(summary)[:6000],
            "messages": [
                {"role": item["role"], "content": str(item["content"])[:6000]}
                for item in messages[-24:]
                if isinstance(item, dict)
                and item.get("role") in ("user", "assistant")
                and isinstance(item.get("content"), str)
            ],
        }
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=str(path.parent),
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                json.dump(payload, temporary_file, ensure_ascii=False, indent=2)
            os.replace(str(temporary_path), str(path))
        except OSError as error:
            self._chat_memory_notice = "La mémoire du projet n'a pas pu être enregistrée."
            print("Erreur sauvegarde mémoire conversation:", error)
        finally:
            if temporary_path and temporary_path.exists():
                temporary_path.unlink()

    def _load_chat_memory(self, project_key):
        path = self._chat_memory_path(project_key)
        if not path.exists():
            return "", [{"role": "assistant", "content": self._welcome_message}]
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("project_key") != project_key:
                raise ValueError("La mémoire appartient à un autre projet.")
            messages = [
                {"role": item["role"], "content": item["content"]}
                for item in data.get("messages", [])
                if isinstance(item, dict)
                and item.get("role") in ("user", "assistant")
                and isinstance(item.get("content"), str)
            ][-24:]
            return str(data.get("summary", ""))[:6000], messages or [
                {"role": "assistant", "content": self._welcome_message}
            ]
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
            self._chat_memory_notice = "La mémoire du projet n'a pas pu être relue."
            print("Erreur chargement mémoire conversation:", error)
            return "", [{"role": "assistant", "content": self._welcome_message}]

    def _render_chat_history(self):
        for widget in self.chat_container.winfo_children():
            widget.destroy()
        if self.conversation_summary:
            self._add_bubble(
                "Mémoire du projet",
                self.conversation_summary,
                "assistant",
                animate=False,
            )
        for message in self.messages:
            role = message["role"]
            sender = "Vous" if role == "user" else "Calisto"
            self._add_bubble(sender, message["content"], role, animate=False)

    def _sync_chat_memory(self):
        project_key = self._current_chat_project_key()
        if project_key == self._chat_project_key:
            return
        if self._chat_project_key is not None:
            self._save_chat_memory()
        self._chat_project_key = project_key
        self.conversation_summary, self.messages = self._load_chat_memory(project_key)
        self._render_chat_history()

    def send(self):
        if self.streaming:
            return
        prompt = self.entry.get("1.0", "end").strip()
        if not prompt and not self.attached_files:
            return
        self._sync_chat_memory()
        self._last_chat_activity = time.monotonic()
        self._is_repeat_query = (prompt == self.last_user_prompt)
        self.last_user_prompt = prompt

        attached_images = [
            p for p in self.attached_files if p.suffix.lower() in IMAGE_EXTENSIONS
        ]
        parts = [prompt] if prompt else []
        for p in self.attached_files:
            if p in attached_images:
                parts.append("\n\n[Image jointe : {}]".format(p.name))
                continue
            content = read_file_content(p)
            parts.append("\n\n[Fichier : {}]\n{}".format(p.name, content))
        full = "\n".join(parts)

        self.entry.delete("1.0", "end")
        self.attached_files = []
        self._refresh_file_chips()
        self.messages.append({"role": "user", "content": full})
        self._save_chat_memory()
        self._add_bubble("Vous", prompt if prompt else "[Fichier(s)]", "user", animate=False)
        bubble, lbl = self._add_bubble("Calisto", "Calisto prepare sa reponse…", "assistant", animate=False)
        self.streaming = True
        self.send_btn.configure(state="disabled", fg_color="#3b4653")
        self.status_var.set("L'IA repond…")
        request = {
            "model": self.model_var.get() or MODEL,
            "temperature": self.temp_var.get(),
            "system": self.sys_text_var.get(),
            "web_enabled": self.web_search_var.get(),
            "allow_modify": self.ai_can_modify_app.get(),
            "repeat_query": self._is_repeat_query,
            "history": [
                dict(m)
                for m in self.messages[-12 if self.conversation_summary else -20:]
            ],
            "memory_history": [dict(m) for m in self.messages],
            "conversation_summary": self.conversation_summary,
            "chat_project_key": self._chat_project_key or "global",
            "editor_context": self._get_editor_context() or self._pending_editor_context,
            "pdf_output": _is_pdf_creation_request(prompt),
            "image_output": _is_image_creation_request(prompt)
            or bool(attached_images and _is_image_edit_request(prompt)),
            "image_edit_source": (
                str(attached_images[0])
                if attached_images and _is_image_edit_request(prompt)
                else ""
            ),
            "code_project": bool(_is_code_project_request(prompt)),
            "image_generator_available": bool(
                image_generation and image_generation.is_ready()
            ),
            "large_output": bool(
                re.search(
                    r"\b(?:creer|créer|cree|crée|generer|générer|genere|génère|fabrique|produis|ecrire|écrire|ecris|écris|redige|rédige|fais|prepare|prépare|construis|dessine|create|generate|write|make)\b"
                    r".{0,100}\b(?:fichier|document|page|site|application|appli|image|logo|archive|rapport|pr[eé]sentation|pdf|script|programme|program|code|projet|composant|template|modele|file|website|app)\b",
                    prompt,
                    re.IGNORECASE | re.DOTALL,
                )
            ),
        }

        if request.get("code_project") and not self._current_project_dir:
            nom_projet = "mon_projet"
            self._create_code_project(nom_projet)

        if request["pdf_output"]:
            request["large_output"] = True
        self._suppress_streaming = request["pdf_output"] or request["image_output"]
        self._pdf_generation_requested = request["pdf_output"]
        requested_filename = re.search(r"([^\s<>\"/\\]+\.pdf)\b", prompt, re.IGNORECASE)
        self._requested_pdf_filename = requested_filename.group(1) if requested_filename else "document.pdf"
        request["pdf_filename"] = self._requested_pdf_filename
        self._is_repeat_query = False
        threading.Thread(target=self._stream, args=(request, lbl, bubble), daemon=True).start()

    def clear_chat(self):
        if self.streaming:
            return
        self._sync_chat_memory()
        project_key = self._chat_project_key or "global"
        self._chat_memory_generations[project_key] = (
            self._chat_memory_generations.get(project_key, 0) + 1
        )
        self.messages = []
        self.conversation_summary = ""
        for w in self.chat_container.winfo_children():
            w.destroy()
        self._send_welcome_message()
        self._save_chat_memory()
        self.status_var.set("Conversation effacee")

    def _add_bubble(self, sender, text, role, animate=True):
        row = ctk.CTkFrame(self.chat_container, fg_color="transparent")
        row.pack(fill="x", pady=6, padx=12)
        if role == "user":
            row.pack_configure(anchor="e")
            bubble_color = BUBBLE_USER
            header_color = "#9cebc9"
            side = "right"
            padx = (max(24, int(self.winfo_width() * 0.08)), 8)
            avatar = "V"
            avatar_bg = "#1c7c59"
        else:
            row.pack_configure(anchor="w")
            bubble_color = BUBBLE_AI
            header_color = ACCENT
            side = "left"
            padx = (8, max(24, int(self.winfo_width() * 0.08)))
            avatar = "C"
            avatar_bg = "#263547"

        avatar_lbl = ctk.CTkLabel(row, text=avatar, font=ctk.CTkFont(size=13, weight="bold"), width=34, height=34, text_color=TEXT_MAIN, fg_color=avatar_bg, corner_radius=17)
        avatar_lbl.pack(side=side, padx=(8, 6), pady=(2, 0))

        bubble = ctk.CTkFrame(row, fg_color=bubble_color, corner_radius=14, border_width=1, border_color="#263547")
        bubble.pack(side=side, padx=padx)
        ctk.CTkLabel(bubble, text=sender, font=ctk.CTkFont(size=10, weight="bold"), text_color=header_color, anchor="w").pack(fill="x", padx=16, pady=(10, 3))
        wraplength = max(360, min(980, int(self.winfo_width() * 0.62)))
        lbl = ctk.CTkLabel(bubble, text=text, font=ctk.CTkFont(size=13), text_color=TEXT_MAIN, justify="left", wraplength=wraplength, anchor="w")
        lbl.pack(fill="x", padx=16, pady=(0, 12))
        if role in ("user", "assistant"):
            ctk.CTkButton(bubble, text="Copier", width=54, height=24, fg_color="transparent", hover_color="#263547", text_color=TEXT_MUTED, font=ctk.CTkFont(size=10), corner_radius=8, command=lambda: self.copy_to_clipboard(lbl.cget("text"))).pack(side="right", padx=8, pady=(0, 8))
        self.after(30, self._scroll_bottom)
        return bubble, lbl

    def _scroll_bottom(self):
        try:
            self.update_idletasks()
            self.chat_container._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass

    def _stream(self, request, lbl, bubble):
        model = request["model"]
        temperature = request["temperature"]
        system = request["system"]
        if request.get("image_output"):
            request["web_enabled"] = False
            if not request.get("image_generator_available"):
                self.ui_queue.put(("done", lbl, "", bubble, request))
                return
            try:
                if request.get("image_edit_source"):
                    image_prompt = self._build_edit_prompt(model, request)
                else:
                    image_prompt = self._build_flux_prompt(model, request)
            except Exception:
                image_prompt = ""
            if not image_prompt:
                self.ui_queue.put(("error", lbl, "Impossible de préparer la description de l'image."))
                return
            self.ui_queue.put(
                ("done", lbl, "[GENERER_IMAGE: {}]".format(image_prompt), bubble, request)
            )
            return
        if request.get("pdf_output"):
            request["web_enabled"] = False
            try:
                document = self._build_pdf_document(model, request)
            except Exception as error:
                print("Erreur redaction PDF:", error)
                document = ""
            if document:
                filename = request.get("pdf_filename") or "document.pdf"
                if filename == "document.pdf":
                    filename = _pdf_filename_from_content(document, filename)
                full = "[CREER_FICHIER: {}]\n{}\n[/CREER_FICHIER]".format(filename, document)
            else:
                full = ""
                self.ui_queue.put(("error", lbl, "Je n'ai pas pu rédiger un document PDF complet. Essayez de donner plus de détails sur le sujet.", bubble, request))
                return
            self.ui_queue.put(("done", lbl, full, bubble, request))
            return
        now = time.strftime("%A %d %B %Y a %H:%M", time.localtime())
        system_with_context = "{}\n\nDate et heure actuelles : {}.\n".format(system, now)

        system_with_context += (
            "\nRegles de conversation :"
            "\n- Tu es un professeur pour debutants. Reduis ton aide au minimum."
            "\n- Pour une question d'apprentissage, donne des indices avant la solution."
            "\n- Encourage l'apprenant a chercher par lui-meme et a experimenter."
            "\n- Si tu ne comprends pas la question, dis-le clairement et demande une precision."
            "\n- Evite le ton robotique et les listes a puces interminables."
            "\n- Va droit au but et reste concis, sauf si l'utilisateur demande des details."
        )
        system_with_context += (
            "\n\nPour toute demande de code :"
            "\n- Si l'utilisateur demande explicitement du code ou une correction, fournis le code demande dans un bloc Markdown avec le langage et le nom du fichier (ex: ```html filename=index.html)."
            "\n- Ecris du code PROPRE, bien structure et commenté, comme un developpeur professionnel :"
            "\n  * Noms de variables et fonctions clairs et explicites (pas de 'a', 'b', 'x1')."
            "\n  * Indentation correcte et constante (2 espaces pour HTML/CSS/JS, 4 pour Python)."
            "\n  * Commentaires en francais pour expliquer le role de chaque partie importante."
            "\n  * Code responsive (mobile-first) pour le web, avec des unites relatives (%, rem, em) au lieu de pixels fixes."
            "\n  * Separation des responsabilités : HTML pour la structure, CSS pour l'apparence, JS pour le comportement."
            "\n  * Pas de code inline (style="" ou onclick="") dans le HTML ; mets tout dans les fichiers CSS et JS dédiés."
            "\n  * Gestion des erreurs basique et accesibilite (balises alt sur les images, contraste, navigation au clavier)."
            "\n  * Un fichier par responsabilite : index.html, style.css, script.js — ne mets pas tout dans un seul fichier."
            "\n- Sinon, aide par des explications et des indices plutot que de donner toute la solution."
            "\n- N'integre jamais une proposition de code dans un fichier sans que l'utilisateur l'ait explicitement acceptee."
        )

        if request["web_enabled"]:
            system_with_context += (
                "\n\nLa recherche web est disponible mais ne l'utilisez JAMAIS pour repondre a une question sur du code local ou de la programmation hors ligne."
                "\nN'appelez rechercher_sur_internet QUE si l'utilisateur demande explicitement des informations en ligne."
            )

        system_with_context += (
            "\n\nCreation de fichiers a la demande :"
            "\n- Pour un fichier texte ou source, quel que soit son type (HTML, code, Markdown, JSON, CSV, configuration, etc.), utilisez [CREER_FICHIER: nom.ext] contenu [/CREER_FICHIER]."
            "\n- Pour un petit fichier binaire, utilisez [CREER_FICHIER_BASE64: nom.ext] puis son Base64 brut, sans bloc de code ni commentaire, et [/CREER_FICHIER_BASE64]. La limite est de 5 Mo; pour une image, n utilisez jamais le Base64 ni le SVG : utilisez le generateur d images local [GENERER_IMAGE: ...] quand il est installe, sinon invitez a l installer dans Reglages."
            "\n- Si l'utilisateur demande un PDF a telecharger, creez-le directement avec [CREER_FICHIER: nom.pdf] puis son contenu textuel complet et [/CREER_FICHIER]. Ne donnez pas un script pour le fabriquer et ne mettez pas le contenu du PDF dans un bloc de code."
            "\n- Dans un PDF, le contenu entre balises doit etre uniquement le document, sans introduction ni commentaire adresse a l'utilisateur. Commencez par un titre Markdown, puis utilisez des sous-titres, des paragraphes, des listes et des blocs de code lorsque c'est pertinent."
            "\n- Gardez tout le contenu utile du PDF et n'ajoutez aucun texte de conversation a l'interieur des balises."
            "\n- Ne demandez pas a l'utilisateur d'utiliser Pandoc, MkDocs, LaTeX ou un autre logiciel; Calisto cree et fournit le PDF directement."
            "\n\nFormats de documents PDF que Calisto sait produire : rapport, note de synthese, lettre, CV, facture, devis, contrat, procedure, guide, catalogue, compte rendu, documentation technique."
            "\nMise en forme reconnue dans le contenu du PDF :"
            "\n- Titres # ## ###, paragraphes, listes - ou numerotees, citations >, separateurs ---."
            "\n- **gras**, *italique*, `code inline`, blocs de code ```langue."
            "\n- Tableaux Markdown : | Colonne | Colonne | puis une ligne |---|---| ; Calisto dessine les bordures et l'en-tete."
            "\n- Couleur de texte : [c:#C0392B]passage a souligner[/c] avec un code hexadecimal #RRGGBB."
            "\n- Document riche (CSS, images, colonnes, filigrane) : placez un document HTML complet (<!DOCTYPE html> ... </html>) entre les balises; Calisto le rend avec un vrai navigateur si disponible."
            "\n- Les images doivent pointer vers une URL http(s) ou un fichier local existant. Pas d'emoji ni de caracteres non latins : ils sont remplaces."
            "\n- Si le fichier est destine au projet ouvert, utilisez TOUJOURS la balise [CREER_FICHIER: nom.ext] avec le code complet a l'interieur. N'utilisez jamais de blocs Markdown ```filename=...``` pour creer des fichiers dans un projet, car ils ne sont pas enregistres sur le disque."
            "\n\nProjets de code - comportement professeur :"
            "\n- Quand l'utilisateur demande de l'aide pour coder ou creer un projet, agis comme un professeur patient."
            "\n- Guide par indices et questions, ne donne pas toute la solution d'un coup."
            "\n- Avant de generer du code, cree le dossier de projet avec la balise [CREER_PROJET: nom_du_projet]."
            "\n- Pour chaque fichier du projet, utilise EXACTEMENT une balise [CREER_FICHIER: nom.ext] suivie du code complet, puis [/CREER_FICHIER]."
            "\n- Exemple : [CREER_FICHIER: index.html] <!DOCTYPE html>... [/CREER_FICHIER]"
            "\n- Separe toujours le code en plusieurs fichiers selon le langage : un fichier HTML, un fichier CSS, un fichier JS. Ne mets pas tout dans un seul fichier."
            "\n- Exemple de structure attendue pour un site : index.html, style.css, script.js."
            "\n- Demande toujours l'autorisation avant de creer ou modifier des fichiers dans le projet."
            "\n- Explique chaque fichier et chaque ligne de code simplement, pour un debutant."
            "\n- Encourage l'utilisateur a tester et a corriger lui-même ses erreurs."
            "\n- Ne bascule pas vers l'editeur sans avoir cree le dossier de projet et obtenu l'accord."
        )
        if request["pdf_output"]:
            system_with_context += (
                "\n\nMODE PDF OBLIGATOIRE : l'utilisateur attend un vrai PDF telechargeable, pas une explication ni du code source."
                "\nProduis le document complet, avec un titre et plusieurs sections developpees selon la demande; ne t'arrete jamais au titre."
                "\nRetourne exactement [CREER_FICHIER: nom.pdf], puis le document Markdown complet, puis [/CREER_FICHIER]."
                "\nLe document doit contenir au moins une introduction ou un paragraphe substantiel et les details utiles demandes."
            )
        if request.get("image_generator_available"):
            system_with_context += (
                "\n\nGenerateur d'images local disponible : FLUX.1-schnell via stable-diffusion.cpp."
                "\nSi l'utilisateur demande explicitement une image, reponds brièvement puis ajoute "
                "exactement une balise [GENERER_IMAGE: description visuelle detaillee en anglais ou francais]."
                "\nC'est la SEULE methode pour generer une image. N'utilisez jamais Base64, SVG, ni code HTML pour une image."
                "\nN'invente pas de balise image pour une simple question ou demande de code."
                "\nL'image sera generee localement puis montree a l'utilisateur pour validation."
            )
        else:
            system_with_context += (
                "\n\nGenerateur d'images local : FLUX.1-schnell via stable-diffusion.cpp (non encore installe)."
                "\nSi l'utilisateur demande explicitement une image, reponds que Calisto peut generer des images "
                "localement et invite-le a ouvrir Reglages pour installer le generateur FLUX.1-schnell."
                "\nQuand il est installe, pour une demande d'image, ajoute exactement une balise "
                "[GENERER_IMAGE: description visuelle detaillee en anglais ou francais]."
                "\nNe proposez jamais de generer une image par Base64, SVG ou code HTML."
                "\nN'affirmez pas avoir cree une image tant que le generateur n'est pas installe."
            )

        if request["allow_modify"]:
            system_with_context += "\n\nVous pouvez modifier l'application Calisto. Utilisez le format [MODIFIER_APP: chemin.py] contenu [/MODIFIER_APP]."

        if request["repeat_query"]:
            system_with_context += "\n\nNOTE : l'utilisateur repose exactement la meme question. Ne repetez pas la meme reponse. Approfondissez, changez d'angle ou demandez ce qui n'a pas ete compris."

        memory_history = [
            dict(m) for m in request.get("memory_history", request["history"])
        ]
        history = [dict(m) for m in request["history"]]
        for index, m in enumerate(history):
            limit = 2500 if index == len(history) - 1 and m.get("role") == "user" else 800
            m["content"] = m.get("content", "")[:limit]
        if request["conversation_summary"]:
            system_with_context += (
                "\n\nMemoire durable du projet (contexte des echanges precedents) :\n"
                + request["conversation_summary"]
            )
        if request["editor_context"]:
            system_with_context += (
                "\n\nContexte actuel du projet dans l'editeur :\n"
                + request["editor_context"]
                + "\nUtilise ce contexte pour discuter des fichiers; ne les modifie jamais sans acceptation explicite."
            )

        msgs = [{"role": "system", "content": system_with_context}] + history
        full = ""
        # Une demande d'image ne doit jamais passer par la recherche web.
        if request.get("image_output"):
            request["web_enabled"] = False
        try:
            if request["web_enabled"]:
                full = chat_with_web_search(
                    model,
                    msgs,
                    temperature,
                    enabled=True,
                    on_search=lambda q: self.ui_queue.put(("search", q)),
                    num_ctx=8192 if request["large_output"] else 4096,
                    num_predict=6144 if request["large_output"] else 768,
                )
                if request["pdf_output"]:
                    full = self._ensure_pdf_response(model, msgs, full, request)
                if request.get("image_output") and request.get("image_generator_available"):
                    full = self._ensure_image_response(request, full)
                self.ui_queue.put(("done", lbl, full, bubble, request))
                self._schedule_chat_compaction(request, memory_history, full)
                return
            num_ctx = 8192 if request["large_output"] else 4096
            num_predict = 6144 if request["large_output"] else 768
            stream = ollama.chat(
                model=model,
                messages=msgs,
                stream=True,
                options={
                    "temperature": temperature,
                    "num_ctx": num_ctx,
                    "num_predict": num_predict,
                },
            )
            pending_text = ""
            last_ui_update = time.monotonic()
            for chunk in stream:
                tok = chunk["message"]["content"]
                full += tok
                pending_text += tok
                if time.monotonic() - last_ui_update >= 0.05:
                    self.ui_queue.put(("token", lbl, pending_text))
                    pending_text = ""
                    last_ui_update = time.monotonic()
            if pending_text:
                self.ui_queue.put(("token", lbl, pending_text))
            if request["pdf_output"]:
                full = self._ensure_pdf_response(model, msgs, full, request)
            if request.get("image_output") and request.get("image_generator_available"):
                full = self._ensure_image_response(request, full)
            self.ui_queue.put(("done", lbl, full, bubble, request))
            self._schedule_chat_compaction(request, memory_history, full)
        except Exception as e:
            self.ui_queue.put(("error", lbl, str(e)))
        finally:
            self.after(0, self._finish)

    def _build_pdf_document(self, model, request):
        user_text = ""
        for item in reversed(request.get("history", [])):
            if item.get("role") == "user":
                user_text = item.get("content", "").strip()
                break
        user_text = user_text[:7000]
        if not user_text:
            return ""
        messages = [
            {
                "role": "system",
                "content": (
                    "Tu rediges un document en francais au format Markdown, d'apres la demande. "
                    "Reponds UNIQUEMENT avec le document, sans phrase d'introduction ni commentaire. "
                    "Le document doit etre TRES LONG, COMPLET et detaille : introduction, plusieurs sections developpees sur plusieurs paragraphes chacune, "
                    "et une conclusion developpee. Chaque section doit contenir au moins 3 paragraphes riches, precises et exhaustifs. "
                    "N'aie pas peur d'ecrire beaucoup : un chapitre peut prendre une page complete, c'est preferable a 2 pauvres lignes. "
                    "Regles de format strictes :"
                    "- La premiere ligne est le titre : # Titre."
                    "- Chaque section commence sur sa propre ligne par ## Titre de section. "
                    "N'utilise pas **gras** a la place des titres."
                    "- Un retour a la ligne entre chaque titre, paragraphe et element de liste."
                    "- Les listes utilisent -  au debut de chaque ligne."
                    "- Le code et les balises HTML s'ecrivent entre balises HTML, jamais en texte brut."
                    "- Utilise des emojis pour illuminer certains titres et sections (varie-les a chaque document)."
                    "- Inclus des encadrés, des listes a puces, des comparaisons, des exemples concrets, des anecdotes ou des cas d'usage."
                    "- VARIE le style d'ecriture a chaque document : tantot pedagogique, tantot journalistique, tantot technique, tantot narratif. "
                    "Ne reuse jamais la meme structure que precedemment. Change l'ordre des sections, le ton et la mise en page a chaque fois."
                    "- Ne mentionne JAMAIS que le document a ete genere par une IA, par Calisto, ou par un assistant. "
                    "Ne signe pas le document, n'ajoute pas de mention 'Cree par Calisto', 'Genere par IA' ou similaire. "
                    "Le document doit paraitre redige directement pour l'utilisateur."
                    "- Base-toi UNIQUEMENT sur les informations fournies dans la demande. "
                    "Si tu ne connais pas le sujet, n'invente aucun fait, produit ou chiffre : "
                    "ecris un document court et indique ce qui manque."
                    "- Contexte (a utiliser seulement si la demande parle de Calisto) : "
                    "Calisto est une application de bureau Windows, ecrite en Python avec CustomTkinter. "
                    "C'est un assistant IA local pour debutants en developpement web, qui fonctionne hors ligne "
                    "grace au moteur Ollama (modele qwen2.5:7b par defaut). "
                    "Fonctions : discussion avec un professeur patient qui guide par indices ; "
                    "generation d'images en local avec FLUX.1-schnell (apercu, validation, telechargement) ; "
                    "creation de PDF avec apercu avant validation ; "
                    "editeur de code integre qui propose des modifications que l'utilisateur accepte ou refuse ; "
                    "mode Apprentissage avec exercices HTML/CSS/JavaScript, chronometre et verification par l'IA. "
                    "Calisto ne convertit pas d'images en PDF et n'execute pas le code. "
                    "N'invente aucune autre fonction, plateforme, version, prix ou technologie."
                ),
            },
            {"role": "user", "content": user_text},
        ]
        for attempt in range(3):
            result = ollama.chat(
                model=model,
                messages=messages,
                stream=False,
                options={
                    "temperature": 0.5 if attempt == 0 else 0.3,
                    "num_ctx": 8192,
                    "num_predict": 12000,
                },
            )
            response = (result.get("message", {}).get("content") or "").strip()
            document = _extract_pdf_document_text(response)
            lines = [line for line in document.splitlines() if line.strip()]
            has_headings = bool(re.search(r"(?m)^\s{0,3}#{1,6}\s+\S", document))
            nb_sections = len(re.findall(r"(?m)^\s{0,3}##\s+\S", document))
            total_chars = len(document)
            if has_headings and nb_sections >= 3 and len(lines) >= 15 and total_chars >= 1500 and _is_complete_pdf_document(document):
                return document
            messages.append({"role": "assistant", "content": response[:4000]})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Format incorrect ou document trop court. Recommence : un titre # ... sur la premiere ligne, "
                        "au moins 3 sections ## avec plusieurs paragraphes riches chacune, une conclusion developpee, "
                        "des listes, des emojis et des exemples. Uniquement le document, tres complet et detaille."
                    ),
                }
            )
        return ""


    def _build_flux_prompt(self, model, request):
        user_text = ""
        for item in reversed(request.get("history", [])):
            if item.get("role") == "user":
                user_text = item.get("content", "").strip()
                break
        user_text = re.sub(r"\[Image jointe[^\]]*\]", "", user_text).strip()
        user_text = " ".join(user_text[:800].split())
        if not user_text:
            return ""
        est_coloriage = bool(re.search(r"coloriage|colori|dessin.*enfant|ligne.*noire", user_text, re.I))
        est_plusieurs_personnes = bool(re.search(
            r"\b(?:deux|trois|quatre|cinq|plusieurs|groupe|couple|famille|personnes|gens|ensemble|"
            r"two|three|four|five|multiple|couple|family|people|group|together)\b",
            user_text, re.I
        ))
        try:
            system = (
                "You turn an image request into ONE English prompt for FLUX.1-schnell. "
                "Reply with ONLY the prompt, a single sentence (subject, setting, style). "
                "No JSON, no code, no quotes, no explanation."
            )
            if est_coloriage:
                system += (
                    " The user wants a CHILDREN COLORING PAGE: black bold outlines on white background, "
                    "no colors, no fill, no shading, clean line art suitable for coloring."
                )
            if est_plusieurs_personnes:
                system += (
                    " The request contains MULTIPLE PEOPLE: describe each person as a SEPARATE figure "
                    "with clear space between them, distinct positions, do not merge or blend subjects "
                    "into one figure, avoid overlapping bodies."
                )
            result = ollama.chat(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": system,
                    },
                    {"role": "user", "content": user_text},
                ],
                options={"temperature": 0.3, "num_predict": 160},
            )
            text = (result.get("message", {}).get("content") or "").strip()
            text = text.replace("[", "").replace("]", "").strip(" \n\"'")
            text = " ".join(text.split())
            if len(text) > 8 and not text.startswith(("{", "<", "`")):
                if est_coloriage and not re.search(r"coloring|outline|line art|black and white", text, re.I):
                    text = "children coloring page, black bold outlines on white background, " + text
                if est_plusieurs_personnes and not re.search(r"separate|distinct|space between|do not merge", text, re.I):
                    text = "multiple separate figures, distinct figures, space between them, do not merge, " + text
                return text
        except Exception:
            pass
        fallback = user_text.replace("[", "").replace("]", "")
        if est_coloriage:
            fallback = "children coloring page, black bold outlines on white background, " + fallback
        if est_plusieurs_personnes:
            fallback = "multiple separate figures, distinct figures, space between them, do not merge, " + fallback
        return fallback

    def _describe_image(self, path):
        """Decrit l image avec un modele de vision Ollama, s il y en a un installe."""
        try:
            names = ai_runtime.list_models() if ai_runtime else []
            vision = next(
                (
                    n for n in names
                    if re.search(r"vision|llava|moondream|minicpm-v|qwen2\.5vl", n, re.I)
                ),
                None,
            )
            if not vision:
                return ""
            result = ollama.chat(
                model=vision,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Describe this image in one detailed English sentence for an image "
                            "generator: subject, colors, setting, style. Reply with only the sentence."
                        ),
                        "images": [str(path)],
                    }
                ],
                options={"temperature": 0.2, "num_predict": 120},
                keep_alive=0,
            )
            text = (result.get("message", {}).get("content") or "").strip()
            return " ".join(text.replace("[", "").replace("]", "").split())
        except Exception:
            return ""

    def _build_edit_prompt(self, model, request):
        wish = self._build_flux_prompt(model, request)
        description = self._describe_image(request.get("image_edit_source"))
        pieces = [p for p in (description, wish, "highly detailed, sharp, high quality") if p]
        return ", ".join(pieces)[:900].replace("[", "").replace("]", "")

    @staticmethod
    def _prepare_init_image(source, output_path):
        """Recadre l image en carre 512x512 pour FLUX et l enregistre a cote de la sortie."""
        with Image.open(source) as opened:
            image = opened.convert("RGB")
        side = min(image.size)
        left = (image.width - side) // 2
        top = (image.height - side) // 2
        image = image.crop((left, top, left + side, top + side)).resize((512, 512))
        init_path = Path(output_path).with_name(Path(output_path).stem + "-source.png")
        image.save(init_path)
        return init_path

    @staticmethod
    def _render_pdf_thumbnail(pdf_path):
        """Rend la premiere page d un PDF en miniature PIL Image (64x64)."""
        try:
            pdf = pdfium.PdfDocument(str(pdf_path))
            if len(pdf) == 0:
                return None
            page = pdf[0]
            image = page.render(scale=0.5).to_pil()
            image.thumbnail((64, 64))
            return ImageTk.PhotoImage(image)
        except Exception:
            return None

    def _ensure_image_response(self, request, response):
        match = re.search(r"\[GENERER_IMAGE:\s*(.*?)\]", str(response), re.IGNORECASE | re.DOTALL)
        if match and match.group(1).strip():
            return str(response)
        prompt = ""
        for item in reversed(request.get("history", [])):
            if item.get("role") == "user":
                prompt = item.get("content", "").strip()
                break
        if not prompt:
            return str(response)
        image_prompt = (
            "Create a polished, high-quality image based on this request. "
            "Do not render text unless explicitly requested. "
            "Visual brief: " + prompt[:1800]
        )
        return "{}\n\n[GENERER_IMAGE: {}]".format(str(response).strip(), image_prompt)

    @staticmethod
    def _image_filename_from_prompt(prompt):
        slug = unicodedata.normalize("NFKD", str(prompt))
        slug = slug.encode("ascii", "ignore").decode("ascii").lower()
        slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")[:48]
        return "image-{}.png".format(slug or "calisto")

    def _ensure_pdf_response(self, model, messages, response, request):
        document = _extract_pdf_document_text(response)
        if not _is_complete_pdf_document(document):
            repair_messages = messages + [
                {"role": "assistant", "content": str(response)[:12000]},
                {
                    "role": "user",
                    "content": (
                        "Ta réponse précédente n'a pas fourni un document PDF complet. "
                        "Recommence maintenant et retourne uniquement un document Markdown complet "
                        "entre [CREER_FICHIER: nom.pdf] et [/CREER_FICHIER]. Inclue le titre, "
                        "les sections et leur contenu; ne renvoie pas seulement un titre."
                    ),
                },
            ]
            try:
                repaired = ollama.chat(
                    model=model,
                    messages=repair_messages,
                    stream=False,
                    options={
                        "temperature": 0.2,
                        "num_ctx": 8192,
                        "num_predict": 6144,
                    },
                )
                response = repaired["message"]["content"]
                document = _extract_pdf_document_text(response)
            except Exception as error:
                print("Nouvelle tentative de creation PDF echouee:", error)
                return ""
        if not _is_complete_pdf_document(document):
            return ""
        filename = request.get("pdf_filename") or _pdf_filename_from_content(document)
        if filename == "document.pdf":
            filename = _pdf_filename_from_content(document, filename)
        return "[CREER_FICHIER: {}]\n{}\n[/CREER_FICHIER]".format(filename, document)

    def _schedule_chat_compaction(self, request, history, assistant_reply):
        project_key = request["chat_project_key"]
        if project_key in self._memory_compaction_in_progress:
            return
        complete_history = history + [
            {"role": "assistant", "content": str(assistant_reply)[:6000]}
        ]
        if len(complete_history) <= 20:
            return
        self._memory_compaction_in_progress.add(project_key)
        threading.Thread(
            target=self._compact_chat_memory,
            args=(
                request["model"],
                project_key,
                request["conversation_summary"],
                self._chat_memory_generations.get(project_key, 0),
                complete_history,
            ),
            daemon=True,
        ).start()

    def _compact_chat_memory(
        self, model, project_key, previous_summary, generation, history
    ):
        while self.streaming or time.monotonic() - self._last_chat_activity < 2:
            time.sleep(0.25)
        keep_count = 12
        older_messages = history[:-keep_count]
        conversation = "\n\n".join(
            "{}: {}".format("Utilisateur" if item["role"] == "user" else "Calisto", item["content"])
            for item in older_messages
        )
        prompt = (
            "Mets a jour la memoire durable de ce projet en francais. Preserve les objectifs, "
            "decisions, preferences, fichiers/code importants et points a reprendre. Ignore le "
            "bavardage et les details temporaires. Reponds sous forme de notes compactes, "
            "sans inventer d'information et en 6000 caracteres maximum.\n\n"
            "Memoire precedente :\n{}\n\nAnciens echanges :\n{}"
        ).format(previous_summary or "(aucune)", conversation)
        try:
            result = ollama.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                stream=False,
                options={"temperature": 0.1, "num_ctx": 4096, "num_predict": 900},
            )
            summary = result["message"]["content"].strip()
            if not summary:
                raise ValueError("Le modele a renvoye une memoire vide.")
            self.ui_queue.put(
                (
                    "memory_compacted",
                    project_key,
                    generation,
                    summary[:6000],
                    history[-keep_count:],
                    history,
                )
            )
        except Exception as error:
            self.ui_queue.put(("memory_error", project_key, generation, str(error)))

    def _process_ui_queue(self):
        token_updates = {}
        done_events = []
        error_events = []
        memory_events = []
        artifact_events = []
        try:
            while True:
                ev = self.ui_queue.get_nowait()
                if ev[0] == "token":
                    _, lbl, tok = ev
                    token_updates[lbl] = token_updates.get(lbl, "") + tok
                elif ev[0] == "done":
                    done_events.append(ev)
                elif ev[0] == "error":
                    error_events.append(ev)
                elif ev[0] in ("memory_compacted", "memory_error"):
                    memory_events.append(ev)
                elif ev[0] in (
                    "image_generated",
                    "image_generation_error",
                    "artifact_regenerated",
                    "artifact_regeneration_error",
                ):
                    artifact_events.append(ev)
                elif ev[0] == "image_setup_progress":
                    _, name, received, total = ev
                    if self._image_setup_label and self._image_setup_label.winfo_exists():
                        if total:
                            self._image_setup_label.configure(
                                text="Téléchargement {} : {:.1f} / {:.1f} Go".format(
                                    name,
                                    received / (1024 ** 3),
                                    total / (1024 ** 3),
                                ),
                                text_color="#eab308",
                            )
                elif ev[0] == "image_setup_done":
                    self._image_generation_busy = False
                    if self._image_setup_label and self._image_setup_label.winfo_exists():
                        self._image_setup_label.configure(
                            text="FLUX.1-schnell est prêt.",
                            text_color=ACCENT,
                        )
                    self.status_var.set("Générateur d'images prêt")
                elif ev[0] == "image_setup_error":
                    self._image_generation_busy = False
                    _, detail = ev
                    if self._image_setup_label and self._image_setup_label.winfo_exists():
                        self._image_setup_label.configure(
                            text="Installation incomplète. Consultez le message d'erreur.",
                            text_color="#ef4444",
                        )
                    messagebox.showerror("Installation de FLUX impossible", detail)
                elif ev[0] == "ai_ready":
                    _, disponible, message = ev
                    self._on_ai_ready(disponible, message)
                elif ev[0] == "ai_status":
                    self.status_var.set(ev[1])
                elif ev[0] == "search":
                    self.status_var.set("Recherche web : {}".format(ev[1]))
                elif ev[0].startswith("learning_"):
                    _, window, *payload = ev
                    if self.learning_mode_window is window and window.is_active():
                        window._handle_worker_event(ev[0], *payload)
        except queue.Empty:
            pass

        completed_labels = set()
        for ev in done_events:
            _, lbl, full, bubble, request = ev
            completed_labels.add(lbl)
            self._scroll_bottom()
            pdf_requested = getattr(self, "_pdf_generation_requested", False)
            has_markdown_document = bool(
                re.search(r"```(?:markdown|md)\b", full, re.IGNORECASE)
                or re.search(r"(?m)^\s{0,3}#{1,6}\s+\S", full)
                or re.search(r"(?im)^\s*\*\*titre\*\*\s*\r?\n\s*=+", full)
                or re.search(
                    r"(?im)^\s*\*\*(?:titre|introduction|etape|étape|fonctionnalit[eé]s|conclusion)\b",
                    full,
                )
            )
            pdf_response = bool(
                re.search(PDF_RESPONSE_HINT_PATTERN, full, re.IGNORECASE)
                and has_markdown_document
            )
            has_pdf_marker = bool(
                re.search(PDF_CREATION_START_PATTERN, full, re.IGNORECASE)
                or re.search(PDF_ALIAS_TAG_PATTERN, full, re.IGNORECASE)
            )
            pdf_output = pdf_requested or pdf_response or has_pdf_marker
            pdf_filename = getattr(self, "_requested_pdf_filename", "document.pdf")
            self._finish()
            created_pdfs = self.check_ai_creation_commands(
                full,
                bubble,
                pdf_requested=pdf_output,
                pdf_filename=pdf_filename,
                request=request,
            )
            display_text = full
            if pdf_output:
                if pdf_output and not has_pdf_marker:
                    display_text = ""
                else:
                    display_text = re.sub(
                        PDF_CREATION_BLOCK_PATTERN,
                        "",
                        full,
                        flags=re.IGNORECASE | re.DOTALL,
                    )
                    display_text = re.sub(
                        r"(?:" + PDF_CREATION_START_PATTERN + r"|" + PDF_ALIAS_TAG_PATTERN + r").*$",
                        "",
                        display_text,
                        flags=re.IGNORECASE | re.DOTALL,
                    )
                    display_text = re.sub(r"\n{3,}", "\n\n", display_text).strip()
                if created_pdfs:
                    summary = "Aperçu du PDF « {} » : valide-le, recommence ou refuse-le ci-dessous.".format(
                        created_pdfs[0].name
                    )
                    display_text = "{}\n\n{}".format(display_text, summary).strip()
                elif has_pdf_marker and _is_complete_pdf_document(
                    _extract_pdf_document_text(full)
                ):
                    display_text = (
                        "Le document est prêt, mais le PDF n'a pas été enregistré. "
                        "Vérifiez l'autorisation de création, puis réessayez."
                    )
                else:
                    notice = (
                        "Je n'ai pas pu obtenir un contenu PDF complet, même après une nouvelle tentative. "
                        "Aucun fichier vide n'a été créé."
                    )
                    display_text = "{}\n\n{}".format(display_text, notice).strip()
            image_output = request.get("image_output", False)
            image_match = re.search(
                r"\[GENERER_IMAGE:\s*(.*?)\]",
                full,
                re.IGNORECASE | re.DOTALL,
            )
            image_prompt = image_match.group(1).strip() if image_match else ""
            if image_match:
                display_text = re.sub(
                    r"\[GENERER_IMAGE:\s*.*?\]",
                    "",
                    display_text,
                    flags=re.IGNORECASE | re.DOTALL,
                ).strip()
            if image_output and request.get("image_generator_available") and image_prompt:
                status_message = "Je prépare l’image localement. Un aperçu apparaîtra ici pour que tu puisses l’accepter, la recommencer ou la refuser."
                display_text = "{}\n\n{}".format(display_text, status_message).strip()
                self._start_image_generation(
                    image_prompt,
                    bubble,
                    request,
                    filename=self._image_filename_from_prompt(image_prompt),
                )
            elif image_output and not request.get("image_generator_available"):
                display_text = (
                    "{}\n\nLe générateur d'images local n'est pas installé. "
                    "Ouvre Réglages pour configurer FLUX.1-schnell.".format(display_text)
                ).strip()
            if lbl.winfo_exists():
                lbl.configure(text=display_text or "Le fichier est prêt.")
            self.messages.append({"role": "assistant", "content": display_text})
            self._save_chat_memory()
            self._offer_code_proposals(
                full,
                pdf_output=pdf_output or bool(image_output),
                code_project=bool(request.get("code_project")),
            )
            self._last_chat_activity = time.monotonic()

        for event in artifact_events:
            self._handle_artifact_event(event)

        for ev in memory_events:
            if ev[0] == "memory_compacted":
                _, project_key, generation, summary, messages, source_history = ev
                if generation != self._chat_memory_generations.get(project_key, 0):
                    self._memory_compaction_in_progress.discard(project_key)
                    continue
                if project_key == self._chat_project_key:
                    current_messages = [dict(item) for item in self.messages]
                    source_prefix = source_history[:-1]
                    if current_messages[:len(source_prefix)] == source_prefix:
                        later_messages = current_messages[len(source_prefix):]
                        if (
                            later_messages
                            and later_messages[0].get("role") == "assistant"
                            and messages
                            and messages[-1].get("role") == "assistant"
                        ):
                            messages[-1] = later_messages.pop(0)
                        messages.extend(later_messages)
                self._save_chat_memory(
                    project_key=project_key,
                    summary=summary,
                    messages=messages,
                )
                if project_key == self._chat_project_key:
                    self.conversation_summary = summary
                    self.messages = messages
                    self._render_chat_history()
            else:
                _, project_key, generation, detail = ev
                print("Erreur condensation mémoire conversation:", detail)
                if (
                    generation == self._chat_memory_generations.get(project_key, 0)
                    and project_key == self._chat_project_key
                ):
                    self.status_var.set("La mémoire du projet n'a pas pu être condensée.")
            self._memory_compaction_in_progress.discard(project_key)

        for lbl, text in token_updates.items():
            if (
                lbl not in completed_labels
                and lbl.winfo_exists()
                and not getattr(self, "_suppress_streaming", False)
            ):
                current = "" if lbl.cget("text") == "Calisto prepare sa reponse…" else lbl.cget("text")
                lbl.configure(text=current + text)
                self._scroll_bottom()

        for ev in error_events:
            _, lbl, detail = ev
            if ai_runtime is not None and not ai_runtime.is_running(timeout=0.1):
                detail = "Le moteur IA (Ollama) n'est pas accessible.\n\n{}\n\nRelancez Ollama puis reessayez.".format(detail)
            if lbl.winfo_exists():
                lbl.configure(text="Erreur : {}".format(detail))
            messagebox.showerror("Erreur de l'IA", detail)
            self._finish()
        if self.streaming:
            self._finish()
        self.after(50, self._process_ui_queue)

    def _finish(self):
        self.streaming = False
        self._suppress_streaming = False
        self._pdf_generation_requested = False
        self.send_btn.configure(state="normal", fg_color=ACCENT)
        self.status_var.set("Pret")

    def _get_editor_context(self):
        if self.dev_window is not None and self.dev_window.winfo_exists():
            context_files = self.dev_window.get_ai_context_files()
            active_files = [
                name for name in context_files if "fichier ouvert" in name.lower()
            ]
            metadata_files = [
                name for name in context_files
                if name.startswith("Projet de l'editeur") or name == "Actions recentes de l'editeur"
            ]
            other_files = [
                name for name in context_files
                if name not in active_files and name not in metadata_files
            ]
            ordered_names = active_files + metadata_files + other_files
            remaining = 12000
            sections = []
            for name in ordered_names:
                if remaining <= 0:
                    break
                content = context_files[name][:remaining]
                sections.append("--- {} ---\n{}".format(name, content))
                remaining -= len(content)
            return "\n\n".join(sections)
        return ""

    def _offer_code_proposals(self, response, pdf_output=False, code_project=False):
        if code_project:
            return
        if (
            pdf_output
            or re.search(PDF_CREATION_START_PATTERN, response, re.IGNORECASE)
            or re.search(PDF_ALIAS_TAG_PATTERN, response, re.IGNORECASE)
            or re.search(PDF_RESPONSE_HINT_PATTERN, response, re.IGNORECASE)
        ):
            return
        if self.dev_window is None or not self.dev_window.winfo_exists():
            return
        blocks = re.findall(r"```([^\n`]*)\n(.*?)```", response, re.DOTALL)
        proposal_count = 0
        for info, code in blocks:
            if not code.strip():
                continue
            language_match = re.match(r"([^\s]+)", info.strip())
            language = language_match.group(1).lower() if language_match else "text"
            filename_match = re.search(r"(?:filename|file)=([^\s]+)", info, re.IGNORECASE)
            filename = filename_match.group(1).strip("\"'") if filename_match else None
            if self.dev_window.create_chat_proposal(code.strip(), language, filename):
                proposal_count += 1
        if proposal_count:
            self.tabs.set("Editeur de code")
            self.status_var.set("Proposition de code disponible dans l'editeur")

    def _extract_pdf_tagged_contents(self, text):
        matches = list(re.finditer(PDF_ALIAS_TAG_PATTERN, text, re.IGNORECASE))
        contents = {}
        for index, match in enumerate(matches):
            filepath = match.group(1).strip().strip("\"'")
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            content = _strip_pdf_chat_text(text[match.end():end]).strip()
            key = filepath.casefold()
            if content and (key not in contents or len(content) > len(contents[key][1])):
                contents[key] = (filepath, content)
        return list(contents.values())

    def check_ai_creation_commands(
        self,
        text,
        bubble=None,
        pdf_requested=False,
        pdf_filename="document.pdf",
        request=None,
    ):
        created_pdfs = []
        explicit_pdf_tag = bool(
            re.search(PDF_CREATION_START_PATTERN, text, re.IGNORECASE)
            or re.search(PDF_ALIAS_TAG_PATTERN, text, re.IGNORECASE)
        )
        binary_pattern = r"\[CREER_FICHIER_BASE64:\s*([^\]]+)\](.*?)\[/CREER_FICHIER_BASE64\]"
        for filepath, content in re.findall(binary_pattern, text, re.DOTALL | re.IGNORECASE):
            filename = Path(filepath.strip()).name
            if filename.lower().endswith(".pdf"):
                target_path = self._stage_binary_pdf_artifact(
                    filename,
                    content.strip(),
                    bubble,
                    request,
                )
            elif Path(filename).suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                target_path = self._stage_binary_image_artifact(
                    filename,
                    content.strip(),
                    bubble,
                    request,
                )
            else:
                target_path = self.handle_ai_creation_request(
                    "fichier",
                    filepath.strip(),
                    content.strip(),
                    binary=True,
                )
            if target_path and target_path.suffix.lower() == ".pdf":
                created_pdfs.append(target_path)
        pattern = r"\[CREER_FICHIER:\s*([^\]]+)\](.*?)\[/CREER_FICHIER\]"
        for filepath, content in re.findall(pattern, text, re.DOTALL | re.IGNORECASE):
            filename = Path(filepath.strip()).name
            if filename.lower().endswith(".pdf"):
                target_path = self._stage_pdf_artifact(
                    filename,
                    content.strip("\r\n"),
                    bubble,
                    request,
                )
            else:
                target_path = self.handle_ai_creation_request(
                    "fichier",
                    filepath.strip(),
                    content.strip("\r\n"),
                )
            if target_path and target_path.suffix.lower() == ".pdf":
                created_pdfs.append(target_path)
        if not re.search(PDF_CREATION_START_PATTERN, text, re.IGNORECASE) and not created_pdfs:
            for filepath, content in self._extract_pdf_tagged_contents(text):
                target_path = self._stage_pdf_artifact(
                    Path(filepath).name,
                    content,
                    bubble,
                    request,
                ) if Path(filepath).suffix.lower() == ".pdf" else self.handle_ai_creation_request(
                    "fichier",
                    filepath,
                    content,
                )
                if target_path:
                    created_pdfs.append(target_path)
        if pdf_requested and not explicit_pdf_tag:
            response_filename = re.search(
                r"([^\s<>\"/\\]+\.pdf)\b",
                text,
                re.IGNORECASE,
            )
            content = _extract_pdf_document_text(text)
            if _is_complete_pdf_document(content):
                filename = (
                    response_filename.group(1)
                    if response_filename
                    else _pdf_filename_from_content(content, pdf_filename)
                )
                target_path = self._stage_pdf_artifact(
                    Path(filename).name,
                    content,
                    bubble,
                    request,
                )
                if target_path:
                    created_pdfs.append(target_path)
        pattern2 = r"\[MODIFIER_APP: ([^\]]+)\](.*?)\[/MODIFIER_APP\]"
        for filepath, content in re.findall(pattern2, text, re.DOTALL):
            self.handle_ai_creation_request("app", filepath.strip(), content.strip("\r\n"))
        # Projets de code : [CREER_PROJET: nom_du_projet]
        pattern3 = r"\[CREER_PROJET:\s*([^\]]+)\]"
        for nom_projet in re.findall(pattern3, text, re.IGNORECASE):
            self._create_code_project(nom_projet.strip())
        return created_pdfs

    def _stage_pdf_artifact(self, filename, content, bubble, request=None):
        if not _is_complete_pdf_document(content):
            return None
        try:
            final_path = resolve_generated_file_path(Path(filename).name)
            artifact_id = hashlib.sha256(
                "{}:{}:{}".format(time.time_ns(), filename, id(bubble)).encode("utf-8")
            ).hexdigest()[:16]
            staging_dir = IA_CREATIONS_DIR / ".pending"
            staging_dir.mkdir(parents=True, exist_ok=True)
            staged_path = staging_dir / (artifact_id + ".pdf")
            write_markdown_pdf(staged_path, content)
            artifact = {
                "id": artifact_id,
                "kind": "pdf",
                "filename": final_path.name,
                "path": staged_path,
                "content": content,
                "prompt": "",
                "request": request,
                "bubble": bubble,
                "accepted": False,
                "busy": False,
            }
            self._pending_generated_artifacts[artifact_id] = artifact
            self._display_generated_artifact(artifact)
            return staged_path
        except (OSError, ValueError, RuntimeError) as error:
            messagebox.showerror("Aperçu PDF impossible", str(error))
            return None

    def _stage_binary_pdf_artifact(self, filename, content, bubble, request=None):
        staged_path = None
        try:
            data = decode_generated_binary(content)
            if not data.startswith(b"%PDF-"):
                raise ValueError("Le contenu Base64 ne correspond pas à un PDF valide.")
            final_path = resolve_generated_file_path(Path(filename).name)
            artifact_id = hashlib.sha256(
                "{}:{}:{}".format(time.time_ns(), filename, id(bubble)).encode("utf-8")
            ).hexdigest()[:16]
            staging_dir = IA_CREATIONS_DIR / ".pending"
            staging_dir.mkdir(parents=True, exist_ok=True)
            staged_path = staging_dir / (artifact_id + ".pdf")
            staged_path.write_bytes(data)
            document = pdfium.PdfDocument(str(staged_path))
            try:
                if not len(document):
                    raise ValueError("Le PDF ne contient aucune page.")
            finally:
                document.close()
            artifact = {
                "id": artifact_id,
                "kind": "pdf",
                "filename": final_path.name,
                "path": staged_path,
                "content": "",
                "prompt": "",
                "request": request,
                "bubble": bubble,
                "accepted": False,
                "busy": False,
            }
            self._pending_generated_artifacts[artifact_id] = artifact
            self._display_generated_artifact(artifact)
            return staged_path
        except (OSError, ValueError, RuntimeError) as error:
            if staged_path and staged_path.exists():
                staged_path.unlink()
            messagebox.showerror("Aperçu PDF impossible", str(error))
            return None

    def _stage_binary_image_artifact(self, filename, content, bubble, request=None):
        staged_path = None
        try:
            data = decode_generated_binary(content)
            final_path = resolve_generated_file_path(Path(filename).name)
            artifact_id = hashlib.sha256(
                "{}:{}:{}".format(time.time_ns(), filename, id(bubble)).encode("utf-8")
            ).hexdigest()[:16]
            staging_dir = IA_CREATIONS_DIR / ".pending"
            staging_dir.mkdir(parents=True, exist_ok=True)
            extension = Path(filename).suffix.lower()
            staged_path = staging_dir / (artifact_id + extension)
            staged_path.write_bytes(data)
            with Image.open(staged_path) as image:
                image.verify()
            prompt = ""
            for item in reversed((request or {}).get("history", [])):
                if item.get("role") == "user":
                    prompt = item.get("content", "")
                    break
            artifact = {
                "id": artifact_id,
                "kind": "image",
                "filename": final_path.name,
                "path": staged_path,
                "content": "",
                "prompt": prompt,
                "request": request,
                "bubble": bubble,
                "accepted": False,
                "busy": False,
            }
            self._pending_generated_artifacts[artifact_id] = artifact
            self._display_generated_artifact(artifact)
            return staged_path
        except (OSError, ValueError, RuntimeError) as error:
            if staged_path and staged_path.exists():
                staged_path.unlink()
            messagebox.showerror("Aperçu image impossible", str(error))
            return None

    def _stage_image_artifact(self, filename, source_path, prompt, bubble, request):
        source_path = Path(source_path).resolve()
        pending_root = (IA_CREATIONS_DIR / ".pending").resolve()
        try:
            source_path.relative_to(pending_root)
        except ValueError as error:
            raise ValueError("L'image générée est hors du dossier temporaire autorisé.") from error
        if not source_path.is_file():
            raise FileNotFoundError("Le moteur n'a pas produit d'image.")
        with Image.open(source_path) as image:
            image.verify()
        final_path = resolve_generated_file_path(Path(filename).name)
        artifact_id = hashlib.sha256(
            "{}:{}:{}".format(time.time_ns(), filename, id(bubble)).encode("utf-8")
        ).hexdigest()[:16]
        artifact = {
            "id": artifact_id,
            "kind": "image",
            "filename": final_path.name,
            "path": source_path,
            "content": "",
            "prompt": prompt,
            "request": request,
            "bubble": bubble,
            "accepted": False,
            "busy": False,
        }
        self._pending_generated_artifacts[artifact_id] = artifact
        self._display_generated_artifact(artifact)

    def _afficher_sortie_moteur(self, detail):
        """Affiche une fenetre dediee avec la sortie brute de sd-cli.exe."""
        win = ctk.CTkToplevel(self)
        win.title("Sortie du moteur FLUX (sd-cli.exe)")
        win.geometry("700x400")
        win.configure(fg_color=BG_APP)
        win.transient(self)
        win.grab_set()

        ctk.CTkLabel(
            win,
            text="Sortie brute du moteur (dernieres lignes) :",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=TEXT_MAIN,
        ).pack(anchor="w", padx=16, pady=(14, 6))

        text = ctk.CTkTextbox(win, font=ctk.CTkFont(family="Consolas", size=11), fg_color="#1a1a1a", text_color="#00ff00")
        text.pack(fill="both", expand=True, padx=16, pady=(0, 10))
        text.insert("1.0", detail)
        text.configure(state="disabled")

        ctk.CTkButton(
            win,
            text="Fermer",
            width=90,
            command=win.destroy,
            fg_color="#263547",
            hover_color="#34475c",
        ).pack(anchor="e", padx=16, pady=(0, 14))

        win.update_idletasks()
        x = (win.winfo_screenwidth() - win.winfo_width()) // 2
        y = (win.winfo_screenheight() - win.winfo_height()) // 2
        win.geometry("{}x{}+{}+{}".format(win.winfo_width(), win.winfo_height(), x, y))

    def _display_generated_artifact(self, artifact):
        old_card = artifact.get("card")
        if old_card is not None and old_card.winfo_exists():
            old_card.destroy()
        card = ctk.CTkFrame(
            artifact["bubble"],
            fg_color=BG_PANEL,
            corner_radius=12,
            border_width=1,
            border_color="#34475c",
        )
        card.pack(fill="x", padx=12, pady=(4, 12))
        artifact["card"] = card
        title = "Aperçu PDF" if artifact["kind"] == "pdf" else "Aperçu de l’image"
        ctk.CTkLabel(
            card,
            text="{} · {}".format(title, artifact["filename"]),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_MAIN,
            anchor="w",
        ).pack(fill="x", padx=12, pady=(10, 4))

        if artifact["kind"] == "image":
            with Image.open(artifact["path"]) as opened:
                preview = opened.convert("RGB")
                preview.thumbnail((560, 360))
            ctk_image = ctk.CTkImage(
                light_image=preview,
                dark_image=preview,
                size=preview.size,
            )
            preview_label = ctk.CTkLabel(card, text="", image=ctk_image)
            preview_label.image = ctk_image
            preview_label.pack(padx=12, pady=(2, 8))
        else:
            document = pdfium.PdfDocument(str(artifact["path"]))
            try:
                page_count = len(document)
                page = document[0]
                preview = page.render(scale=1.25).to_pil().convert("RGB")
            finally:
                document.close()
            preview.thumbnail((760, 920))
            ctk_image = ctk.CTkImage(
                light_image=preview,
                dark_image=preview,
                size=preview.size,
            )
            preview_label = ctk.CTkLabel(card, text="", image=ctk_image)
            preview_label.image = ctk_image
            preview_label.pack(padx=12, pady=(2, 4))
            ctk.CTkLabel(
                card,
                text="Page 1 sur {} · l’aperçu utilise le PDF réellement généré.".format(
                    page_count
                ),
                font=ctk.CTkFont(size=10),
                text_color=TEXT_MUTED,
            ).pack(anchor="w", padx=14, pady=(0, 8))

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(fill="x", padx=8, pady=(0, 8))
        if artifact["accepted"]:
            ctk.CTkLabel(
                actions,
                text="Validé · enregistré dans ia_creations",
                text_color=ACCENT,
                font=ctk.CTkFont(size=11, weight="bold"),
            ).pack(side="left", padx=6)
        elif artifact["busy"]:
            ctk.CTkLabel(
                actions,
                text="Nouvelle version en cours…",
                text_color="#eab308",
                font=ctk.CTkFont(size=11),
            ).pack(side="left", padx=6)
        else:
            ctk.CTkButton(
                actions,
                text="Valider",
                width=78,
                command=lambda item=artifact["id"]: self._accept_generated_artifact(item),
                fg_color=ACCENT,
                hover_color=ACCENT_HOVER,
            ).pack(side="left", padx=4)
            ctk.CTkButton(
                actions,
                text="Recommencer",
                width=104,
                command=lambda item=artifact["id"]: self._regenerate_artifact(item),
                fg_color="#34475c",
                hover_color="#465d75",
            ).pack(side="left", padx=4)
            ctk.CTkButton(
                actions,
                text="Refuser",
                width=76,
                command=lambda item=artifact["id"]: self._reject_generated_artifact(item),
                fg_color="#7f1d1d",
                hover_color="#991b1b",
            ).pack(side="left", padx=4)
        ctk.CTkButton(
            actions,
            text="Télécharger",
            width=100,
            command=lambda path=artifact["path"]: self.download_generated_file(path),
            fg_color="#263547",
            hover_color="#34475c",
        ).pack(side="right", padx=4)

    def _accept_generated_artifact(self, artifact_id):
        artifact = self._pending_generated_artifacts.get(artifact_id)
        if not artifact or artifact["accepted"]:
            return
        try:
            target = resolve_generated_file_path(artifact["filename"])
            if target.exists() and not messagebox.askyesno(
                "Remplacer le fichier ?",
                "Le fichier existe déjà :\n{}\n\nLe remplacer ?".format(target),
            ):
                return
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(str(artifact["path"]), str(target))
            artifact["path"] = target
            artifact["accepted"] = True
            self._display_generated_artifact(artifact)
            self.status_var.set("Fichier validé : {}".format(target.name))
        except (OSError, ValueError, RuntimeError) as error:
            messagebox.showerror("Validation impossible", str(error))

    def _reject_generated_artifact(self, artifact_id):
        artifact = self._pending_generated_artifacts.pop(artifact_id, None)
        if not artifact or artifact["accepted"]:
            return
        try:
            artifact["path"].unlink(missing_ok=True)
        except OSError as error:
            messagebox.showerror("Refus impossible", str(error))
            self._pending_generated_artifacts[artifact_id] = artifact
            return
        card = artifact.get("card")
        if card is not None and card.winfo_exists():
            card.destroy()
        self.status_var.set("Fichier refusé")

    def _regenerate_artifact(self, artifact_id):
        artifact = self._pending_generated_artifacts.get(artifact_id)
        if not artifact or artifact["accepted"] or artifact["busy"]:
            return
        artifact["busy"] = True
        self._display_generated_artifact(artifact)
        if artifact["kind"] == "image":
            self._start_image_generation(
                artifact["prompt"],
                artifact["bubble"],
                artifact["request"],
                filename=artifact["filename"],
                artifact_id=artifact_id,
            )
            self._finish()
            return
        threading.Thread(
            target=self._regenerate_pdf_worker,
            args=(artifact_id, artifact),
            daemon=True,
        ).start()

    def _regenerate_pdf_worker(self, artifact_id, artifact):
        request = artifact.get("request") or {}
        messages = [
            {
                "role": "system",
                "content": (
                    "Tu rédiges le document demandé en français. Retourne le document complet "
                    "entre [CREER_FICHIER: nom.pdf] et [/CREER_FICHIER], avec son titre, ses sections "
                    "et leur contenu. N'ajoute aucun texte de conversation dans le document."
                ),
            }
        ] + [dict(item) for item in request.get("history", [])]
        messages.extend(
            [
                {"role": "assistant", "content": artifact["content"][:12000]},
                {
                    "role": "user",
                    "content": "Recommence la rédaction avec une nouvelle version complète du document.",
                },
            ]
        )
        try:
            result = ollama.chat(
                model=request.get("model") or MODEL,
                messages=messages,
                stream=False,
                options={"temperature": 0.35, "num_ctx": 8192, "num_predict": 6144},
            )
            response = result.get("message", {}).get("content", "")
            document = _extract_pdf_document_text(response)
            if not _is_complete_pdf_document(document):
                raise ValueError("La nouvelle réponse ne contient pas un document complet.")
            self.ui_queue.put(("artifact_regenerated", artifact_id, document))
        except Exception as error:
            self.ui_queue.put(("artifact_regeneration_error", artifact_id, str(error)))

    def _start_image_generation(
        self,
        prompt,
        bubble,
        request,
        filename,
        artifact_id=None,
    ):
        if image_generation is None or not image_generation.is_ready():
            self.ui_queue.put(
                (
                    "image_generation_error",
                    bubble,
                    "Le générateur FLUX n'est pas installé. Ouvre Réglages pour le configurer.",
                    prompt,
                    request,
                    filename,
                    artifact_id,
                )
            )
            return
        if self._image_generation_active:
            self.ui_queue.put(
                (
                    "image_generation_error",
                    bubble,
                    "Une autre image est déjà en cours de génération.",
                    prompt,
                    request,
                    filename,
                    artifact_id,
                )
            )
            return
        try:
            staging_dir = IA_CREATIONS_DIR / ".pending"
            staging_dir.mkdir(parents=True, exist_ok=True)
            output_path = staging_dir / _nom_fichier_image(prompt, staging_dir)
        except OSError as error:
            self.ui_queue.put(
                (
                    "image_generation_error",
                    bubble,
                    str(error),
                    prompt,
                    request,
                    filename,
                    artifact_id,
                )
            )
            return
        self._image_generation_active = True
        self._image_progress_value = 0
        self._image_progress_job = None
        try:
            self._image_progress_frame = ctk.CTkFrame(bubble, fg_color="transparent")
            self._image_progress_frame.pack(padx=16, pady=(0, 8), fill="x")
            self._image_progress_label = ctk.CTkLabel(
                self._image_progress_frame,
                text="Génération de l'image…",
                font=ctk.CTkFont(size=12),
                text_color="#eab308",
            )
            self._image_progress_label.pack(anchor="w")
            self._image_progress_bar = ctk.CTkProgressBar(
                self._image_progress_frame, width=220, height=16
            )
            self._image_progress_bar.pack(fill="x", padx=2, pady=(4, 0))
            self._image_progress_bar.set(0)
            self._image_progress_pct = ctk.CTkLabel(
                self._image_progress_frame,
                text="0%",
                font=ctk.CTkFont(size=11),
                text_color=TEXT_MUTED,
            )
            self._image_progress_pct.pack(anchor="e")
            self._animate_image_progress()
        except Exception:
            self._image_progress_frame = None
            self._image_progress_bar = None
            self._image_progress_label = None
            self._image_progress_pct = None

        def worker():
            try:
                # Libère la mémoire vidéo occupée par Ollama avant FLUX
                try:
                    ollama.generate(
                        model=(request or {}).get("model") or MODEL,
                        prompt="",
                        keep_alive=0,
                    )
                    time.sleep(2)
                except Exception:
                    pass
                init_path = None
                source = (request or {}).get("image_edit_source")
                if source:
                    init_path = self._prepare_init_image(source, output_path)
                try:
                    result = image_generation.generate(
                        prompt, output_path, init_image=init_path, strength=0.6
                    )
                finally:
                    if init_path is not None:
                        Path(init_path).unlink(missing_ok=True)
                self.ui_queue.put(
                    (
                        "image_generated",
                        bubble,
                        prompt,
                        str(result),
                        request,
                        filename,
                        artifact_id,
                    )
                )
            except Exception as error:
                output_path.unlink(missing_ok=True)
                self.ui_queue.put(
                    (
                        "image_generation_error",
                        bubble,
                        str(error),
                        prompt,
                        request,
                        filename,
                        artifact_id,
                    )
                )
            finally:
                self._image_generation_active = False
                if getattr(self, "_image_loading_label", None) is not None:
                    try:
                        self._image_loading_label.destroy()
                    except Exception:
                        pass
                    self._image_loading_label = None

        threading.Thread(target=worker, daemon=True).start()

    def _animate_image_progress(self):
        if not self._image_generation_active:
            return
        if self._image_progress_value < 80:
            self._image_progress_value += 5
            delay = 700
        elif self._image_progress_value < 98:
            self._image_progress_value += 1
            delay = 2000
        else:
            delay = 2000
        try:
            if self._image_progress_bar is not None:
                self._image_progress_bar.set(self._image_progress_value / 100)
            if self._image_progress_pct is not None:
                self._image_progress_pct.configure(text="{}%".format(self._image_progress_value))
        except Exception:
            pass
        self._image_progress_job = self.after(delay, self._animate_image_progress)

    def _finish_image_progress(self):
        self._image_generation_active = False
        try:
            if self._image_progress_job is not None:
                try:
                    self.after_cancel(self._image_progress_job)
                except Exception:
                    pass
                self._image_progress_job = None
            if self._image_progress_bar is not None:
                self._image_progress_bar.set(1.0)
            if self._image_progress_pct is not None:
                self._image_progress_pct.configure(text="100%")
        except Exception:
            pass
        if self._image_progress_frame is not None:
            try:
                self._image_progress_frame.destroy()
            except Exception:
                pass
            self._image_progress_frame = None
            self._image_progress_bar = None
            self._image_progress_label = None
            self._image_progress_pct = None

    def _handle_artifact_event(self, event):
        kind = event[0]
        if kind == "image_generated":
            self._image_generation_active = False
            self._finish_image_progress()
            _, bubble, prompt, path, request, filename, artifact_id = event
            try:
                if artifact_id:
                    artifact = self._pending_generated_artifacts.get(artifact_id)
                    if not artifact:
                        Path(path).unlink(missing_ok=True)
                        return
                    old_path = artifact["path"]
                    artifact["path"] = Path(path)
                    artifact["busy"] = False
                    old_path.unlink(missing_ok=True)
                    self._display_generated_artifact(artifact)
                else:
                    self._stage_image_artifact(filename, path, prompt, bubble, request)
            except (OSError, ValueError, RuntimeError) as error:
                try:
                    Path(path).unlink(missing_ok=True)
                except OSError as cleanup_error:
                    print("Impossible de supprimer l'image invalide:", cleanup_error)
                messagebox.showerror("Aperçu de l’image impossible", str(error))
        elif kind == "image_generation_error":
            self._image_generation_active = False
            self._finish_image_progress()
            _, bubble, detail, prompt, request, filename, artifact_id = event
            if artifact_id and artifact_id in self._pending_generated_artifacts:
                artifact = self._pending_generated_artifacts[artifact_id]
                artifact["busy"] = False
                self._display_generated_artifact(artifact)
            if bubble is not None and bubble.winfo_exists():
                self._add_bubble(
                    "Calisto",
                    "La génération de l’image a échoué.",
                    "assistant",
                    animate=False,
                )
                btns = ctk.CTkFrame(bubble, fg_color="transparent")
                btns.pack(anchor="e", padx=14, pady=(0, 6))
                ctk.CTkButton(
                    btns,
                    text="Voir les details",
                    width=110,
                    command=lambda d=detail: self._afficher_sortie_moteur(d),
                    fg_color="#263547",
                    hover_color="#34475c",
                    font=ctk.CTkFont(size=10),
                ).pack(side="left", padx=4)
            self.status_var.set("Génération d’image impossible")
        elif kind == "artifact_regenerated":
            _, artifact_id, content = event
            artifact = self._pending_generated_artifacts.get(artifact_id)
            if not artifact or artifact["accepted"]:
                return
            try:
                write_markdown_pdf(artifact["path"], content)
                artifact["content"] = content
                artifact["busy"] = False
                self._display_generated_artifact(artifact)
            except (OSError, ValueError, RuntimeError) as error:
                artifact["busy"] = False
                self._display_generated_artifact(artifact)
                messagebox.showerror("Nouvelle version impossible", str(error))
        else:
            _, artifact_id, detail = event
            artifact = self._pending_generated_artifacts.get(artifact_id)
            if artifact:
                artifact["busy"] = False
                self._display_generated_artifact(artifact)
            messagebox.showerror("Nouvelle version impossible", detail)

    def download_generated_file(self, filepath):
        try:
            source = Path(filepath).resolve()
            root = IA_CREATIONS_DIR.resolve()
            source.relative_to(root)
            if not source.is_file():
                raise FileNotFoundError("Le fichier généré n'existe plus.")
            destination = filedialog.asksaveasfilename(
                title="Télécharger le fichier",
                initialfile=source.name,
                defaultextension=source.suffix,
                filetypes=[
                    ("Image PNG", "*.png"),
                    ("Document PDF", "*.pdf"),
                    ("Tous les fichiers", "*.*"),
                ],
            )
            if not destination:
                return
            target = Path(destination).resolve()
            if target == source:
                self.status_var.set("Le PDF est déjà enregistré à cet emplacement.")
                return
            shutil.copy2(str(source), str(target))
            self.status_var.set("PDF téléchargé : {}".format(target))
        except (OSError, ValueError, RuntimeError) as error:
            messagebox.showerror("Téléchargement impossible", str(error))

    def _create_code_project(self, nom_projet):
        """Cree un dossier de projet de code dans ia_creations/projets/ et l'ouvre dans l'editeur."""
        if not nom_projet:
            nom_projet = "mon_projet"
        nom_projet = nom_projet.strip()
        nom_projet = re.sub(r'[<>:"/\\|?*]', "_", nom_projet)
        if not nom_projet:
            nom_projet = "mon_projet"

        CODE_PROJECT_DIR.mkdir(parents=True, exist_ok=True)
        target = CODE_PROJECT_DIR / nom_projet

        if target.exists():
            if not messagebox.askyesno(
                "Dossier existant",
                "Le dossier '{}' existe deja.\nVoulez-vous l'utiliser pour ce projet ?".format(nom_projet),
            ):
                self.status_var.set("Projet annule")
                return None
        else:
            if not messagebox.askyesno(
                "Creer le dossier",
                "L'IA propose de creer le dossier de projet :\n{}\n\nAutoriser ?".format(target),
            ):
                self.status_var.set("Projet annule")
                return None

        try:
            target.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            messagebox.showerror("Erreur", "Impossible de creer le dossier : {}".format(error))
            return None

        self._current_project_dir = target
        if self.dev_window is not None and self.dev_window.winfo_exists():
            try:
                self.dev_window.open_folder(str(target))
            except Exception:
                pass
        try:
            self.tabs.set("Editeur de code")
        except Exception:
            pass
        self.status_var.set("Projet ouvert : {}".format(target.name))
        return target

    def handle_ai_creation_request(self, command_type, filepath, content, binary=False):
        if command_type == "fichier":
            try:
                output_dir = self._current_project_dir if self._current_project_dir else None
                # Si un projet est ouvert, on n'utilise que le nom du fichier (sans sous-dossiers)
                # pour eviter que l'IA cree des dossiers imbriques comme PortfolioCalisto/index.html
                clean_name = Path(filepath).name
                target_path = resolve_generated_file_path(clean_name, output_dir=output_dir)
            except ValueError as error:
                messagebox.showerror("Nom de fichier invalide", str(error))
                return
        else:
            target_path = Path(filepath)

        if command_type == "app" and not self.ai_can_modify_app.get():
            title = "Autorisation IA"
            prompt = "L'IA propose de modifier le fichier de l'application :\n{}\n\nAutoriser ?".format(filepath)
        elif command_type == "fichier" and not self.ai_can_create_files.get():
            title = "Autorisation IA"
            prompt = "L'IA propose de creer le fichier local :\n{}\n\nAutoriser ?".format(target_path)
        else:
            title = "Confirmer"
            action = "modifier l'application" if command_type == "app" else "creer"
            prompt = "L'IA propose de {} le fichier :\n{}\n\nConfirmer ?".format(action, target_path)
        if not messagebox.askyesno(title, prompt):
            self.status_var.set("Action annulee")
            return

        if target_path.exists() and not messagebox.askyesno(
            "Remplacer le fichier ?",
            "Le fichier existe deja :\n{}\n\nLe remplacer ?".format(target_path),
        ):
            self.status_var.set("Remplacement refuse")
            return

        try:
            if binary:
                if command_type != "fichier":
                    raise ValueError("Le mode Base64 est reserve aux fichiers generes.")
                content_bytes = decode_generated_binary(content)
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_bytes(content_bytes)
            elif str(filepath).lower().endswith(".pdf") and command_type == "fichier":
                if len(str(content).encode("utf-8")) > MAX_GENERATED_FILE_BYTES:
                    raise ValueError("Le contenu depasse la limite de 5 Mo.")
                write_markdown_pdf(target_path, content)
            else:
                if command_type == "fichier" and target_path.suffix.lower() in BINARY_FILE_EXTENSIONS:
                    raise ValueError(
                        "Ce format est binaire. Demandez une sortie Base64 ou choisissez un format texte comme SVG."
                    )
                content_bytes = str(content).encode("utf-8")
                if len(content_bytes) > MAX_GENERATED_FILE_BYTES:
                    raise ValueError("Le contenu depasse la limite de 5 Mo.")
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_bytes(content_bytes)
            action = "modifie" if command_type == "app" else "cree"
            if command_type != "fichier" or target_path.suffix.lower() != ".pdf":
                messagebox.showinfo(
                    "Fichier genere",
                    "Fichier {} avec succes :\n{}".format(action, target_path),
                )
            self.status_var.set("Fichier {} : {}".format(action, target_path.name))
            # Rafraichir l'arbre de l'editeur si le fichier est dans le projet ouvert
            if (
                self.dev_window is not None
                and self.dev_window.winfo_exists()
                and self._current_project_dir is not None
            ):
                try:
                    target_path.resolve().relative_to(self._current_project_dir.resolve())
                    self.dev_window.refresh_tree()
                except ValueError:
                    pass
            return target_path
        except (OSError, ValueError, binascii.Error) as error:
            messagebox.showerror("Erreur de creation", "Impossible de creer le fichier : {}".format(error))
        except Exception as e:
            messagebox.showerror("Erreur de creation", "Impossible de creer le fichier : {}".format(str(e)))
        return None

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

    def open_ai_creations_folder(self):
        IA_CREATIONS_DIR.mkdir(parents=True, exist_ok=True)
        try:
            if os.name == "nt":
                os.startfile(str(IA_CREATIONS_DIR))
            else:
                webbrowser.open(IA_CREATIONS_DIR.as_uri())
        except OSError as error:
            messagebox.showerror("Ouverture impossible", str(error))

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
        """Etat du moteur IA, rafraichi toutes les 30 secondes."""
        if ai_runtime is not None and ai_runtime.is_running():
            self.status_var.set("IA en ligne")
        else:
            self.status_var.set("IA indisponible")
        self.after(30000, self._check_ollama)

    def _start_ai(self):
        """Demarre le moteur IA en arriere-plan au lancement de l'application."""
        if ai_runtime is None:
            return

        def worker():
            disponible, message = ai_runtime.ensure_server()
            self.ui_queue.put(("ai_ready", disponible, message))

        threading.Thread(target=worker, daemon=True).start()

    def _on_ai_ready(self, disponible, message):
        self.status_var.set(message)
        if not disponible:
            messagebox.showwarning(
                "Moteur IA indisponible",
                "L'IA n'a pas pu demarrer.\n\n"
                "Installez Ollama depuis {} puis relancez Calisto.".format(
                    ai_runtime.DOWNLOAD_URL if ai_runtime else "https://ollama.com/download"
                ),
            )
            return
        modele = self.model_var.get() or MODEL
        if not ai_runtime.has_model(modele):
            if messagebox.askyesno(
                "Modele manquant",
                "Le modele '{}' n'est pas encore installe.\n\nLe telecharger maintenant ?".format(modele),
            ):
                self.status_var.set("Telechargement du modele...")
                threading.Thread(target=self._download_model, args=(modele,), daemon=True).start()

    def _download_model(self, modele):
        ok = ai_runtime.pull_model(modele)
        self.ui_queue.put(("ai_status", "IA prete" if ok else "Telechargement du modele impossible"))

    def configure_image_generator(self):
        if image_generation is None:
            messagebox.showerror(
                "Générateur indisponible",
                "Le module du générateur FLUX n'a pas pu être chargé.",
            )
            return
        if self._image_generation_busy:
            return
        if image_generation.is_ready():
            if self._image_setup_label and self._image_setup_label.winfo_exists():
                self._image_setup_label.configure(
                    text="FLUX.1-schnell est prêt.",
                    text_color=ACCENT,
                )
            messagebox.showinfo(
                "FLUX.1-schnell",
                "Le moteur local et les modèles sont déjà installés.",
            )
            return

        model_gb = 9.6
        try:
            free_gb = shutil.disk_usage(
                image_generation.data_dir().parent.parent
            ).free / (1024 ** 3)
        except OSError:
            free_gb = None
        if free_gb is not None and free_gb < model_gb:
            messagebox.showerror(
                "Espace disque insuffisant",
                "FLUX.1-schnell nécessite environ 10 Go libres. "
                "Il ne reste que {:.1f} Go sur le disque cible.".format(free_gb),
            )
            return

        consent = messagebox.askyesno(
            "Installer le générateur local",
            "Calisto va télécharger le moteur C++ et environ 9,6 Go de poids FLUX.1-schnell "
            "(version q2, adaptée aux GPU avec peu de mémoire).\n\n"
            "Le modèle est sous licence Apache 2.0, mais son dépôt officiel exige d'accepter "
            "ses conditions Hugging Face. Le jeton d'accès Read ne sera utilisé que pendant "
            "le téléchargement du VAE et ne sera pas enregistré.\n\n"
            "Continuer vers la page officielle du modèle ?",
        )
        if not consent:
            return
        token = None
        vae_path = image_generation.model_dir() / "ae.safetensors"
        if not vae_path.is_file():
            webbrowser.open(image_generation.MODEL_CARD_URL)
            token = simpledialog.askstring(
                "Accès au modèle FLUX",
                "Après avoir accepté les conditions sur Hugging Face, collez un jeton d'accès "
                "personnel en lecture seule.\n\nLe jeton reste en mémoire pendant l'installation "
                "et n'est pas enregistré.",
                show="*",
                parent=self,
            )
            if not token:
                return
        self._image_generation_busy = True
        if self._image_setup_label and self._image_setup_label.winfo_exists():
            self._image_setup_label.configure(
                text="Installation en cours : le téléchargement peut durer longtemps.",
                text_color="#eab308",
            )
        threading.Thread(
            target=self._image_generator_install_worker,
            args=(token,),
            daemon=True,
        ).start()

    def _image_generator_install_worker(self, token):
        try:
            image_generation.install(
                token=token,
                on_progress=lambda name, received, total: self.ui_queue.put(
                    ("image_setup_progress", name, received, total)
                ),
            )
            self.ui_queue.put(("image_setup_done",))
        except Exception as error:
            self.ui_queue.put(("image_setup_error", str(error)))
        finally:
            token = None

    # ---------- Settings ----------
    def open_settings(self):
        win = ctk.CTkToplevel(self)
        win.title("Reglages")
        win.geometry("700x850")
        win.configure(fg_color=BG_APP)
        win.transient(self)
        win.grab_set()
        win.resizable(True, True)

        ctk.CTkLabel(win, text="⚙️ Reglages", font=ctk.CTkFont(size=22, weight="bold"), text_color=TEXT_MAIN).pack(pady=(20, 15))

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

        section("Modele IA")
        row("Modele Ollama :", ctk.CTkEntry(body, textvariable=self.model_var, width=180, height=32, fg_color=BG_INPUT, border_color="#4b4c54", text_color=TEXT_MAIN))
        row("Temperature :", ctk.CTkSlider(body, from_=0.0, to=1.5, variable=self.temp_var, width=200))
        ctk.CTkLabel(body, textvariable=self.temp_var, font=ctk.CTkFont(size=12), text_color=TEXT_MUTED).grid(row=row_idx[0], column=1, sticky="e", pady=(0, 8))
        row_idx[0] += 1

        section("Personnalite de l'IA")
        ctk.CTkLabel(body, text="Instruction systeme (comment l'IA se comporte) :", font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_MAIN).grid(row=row_idx[0], column=0, columnspan=2, sticky="w", pady=(0, 5))
        row_idx[0] += 1
        sys_txt = ctk.CTkTextbox(body, height=120, font=ctk.CTkFont(size=12), fg_color=BG_INPUT, border_color="#4b4c54", text_color=TEXT_MAIN, corner_radius=8)
        sys_txt.grid(row=row_idx[0], column=0, columnspan=2, sticky="ew", pady=(0, 15))
        row_idx[0] += 1
        sys_txt.insert("1.0", self.sys_text_var.get())

        section("Options")
        for sw in [
            ctk.CTkSwitch(body, text="Autoriser la recherche web", variable=self.web_search_var, font=ctk.CTkFont(size=13), text_color=TEXT_MAIN),
            ctk.CTkSwitch(body, text="Suggestions de code IA en direct (editeur)", variable=self.inline_completion_var, font=ctk.CTkFont(size=13), text_color=TEXT_MAIN),
            ctk.CTkSwitch(body, text="Autoriser l'IA a creer des fichiers", variable=self.ai_can_create_files, font=ctk.CTkFont(size=13), text_color=TEXT_MAIN),
            ctk.CTkSwitch(body, text="Autoriser l'IA a modifier l'application", variable=self.ai_can_modify_app, font=ctk.CTkFont(size=13), text_color=TEXT_MAIN),
        ]:
            sw.grid(row=row_idx[0], column=0, columnspan=2, sticky="w", pady=5)
            row_idx[0] += 1

        section("Générateur d'images local")
        image_ready = bool(image_generation and image_generation.is_ready())
        self._image_setup_label = ctk.CTkLabel(
            body,
            text=(
                "FLUX.1-schnell est prêt."
                if image_ready
                else "Moteur non installé · téléchargement d'environ 10 Go."
            ),
            font=ctk.CTkFont(size=11),
            text_color=ACCENT if image_ready else TEXT_MUTED,
            wraplength=420,
            justify="left",
        )
        self._image_setup_label.grid(
            row=row_idx[0], column=0, columnspan=2, sticky="w", pady=(2, 8)
        )
        row_idx[0] += 1
        ctk.CTkButton(
            body,
            text="Installer / vérifier FLUX.1-schnell",
            command=self.configure_image_generator,
            fg_color="#263547",
            hover_color="#34475c",
            font=ctk.CTkFont(size=12),
        ).grid(row=row_idx[0], column=0, columnspan=2, sticky="w", pady=(0, 8))
        row_idx[0] += 1
        ctk.CTkLabel(
            body,
            text="Moteur C++ stable-diffusion.cpp (Vulkan) · images générées localement.",
            font=ctk.CTkFont(size=10),
            text_color=TEXT_MUTED,
            wraplength=420,
            justify="left",
        ).grid(row=row_idx[0], column=0, columnspan=2, sticky="w", pady=(0, 10))
        row_idx[0] += 1

        section("Aide / Raccourcis")
        help_txt = (
            "Raccourcis editeur :\n"
            "  Ctrl+S : Sauvegarder   Ctrl+F : Rechercher   Ctrl+H : Remplacer\n"
            "  Ctrl+G : Aller a la ligne   Ctrl+/ : Commenter/Decommenter\n"
            "  Ctrl+D : Selectionner occurrence suivante   Ctrl+L : Selectionner ligne\n"
            "  Ctrl+Shift+K : Supprimer ligne   Ctrl+Entree : Ligne en dessous\n"
            "  Ctrl+Shift+Entree : Ligne au-dessus   Alt+↑/↓ : Deplacer ligne\n"
            "  Ctrl+] / Ctrl+[ : Indenter / Desindenter   Ctrl+Z/Y : Annuler/Refaire\n"
            "  Ctrl+Molette : Zoom   Ctrl+A : Tout selectionner\n"
            "  Auto-fermeture : ( ) [ ] { } \" \" ' '\n\n"
            "Chat IA :\n"

            "  Reponse directe, sans recherche web inutile.\n"

            "  La recherche web ne se declenche que si vous la demandez.\n"

            "  Creation : fichiers texte/source de tout type, PDF texte et petits binaires Base64 (5 Mo max).\n"
            "  Les PDF créés dans le chat ont un bouton Télécharger dans leur réponse.\n"

            "  Les fichiers vont dans ia_creations; ils ne sont jamais executes automatiquement.\n"

            "  Personnalisez la personnalite dans l'instruction systeme."

        )
        ctk.CTkLabel(body, text=help_txt, font=ctk.CTkFont(size=11), text_color=TEXT_MUTED, justify="left").grid(row=row_idx[0], column=0, columnspan=2, sticky="w", pady=(0, 15))
        row_idx[0] += 1

        def save_close():
            self.sys_text_var.set(sys_txt.get("1.0", "end").strip())
            self.status_var.set("Reglages enregistres")
            win.destroy()

        btns = ctk.CTkFrame(win, fg_color="transparent")
        btns.pack(fill="x", padx=30, pady=20)
        ctk.CTkButton(btns, text="Annuler", width=100, command=win.destroy, fg_color=BG_INPUT, hover_color="#4b4c54", font=ctk.CTkFont(size=12)).pack(side="right", padx=10)
        ctk.CTkButton(btns, text="Enregistrer", width=100, command=save_close, fg_color=ACCENT, hover_color=ACCENT_HOVER, font=ctk.CTkFont(size=13, weight="bold")).pack(side="right")

    # ---------- Learning mode ----------
    def build_library_tab(self):
        for w in self.library_tab.winfo_children():
            w.destroy()

        self.library_tab.grid_columnconfigure(0, weight=1)
        self.library_tab.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self.library_tab, fg_color=BG_PANEL, corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 8))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header,
            text="Bibliotheque",
            font=ctk.CTkFont(size=19, weight="bold"),
            text_color=TEXT_MAIN,
        ).grid(row=0, column=0, sticky="w", padx=18, pady=10)

        btns = ctk.CTkFrame(header, fg_color="transparent")
        btns.grid(row=0, column=2, sticky="e", padx=18, pady=6)
        ctk.CTkButton(
            btns,
            text="Actualiser",
            width=90,
            command=self.build_library_tab,
            fg_color="#263547",
            hover_color="#34475c",
            font=ctk.CTkFont(size=11),
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            btns,
            text="Ouvrir le dossier",
            width=110,
            command=self.open_ai_creations_folder,
            fg_color="#263547",
            hover_color="#34475c",
            font=ctk.CTkFont(size=11),
        ).pack(side="left", padx=4)

        body = ctk.CTkScrollableFrame(self.library_tab, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 8))
        body.grid_columnconfigure(0, weight=1)

        IA_CREATIONS_DIR.mkdir(parents=True, exist_ok=True)
        tous = sorted(
            [p for p in IA_CREATIONS_DIR.iterdir() if p.is_file() and not p.name.startswith(".")],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
        DOC_EXTS = {".pdf", ".md", ".txt", ".html", ".css", ".js", ".py", ".json", ".csv"}

        images = [p for p in tous if p.suffix.lower() in IMG_EXTS]
        documents = [p for p in tous if p.suffix.lower() in DOC_EXTS]

        def section(title, files, kind):
            ctk.CTkLabel(
                body,
                text=title,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=ACCENT,
            ).pack(anchor="w", padx=10, pady=(14, 6))
            if not files:
                ctk.CTkLabel(
                    body,
                    text="Aucun fichier pour le moment.",
                    font=ctk.CTkFont(size=12),
                    text_color=TEXT_MUTED,
                ).pack(anchor="w", padx=10, pady=4)
                return
            for p in files:
                row = ctk.CTkFrame(body, fg_color=BG_PANEL, corner_radius=10)
                row.pack(fill="x", padx=8, pady=4)
                row.grid_columnconfigure(1, weight=1)

                try:
                    taille = p.stat().st_size
                    if taille < 1024:
                        taille_txt = "{} o".format(taille)
                    elif taille < 1024 * 1024:
                        taille_txt = "{:.1f} Ko".format(taille / 1024)
                    else:
                        taille_txt = "{:.1f} Mo".format(taille / (1024 * 1024))
                except Exception:
                    taille_txt = ""

                if kind == "image":
                    try:
                        with Image.open(p) as im:
                            im.thumbnail((64, 64))
                            photo = ImageTk.PhotoImage(im)
                        img_lbl = ctk.CTkLabel(row, image=photo, text="")
                        img_lbl.image = photo
                        img_lbl.grid(row=0, column=0, padx=10, pady=8)
                    except Exception:
                        ctk.CTkLabel(row, text="[img]", width=30).grid(row=0, column=0, padx=10, pady=8)
                elif kind == "document" and p.suffix.lower() == ".pdf":
                    try:
                        thumb = self._render_pdf_thumbnail(p)
                        if thumb is not None:
                            img_lbl = ctk.CTkLabel(row, image=thumb, text="")
                            img_lbl.image = thumb
                            img_lbl.grid(row=0, column=0, padx=10, pady=8)
                        else:
                            ctk.CTkLabel(row, text="[pdf]", width=30).grid(row=0, column=0, padx=10, pady=8)
                    except Exception:
                        ctk.CTkLabel(row, text="[pdf]", width=30).grid(row=0, column=0, padx=10, pady=8)
                else:
                    ctk.CTkLabel(row, text="[doc]", width=30).grid(row=0, column=0, padx=10, pady=8)

                info = ctk.CTkFrame(row, fg_color="transparent")
                info.grid(row=0, column=1, sticky="ew", padx=8, pady=8)
                info.grid_columnconfigure(0, weight=1)
                ctk.CTkLabel(
                    info,
                    text=p.name,
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color=TEXT_MAIN,
                    anchor="w",
                ).grid(row=0, column=0, sticky="ew")
                ctk.CTkLabel(
                    info,
                    text=taille_txt,
                    font=ctk.CTkFont(size=10),
                    text_color=TEXT_MUTED,
                    anchor="w",
                ).grid(row=1, column=0, sticky="w")

                actions = ctk.CTkFrame(row, fg_color="transparent")
                actions.grid(row=0, column=2, padx=10, pady=8)
                ctk.CTkButton(
                    actions,
                    text="Telecharger",
                    width=86,
                    command=lambda pp=p: self.download_generated_file(pp),
                    fg_color=ACCENT,
                    hover_color=ACCENT_HOVER,
                    font=ctk.CTkFont(size=10),
                ).pack(side="left", padx=3)
                ctk.CTkButton(
                    actions,
                    text="Supprimer",
                    width=86,
                    command=lambda pp=p: self._supprimer_fichier_bibliotheque(pp),
                    fg_color="#7f1d1d",
                    hover_color="#991b1b",
                    font=ctk.CTkFont(size=10),
                ).pack(side="left", padx=3)

        section("Images", images, "image")
        section("Documents", documents, "document")

    def _supprimer_fichier_bibliotheque(self, chemin):
        p = Path(chemin)
        if not p.exists():
            return
        if not messagebox.askyesno(
            "Supprimer le fichier",
            "Supprimer définitivement : {} ?".format(p.name),
        ):
            return
        try:
            p.unlink()
            self.build_library_tab()
            self.status_var.set("Fichier supprime : {}".format(p.name))
        except Exception as error:
            messagebox.showerror("Suppression impossible", str(error))

    def open_learning_mode(self):
        if self.streaming:
            self.status_var.set("Attendez la fin de la reponse avant d'ouvrir le mode Apprentissage.")
            return
        if self.learning_mode_window is not None and self.learning_mode_window.is_active():
            self.tabs.set("Apprentissage")
            return
        self.learning_mode_window = LearningModeWindow(self)
        self.tabs.set("Apprentissage")

    def _show_learning_landing(self):
        for widget in self.learning_tab.winfo_children():
            widget.destroy()
        self.learning_mode_window = None
        learn_frame = ctk.CTkFrame(self.learning_tab, fg_color=BG_PANEL, corner_radius=12)
        learn_frame.grid(row=0, column=0, sticky="nsew", padx=40, pady=40)
        ctk.CTkLabel(
            learn_frame,
            text="Mode Apprentissage",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=TEXT_MAIN,
        ).pack(pady=(35, 12))
        ctk.CTkLabel(
            learn_frame,
            text="Entrainez-vous en HTML, CSS et JavaScript avec des projets adaptes a votre niveau.",
            font=ctk.CTkFont(size=13),
            text_color=TEXT_MUTED,
            justify="center",
            wraplength=520,
        ).pack(pady=8)
        ctk.CTkButton(
            learn_frame,
            text="Lancer un exercice",
            width=220,
            height=42,
            command=self.open_learning_mode,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(pady=(18, 35))


LEARNING_LEVELS = {
    "junior": {"label": "Junior", "max_files": 5, "advice_freq": "beaucoup", "tolerance": "elevee"},
    "facile": {"label": "Facile", "max_files": 4, "advice_freq": "peu", "tolerance": "elevee"},
    "normale": {"label": "Normale", "max_files": 3, "advice_freq": "modere", "tolerance": "moyenne"},
    "difficile": {"label": "Difficile", "max_files": 3, "advice_freq": "minimal", "tolerance": "faible"},
    "legendaire": {"label": "Legendaire", "max_files": 2, "advice_freq": "aucun", "tolerance": "aucune"},
    "senior": {"label": "Senior", "max_files": 4, "advice_freq": "tres peu", "tolerance": "strict"},
}

LEARNING_PROJECT_THEMES = {
    "junior": (
        "une page de presentation pour un petit cafe de quartier",
        "une page pour un refuge animalier",
        "une page d'information pour un parc naturel",
        "une page de presentation pour un artisan local",
        "une page d'annonce pour un festival de musique",
        "une page de presentation pour une librairie independante",
    ),
    "facile": (
        "un menu de restaurant avec filtres par categorie",
        "une galerie de destinations de voyage avec recherche",
        "un quiz interactif de culture generale",
        "une liste de films avec recherche et favoris",
        "un formulaire d'inscription a un evenement avec validation",
        "une liste de taches avec ajout et suppression",
    ),
    "normale": (
        "une boutique de produits locaux avec panier simple",
        "un catalogue de recettes avec recherche et favoris",
        "un site d'agence de voyage avec formulaire de reservation",
        "un blog thematique avec navigation et filtres",
        "un calendrier d'evenements avec inscription",
        "un tableau de bord de suivi d'habitudes",
    ),
    "difficile": (
        "une plateforme de reservation de chambres avec plusieurs pages",
        "une application de gestion de stock avec recherche et filtres",
        "une boutique en ligne avec panier et etapes de commande",
        "une plateforme de cours avec progression par module",
        "un planificateur de voyage avec plusieurs vues",
        "un outil de gestion de projets avec tableau de taches",
    ),
    "legendaire": (
        "une application e-commerce multi-pages avec catalogue et panier",
        "un gestionnaire de bibliotheque avec emprunts et disponibilites",
        "un outil Kanban avec colonnes, priorites et filtres",
        "une plateforme de reservations avec calendrier et gestion des places",
        "un tableau de bord analytique avec graphiques et filtres",
        "un mini-systeme de gestion de contenu avec articles et categories",
    ),
    "senior": (
        "une application de gestion de rendez-vous avec calendrier et espaces utilisateur",
        "un tableau de bord de gestion avec modules, filtres et donnees partagees",
        "une plateforme de commerce avec catalogue, panier et administration",
        "un outil de gestion d'equipe avec projets, taches et suivi d'activite",
        "un systeme de gestion de contenu avec edition, publication et recherche",
        "une plateforme de formation avec parcours, progression et evaluation",
    ),
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
        self._advice_job = None
        self._generation_id = 0
        self._verification_id = 0
        self._advice_generation = 0
        self.files = {}
        self.project_history = []
        self.current_project_theme = ""
        self.max_files = 5
        self.current_file = "index.html"
        self.paused = False
        self.current_subject = ""
        self.exercise_count = 0
        self.started = False
        self.subject_ready = False
        self.active = True
        self.verification_in_progress = False

        self._build_ui()
        self._generate_subject()

    def is_active(self):
        return self.active and bool(self.root_frame.winfo_exists())

    def _build_ui(self):
        self.win.grid_columnconfigure(0, weight=1)
        self.win.grid_rowconfigure(0, weight=1)
        self.root_frame = ctk.CTkFrame(self.win, fg_color="transparent")
        self.root_frame.grid(row=0, column=0, sticky="nsew")
        self.root_frame.grid_columnconfigure(0, weight=1)
        self.root_frame.grid_rowconfigure(3, weight=1)

        header = ctk.CTkFrame(self.root_frame, fg_color=BG_PANEL, height=50, corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        header.pack_propagate(False)

        ctk.CTkLabel(header, text="Mode Apprentissage", font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT_MAIN).pack(side="left", padx=15, pady=10)
        self.exercise_label = ctk.CTkLabel(header, text="Exercice 0", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_MUTED)
        self.exercise_label.pack(side="left", padx=15, pady=10)
        self.level_btn = ctk.CTkOptionMenu(
            header,
            values=[LEARNING_LEVELS[k]["label"] for k in LEARNING_LEVELS],
            command=self._on_level_change,
            width=140,
            fg_color=BG_INPUT,
            button_color=ACCENT,
            button_hover_color=ACCENT_HOVER,
        )
        self.level_btn.set("Junior")
        self.level_btn.pack(side="right", padx=15, pady=10)
        self.generate_btn = ctk.CTkButton(
            header,
            text="Nouveau sujet",
            width=120,
            command=self._request_new_subject,
            fg_color="#263547",
            hover_color="#34475c",
            font=ctk.CTkFont(size=11, weight="bold"),
        )
        self.generate_btn.pack(side="right", padx=4, pady=10)

        self.timer_label = ctk.CTkLabel(self.root_frame, text="00:00:00", font=ctk.CTkFont(size=22, weight="bold"), text_color=ACCENT)
        self.timer_label.grid(row=1, column=0, pady=(0, 10))

        self.progress_frame = ctk.CTkFrame(self.root_frame, fg_color=BG_PANEL, corner_radius=8)
        self.progress_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 8))
        ctk.CTkLabel(self.progress_frame, text="Preparation du sujet", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_MAIN).pack(side="left", padx=(12, 8), pady=8)
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, width=300, height=12, corner_radius=10, fg_color=BG_INPUT, progress_color=ACCENT)
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=8)
        self.progress_bar.set(0)
        self.progress_label = ctk.CTkLabel(self.progress_frame, text="En attente", font=ctk.CTkFont(size=11, weight="bold"), text_color=ACCENT, width=70)
        self.progress_label.pack(side="right", padx=(0, 12), pady=8)

        body = ctk.CTkFrame(self.root_frame, fg_color="transparent")
        body.grid(row=3, column=0, sticky="nsew", padx=10, pady=5)
        body.grid_columnconfigure(0, weight=1, minsize=160)
        body.grid_columnconfigure(1, weight=3, minsize=360)
        body.grid_columnconfigure(2, weight=2, minsize=280)
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
        editor_frame = ctk.CTkFrame(body, fg_color=BG_INPUT, corner_radius=10)
        editor_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        editor_frame.grid_rowconfigure(1, weight=1)
        editor_frame.grid_columnconfigure(0, weight=1)

        self.editor_label = ctk.CTkLabel(editor_frame, text="index.html", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_MUTED)
        self.editor_label.grid(row=0, column=0, sticky="w", padx=10, pady=5)

        self.code_editor = ctk.CTkTextbox(
            editor_frame,
            font=ctk.CTkFont(family="Consolas", size=14),
            fg_color=BG_INPUT,
            text_color=TEXT_MAIN,
            border_width=0,
            wrap="none",
        )
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
        ia_frame.grid_columnconfigure(0, weight=1)
        ia_frame.grid_rowconfigure(1, weight=3)
        ia_frame.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(ia_frame, text="Consignes du projet (IA)", font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_MAIN).grid(row=0, column=0, sticky="w", padx=8, pady=(8, 2))
        self.ia_instructions = ctk.CTkTextbox(ia_frame, font=ctk.CTkFont(size=12), fg_color=BG_INPUT, border_color="#263547", text_color=TEXT_MAIN, wrap="word")
        self.ia_instructions.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.ia_instructions.configure(state="disabled")

        ctk.CTkLabel(ia_frame, text="Conseils IA", font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_MAIN).grid(row=2, column=0, sticky="w", padx=8, pady=(8, 2))
        self.ia_advice = ctk.CTkTextbox(ia_frame, font=ctk.CTkFont(size=11), fg_color=BG_INPUT, border_color="#263547", text_color=TEXT_MAIN, wrap="word")
        self.ia_advice.grid(row=3, column=0, sticky="nsew", padx=5, pady=5)
        self.ia_advice.configure(state="disabled")

        btn_frame = ctk.CTkFrame(self.root_frame, fg_color="transparent")
        btn_frame.grid(row=4, column=0, sticky="ew", padx=10, pady=10)

        self.abandon_btn = ctk.CTkButton(btn_frame, text="Annuler", command=self._abandon, fg_color="#c24141", hover_color="#a33434", font=ctk.CTkFont(size=12, weight="bold"))
        self.abandon_btn.pack(side="left", padx=10)
        self.pause_btn = ctk.CTkButton(btn_frame, text="Pause", command=self._toggle_pause, fg_color="#b45309", hover_color="#d97706", font=ctk.CTkFont(size=12, weight="bold"))
        self.pause_btn.pack(side="left", padx=10)
        self.verify_btn = ctk.CTkButton(btn_frame, text="Verifier le site", command=self._verify, fg_color=ACCENT, hover_color=ACCENT_HOVER, font=ctk.CTkFont(size=12, weight="bold"))
        self.verify_btn.pack(side="right", padx=10)

        self.start_btn = ctk.CTkButton(btn_frame, text="Demarrer l'exercice", command=self._start_exercise, fg_color=ACCENT, hover_color=ACCENT_HOVER, font=ctk.CTkFont(size=12, weight="bold"))
        self.start_btn.pack(side="right", padx=10)
        self.start_btn.configure(state="disabled")
        self.pause_btn.configure(state="disabled")
        self.verify_btn.configure(state="disabled")

        self.status_label = ctk.CTkLabel(self.root_frame, text="", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED, wraplength=900)
        self.status_label.grid(row=5, column=0, sticky="ew", padx=12, pady=(0, 5))

        self.files["index.html"] = "<!DOCTYPE html>\n<html>\n<head>\n    <title>Mon site</title>\n</head>\n<body>\n    <h1>Bonjour</h1>\n</body>\n</html>"
        self._open_file("index.html")
        self.status_label.configure(text="Generation du sujet en cours…", text_color=TEXT_MAIN)
        self._set_level_instructions("junior")

    def _on_level_change(self, value):
        if self.started or self.verification_in_progress:
            self.level_btn.set(LEARNING_LEVELS[self.level.get()]["label"])
            self.status_label.configure(text="Terminez l'exercice avant de changer de niveau.", text_color="#c24141")
            return
        for k, v in LEARNING_LEVELS.items():
            if v["label"] == value:
                self.level.set(k)
                self.max_files = v["max_files"]
                self._set_level_instructions(k)
                self._refresh_files_ui()
                self._generate_subject()
                break

    def _set_text(self, widget, text):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _set_level_instructions(self, key):
        lv = LEARNING_LEVELS[key]
        instr = (
            "Je te prepare un defi de niveau {}. Il apparaitra ici dans un instant.\n\n".format(lv["label"]) +
            "Tu pourras le lire tranquillement, puis demarrer quand tu te sentiras pret. "
            "Le bouton « Verifier le site » te donnera un retour sur ton travail."
        )
        self._set_text(self.ia_instructions, instr)
        self._update_advice(key)

    def _update_advice(self, key):
        if key == "junior":
            advice = "Tu peux commencer simplement : pose la structure de ta page, puis ajoute un titre et un premier paragraphe."
        elif key == "facile":
            advice = "Petit rappel : teste chaque interaction au fur et à mesure et vérifie que ta feuille CSS est bien reliée."
        elif key == "normale":
            advice = "Prends le temps de vérifier que tes styles ciblent les bons éléments et que tes interactions fonctionnent."
        elif key == "difficile":
            advice = "Avant de te lancer, découpe le défi en petites étapes. Ça aide à garder le cap sur un projet plus dense."
        elif key == "legendaire":
            advice = "Un projet ambitieux se construit par étapes : commence par le parcours principal, puis ajoute les détails."
        else:
            advice = "Pense à garder une structure claire : tu gagneras du temps quand le projet prendra de l’ampleur."
        self._set_text(self.ia_advice, advice)

    def _schedule_advice(self):
        if self._advice_job:
            try:
                self.app.after_cancel(self._advice_job)
            except Exception:
                pass
        self._advice_generation += 1
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
        model = self.app.model_var.get() or MODEL
        generation = self._advice_generation
        threading.Thread(
            target=self._advice_thread,
            args=(code, level, model, generation),
            daemon=True,
        ).start()

    def _advice_thread(self, code, level, model, generation):
        try:
            prompt = (
                "Tu es Calisto, un mentor patient qui tutoie l'apprenant. Il code en ce moment au niveau {}. "
                "Voici son code :\n```\n{}\n```\n"
                "Reponds comme dans une conversation : donne une seule piste utile, concrete et encourageante "
                "en une ou deux phrases. Adapte-la au code visible; ne recite pas un conseil generique, "
                "ne commence pas par « Conseil : » et ne donne pas la solution complete. Ecris en francais."
            ).format(level, code[:2000])
            response = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}], options={"temperature": 0.6, "num_predict": 120})
            advice = response["message"]["content"]
            self.app.ui_queue.put(("learning_advice", self, generation, advice))
        except Exception as e:
            self.app.ui_queue.put(("learning_advice_error", self, generation, str(e)))

    def _start_exercise(self):
        if not self.subject_ready:
            self.status_label.configure(text="Attendez que le sujet soit genere.", text_color="#c24141")
            return
        if self.started:
            return
        self.started = True
        self.paused = False
        self.code_editor.configure(state="normal")
        self.abandon_btn.configure(text="Abandonner")
        self.start_btn.configure(state="disabled")
        self.pause_btn.configure(state="normal")
        self.verify_btn.configure(state="normal")
        self.level_btn.configure(state="disabled")
        self.generate_btn.configure(state="disabled")
        self._start_timer()
        self.status_label.configure(text="C’est parti, à toi de jouer !", text_color="#0d8a6a")

    def _start_timer(self):
        self.start_time = time.time()
        self._tick_timer()

    def _tick_timer(self):
        if not self.active or self.start_time is None or self.paused:
            return
        elapsed = int(time.time() - self.start_time)
        h = elapsed // 3600
        m = (elapsed % 3600) // 60
        s = elapsed % 60
        self.timer_label.configure(text="{:02d}:{:02d}:{:02d}".format(h, m, s))
        self.timer_job = self.app.after(1000, self._tick_timer)

    def _stop_timer(self):
        if self.timer_job:
            try:
                self.app.after_cancel(self.timer_job)
            except Exception:
                pass
            self.timer_job = None

    def _on_code_change(self, event=None):
        if not self.paused:
            code = self.code_editor.get("1.0", "end-1c")
            if (
                self.started
                and self.current_file.lower().endswith((".html", ".htm"))
                and code.strip() == "<!>"
                and messagebox.askyesno(
                    "Structure HTML",
                    "Remplacer <!> par une structure HTML de base ?",
                )
            ):
                self.code_editor.delete("1.0", "end")
                self.code_editor.insert("1.0", LEARNING_HTML_BOILERPLATE)
                getattr(self.code_editor, "_textbox", self.code_editor).mark_set("insert", "end-1c")
                code = LEARNING_HTML_BOILERPLATE
                self.status_label.configure(text="Structure HTML de base inseree.", text_color=ACCENT)
            self.files[self.current_file] = code
        # Conseils IA automatiques pour les 2 niveaux les plus bas (junior, facile)
        level = self.level.get()
        if level in ("junior", "facile") and self.started and not self.paused:
            self._schedule_advice()

    def _toggle_pause(self):
        if not self.started or self.verification_in_progress:
            return
        self.paused = not self.paused
        if self.paused:
            self._paused_elapsed = int(time.time() - self.start_time) if self.start_time else 0
            self._stop_timer()
            self.code_editor.configure(state="disabled")
            self.pause_btn.configure(text="Reprendre", fg_color="#15803d", hover_color="#16a34a")
            self.verify_btn.configure(state="disabled")
            self.status_label.configure(text="Pause activée. Reprends quand tu veux.", text_color="#b45309")
        else:
            # Reprendre depuis le temps ecoule avant la pause
            elapsed_before = getattr(self, "_paused_elapsed", 0)
            self.start_time = time.time() - elapsed_before
            self._tick_timer()
            self.code_editor.configure(state="normal")
            self.pause_btn.configure(text="Pause", fg_color="#b45309", hover_color="#d97706")
            self.verify_btn.configure(state="normal")
            self.status_label.configure(text="On reprend ? À toi de jouer !", text_color="#0d8a6a")

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
        dialog = ctk.CTkInputDialog(
            text="Nom du fichier (ex. style.css ou script.js) :",
            title="Nouveau fichier",
        )
        fname = (dialog.get_input() or "").strip()
        if not fname:
            return
        if not re.fullmatch(r"[A-Za-z0-9_-]+\.(?:html?|css|js)", fname, re.IGNORECASE):
            self.status_label.configure(
                text="Nom invalide. Utilisez un nom simple termine par .html, .css ou .js.",
                text_color="#c24141",
            )
            return
        if fname in self.files:
            self.status_label.configure(text="Ce fichier existe deja.", text_color="#c24141")
            return
        self.files[fname] = ""
        self._refresh_files_ui()
        self._open_file(fname)

    def _request_new_subject(self):
        if self.verification_in_progress:
            return
        if self.started and not messagebox.askyesno(
            "Nouveau sujet",
            "L'exercice en cours sera abandonne. Continuer ?",
        ):
            return
        self._stop_timer()
        self.started = False
        self.paused = False
        self.start_time = None
        self.files = {
            "index.html": "<!DOCTYPE html>\n<html>\n<head>\n    <title>Mon site</title>\n</head>\n<body>\n    <h1>Bonjour</h1>\n</body>\n</html>"
        }
        self.current_file = "index.html"
        self._refresh_files_ui()
        self._open_file(self.current_file)
        self.code_editor.configure(state="disabled")
        self.pause_btn.configure(state="disabled", text="Pause")
        self.verify_btn.configure(state="disabled")
        self.level_btn.configure(state="normal")
        self._generate_subject()

    def _abandon(self):
        self.active = False
        self._generation_id += 1
        self._verification_id += 1
        self._stop_timer()
        self._stop_loading()
        if self._advice_job:
            try:
                self.app.after_cancel(self._advice_job)
            except Exception:
                pass
            self._advice_job = None
        self.app._show_learning_landing()

    def _verify(self):
        if not self.started or self.paused or self.verification_in_progress:
            return
        html_content = self.files.get("index.html", "")
        if not html_content.strip():
            self.status_label.configure(text="Je ne vois pas encore de code dans index.html. Ajoute un peu de contenu avant de lancer la vérification.", text_color="#c24141")
            return
        if self._is_default_skeleton(html_content):
            self.status_label.configure(text="La structure de départ est toujours là. Ajoute ton contenu, puis demande une nouvelle vérification.", text_color="#c24141")
            return
        all_code = ""
        for fname, content in self.files.items():
            all_code += "\n--- FICHIER : {} ---\n{}\n--- FIN ---".format(fname, content)
        level = self.level.get()
        lv = LEARNING_LEVELS[level]
        verify_prompt = (
            "Tu es Calisto, un mentor patient qui tutoie l'apprenant. Il travaille au niveau {} ({}); "
            "tiens compte de cette tolerance aux erreurs : {}.\n"
            "Vérifie avec attention si son travail répond au défi et si le site semble fonctionnel. "
            "Défi :\n{}\n\nCode réalisé :\n{}\n\n"
            "Commence ta réponse par VALIDE ou REFUSE, seul sur la première ligne. "
            "Ensuite, réponds avec naturel et bienveillance : souligne ce qui fonctionne, explique les points "
            "importants à corriger s'il y en a, puis propose une prochaine étape concrète. "
            "Évite les listes numérotées et les formules d'examinateur. Ne fournis pas le code complet."
        ).format(lv["label"], level, lv["tolerance"], self.current_subject, all_code)

        self._stop_timer()
        self.verification_in_progress = True
        self.verify_btn.configure(state="disabled")
        self.pause_btn.configure(state="disabled")
        self.status_label.configure(text="Verification en cours…", text_color=TEXT_MAIN)
        self._verification_id += 1
        request_id = self._verification_id
        model = self.app.model_var.get() or MODEL
        threading.Thread(
            target=self._verify_thread,
            args=(verify_prompt, model, request_id),
            daemon=True,
        ).start()

    @staticmethod
    def _is_default_skeleton(html):
        default = "<!DOCTYPE html>\n<html>\n<head>\n    <title>Mon site</title>\n</head>\n<body>\n    <h1>Bonjour</h1>\n</body>\n</html>"
        normal = " ".join(html.split())
        norm_default = " ".join(default.split())
        return normal == norm_default

    def _generate_subject(self):

        self._generation_id += 1
        request_id = self._generation_id
        level = self.level.get()

        lv = LEARNING_LEVELS[level]

        sujets_deja = list(self.app._learning_sujets[-10:])
        themes = LEARNING_PROJECT_THEMES[level]
        available_themes = [theme for theme in themes if theme not in self.project_history[-8:]]
        project_theme = random.choice(available_themes or themes)
        self.current_project_theme = project_theme
        historique = ""
        if sujets_deja:
            historique = "SUJETS DEJÀ PROPOSES (NE PAS les reprendre) :\n- {}\n\n".format("\n- ".join(sujets_deja[-10:]))
        difficulty_desc = {
            "junior": "simple, une seule page, basique",
            "facile": "une page avec quelques elements interactifs",
            "normale": "plusieurs sections, mise en page soignee, un peu de JavaScript",
            "difficile": "site multi-pages ou application web avec JavaScript significatif",
            "legendaire": "application web complete ou site e-commerce complexe",
            "senior": "projet professionnel complet avec architecture, design responsive et fonctionnalites avancees",
        }[level]
        prompt = (
            "Tu es Calisto, un mentor en developpement web patient et encourageant. Tu tutoies l'apprenant.\n"
            "Imagine un seul projet concret, adapte au niveau {label} ({level}). Le theme tire au sort est "
            "\"{theme}\" : garde exactement cette idee, sans la transformer en portfolio ni en un autre type de site.\n"
            "La difficulte attendue est {difficulty_desc}. Elle doit se voir dans les fonctionnalites a realiser, "
            "pas seulement dans le nombre de pages.\n"
            "Presente le defi en francais naturel, comme si tu l'expliquais directement a la personne. "
            "Commence par une phrase engageante, explique simplement ce qu'elle va construire et a quoi cela sert. "
            "Ajoute quelques points concrets a realiser seulement si cela aide a comprendre le projet; pas de plan "
            "numerote ni de rubriques mecaniques comme SUJET, OBJECTIF ou EXIGENCES TECHNIQUES. "
            "Termine par une courte phrase motivante.\n"
            "Le defi doit tout de meme donner assez de details pour guider le travail : fonctionnalites attendues, "
            "sections utiles, une exigence HTML/CSS/JavaScript adaptee au niveau et une facon claire de savoir "
            "quand le projet est reussi. Ne fournis pas de code ni la solution complete.\n"
            "{history}"
        ).format(
            label=lv["label"],
            level=level,
            theme=project_theme,
            difficulty_desc=difficulty_desc,
            history=historique,
        )
        # Afficher un indicateur de chargement
        model = self.app.model_var.get() or MODEL
        self.subject_ready = False
        self.start_btn.configure(state="disabled")
        self.generate_btn.configure(state="disabled", text="Generation…")
        self.level_btn.configure(state="disabled")
        self.abandon_btn.configure(text="Annuler")
        self.status_label.configure(text="Preparation du projet et de ses consignes…", text_color=TEXT_MAIN)
        self._stop_loading()
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.set(0)
        self.progress_label.configure(text="En cours")
        self.progress_bar.start()
        threading.Thread(
            target=self._generate_subject_worker,
            args=(request_id, model, prompt),
            daemon=True,
        ).start()

    def _generate_subject_worker(self, request_id, model, prompt):
        try:
            with ollama.Client(timeout=120.0) as client:
                response = client.chat(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    options={"temperature": 0.7, "num_predict": 400},
                )
            sujet = (response.get("message", {}).get("content") or "").strip()
            if not sujet:
                raise RuntimeError("Le modele a renvoye un sujet vide.")
            self.app.ui_queue.put(("learning_subject", self, request_id, sujet))
        except Exception as e:
            self.app.ui_queue.put(("learning_subject_error", self, request_id, str(e)))

    def _finish_loading(self, sujet):
        self._stop_loading()
        self.progress_bar.set(1.0)
        self.progress_label.configure(text="100%")
        self._display_subject(sujet)

    def _handle_worker_event(self, kind, *payload):
        if kind == "learning_subject":
            request_id, sujet = payload
            if request_id != self._generation_id:
                return
            self.project_history.append(self.current_project_theme)
            first_line = next((line.strip() for line in sujet.splitlines() if line.strip()), sujet[:80])
            self.app._learning_sujets.append(first_line[:80])
            self._finish_loading(sujet)
        elif kind == "learning_subject_error":
            request_id, detail = payload
            if request_id != self._generation_id:
                return
            self._stop_loading()
            self.subject_ready = False
            self.start_btn.configure(state="disabled")
            self.generate_btn.configure(state="normal", text="Reessayer")
            self.level_btn.configure(state="normal")
            self.progress_bar.set(0)
            self.progress_label.configure(text="Erreur")
            self.status_label.configure(
                text="Je n’ai pas réussi à préparer le défi : {}. Vérifie le moteur IA, puis clique sur « Réessayer ».".format(detail),
                text_color="#c24141",
            )
            self._set_text(
                self.ia_instructions,
                "Je n’ai pas réussi à préparer ton défi pour le moment. "
                "Vérifie que le moteur IA est disponible, puis réessaie.",
            )
        elif kind == "learning_advice":
            generation, advice = payload
            if generation == self._advice_generation and self.started and not self.paused:
                self._set_text(self.ia_advice, advice)
        elif kind == "learning_advice_error":
            generation, detail = payload
            if generation == self._advice_generation and self.started and not self.paused:
                self.status_label.configure(text="Conseil IA indisponible : {}".format(detail), text_color="#c24141")
        elif kind == "learning_verify_result":
            request_id, result = payload
            if request_id == self._verification_id:
                self._show_result(result)
        elif kind == "learning_verify_error":
            request_id, detail = payload
            if request_id != self._verification_id:
                return
            self.verification_in_progress = False
            self.verify_btn.configure(state="normal")
            self.pause_btn.configure(state="normal")
            self.code_editor.configure(state="normal")
            if self.started and not self.paused:
                self._tick_timer()
            self.status_label.configure(text="Erreur pendant la verification : {}".format(detail), text_color="#c24141")

    def _stop_loading(self):
        if hasattr(self, "progress_bar"):
            self.progress_bar.stop()
            self.progress_bar.configure(mode="determinate")

    def _display_subject(self, sujet):
        self._stop_loading()
        lv = LEARNING_LEVELS[self.level.get()]
        self.current_subject = "Theme choisi : {}\n\n{}".format(self.current_project_theme, sujet)
        self.exercise_count += 1
        self.exercise_label.configure(text="Exercice {}".format(self.exercise_count))
        full = (
            "Défi {} · niveau {}\n\n".format(self.exercise_count, lv["label"]) +
            "{}\n\n".format(sujet) +
            "Tu peux créer jusqu’à {} fichiers HTML, CSS ou JavaScript. "
            "Quand tu te sens prêt, clique sur « Démarrer l’exercice » ; tu pourras faire une pause à tout moment.".format(
                lv["max_files"]
            )
        )
        self._set_text(self.ia_instructions, full)
        self.subject_ready = True
        self.start_btn.configure(state="normal")
        self.generate_btn.configure(state="normal", text="Nouveau sujet")
        self.level_btn.configure(state="normal")
        self.abandon_btn.configure(text="Abandonner")
        self.status_label.configure(text="Ton défi est prêt. Lis les consignes, puis démarre quand tu veux.", text_color="#0d8a6a")

    def _verify_thread(self, prompt, model, request_id):
        try:
            response = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}], options={"temperature": 0.3, "num_predict": 512})
            content = (response.get("message", {}).get("content") or "").strip()
            if not content:
                raise RuntimeError("Le modele a renvoye une reponse vide.")
            self.app.ui_queue.put(("learning_verify_result", self, request_id, content))
        except Exception as e:
            self.app.ui_queue.put(("learning_verify_error", self, request_id, str(e)))

    @staticmethod
    def _verification_passed(text):
        normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").upper()
        first_line = normalized.strip().splitlines()[0] if normalized.strip() else ""
        outcome = re.match(
            r"^(?:[*#>\s-]*)(?:RESULTAT\s*[:\-]\s*)?(?:\d+\.\s*)?(VALIDE|VALIDEE|REFUSE|REFUSEE)\b",
            first_line.strip(),
        )
        return bool(outcome and outcome.group(1).startswith("VALID"))

    def _show_result(self, text):
        is_valid = self._verification_passed(text)
        color = "#0d8a6a" if is_valid else "#c24141"
        self.verification_in_progress = False
        self._set_text(self.ia_advice, text)
        self.status_label.configure(text=text, text_color=color)
        elapsed = int(time.time() - self.start_time) if self.start_time else 0
        if is_valid:
            self._stop_timer()
            self._save_time(self.level.get(), elapsed)
            self.status_label.configure(text="Exercice reussi ! Generation d'un nouvel exercice…", text_color=ACCENT)
            self.files = {"index.html": "<!DOCTYPE html>\n<html>\n<head>\n    <title>Mon site</title>\n</head>\n<body>\n    <h1>Bonjour</h1>\n</body>\n</html>"}
            self.current_file = "index.html"
            self._refresh_files_ui()
            self._open_file("index.html")
            self._set_level_instructions(self.level.get())
            self.started = False
            self.paused = False
            self.start_time = None
            self.subject_ready = False
            self.code_editor.configure(state="disabled")
            self.verify_btn.configure(state="disabled")
            self.pause_btn.configure(state="disabled", text="Pause")
            self.start_btn.configure(state="disabled")
            self.level_btn.configure(state="normal")
            self._generate_subject()
        else:
            self.code_editor.configure(state="normal")
            self.verify_btn.configure(state="normal")
            self.pause_btn.configure(state="normal")
            if self.started and not self.paused:
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


def _install_log_redirect():
    """Sans fenetre console, les messages sont recopies dans un fichier."""
    sans_console = sys.executable.lower().endswith("pythonw.exe") or getattr(sys, "frozen", False)
    if not sans_console:
        return
    try:
        log_file = open(base_dir() / "calisto_log.txt", "a", encoding="utf-8", buffering=1)
        sys.stdout = log_file
        sys.stderr = log_file
    except Exception:
        pass


class ProfileSelector(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Calisto - Choisir un profil")
        self.geometry("520x400")
        self.configure(fg_color=BG_APP)
        self.resizable(False, False)
        self.profil_choisi = None
        self._profils_path = base_dir() / "profils.json"
        self._load_profils()
        self._build_ui()
        self._center()

    def _load_profils(self):
        self.profils = []
        self.courant = None
        try:
            if self._profils_path.exists():
                with open(self._profils_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.profils = data.get("profils", [])
                self.courant = data.get("courant")
        except Exception:
            self.profils = []
            self.courant = None
        if not self.profils:
            self.profils = ["Par defaut"]
            self.courant = "Par defaut"
        if self.courant not in self.profils:
            self.courant = self.profils[0]

    def _save_profils(self):
        try:
            with open(self._profils_path, "w", encoding="utf-8") as f:
                json.dump({"profils": self.profils, "courant": self.courant}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _build_ui(self):
        ctk.CTkLabel(
            self,
            text="Calisto",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=TEXT_MAIN,
        ).pack(pady=(24, 4))
        ctk.CTkLabel(
            self,
            text="Choisissez un profil ou creez-en un nouveau",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_MUTED,
        ).pack(pady=(0, 16))

        self.list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 12))
        self.list_frame.grid_columnconfigure(0, weight=1)

        self._refresh_list()

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=20, pady=(0, 20))
        btns.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(
            btns,
            text="+ Nouveau",
            command=self._ajouter_profil,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).grid(row=0, column=0, padx=4, sticky="ew")

        ctk.CTkButton(
            btns,
            text="Supprimer",
            command=self._supprimer_profil,
            fg_color="#7f1d1d",
            hover_color="#991b1b",
            font=ctk.CTkFont(size=11, weight="bold"),
        ).grid(row=0, column=1, padx=4, sticky="ew")

        ctk.CTkButton(
            btns,
            text="Se connecter",
            command=self._connecter,
            fg_color="#263547",
            hover_color="#34475c",
            font=ctk.CTkFont(size=11, weight="bold"),
        ).grid(row=0, column=2, padx=4, sticky="ew")

    def _refresh_list(self):
        for w in self.list_frame.winfo_children():
            w.destroy()
        for nom in self.profils:
            marque = " (courant)" if nom == self.courant else ""
            row = ctk.CTkFrame(self.list_frame, fg_color=BG_PANEL, corner_radius=8)
            row.pack(fill="x", pady=4)
            row.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(
                row,
                text=nom + marque,
                font=ctk.CTkFont(size=12),
                text_color=TEXT_MAIN,
                anchor="w",
            ).grid(row=0, column=0, sticky="ew", padx=12, pady=8)
            ctk.CTkButton(
                row,
                text="Choisir",
                width=70,
                command=lambda n=nom: self._choisir(n),
                fg_color=ACCENT,
                hover_color=ACCENT_HOVER,
                font=ctk.CTkFont(size=10),
            ).grid(row=0, column=1, padx=6)

    def _choisir(self, nom):
        self.courant = nom
        self._save_profils()
        self.profil_choisi = nom
        self.destroy()

    def _ajouter_profil(self):
        nom = simpledialog.askstring("Nouveau profil", "Nom du profil :", parent=self)
        if not nom:
            return
        nom = nom.strip()
        if not nom:
            return
        if nom in self.profils:
            messagebox.showwarning("Profil existe", "Ce profil existe deja.", parent=self)
            return
        self.profils.append(nom)
        self.courant = nom
        self._save_profils()
        self._refresh_list()

    def _supprimer_profil(self):
        if len(self.profils) <= 1:
            messagebox.showwarning("Impossible", "Il faut garder au moins un profil.", parent=self)
            return
        nom = self.courant
        if not messagebox.askyesno("Supprimer", "Supprimer le profil '{}' ?".format(nom), parent=self):
            return
        self.profils.remove(nom)
        if self.courant == nom:
            self.courant = self.profils[0]
        self._save_profils()
        self._refresh_list()

    def _connecter(self):
        if self.courant:
            self._choisir(self.courant)

    def _center(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry("{}x{}+{}+{}".format(w, h, x, y))


def main():
    _install_log_redirect()
    try:
        selector = ProfileSelector()
        selector.mainloop()
        profil = selector.profil_choisi
        if profil is None:
            return
        app = App(profil=profil)
        app.mainloop()
    except Exception:
        detail = traceback.format_exc()
        try:
            sys.stderr.write(detail)
        except Exception:
            pass
        try:
            messagebox.showerror(
                "Calisto s'est arrete",
                "Une erreur inattendue est survenue :\n\n{}".format(detail[-700:]),
            )
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
