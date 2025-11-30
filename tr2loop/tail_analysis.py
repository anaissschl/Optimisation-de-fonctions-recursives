#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
tail_analysis.py
----------------
Étape 2 : Détection des fonctions récursives terminales via l'AST Python.

Objectifs :
  - Marquer les fonctions récursives (auto-appels).
  - Vérifier la "position terminale" : un auto-appel est autorisé
    uniquement s'il est directement retourné (pattern: `return f(...)`).
  - Vérifier que tous les chemins d'exécution d'une fonction se terminent
    par un `return` (condition pratique pour raisonner simplement sur le tail-call).

Utilisation :
  python tail_analysis.py chemin/vers/fichier_source.py
"""

from __future__ import annotations
import ast
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# --------------------------------------------------------------------
# Résultat d'analyse par fonction
# --------------------------------------------------------------------
@dataclass
class FunctionAnalysis:
    name: str
    is_recursive: bool
    is_tail_recursive: bool
    reasons: List[str] = field(default_factory=list)
    total_self_calls: int = 0


# ///////////////////////////// ANALYSE SEMANTIQUE ////////////////////////////////
# Cette section réalise une analyse sémantique structurée :
#  - détection des auto-appels (récursivité),
#  - vérification de la position terminale (return f(...)),
#  - vérification que tous les chemins d'exécution mènent à un return.

# --------------------------------------------------------------------
# Outils d'analyse structurée des blocs
# --------------------------------------------------------------------
@dataclass
class BlockCheck:
    """Résumé d'analyse d'un bloc de statements."""
    ok: bool                    # True si aucun problème (self-call hors tail, etc.)
    always_returns: bool        # True si TOUS les chemins retournent (utile pour la simplicité de l'analyse)
    self_calls_in_tail: int     # Nombre d'auto-appels détectés en position terminale
    self_calls_non_tail: int    # Nombre d'auto-appels détectés hors position terminale
    reasons: List[str] = field(default_factory=list)


class TailRecursionAnalyzer:
    """
    Analyse une FunctionDef `f` pour détecter :
      - présence d'auto-appels,
      - conformité "tail recursion" (tous les auto-appels doivent être `return f(...)`),
      - et (heuristique V1) que chaque chemin se termine par un `return`.
    """

    def __init__(self, func: ast.FunctionDef):
        self.func = func
        self.fname = func.name

    # -------------------------
    # API principale
    # -------------------------
    def analyze(self) -> FunctionAnalysis:
        block = self._check_block(self.func.body, in_loop=False)

        is_recursive = (block.self_calls_in_tail + block.self_calls_non_tail) > 0
        is_tail = (
            is_recursive
            and block.ok
            and block.self_calls_non_tail == 0
            and block.always_returns
        )

        reasons = list(block.reasons)
        if is_recursive and block.self_calls_non_tail > 0:
            reasons.append("Auto-appel détecté hors position terminale (pas de `return f(...)`).")
        if not block.always_returns:
            reasons.append("Tous les chemins n'aboutissent pas à un `return` (analyse tail simplifiée échoue).")
        if not is_recursive:
            reasons.append("Pas d'auto-appel détecté (fonction non récursive).")

        return FunctionAnalysis(
            name=self.fname,
            is_recursive=is_recursive,
            is_tail_recursive=is_tail,
            reasons=reasons,
            total_self_calls=block.self_calls_in_tail + block.self_calls_non_tail,
        )

    # -------------------------
    # Analyse d'un bloc (liste de statements)
    # -------------------------
    def _check_block(self, stmts: List[ast.stmt], *, in_loop: bool) -> BlockCheck:
        """
        Analyse séquentielle d'un bloc :
          - si on rencontre un `return`, les statements suivants sont inaccessibles (on s'arrête).
          - on agrège ok / returns / compte des self-calls.
        """
        ok = True
        always_returns = False
        tail_calls = 0
        non_tail_calls = 0
        reasons: List[str] = []

        # Flag : ce bloc termine-t-il sur un return sur *tous* les chemins ?
        block_returns = False

        i = 0
        while i < len(stmts):
            s = stmts[i]

            # Cas 1 : Return
            if isinstance(s, ast.Return):
                # On analyse l'expression du return (pour voir si c'est un self-call direct)
                tail_ok, self_in_return, self_in_non_tail, msgs = self._analyze_return_expr(s.value)
                ok = ok and tail_ok
                tail_calls += self_in_return
                non_tail_calls += self_in_non_tail
                reasons.extend(msgs)
                block_returns = True
                # Tout ce qui suit un `return` est inatteignable
                break

            # Cas 2 : If ... (il faut que chaque branche se termine correctement)
            elif isinstance(s, ast.If):
                # Corps du if
                then_res = self._check_block(s.body, in_loop=in_loop)
                else_body = s.orelse or []
                else_res = self._check_block(else_body, in_loop=in_loop)

                ok = ok and then_res.ok and else_res.ok
                tail_calls += then_res.self_calls_in_tail + else_res.self_calls_in_tail
                non_tail_calls += then_res.self_calls_non_tail + else_res.self_calls_non_tail
                reasons.extend(then_res.reasons)
                reasons.extend(else_res.reasons)

                # Pour garantir la simplicité : if/else doivent *tous deux* mener à un return
                if then_res.always_returns and else_res.always_returns:
                    block_returns = True
                    # on peut s'arrêter ici si le if est terminal
                    # sinon, on continue (mais en pratique, le style qu'on attend est terminal)
                    # Nous choisissons de stopper : statements suivants seraient inaccessibles si if/else exhaustif
                    break
                else:
                    # Le chemin ne garantit pas un return -> la fonction pourrait "tomber" plus loin
                    pass

            # Cas 3 : Boucles / autres statements
            elif isinstance(s, (ast.While, ast.For, ast.Try, ast.With, ast.Match)):
                # Hors du scope V1 : on reste conservateur.
                reasons.append(f"Structure {s.__class__.__name__} détectée : analyse V1 conservatrice (peut empêcher la preuve 'always returns').")
                # On cherche des self-calls arbitraires à l'intérieur (non tail par défaut)
                sc_tail, sc_nontail = self._scan_for_self_calls_generic(s)
                tail_calls += sc_tail
                non_tail_calls += sc_nontail
                # On ne peut pas affirmer always_returns pour ce bloc via heuristique simple.
                ok = ok and (sc_nontail == 0)

            else:
                # Statements génériques (Assign, Expr, etc.) : vérifier s'ils contiennent un self-call
                sc_tail, sc_nontail = self._scan_for_self_calls_generic(s)
                tail_calls += sc_tail
                non_tail_calls += sc_nontail
                if sc_nontail > 0:
                    ok = False
                    reasons.append(f"Auto-appel à '{self.fname}' trouvé hors `return` (statement {s.__class__.__name__}).")

            i += 1

        # always_returns = True si on a rencontré un return "terminal" pour le bloc
        always_returns = block_returns
        return BlockCheck(
            ok=ok,
            always_returns=always_returns,
            self_calls_in_tail=tail_calls,
            self_calls_non_tail=non_tail_calls,
            reasons=reasons,
        )

    # -------------------------
    # Analyse d'un `return <expr>`
    # -------------------------
    def _analyze_return_expr(self, value: Optional[ast.AST]) -> Tuple[bool, int, int, List[str]]:
        """
        Retourne (ok, self_calls_in_tail, self_calls_non_tail, reasons).
        ok = False si l'expression de retour contient un self-call non direct.
        """
        reasons: List[str] = []
        if value is None:
            # return None
            return True, 0, 0, reasons

        # Retour direct : return f(...)? (self-call terminal)
        if isinstance(value, ast.Call) and self._is_self_call(value.func):
            # ex: return f(n-1, acc*n) -> TAIL CALL
            return True, 1, 0, reasons

        # Sinon, si l'expression contient un self-call *imbriqué* (ex: return 1 + f(...))
        # alors ce n'est PAS terminal.
        has_self_inside = self._contains_self_call(value)
        if has_self_inside:
            reasons.append("Self-call détecté *dans* l'expression de retour (ex: `return g(f(...))` ou `x + f(...)`) -> non terminal.")
            return False, 0, 1, reasons

        # Return "base" sans self-call : OK
        return True, 0, 0, reasons

    # -------------------------
    # Helpers : détection générique de self-calls
    # -------------------------
    def _is_self_call(self, func_node: ast.AST) -> bool:
        """Vrai si `func_node` correspond à l'identifiant de la fonction courante."""
        return isinstance(func_node, ast.Name) and func_node.id == self.fname

    def _contains_self_call(self, node: ast.AST) -> bool:
        """Vrai si un sous-arbre contient un appel à la fonction courante."""
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call) and self._is_self_call(sub.func):
                return True
        return False

    def _scan_for_self_calls_generic(self, node: ast.AST) -> Tuple[int, int]:
        """
        Scrute un statement/expr générique :
          - si on trouve `f(...)` sous forme d'expression "libre" (Expr) ou dans un Assign, etc.
            => ce sont des self-calls *non terminaux* (hors `return`).
          - si on trouve `return f(...)`, ce cas est traité ailleurs.
        Renvoie (self_calls_in_tail, self_calls_non_tail).
        """
        tail = 0
        non_tail = 0
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call) and self._is_self_call(sub.func):
                non_tail += 1
        return tail, non_tail


# --------------------------------------------------------------------
# Utilities : analyse d'un Module et interface CLI
# --------------------------------------------------------------------
def analyze_source(source: str) -> List[FunctionAnalysis]:
    tree = ast.parse(source)
    results: List[FunctionAnalysis] = []

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            analyzer = TailRecursionAnalyzer(node)
            res = analyzer.analyze()
            results.append(res)
    return results


def main(argv: List[str]) -> None:
    if len(argv) != 2:
        print("Usage : python tail_analysis.py chemin/vers/fichier_source.py")
        sys.exit(1)

    path = argv[1]
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()

    analyses = analyze_source(src)

    if not analyses:
        print("Aucune fonction trouvée au niveau supérieur.")
        return

    print("=" * 68)
    print(f"Analyse tail-recursion du fichier : {path}")
    print("=" * 68)
    for a in analyses:
        status = (
            "TAIL-RECURSIVE ✅" if a.is_tail_recursive
            else "RECURSIVE (non terminale) ⚠️" if a.is_recursive
            else "NON RECURSIVE ℹ️"
        )
        print(f"\n• Function `{a.name}` -> {status}")
        print(f"  - auto-appels détectés : {a.total_self_calls}")
        if a.reasons:
            for r in a.reasons:
                print(f"  - raison: {r}")

if __name__ == "__main__":
    main(sys.argv)
