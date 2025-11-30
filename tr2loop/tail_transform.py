#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
tail_transform.py
-----------------
Transforme automatiquement les fonctions récursives terminales
en boucles while équivalentes (forme itérative).

Affichage demandé :
1) Un récapitulatif initial listant TOUTES les fonctions (✅ si transformée, ℹ️ sinon).
2) Puis, pour CHAQUE fonction transformée :
   ///////////////Version originale ( nom ) ://///////////////////////////////
   <corps original>
   ///////////////Version transformée ( nom ) ://////////////////////////////
   <corps transformé>
"""

import ast
import sys
from typing import List, Tuple, Dict, Any

# ///////////////////////// ANALYSE SEMANTIQUE (DETECTION) /////////////////////////
# Cette partie fait une analyse sémantique simplifiée pour décider si une
# fonction est récursive terminale ou non, à partir de l'AST.

# ------------------------------------------------------------
# Étape 1 : Détection — Récursion terminale ?
# ------------------------------------------------------------
def is_tail_recursive(func: ast.FunctionDef) -> bool:
    """Vérifie si une fonction contient une récursion terminale."""
    name = func.name
    found_call = False

    for node in ast.walk(func):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == name:
            # Vérifie que l'appel est directement retourné
            parent = getattr(node, 'parent', None)
            if not isinstance(parent, ast.Return):
                return False
            found_call = True
    return found_call


def attach_parents(node: ast.AST) -> None:
    """Ajoute les liens parent dans l’AST pour l’analyse."""
    for child in ast.iter_child_nodes(node):
        child.parent = node
        attach_parents(child)

# ////////////////////////////// OPTIMISATION ////////////////////////////////
# À partir de l'analyse précédente, on transforme les fonctions récursives
# terminales en boucles while True équivalentes (élimination de récursion).

# ------------------------------------------------------------
# Étape 2 : Transformation
# ------------------------------------------------------------
class TailTransformer(ast.NodeTransformer):
    """Remplace 'return f(...)' par des affectations + continue."""

    def __init__(self, func_name: str, params: List[str]):
        self.func_name = func_name
        self.params = params

    def visit_Return(self, node: ast.Return) -> Any:
        # Cas : return func(...)
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == self.func_name:
            new_values = [self.visit(a) for a in node.value.args]
            assign = ast.Assign(
                targets=[ast.Tuple(elts=[ast.Name(id=p, ctx=ast.Store()) for p in self.params], ctx=ast.Store())],
                value=ast.Tuple(elts=new_values, ctx=ast.Load())
            )
            # On renvoie une liste d'instructions qui remplacent le "return f(...)"
            return [assign, ast.Continue()]
        return node


def transform_tail_recursion(func: ast.FunctionDef) -> ast.FunctionDef:
    """Transforme la fonction récursive terminale en boucle while True."""
    params = [a.arg for a in func.args.args]
    transformer = TailTransformer(func.name, params)

    new_body: List[ast.stmt] = []
    for stmt in func.body:
        res = transformer.visit(stmt)
        if isinstance(res, list):
            new_body.extend(res)
        else:
            new_body.append(res)

    # Encapsule tout dans une boucle infinie
    loop = ast.While(test=ast.Constant(value=True), body=new_body, orelse=[])
    func.body = [loop]
    return func

# //////////////////////// PIPELINE & GENERATION DE CODE //////////////////////////
# Cette section :
#  - parcourt toutes les fonctions,
#  - applique l'optimisation si tail-recursive,
#  - régénère le code Python (ast.unparse),
#  - sauvegarde le nouveau fichier *transformed.py.

# ------------------------------------------------------------
# Étape 3 : Analyse + transformation + préparation de l'affichage
# ------------------------------------------------------------
def analyze_and_transform(source: str) -> Tuple[str, List[Tuple[str, bool]], List[Tuple[str, str, str]]]:
    """
    Retourne :
      - transformed_source : code complet transformé
      - info : liste [(nom, is_transformed)]
      - sections : liste [(nom, original_func_src, transformed_func_src)] pour les fonctions transformées
    """
    original_tree = ast.parse(source)
    attach_parents(original_tree)

    # Indexer les fonctions originales par (nom -> liste d'occurrences) pour retrouver le bon texte
    original_funcs_by_name: Dict[str, List[ast.FunctionDef]] = {}
    for node in original_tree.body:
        if isinstance(node, ast.FunctionDef):
            original_funcs_by_name.setdefault(node.name, []).append(node)

    new_tree = ast.parse(source)
    attach_parents(new_tree)

    info: List[Tuple[str, bool]] = []
    sections: List[Tuple[str, str, str]] = []

    # Tracker l'occurrence visitée par nom (si plusieurs définitions du même nom)
    seen_count: Dict[str, int] = {}

    for node in new_tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue

        name = node.name
        seen_count[name] = seen_count.get(name, 0) + 1

        if is_tail_recursive(node):
            info.append((name, True))

            # Récupérer le code original de CETTE occurrence
            occ_idx = seen_count[name] - 1
            orig_node = original_funcs_by_name.get(name, [])[occ_idx]
            original_src = ast.get_source_segment(source, orig_node) or f"def {name}(...):\n    <source indisponible>"

            # Transformer
            transform_tail_recursion(node)
            ast.fix_missing_locations(node)
            transformed_func_src = ast.unparse(node)

            sections.append((name, original_src, transformed_func_src))
        else:
            info.append((name, False))

    ast.fix_missing_locations(new_tree)
    transformed_source = ast.unparse(new_tree)
    return transformed_source, info, sections

# ------------------------------------------------------------
# Étape 4 : CLI
# ------------------------------------------------------------
def run_cli(argv: List[str]) -> None:
    if len(argv) < 2:
        print("Usage: python -m tr2loop <fichier_source.py> [--dry-run]")
        sys.exit(1)

    path = argv[1]
    dry_run = "--dry-run" in argv

    with open(path, encoding="utf-8") as f:
        source = f.read()

    transformed_source, info, sections = analyze_and_transform(source)


    # 1) AFFICHAGE PAR FONCTION (UNIQUEMENT CELLES TRANSFORMÉES)
    for name, original_src, transformed_func_src in sections:
        print("\n" + "/" * 95)
        print(f"Version originale ( {name} ) :".center(95, "/"))
        print("/" * 95)
        print(original_src)

        print("\n" + "/" * 95)
        print(f"Version transformée ( {name} ) :".center(95, "/"))
        print("/" * 95)
        print(transformed_func_src)

    # 2) Sauvegarde (si pas dry-run)
    if not dry_run:
        out_path = path.replace(".py", "_transformed.py")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(transformed_source)
        print(f"\n✅ Fichier sauvegardé sous : {out_path}")


if __name__ == "__main__":
    run_cli(sys.argv)