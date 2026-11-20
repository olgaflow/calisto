# Calisto - Assistant IA pour débutants

Calisto est une application de bureau (Python + CustomTkinter + Ollama) conçue pour être simple, claire et accessible aux débutants. Elle combine un chat IA, un éditeur de code moderne et un mode d'apprentissage interactif pour apprendre à coder HTML/CSS/JavaScript.

## Fonctionnalités

### 1. Discussion (Chat IA)
- Posez vos questions en français à l'IA locale (Ollama).
- L'IA répond de façon naturelle et chaleureuse, sans ton robotique.
- Les réponses s'affichent progressivement et restent concises par défaut pour accélérer les échanges.
- Le chat peut lire le fichier actuellement ouvert et les autres fichiers de code du projet, y compris les modifications non enregistrées dans l'éditeur.
- Une mémoire par projet conserve les derniers échanges et résume les plus anciens pour aider l'IA à suivre le travail au fil du temps.
- Les blocs de code proposés apparaissent dans l'éditeur comme des propositions à accepter ou refuser ; l'acceptation remplace et enregistre le fichier cible.
- À la demande, l'IA peut créer des fichiers texte/source de différents formats, des PDF à partir de texte et de petits fichiers binaires Base64 (5 Mo maximum). Les PDF apparaissent dans la conversation avec un bouton **Télécharger** ; les créations sont aussi enregistrées dans `ia_creations`, accessible avec le bouton **Fichiers IA**.
- Les PDF sont créés directement par Calisto, sans outil externe, et mis en forme avec titres, sections, listes, tableaux et blocs de code ; les phrases de conversation sont écartées du document. Si la réponse ne contient pas un document complet, Calisto demande automatiquement une nouvelle génération et refuse d'enregistrer un PDF réduit à un titre. Le code non encadré par des balises est séparé et formaté quand sa syntaxe est valide, sinon il est signalé plutôt qu'affiché en bloc illisible.
- Les PDF et images sont d'abord montrés dans le chat avec un aperçu réel, puis les boutons **Valider**, **Recommencer**, **Refuser** et **Télécharger**. Le fichier n'est enregistré dans `ia_creations` qu'après validation.
- FLUX.1-schnell peut générer des images localement via stable-diffusion.cpp (C++/Vulkan). L'installation se lance dans **Réglages** et télécharge environ 9,6 Go de modèles ; l'accès au modèle officiel nécessite d'accepter ses conditions Hugging Face. Le jeton Read est utilisé uniquement en mémoire pendant le téléchargement du VAE et n'est pas enregistré.
- Les blocs de code destinés à l'éditeur restent des propositions à accepter ou refuser. Les fichiers générés ne sont jamais exécutés automatiquement.
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
- Le type de projet est tiré au hasard dans une sélection adaptée au niveau ; une barre animée indique la préparation des consignes.
- Les consignes sont formulées en français naturel, comme une explication directe et encourageante du défi.
- Le démarrage reste désactivé jusqu'à ce que le sujet soit prêt ; vous pouvez annuler la préparation ou mettre l'exercice en pause.
- Vous codez dans l'éditeur intégré (copier-coller désactivé).
- L'IA vérifie votre travail et répond uniquement `VALIDÉ` ou `REFUSÉ`.
- En cas de refus, l'éditeur reste accessible pour corriger le projet ; les fichiers HTML, CSS et JavaScript peuvent être ajoutés.
- Dans un fichier HTML, saisir `<!>` propose d'insérer la structure HTML de base.
- En cas de succès, un nouvel exercice est généré automatiquement.
- Si Ollama ne répond pas, l'erreur est affichée dans l'onglet et le sujet peut être relancé.
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

Calisto démarre Ollama tout seul s'il est installé mais éteint, et propose de
télécharger le modèle manquant au premier lancement.

### Dépendances Python
```bash
pip install -r requirements.txt
```

### Lancement
Double-clic sur **`Lancer Calisto.vbs`** : l'application s'ouvre sans aucune
fenêtre console noire.

`Lancer IA.bat` reste disponible : il installe (ou vérifie) les dépendances
puis lance l'application sans console non plus.

En ligne de commande :
```bash
python app_desktop.py
```

Les erreurs éventuelles sont consignées dans `calisto_log.txt`.

## Structure du projet

```
calisto/
├── app_desktop.py      # Fenêtre principale (chat, réglages, lancement du mode apprentissage)
├── dev_window.py       # Éditeur de code intégré
├── ai_runtime.py       # Moteur IA intégré (démarrage d'Ollama, modèles)
├── app.py              # Version Streamlit (alternative)
├── Lancer Calisto.vbs  # Lancement silencieux (sans console)
├── Lancer IA.bat       # Installation des dépendances + lancement
├── calisto.spec        # Configuration PyInstaller (déploiement Windows)
├── build_windows.bat   # Construction de l'exécutable Windows
├── requirements.txt    # Dépendances Python
├── README.md           # Ce fichier
├── ia_creations/       # Fichiers créés par l'IA
├── generated/          # Fichiers générés
└── learning_times.json # Temps enregistrés par niveau (mode apprentissage)
```

## Préparer un déploiement Windows

La construction n'est pas lancée automatiquement, elle est prête à l'emploi :

```bat
build_windows.bat
```

Le script installe PyInstaller puis produit `dist\Calisto\Calisto.exe`
(application en mode fenêtre, sans console). Copier le dossier `dist\Calisto`
sur le poste cible suffit.

## Utilisation pour les débutants

1. **Lancez l'application** et vérifiez qu'Ollama est en ligne (indicateur en bas).
2. **Discutez** avec l'IA dans l'onglet "Discussion".
3. **Écrivez du code** dans l'onglet "Éditeur de code".
4. **Apprenez** dans l'onglet "Apprentissage" en cliquant sur "Lancer un exercice".
5. **Personnalisez** l'IA dans "⚙️ Réglages".

## Notes

- Le chat conserve localement, par projet, les derniers échanges et leur résumé dans le dossier d'état de Calisto. Le bouton d'effacement supprime la mémoire de la conversation du projet courant.
- L'IA ne modifie jamais les fichiers sans votre confirmation explicite.
- La recherche web ne se déclenche que si vous l'activez dans les réglages et si vous posez une question nécessitant des informations en ligne.
