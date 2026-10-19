# Calisto - Assistant IA pour débutants

Calisto est une application de bureau (Python + CustomTkinter + Ollama) conçue pour être simple, claire et accessible aux débutants. Elle combine un chat IA, un éditeur de code moderne et un mode d'apprentissage interactif pour apprendre à coder HTML/CSS/JavaScript.

## Fonctionnalités

### 1. Discussion (Chat IA)
- Posez vos questions en français à l'IA locale (Ollama).
- L'IA répond de façon naturelle et chaleureuse, sans ton robotique.
- Si vous reposez la même question, l'IA approfondit plutôt que de répéter.
- La recherche web est désactivée par défaut : l'IA ne cherche pas sur internet pour répondre à des questions de code ou hors ligne.

### 2. Éditeur de code
Onglet intégré pour écrire et modifier du code (HTML, CSS, JavaScript, Python, etc.) :
- Auto-fermeture des paires : `() [] {} "" ''`
- Commenter/décommenter : `Ctrl+/`
- Rechercher/remplacer : `Ctrl+F`
- Aller à la ligne : `Ctrl+G`
- Zoom : `Ctrl` + molette
- Sauvegarde : `Ctrl+S`
- Retour à la ligne (word wrap)
- Surbrillance des accolades correspondantes

### 3. Mode Apprentissage
Un mode ludique pour apprendre à coder sans aide de l'IA :
- 6 niveaux de difficulté : Junior, Facile, Normale, Difficile, Légendaire, Senior.
- L'IA génère un sujet de projet précis (landing page, site de voyage, e-commerce, blog, etc.) avec des consignes structurées.
- Vous codez dans l'éditeur intégré (copier-coller désactivé).
- L'IA vérifie votre travail et répond uniquement `VALIDÉ` ou `REFUSÉ`.
- En cas de succès, un nouvel exercice est généré automatiquement.
- Chronomètre et historique des temps par niveau.
- Bouton Pause pour bloquer l'éditeur et faire une pause.

### 4. Réglages
- Choisir le modèle Ollama et la température.
- Personnaliser l'instruction système (personnalité de l'IA).
- Activer/désactiver la recherche web.
- Autoriser l'IA à créer des fichiers ou modifier l'application (avec confirmation à chaque fois).

## Installation

### Prérequis
- Python 3.10 ou supérieur
- [Ollama](https://ollama.com/) installé et en cours d'exécution (port 11434)
- Un modèle Ollama téléchargé (ex: `ollama pull llama3.2`)

### Dépendances Python
```bash
pip install customtkinter ollama ddgs PyPDF2 fpdf2
```

### Lancement
```bash
python app_desktop.py
```

Ou avec le script :
```bash
"Lancer IA.bat"
```

## Structure du projet

```
calisto/
├── app_desktop.py      # Fenêtre principale (chat, réglages, lancement du mode apprentissage)
├── dev_window.py       # Éditeur de code intégré
├── app.py              # Version Streamlit (alternative)
├── Lancer IA.bat       # Script de lancement Windows
├── README.md           # Ce fichier
├── ia_creations/       # Fichiers créés par l'IA
├── generated/          # Fichiers générés
└── learning_times.json # Temps enregistrés par niveau (mode apprentissage)
```

## Utilisation pour les débutants

1. **Lancez l'application** et vérifiez qu'Ollama est en ligne (indicateur en bas).
2. **Discutez** avec l'IA dans l'onglet "Discussion".
3. **Écrivez du code** dans l'onglet "Éditeur de code".
4. **Apprenez** dans l'onglet "Apprentissage" en cliquant sur "Ouvrir le mode Apprentissage".
5. **Personnalisez** l'IA dans "⚙️ Réglages".

## Notes

- Aucune conversation n'est enregistrée sur le disque (pas d'historique persistant).
- L'IA ne modifie jamais les fichiers sans votre confirmation explicite.
- La recherche web ne se déclenche que si vous l'activez dans les réglages et si vous posez une question nécessitant des informations en ligne.
