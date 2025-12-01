#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
analyze_frontend.py
-------------------
Étape 1 : Analyse lexicale + syntaxique (frontend) pour le projet
"Optimisation des fonctions récursives terminales en Python".

Ce script :
  1) Tokenise (découpe en sous ense) le code source à l'aide d'expressions régulières (LEXER).
  2) Construit l'AST officiel avec ast.parse et imprime un résumé de structure (PARSER).

Utilisation :
  python analyze_frontend.py chemin/vers/fichier_source.py

Remarque :
  - Le LEXER ici est pédagogique : pour la transformation réelle, on
    s'appuiera surtout sur l'AST Python (plus fiable et complet).
"""

from __future__ import annotations
import re
import sys
import ast
from dataclasses import dataclass
from typing import Iterator, List, Optional, Tuple

# =========================
# 1) ANALYSE LEXICALE (LEXER)
# =========================

# --- Définition des catégories de tokens utiles à notre projet ---
# On couvre : COMMENT, WHITESPACE, NEWLINE, KEYWORD, IDENT, INT, FLOAT, STRING, OP
# NB : l'ordre et le "longest match" sont importants pour éviter des ambiguïtés.

# a) Fragments réutilisables (lisibilité)
INT_FRAG   = r"(?:0|[1-9][0-9_]*)"  # entier décimal simple (avec underscores autorisés)
FLOAT_FRAG = (
    r"(?:(?:\d+\.\d*|\.\d+|\d+\.)(?:[eE][+-]?\d+)?|(?:\d+[eE][+-]?\d+))"
)  # nombres flottants (décimal + exponentiel)

# Chaînes : versions simples et triple quotes (non-gourmandes)
STRING_FRAG = r"""
(?:
    \"\"\"[\s\S]*?\"\"\"      # triple double quotes
  | \'\'\'[\s\S]*?\'\'\'      # triple single quotes
  | \"[^\"\\]*(?:\\.[^\"\\]*)*\"   # "..."
  | \'[^\'\\]*(?:\\.[^\'\\]*)*\'   # '...'
)
"""

# Mots-clés minimaux requis pour détecter des fonctions, retours, conditions, boucles, etc.
KEYWORDS = r"\b(?:def|return|if|elif|else|while|True|False|None|and|or|not|pass|continue|break|in)\b"

# Opérateurs/délimiteurs nécessaires (mettre les plus longs d'abord)
OPS = r"""
\*\*|//|==|!=|<=|>=|->|\+=|-=|\*=|/=|%=|
\(|\)|:|,|\.|=|<|>|\+|-|\*|/|%
"""

# b) REGEX "maître" avec groupes nommés pour catégoriser chaque token
MASTER_PATTERN = rf"""
(?P<COMMENT>     \#[^\n]* )
|(?P<WHITESPACE> [ \t\r\f]+ )
|(?P<NEWLINE>    \n )

|(?P<KEYWORD>    {KEYWORDS} )

|(?P<STRING>     {STRING_FRAG} )

|(?P<FLOAT>      {FLOAT_FRAG} )
|(?P<INT>        {INT_FRAG} )

|(?P<IDENT>      [A-Za-z_][A-Za-z_0-9]* )

|(?P<OP>         {OPS} )
"""

TOKEN_RE = re.compile(MASTER_PATTERN, re.VERBOSE | re.MULTILINE)

@dataclass
class Token:
    kind: str      # type de token (ex: KEYWORD, IDENT, INT, FLOAT, OP, ...)
    text: str      # texte exact matché
    line: int      # numéro de ligne (1-based)
    col: int       # colonne (0-based)

def lex(source: str) -> Iterator[Token]:
    """
    Générateur de tokens.
    - Ignore COMMENT et WHITESPACE (courants).
    - NEWLINE est conservé (utile si tu veux compter les lignes).
    - Produit un flux de Token(kind, text, line, col).
    """
    # Pour calculer line/col : on précompute les offsets de début de ligne
    line_starts: List[int] = [0]
    for m in re.finditer(r"\n", source):
        line_starts.append(m.end())

    def pos_to_linecol(pos: int) -> Tuple[int, int]:
        # Cherche la plus grande ligne dont le start <= pos
        # (recherche linéaire OK pour un petit projet ; pour gros fichiers, utiliser bisect)
        line_idx = 0
        for i, start in enumerate(line_starts):
            if start <= pos:
                line_idx = i
            else:
                break
        line_no = line_idx + 1
        col_no = pos - line_starts[line_idx]
        return line_no, col_no

    for m in TOKEN_RE.finditer(source):
        kind = m.lastgroup or "UNKNOWN"
        text = m.group()

        if kind in ("WHITESPACE", "COMMENT"):
            continue  # on ignore

        # Calcule line/col pour le début du match
        start_pos = m.start()
        line, col = pos_to_linecol(start_pos)

        yield Token(kind=kind, text=text, line=line, col=col)

# =========================
# 2) ANALYSE SYNTAXIQUE (PARSER via AST Python)
# =========================

class StructurePrinter(ast.NodeVisitor):
    """
    Visiteur d'AST avec une sortie plus claire et lisible.
    Affiche :
      - les fonctions et leurs paramètres
      - les retours (valeurs simples ou appels récursifs)
      - les appels de fonction
    """
    def __init__(self):
        self._indent = 0

    def _p(self, msg: str) -> None:
        print("   " * self._indent + msg)

    def visit_Module(self, node: ast.Module) -> None:
        print("📘 Analyse de la structure du module")
        self._indent += 1
        self.generic_visit(node)
        self._indent -= 1

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        params = [a.arg for a in node.args.args]
        self._p(f"🧩 Fonction : {node.name}({', '.join(params)})")
        self._indent += 1

        doc = ast.get_docstring(node)
        if doc:
            self._p(f"📝 Docstring : {doc.splitlines()[0][:60]}")

        self.generic_visit(node)
        self._indent -= 1

    def visit_Return(self, node: ast.Return) -> None:
        if isinstance(node.value, ast.Call):
            callee = self._short_call(node.value)
            self._p(f"↩️  Retourne un appel récursif : {callee}")
        else:
            self._p(f"↩️  Retourne la valeur : {self._short_expr(node.value)}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        self._p(f"📞 Appel de fonction : {self._short_call(node)}")
        self.generic_visit(node)

    # --- Helpers d’affichage ---
    def _short_expr(self, node: Optional[ast.AST]) -> str:
        if node is None:
            return "None"
        try:
            return ast.unparse(node)
        except Exception:
            return node.__class__.__name__

    def _short_call(self, node: ast.Call) -> str:
        func_name = (
            node.func.id if isinstance(node.func, ast.Name)
            else ast.unparse(node.func)
        )
        args = [self._short_expr(a) for a in node.args]
        return f"{func_name}({', '.join(args)})"

def parse_and_summarize_ast(source: str) -> None:
    """
    Construit l'AST via ast.parse et affiche un résumé structurel.
    Si le parsing échoue (erreur de syntaxe), lève une exception explicite.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        print(f"[ERREUR SYNTAXE] {e.msg} (ligne {e.lineno}, col {e.offset})")
        raise

    printer = StructurePrinter()
    printer.visit(tree)

# =========================
# 3) "MAIN" : exécution sur un fichier source
# =========================

def main(argv: List[str]) -> None:
    if len(argv) != 2:
        print("Usage : python analyze_frontend.py chemin/vers/fichier_source.py")
        sys.exit(1)

    src_path = argv[1]
    with open(src_path, "r", encoding="utf-8") as f:
        source = f.read()

    print("=" * 70)
    print("1) ANALYSE LEXICALE (TOKENS)")
    print("=" * 70)
    for tok in lex(source):
        # On n'affiche pas NEWLINE pour alléger ; décommente si besoin
        if tok.kind == "NEWLINE":
            continue
        print(f"{tok.line:>4}:{tok.col:<3}  {tok.kind:<10}  {tok.text!r}")

    print("\n" + "=" * 70)
    print("2) ANALYSE SYNTAXIQUE (AST SUMMARY)")
    print("=" * 70)
    parse_and_summarize_ast(source)

if __name__ == "__main__":
    main(sys.argv)
 