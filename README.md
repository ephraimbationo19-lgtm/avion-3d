# ✈️ Pilote d'Avion 3D

Un petit jeu de pilotage en **3D**, en vue troisième personne : vous voyez l'avion
que vous contrôlez, vous virez avec les flèches et vous traversez des anneaux
pour marquer des points.

Deux versions disponibles :
- 🌐 **Version web** (HTML/JS) — jouable directement dans le navigateur, sans installation
- 🐍 **Version Python** (pyglet / OpenGL) — le code source original

---

## 🌐 Jouer sur le web (le plus simple)

Ouvrez simplement [`web/index.html`](web/index.html) dans un navigateur
(Chrome, Firefox, Safari…). Un double-clic suffit, aucune installation.

Pour le partager avec des amis :
1. Activez **GitHub Pages** dans les paramètres du dépôt (branche `main`, dossier `/root` ou `/web`).
2. Envoyez le lien `https://<votre-pseudo>.github.io/avion-3d/web/` à vos amis.

💡 Fonctionne aussi sur **mobile** : des boutons tactiles apparaissent automatiquement.

## 🐍 Jouer en Python

### 1. Installer Python 3.10+

https://www.python.org/downloads/

### 2. Installer la dépendance

```bash
pip install -r requirements.txt
```

### 3. Lancer

```bash
python avion.py
```

(sur Linux/macOS : `python3 avion.py`)

---

## 🎮 Commandes

| Touches | Action |
|---------|--------|
| ← / → | Virer à gauche / à droite (l'avion s'incline) |
| ↑ / ↓ | Cabrer (monter) / piquer (descendre) |
| R | Recommencer après un crash |
| Échap | Quitter (version Python) |

**Objectif :** traverser les anneaux jaunes (100 points chacun) sans toucher le sol.

## 🧊 Bonus

`game.py` est un second jeu, **Cube Runner 3D** (esquive de cubes en vue subjective).
Lancez-le avec `python game.py`.

---

Fait avec Python + pyglet (OpenGL) et HTML5 Canvas. Amusez-vous bien ! 🛩️
