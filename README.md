# tr2loop — Transformation de récursion terminale en boucle (Python)

## Objectif
Détecter dans un fichier Python les fonctions **récursives terminales** et les **transformer** automatiquement en **boucles `while True`**.

## Structure
- `tr2loop/analyze_frontend.py` — Étape 1 : Lexing pédagogique + Parsing (AST) + résumé.
- `tr2loop/tail_analysis.py` — Étape 2 : Détection de la récursion terminale.
- `tr2loop/tail_transform.py` — Étape 3 : Transformation automatique (tail-call -> boucle).
- `tr2loop/__main__.py` — Petite CLI pour lancer la transformation.
- `examples/sample_input.py` — Exemple de fonctions à transformer.

## Installation
Python 3.10+ recommandé (pour `ast.unparse`).
# Commandes à exécuter
# python tr2loop\analyze_frontend.py examples\sample_input.py
# python tr2loop\tail_analysis.py examples\sample_input.py
# python -m tr2loop "examples\sample_input.py" --dry-run

