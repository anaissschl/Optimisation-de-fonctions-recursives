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

# Importations nécessaires pour le script :

# from __future__ import annotations
#   Permet d'utiliser les annotations de type sous forme de chaînes de caractères
#   même avant que les classes ou fonctions soient définies.
#   Utile pour les types qui font référence à eux-mêmes ou à d'autres classes non encore définies.

# import ast
#   Module pour analyser le code Python en AST (Abstract Syntax Tree),
#   ce qui permet d'examiner la structure du code sans l'exécuter.

# import sys
#   Module pour accéder aux arguments de la ligne de commande et aux fonctionnalités système.

# from dataclasses import dataclass, field
#   Permet de créer des classes simples pour stocker des données (data containers),
#   avec `field` pour définir des valeurs par défaut comme des listes vides.

# from typing import List, Optional, Tuple
#   Fournit des annotations de type pour préciser :
#     List  -> liste d'éléments d'un type donné
#     Optional -> un type ou None
#     Tuple -> un ensemble de valeurs de types définis

from __future__ import annotations
import ast
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# --------------------------------------------------------------------
# Résultat d'analyse par fonction
# --------------------------------------------------------------------

# Classe pour stocker le résultat de l'analyse d'une fonction :
# - name : nom de la fonction
# - is_recursive : True si la fonction s'appelle elle-même
# - is_tail_recursive : True si tous les appels récursifs sont en position terminale
# - reasons : liste des explications/raisons détectées
# - total_self_calls : nombre total d'appels récursifs détectés
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


# Classe principale pour analyser une fonction Python et détecter la récursion terminale.
class TailRecursionAnalyzer:
    """
    Analyse une fonction pour :
      - détecter les appels à elle-même (récursivité),
      - vérifier si ces appels sont en position terminale (`return f(...)`),
      - et vérifier si tous les chemins se terminent par un return (heuristique simple).
    """

    def __init__(self, func: ast.FunctionDef):
        # Stocke le nœud AST de la fonction à analyser
        self.func = func
        # Stocke le nom de la fonction pour identifier les auto-appels
        self.fname = func.name

    # Méthode principale pour lancer l'analyse
    def analyze(self) -> FunctionAnalysis:
        # Analyse le corps de la fonction et retourne un résumé des auto-appels et des retours
        block = self._check_block(self.func.body, in_loop=False)

        # La fonction est récursive si elle contient au moins un appel à elle-même
        is_recursive = (block.self_calls_in_tail + block.self_calls_non_tail) > 0
        # La fonction est tail-recursive si tous les appels sont en position terminale et que tous les chemins retournent
        is_tail = (
            is_recursive
            and block.ok
            and block.self_calls_non_tail == 0
            and block.always_returns
        )

        # Copie des raisons détectées lors de l'analyse du bloc
        reasons = list(block.reasons)
        if is_recursive and block.self_calls_non_tail > 0:
            reasons.append("Auto-appel détecté hors position terminale (pas de `return f(...)`).")
        if not block.always_returns:
            reasons.append("Tous les chemins n'aboutissent pas à un `return` (analyse tail simplifiée échoue).")
        if not is_recursive:
            reasons.append("Pas d'auto-appel détecté (fonction non récursive).")

        # Retourne un objet FunctionAnalysis résumant l'analyse
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
    
    # Méthode interne pour analyser un bloc de code (liste de statements) dans la fonction
    # Elle vérifie la présence d'appels récursifs et si le bloc se termine toujours par un return
    def _check_block(self, stmts: List[ast.stmt], *, in_loop: bool) -> BlockCheck:
        """
        Parcourt les statements du bloc :
        - Si un 'return' est rencontré, tout ce qui suit est inatteignable.
        - Compte les appels à soi-même (tail ou non tail).
        - Agrège les informations pour déterminer si le bloc est correct pour une tail recursion.
        """
        ok = True                 # True si aucun self-call non-terminal trouvé
        always_returns = False    # True si tous les chemins du bloc finissent par un return
        tail_calls = 0            # Nombre d'appels récursifs en position terminale
        non_tail_calls = 0        # Nombre d'appels récursifs hors return
        reasons: List[str] = []   # Explications/raisons pour les problèmes détectés

        block_returns = False     # Flag local pour savoir si le bloc se termine par un return

        i = 0
        while i < len(stmts):
            s = stmts[i]

            # Cas 1 : statement Return
            if isinstance(s, ast.Return):
                # Analyse l'expression du return pour détecter un self-call direct
                tail_ok, self_in_return, self_in_non_tail, msgs = self._analyze_return_expr(s.value)
                ok = ok and tail_ok
                tail_calls += self_in_return
                non_tail_calls += self_in_non_tail
                reasons.extend(msgs)
                block_returns = True
                # Tout ce qui suit le return est inatteignable
                break

            # Cas 2 : statement If
            elif isinstance(s, ast.If):
                # Analyse le corps du if et du else
                then_res = self._check_block(s.body, in_loop=in_loop)
                else_body = s.orelse or []
                else_res = self._check_block(else_body, in_loop=in_loop)

                # Agrège les résultats
                ok = ok and then_res.ok and else_res.ok
                tail_calls += then_res.self_calls_in_tail + else_res.self_calls_in_tail
                non_tail_calls += then_res.self_calls_non_tail + else_res.self_calls_non_tail
                reasons.extend(then_res.reasons)
                reasons.extend(else_res.reasons)

                # Pour être simple, les deux branches doivent se terminer par un return
                if then_res.always_returns and else_res.always_returns:
                    block_returns = True
                    break  # Statements suivants inaccessibles si if/else exhaustif

            # Cas 3 : Boucles, try, with, match, etc.
            elif isinstance(s, (ast.While, ast.For, ast.Try, ast.With, ast.Match)):
                # Analyse conservatrice : impossible de garantir always_returns
                reasons.append(f"Structure {s.__class__.__name__} détectée : analyse V1 conservatrice")
                sc_tail, sc_nontail = self._scan_for_self_calls_generic(s)
                tail_calls += sc_tail
                non_tail_calls += sc_nontail
                ok = ok and (sc_nontail == 0)

            # Cas 4 : statements génériques (Assign, Expr, etc.)
            else:
                sc_tail, sc_nontail = self._scan_for_self_calls_generic(s)
                tail_calls += sc_tail
                non_tail_calls += sc_nontail
                if sc_nontail > 0:
                    ok = False
                    reasons.append(f"Auto-appel à '{self.fname}' trouvé hors `return` (statement {s.__class__.__name__}).")

            i += 1

        # Détermine si le bloc retourne toujours quelque chose
        always_returns = block_returns

        # Retourne un résumé de l'analyse pour ce bloc
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

    # Analyse l'expression d'un return pour détecter un self-call
    # Renvoie un tuple : (ok, self_calls_in_tail, self_calls_non_tail, reasons)
    # - ok : False si l'appel récursif n'est pas directement dans le return
    # - self_calls_in_tail : nombre de self-calls en position terminale
    # - self_calls_non_tail : nombre de self-calls non terminaux
    # - reasons : explications si problème détecté
    def _analyze_return_expr(self, value: Optional[ast.AST]) -> Tuple[bool, int, int, List[str]]:
        reasons: List[str] = []

        # Cas return sans valeur (return None)
        if value is None:
            return True, 0, 0, reasons

        # Cas return f(...) direct -> tail call
        if isinstance(value, ast.Call) and self._is_self_call(value.func):
            return True, 1, 0, reasons

        # Cas return avec self-call imbriqué (ex: return 1 + f(...)) -> non terminal
        has_self_inside = self._contains_self_call(value)
        if has_self_inside:
            reasons.append("Self-call détecté dans l'expression de retour -> non terminal")
            return False, 0, 1, reasons

        # Return sans self-call -> OK
        return True, 0, 0, reasons


    # -------------------------
    # Helpers : détection générique de self-calls
    # -------------------------

    # Vérifie si un nœud AST correspond à un appel à la fonction courante
    def _is_self_call(self, func_node: ast.AST) -> bool:
        # True si le nœud est un identifiant et que son nom correspond à celui de la fonction analysée
        return isinstance(func_node, ast.Name) and func_node.id == self.fname

    # Vérifie si un sous-arbre AST contient un appel à la fonction courante
    def _contains_self_call(self, node: ast.AST) -> bool:
        # Parcourt tous les nœuds du sous-arbre
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call) and self._is_self_call(sub.func):
                return True
        return False

    # Recherche des self-calls dans un statement générique (Assign, Expr, boucle, etc.)
    # Renvoie (self_calls_in_tail, self_calls_non_tail)
    # Ici, tous les appels trouvés sont considérés comme non terminaux
    def _scan_for_self_calls_generic(self, node: ast.AST) -> Tuple[int, int]:
        tail = 0
        non_tail = 0
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call) and self._is_self_call(sub.func):
                non_tail += 1  # Tous les appels détectés ici sont hors return
        return tail, non_tail



# --------------------------------------------------------------------
# Utilities : analyse d'un Module et interface CLI
# --------------------------------------------------------------------
def analyze_source(source: str) -> List[FunctionAnalysis]:
    tree = ast.parse(source)
    # Le code lit le fichier source Python.
    # Il le transforme en AST (Abstract Syntax Tree) → une structure arborescente qui représente le code Python.
    # Chaque nœud de l’arbre correspond à un élément du code : fonction, if, return, boucle, etc.

    results: List[FunctionAnalysis] = []

    # Le script prend chaque fonction définie au niveau supérieur du fichier.
    # Pour chaque fonction, il crée un objet TailRecursionAnalyzer.
    # La méthode analyze() va déterminer si la fonction est récursive et/ou tail-recursive.
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
        # Détermine le statut de la fonction selon l'analyse
        status = (
            "TAIL-RECURSIVE " if a.is_tail_recursive
            else "RECURSIVE (non terminale) " if a.is_recursive
            else "NON RECURSIVE "
        )
        print(f"\n• Function `{a.name}` -> {status}")
        print(f"  - auto-appels détectés : {a.total_self_calls}")
        # Affiche les raisons si des problèmes ou avertissements sont présents
        if a.reasons:
            for r in a.reasons:
                print(f"  - raison: {r}")

# Si le script est exécuté directement, lance la fonction main
if __name__ == "__main__":
    main(sys.argv)

