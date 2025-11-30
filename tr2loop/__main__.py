#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
__main__.py
------------
Point d’entrée du module tr2loop.
Permet d’exécuter la transformation via :
    python -m tr2loop examples\sample_input.py
ou en mode test :
    python -m tr2loop examples\sample_input.py --dry-run
"""

import os
import sys

# --- S'assurer que les imports relatifs fonctionnent même en exécution directe ---
if __package__ is None:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    __package__ = "tr2loop"

# --- Import de la fonction d'exécution principale ---
from .tail_transform import run_cli

# --- Lancement de la transformation ---
if __name__ == "__main__":
    run_cli(sys.argv)