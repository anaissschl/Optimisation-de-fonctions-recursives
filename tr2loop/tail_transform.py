#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Transforme automatiquement les fonctions récursives terminales
en boucles while équivalentes (forme itérative).
"""

import ast      # Module standard pour manipuler l'AST (arbre syntaxique) de Python
import sys      # Pour récupérer les arguments de la ligne de commande
from typing import List, Tuple, Dict, Any  # Pour typer les fonctions (optionnel, mais plus clair)

# ///////////////////////// ANALYSE SEMANTIQUE (DETECTION) /////////////////////////
# Cette partie fait une analyse sémantique simplifiée pour décider si une
# fonction est récursive terminale ou non, à partir de l'AST.

# ------------------------------------------------------------
# Étape 1 : Détection — Récursion terminale ?
# ------------------------------------------------------------
def is_tail_recursive(func: ast.FunctionDef) -> bool:
    """
    Vérifie si une fonction contient une récursion terminale.

    Une fonction est considérée tail-récursive ici si :
      - elle s'appelle elle-même (auto-appels),
      - et chaque auto-appel apparaît directement dans un 'return f(...)'.
    """
    name = func.name        # On récupère le nom de la fonction (ex : "fact")
    found_call = False      # Flag pour savoir si on a trouvé au moins un auto-appel

    # ast.walk parcourt récursivement tous les nœuds du sous-arbre 'func'
    for node in ast.walk(func):
        # On cherche les nœuds qui sont des appels de fonction
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == name:
            # Ici on a un appel de la même fonction (auto-appel)
            # Vérifie que l'appel est directement retourné : 'return f(...)'
            parent = getattr(node, 'parent', None)  # On récupère le parent du nœud (ajouté par attach_parents)
            if not isinstance(parent, ast.Return):
                # Si le parent n'est PAS un 'Return', l'appel n'est pas en position terminale
                # Donc la fonction n'est pas tail-récursive au sens de notre critère simple
                return False
            # On a trouvé au moins un auto-appel en position terminale
            found_call = True

    # Si on a trouvé au moins un auto-appel terminal, la fonction est tail-récursive
    # (et on n'a pas rencontré d'auto-appel non terminal, sinon on aurait déjà retourné False)
    return found_call


def attach_parents(node: ast.AST) -> None:
    """
    Ajoute les liens 'parent' dans l’AST pour l’analyse.

    Par défaut, les nœuds ast.* n'ont pas de référence vers leur parent.
    On parcourt donc l'arbre et on ajoute un attribut 'parent' à chaque enfant.
    """
    # ast.iter_child_nodes renvoie tous les enfants directs du nœud
    for child in ast.iter_child_nodes(node):
        child.parent = node   # On ajoute un attribut 'parent' vers le nœud courant
        attach_parents(child) # Appel récursif pour descendre dans l'arbre


# ////////////////////////////// OPTIMISATION ////////////////////////////////
# À partir de l'analyse précédente, on transforme les fonctions récursives
# terminales en boucles while True équivalentes (élimination de récursion).

# ------------------------------------------------------------
# Étape 2 : Transformation
# ------------------------------------------------------------
class TailTransformer(ast.NodeTransformer):
    """
    Visiteur AST spécialisé qui remplace les 'return f(...)' par :

        (param1, param2, ...) = (nouvelle_valeur1, nouvelle_valeur2, ...)
        continue

    Autrement dit, on ne fait plus un appel récursif, on met à jour les
    paramètres et on recommence la boucle.
    """

    def __init__(self, func_name: str, params: List[str]):
        """
        Initialise le transformeur avec :

          - func_name : le nom de la fonction à transformer (ex : "fact")
          - params    : la liste de ses paramètres (ex : ["n", "acc"])
        """
        self.func_name = func_name  # Nom de la fonction cible
        self.params = params        # Liste des paramètres formels de la fonction

    def visit_Return(self, node: ast.Return) -> Any:
        """
        Visite un nœud 'Return'.

        Si on a 'return f(...)' où f est la fonction courante,
        on le transforme en :

            (p1, p2, ...) = (arg1, arg2, ...)
            continue

        Sinon, on laisse le return tel quel.
        """
        # Cas : return func(...)
        if (
            isinstance(node.value, ast.Call)             # La valeur retournée est un appel de fonction
            and isinstance(node.value.func, ast.Name)    # Le nom de la fonction appelée est un simple identifiant
            and node.value.func.id == self.func_name     # Cet identifiant correspond à la fonction courante
        ):
            # On visite chaque argument de l'appel récursif (par sécurité / cohérence)
            new_values = [self.visit(a) for a in node.value.args]

            # On crée une assignation multiple sous forme AST :
            # (param1, param2, ...) = (expr1, expr2, ...)
            assign = ast.Assign(
                targets=[  # Partie gauche de l'assignation
                    ast.Tuple(
                        elts=[ast.Name(id=p, ctx=ast.Store()) for p in self.params],  # p1, p2, ...
                        ctx=ast.Store(),
                    )
                ],
                value=ast.Tuple(  # Partie droite : les nouvelles valeurs des paramètres
                    elts=new_values,
                    ctx=ast.Load(),
                ),
            )

            # On renvoie une LISTE d'instructions qui remplace le "return f(...)"
            #  1) l'assignation des paramètres,
            #  2) un 'continue' pour recommencer la boucle while True
            return [assign, ast.Continue()]

        # Si ce n'est pas un 'return f(...)', on ne modifie pas ce nœud
        return node


def transform_tail_recursion(func: ast.FunctionDef) -> ast.FunctionDef:
    """
    Transforme la fonction récursive terminale en boucle while True.

    Idée :
      - on remplace tout le corps de la fonction par une boucle 'while True:',
      - les 'return valeur' de base restent des retours (ils quittent la fonction),
      - les 'return f(...)' sont transformés en mise à jour des paramètres + 'continue'.
    """
    # On récupère les noms de tous les paramètres positionnels de la fonction
    params = [a.arg for a in func.args.args]

    # On crée un transformeur spécialisé pour cette fonction
    transformer = TailTransformer(func.name, params)

    new_body: List[ast.stmt] = []  # Nouveau corps de la fonction (avant mise dans while True)

    # On parcourt chaque instruction du corps original
    for stmt in func.body:
        # On applique le transformeur sur le statement
        res = transformer.visit(stmt)

        # Si visit_Return a renvoyé une liste (cas return f(...)), on doit étendre
        if isinstance(res, list):
            new_body.extend(res)  # On ajoute assign + continue
        else:
            # Sinon, on ajoute simplement le statement transformé
            new_body.append(res)

    # On encapsule tout le nouveau corps dans une boucle infinie : while True:
    loop = ast.While(
        test=ast.Constant(value=True),  # condition True => boucle infinie
        body=new_body,                  # corps de la boucle
        orelse=[],                      # pas de 'else' sur la boucle
    )

    # On remplace le corps de la fonction par cette unique boucle
    func.body = [loop]

    # On renvoie la fonction transformée
    return func


# //////////////////////// PIPELINE & GENERATION DE CODE //////////////////////////
# Cette section :
#  - parcourt toutes les fonctions d'un fichier source,
#  - applique l'optimisation si la fonction est tail-récursive,
#  - régénère le code Python (ast.unparse),
#  - sauvegarde le nouveau fichier *transformed.py.

# ------------------------------------------------------------
# Étape 3 : Analyse + transformation + préparation de l'affichage
# ------------------------------------------------------------
def analyze_and_transform(
    source: str,
) -> Tuple[str, List[Tuple[str, bool]], List[Tuple[str, str, str]]]:
    """
    Analyse le code source et applique la transformation.

    Retourne :
      - transformed_source : code complet transformé (texte)
      - info : liste [(nom, is_transformed)] pour chaque fonction trouvée
      - sections : liste [(nom, original_func_src, transformed_func_src)]
                   pour les fonctions qui ont effectivement été transformées.
    """
    # On parse le code source original en AST
    original_tree = ast.parse(source)
    # On ajoute les pointeurs 'parent' sur cet AST (utile pour is_tail_recursive)
    attach_parents(original_tree)

    # On construit un dictionnaire : nom_de_fonction -> liste de nœuds FunctionDef
    # Cela permet de retrouver plus tard le bon texte source pour chaque occurrence
    original_funcs_by_name: Dict[str, List[ast.FunctionDef]] = {}
    for node in original_tree.body:  # On parcourt les nœuds au niveau du module
        if isinstance(node, ast.FunctionDef):  # On ne garde que les définitions de fonctions
            original_funcs_by_name.setdefault(node.name, []).append(node)

    # On reparse le même code pour avoir un AST "copie" sur lequel on va transformer
    new_tree = ast.parse(source)
    attach_parents(new_tree)  # On ajoute aussi les parents sur ce nouvel AST

    info: List[Tuple[str, bool]] = []          # Pour stocker (nom, transformée ?) pour toutes les fonctions
    sections: List[Tuple[str, str, str]] = []  # Pour stocker les versions texte (original / transformé)

    # Dictionnaire pour suivre combien de fois on a déjà vu une fonction d'un nom donné
    # (utile si plusieurs fonctions portent le même nom dans le fichier)
    seen_count: Dict[str, int] = {}

    # On parcourt les nœuds du nouveau module
    for node in new_tree.body:
        # On ne s'intéresse qu'aux définitions de fonctions
        if not isinstance(node, ast.FunctionDef):
            continue

        name = node.name  # Nom de la fonction en cours
        # On incrémente le compteur d'occurrences pour ce nom de fonction
        seen_count[name] = seen_count.get(name, 0) + 1

        # On teste si cette fonction est tail-récursive
        if is_tail_recursive(node):
            # On marque cette fonction comme transformée
            info.append((name, True))

            # On retrouve la bonne occurrence dans l'AST original
            occ_idx = seen_count[name] - 1  # index de l'occurrence (0-based)
            orig_node = original_funcs_by_name.get(name, [])[occ_idx]

            # On récupère exactement le texte source de cette définition de fonction
            original_src = (
                ast.get_source_segment(source, orig_node)
                or f"def {name}(...):\n    <source indisponible>"
            )

            # On applique la transformation tail-recursive sur le nœud de fonction
            transform_tail_recursion(node)
            # On corrige les informations de position (lineno, col_offset, etc.)
            ast.fix_missing_locations(node)
            # On régénère le code Python de la fonction transformée
            transformed_func_src = ast.unparse(node)

            # On ajoute cette paire (original, transformé) à la liste des sections
            sections.append((name, original_src, transformed_func_src))
        else:
            # Fonction non tail-récursive (ou non récursive) → pas de transformation
            info.append((name, False))

    # On corrige les positions sur tout l'AST final
    ast.fix_missing_locations(new_tree)
    # On régénère le code complet (tout le module) sous forme de texte Python
    transformed_source = ast.unparse(new_tree)

    # On renvoie :
    #  - le code complet transformé,
    #  - la liste des infos par fonction,
    #  - et les sections détaillées pour l'affichage
    return transformed_source, info, sections


# ------------------------------------------------------------
# Étape 4 : CLI (interface ligne de commande)
# ------------------------------------------------------------
def run_cli(argv: List[str]) -> None:
    """
    Point d'entrée lorsqu'on lance le module en ligne de commande.

    Usage :
        python -m tr2loop <fichier_source.py> [--dry-run]

    - <fichier_source.py> : chemin du fichier à analyser/transformer
    - --dry-run           : si présent, on n'écrit pas le fichier *_transformed.py
    """
    # On vérifie qu'au moins un argument (le chemin du fichier) a été donné
    if len(argv) < 2:
        print("Usage: python -m tr2loop <fichier_source.py> [--dry-run]")
        sys.exit(1)

    path = argv[1]                 # Chemin du fichier source à traiter
    dry_run = "--dry-run" in argv  # True si l'utilisateur a passé l'option --dry-run

    # On lit le contenu du fichier source en mémoire
    with open(path, encoding="utf-8") as f:
        source = f.read()

    # On lance l'analyse + transformation sur ce code source
    transformed_source, info, sections = analyze_and_transform(source)

    # ---- (Optionnel) On pourrait afficher ici un récapitulatif pour TOUTES les fonctions via 'info'
    # Par exemple :
    # for name, is_transformed in info:
    #     if is_transformed:
    #         print(f" Fonction '{name}' transformée (récursion terminale).")
    #     else:
    #         print(f"ℹ Fonction '{name}' non transformée (non tail-récursive).")

    # 1) AFFICHAGE PAR FONCTION (UNIQUEMENT CELLES TRANSFORMÉES)
    for name, original_src, transformed_func_src in sections:
        # Séparateur visuel
        print("\n" + "/" * 95)
        print(f"Version originale ( {name} ) :".center(95, "/"))
        print("/" * 95)
        # On affiche le code original de la fonction
        print(original_src)

        print("\n" + "/" * 95)
        print(f"Version transformée ( {name} ) :".center(95, "/"))
        print("/" * 95)
        # On affiche le code transformé de la fonction
        print(transformed_func_src)

    # 2) Sauvegarde du fichier complet transformé (si on n'est pas en dry-run)
    if not dry_run:
        # On construit le chemin du nouveau fichier : on remplace ".py" par "_transformed.py"
        out_path = path.replace(".py", "_transformed.py")
        # On écrit le code transformé dans ce nouveau fichier
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(transformed_source)
        # On confirme à l'utilisateur où le fichier a été sauvegardé
        print(f"\n Fichier sauvegardé sous : {out_path}")


# Si le fichier est exécuté directement (et non importé), on lance run_cli
if __name__ == "__main__":
    run_cli(sys.argv)