# -*- coding: utf-8 -*-
"""
Exemples de fonctions récursives terminales (tail recursion) en Python.

⚠️ Avertissement important :
Python N'APPLIQUE PAS l'optimisation des appels terminaux (TCO).
Ces exemples sont pédagogiques pour montrer le schéma « accumulateur »
qui rend une fonction *structurellement* terminale, mais ils n'évitent pas
la limite de profondeur de récursion (~1000 par défaut). Pour des entrées
très grandes, préférez une version itérative… ou utilisez une technique
de *trampoline* fournie plus bas.

Chaque fonction ci‑dessous est :
  - purement récursive (pas de boucle), et
  - la dernière opération de la branche récursive est l’appel récursif.

Les doctests peuvent être lancés avec :
    python -m doctest -v tail_recursion_examples.py
"""

from __future__ import annotations
from typing import Callable, Iterable, List, Optional, Sequence, Tuple, TypeVar, Any

T = TypeVar("T")
U = TypeVar("U")

# ---------------------------------------------------------------------------
# 0) Petit utilitaire de trampoline (optionnel)
# ---------------------------------------------------------------------------

class Bounce:
    """Type représentant un *rebond* pour le trampoline."""
    __slots__ = ("fn", "args", "kwargs")
    def __init__(self, fn: Callable, *args, **kwargs):
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

def bounce(fn: Callable, *args, **kwargs) -> Bounce:
    return Bounce(fn, *args, **kwargs)

def trampoline(thunk: Callable[..., Any], *args, **kwargs) -> Any:
    """Exécute des fonctions terminales écrites en style *bounce* sans déborder la pile.

    Exemple :
        >>> trampoline(factorielle_tr_bounce, 10)
        3628800
    """
    result = thunk(*args, **kwargs)
    while isinstance(result, Bounce):
        result = result.fn(*result.args, **result.kwargs)
    return result

# ---------------------------------------------------------------------------
# 1) Factorielle (classique) – terminale via accumulateur
# ---------------------------------------------------------------------------

def factorielle_tr(n: int, acc: int = 1) -> int:
    """Factorielle en récursion terminale.

    >>> factorielle_tr(0)
    1
    >>> factorielle_tr(5)
    120
    """
    if n < 0:
        raise ValueError("n doit être >= 0")
    if n == 0:
        return acc
    return factorielle_tr(n - 1, acc * n)

# Variante *bounce* compatible trampoline
def factorielle_tr_bounce(n: int, acc: int = 1):
    if n < 0:
        raise ValueError("n doit être >= 0")
    if n == 0:
        return acc
    return bounce(factorielle_tr_bounce, n - 1, acc * n)

# ---------------------------------------------------------------------------
# 2) Fibonacci (linéaire) – terminale via deux accumulateurs
# ---------------------------------------------------------------------------

def fibonacci_tr(n: int, a: int = 0, b: int = 1) -> int:
    """Fibonacci (F(0)=0, F(1)=1) en forme terminale.

    >>> fibonacci_tr(0)
    0
    >>> fibonacci_tr(1)
    1
    >>> fibonacci_tr(10)
    55
    """
    if n < 0:
        raise ValueError("n doit être >= 0")
    if n == 0:
        return a
    if n == 1:
        return b
    return fibonacci_tr(n - 1, b, a + b)

def fibonacci_tr_bounce(n: int, a: int = 0, b: int = 1):
    if n < 0:
        raise ValueError("n doit être >= 0")
    if n == 0:
        return a
    if n == 1:
        return b
    return bounce(fibonacci_tr_bounce, n - 1, b, a + b)

# ---------------------------------------------------------------------------
# 3) PGCD (Euclide) – appel terminal direct
# ---------------------------------------------------------------------------

def pgcd_tr(a: int, b: int) -> int:
    """Plus grand commun diviseur via l'algorithme d'Euclide.

    >>> pgcd_tr(54, 24)
    6
    """
    if b == 0:
        return abs(a)
    return pgcd_tr(b, a % b)

# ---------------------------------------------------------------------------
# 4) Puissance entière – exponentiation naïve terminale
# ---------------------------------------------------------------------------

def puissance_tr(base: int, exp: int, acc: int = 1) -> int:
    """Calcule base**exp en forme terminale (naïf).

    >>> puissance_tr(2, 10)
    1024
    >>> puissance_tr(3, 0)
    1
    """
    if exp < 0:
        raise ValueError("exp doit être >= 0")
    if exp == 0:
        return acc
    return puissance_tr(base, exp - 1, acc * base)

# ---------------------------------------------------------------------------
# 5) Somme / Produit / Longueur d'une liste – accumulateurs
# ---------------------------------------------------------------------------

def somme_tr(xs: Sequence[int], i: int = 0, acc: int = 0) -> int:
    """Somme des éléments.

    >>> somme_tr([1,2,3,4])
    10
    """
    if i == len(xs):
        return acc
    return somme_tr(xs, i + 1, acc + xs[i])

def produit_tr(xs: Sequence[int], i: int = 0, acc: int = 1) -> int:
    """Produit des éléments.

    >>> produit_tr([1,2,3,4])
    24
    """
    if i == len(xs):
        return acc
    return produit_tr(xs, i + 1, acc * xs[i])

def longueur_tr(xs: Sequence[T], i: int = 0, acc: int = 0) -> int:
    """Longueur d'une séquence.

    >>> longueur_tr("bonjour")
    7
    """
    if i == len(xs):
        return acc
    return longueur_tr(xs, i + 1, acc + 1)

# ---------------------------------------------------------------------------
# 6) Maximum d'une liste – accumulateur courant
# ---------------------------------------------------------------------------

def maximum_tr(xs: Sequence[int], i: int = 0, current: Optional[int] = None) -> int:
    """Maximum en récursion terminale.

    >>> maximum_tr([3, 9, 2, 7])
    9
    """
    if i == len(xs):
        if current is None:
            raise ValueError("liste vide")
        return current
    x = xs[i]
    new_current = x if current is None or x > current else current
    return maximum_tr(xs, i + 1, new_current)

# ---------------------------------------------------------------------------
# 7) Inversion d'une liste – accumulateur liste (attention à la copie)
# ---------------------------------------------------------------------------

def inverse_tr(xs: Sequence[T], i: int = 0, acc: Optional[List[T]] = None) -> List[T]:
    """Inverse une liste en forme terminale.

    >>> inverse_tr([1,2,3])
    [3, 2, 1]
    """
    if acc is None:
        acc = []
    if i == len(xs):
        return acc
    acc.insert(0, xs[i])  # O(n) par insertion en tête (pédagogique)
    return inverse_tr(xs, i + 1, acc)

# Variante plus efficace en accumulant et retournant à la fin
def inverse_tr2(xs: Sequence[T], i: int = 0, acc: Optional[List[T]] = None) -> List[T]:
    if acc is None:
        acc = []
    if i == len(xs):
        return acc
    acc.append(xs[len(xs) - 1 - i])
    return inverse_tr2(xs, i + 1, acc)

# ---------------------------------------------------------------------------
# 8) map / filter – en style terminal
# ---------------------------------------------------------------------------

def map_tr(f: Callable[[T], U], xs: Sequence[T], i: int = 0, acc: Optional[List[U]] = None) -> List[U]:
    """Version terminale de map.

    >>> map_tr(lambda x: x*x, [1,2,3])
    [1, 4, 9]
    """
    if acc is None:
        acc = []
    if i == len(xs):
        return acc
    acc.append(f(xs[i]))
    return map_tr(f, xs, i + 1, acc)

def filter_tr(pred: Callable[[T], bool], xs: Sequence[T], i: int = 0, acc: Optional[List[T]] = None) -> List[T]:
    """Version terminale de filter.

    >>> filter_tr(lambda x: x%2==0, [1,2,3,4])
    [2, 4]
    """
    if acc is None:
        acc = []
    if i == len(xs):
        return acc
    x = xs[i]
    if pred(x):
        acc.append(x)
    return filter_tr(pred, xs, i + 1, acc)

# ---------------------------------------------------------------------------
# 9) Recherche dichotomique – appel terminal
# ---------------------------------------------------------------------------

def recherche_binaire_tr(
    arr: Sequence[int], cible: int, gauche: int = 0, droite: Optional[int] = None
) -> int:
    """Recherche dichotomique (terminal). Renvoie l'indice ou -1.

    >>> recherche_binaire_tr([1,3,5,7,9], 7)
    3
    >>> recherche_binaire_tr([1,3,5,7,9], 2)
    -1
    """
    if droite is None:
        droite = len(arr) - 1
    if gauche > droite:
        return -1
    milieu = (gauche + droite) // 2
    x = arr[milieu]
    if x == cible:
        return milieu
    if x < cible:
        return recherche_binaire_tr(arr, cible, milieu + 1, droite)
    else:
        return recherche_binaire_tr(arr, cible, gauche, milieu - 1)

# ---------------------------------------------------------------------------
# 10) Aplatissement simple de liste imbriquée (niveau arbitraire)
#     Variante terminale avec *pile explicite* (pas 100% pur récursif)
# ---------------------------------------------------------------------------

def flatten_tr(nested: Sequence[Any], i: int = 0, acc: Optional[List[Any]] = None) -> List[Any]:
    """Aplatissement d'une structure de listes (seulement list/tuple).

    >>> flatten_tr([1, [2, (3, 4)], 5])
    [1, 2, 3, 4, 5]
    """
    if acc is None:
        acc = []
    if i == len(nested):
        return acc
    x = nested[i]
    if isinstance(x, (list, tuple)):
        # On traite *d'abord* x (en la remplaçant par ses éléments) – terminalité préservée
        return flatten_tr(list(x) + list(nested[i+1:]), 0, acc)
    else:
        acc.append(x)
        return flatten_tr(nested, i + 1, acc)

# ---------------------------------------------------------------------------
# 11) Somme des chiffres (accumulateur)
# ---------------------------------------------------------------------------

def somme_chiffres_tr(n: int, acc: int = 0) -> int:
    """Somme des chiffres d'un entier non négatif.

    >>> somme_chiffres_tr(0)
    0
    >>> somme_chiffres_tr(942)
    15
    """
    if n < 0:
        raise ValueError("n doit être >= 0")
    if n == 0:
        return acc
    return somme_chiffres_tr(n // 10, acc + (n % 10))

# ---------------------------------------------------------------------------
# 12) Conversion de base (accumulateur liste de chiffres)
# ---------------------------------------------------------------------------

def en_base_tr(n: int, base: int, acc: Optional[List[int]] = None) -> List[int]:
    """Convertit n en une liste de chiffres dans la base donnée (2..36).

    >>> en_base_tr(13, 2)
    [1, 1, 0, 1]
    >>> en_base_tr(255, 16)
    [15, 15]
    """
    if acc is None:
        acc = []
    if base < 2 or base > 36:
        raise ValueError("base doit être dans [2, 36]")
    if n < 0:
        raise ValueError("n doit être >= 0")
    if n < base:
        acc.insert(0, n)
        return acc
    acc.insert(0, n % base)
    return en_base_tr(n // base, base, acc)

# ---------------------------------------------------------------------------
# 13) Collatz – nombre d'étapes jusqu'à 1
# ---------------------------------------------------------------------------

def collatz_steps_tr(n: int, acc: int = 0) -> int:
    """Nombre d'étapes de la suite de Collatz pour atteindre 1.

    >>> collatz_steps_tr(1)
    0
    >>> collatz_steps_tr(6)
    8
    """
    if n <= 0:
        raise ValueError("n doit être > 0")
    if n == 1:
        return acc
    if n % 2 == 0:
        return collatz_steps_tr(n // 2, acc + 1)
    else:
        return collatz_steps_tr(3 * n + 1, acc + 1)

# ---------------------------------------------------------------------------
# 14) Partition d'un entier (comptage simple) – terminal via accumulateurs
#     (Version limitée : partitions en nombres <= k)
# ---------------------------------------------------------------------------

def partitions_count_tr(n: int, k: int, acc: int = 0) -> int:
    """Compte le nombre de partitions de n avec des parts <= k.

    >>> partitions_count_tr(5, 5)
    7
    """
    if n == 0:
        return acc + 1
    if n < 0 or k == 0:
        return acc
    # p(n,k) = p(n, k-1) + p(n-k, k)
    # Terminalité en accumulant le résultat de la première branche dans acc
    return partitions_count_tr(n, k - 1, partitions_count_tr(n - k, k, acc))

# ---------------------------------------------------------------------------
# 15) Parcours de chaîne – inversion par accumulateur
# ---------------------------------------------------------------------------

def inverse_chaine_tr(s: str, i: int = 0, acc: str = "") -> str:
    """Inverse une chaîne.

    >>> inverse_chaine_tr("abc")
    'cba'
    """
    if i == len(s):
        return acc
    return inverse_chaine_tr(s, i + 1, s[i] + acc)

# ---------------------------------------------------------------------------
# 16) Suppression des doublons en conservant l'ordre – accumulateur
# ---------------------------------------------------------------------------

def supprime_doublons_tr(xs: Sequence[T], i: int = 0, vus: Optional[set] = None, acc: Optional[List[T]] = None) -> List[T]:
    """Supprime les doublons en gardant l'ordre d'apparition.

    >>> supprime_doublons_tr([1,2,1,3,2,4])
    [1, 2, 3, 4]
    """
    if vus is None:
        vus = set()
    if acc is None:
        acc = []
    if i == len(xs):
        return acc
    x = xs[i]
    if x not in vus:
        vus.add(x)
        acc.append(x)
    return supprime_doublons_tr(xs, i + 1, vus, acc)

# ---------------------------------------------------------------------------
# 17) Regroupe en paquets de taille k – accumulateur
# ---------------------------------------------------------------------------

def group_by_k_tr(xs: Sequence[T], k: int, i: int = 0, pack: Optional[List[T]] = None, acc: Optional[List[List[T]]] = None) -> List[List[T]]:
    """Regroupe la séquence en sous‑listes de taille k (dernière incomplète possible).

    >>> group_by_k_tr([1,2,3,4,5], 2)
    [[1, 2], [3, 4], [5]]
    """
    if k <= 0:
        raise ValueError("k doit être > 0")
    if pack is None:
        pack = []
    if acc is None:
        acc = []
    if i == len(xs):
        if pack:
            acc.append(pack)
        return acc
    pack = pack + [xs[i]]
    if len(pack) == k:
        acc.append(pack)
        pack = []
    return group_by_k_tr(xs, k, i + 1, pack, acc)

# ---------------------------------------------------------------------------
# 18) Vérifie si une chaîne est un palindrome – terminal
# ---------------------------------------------------------------------------

def palindrome_tr(s: str, i: int = 0, j: Optional[int] = None) -> bool:
    """Teste si s est un palindrome.

    >>> palindrome_tr("kayak")
    True
    >>> palindrome_tr("bonjour")
    False
    """
    if j is None:
        j = len(s) - 1
    if i >= j:
        return True
    if s[i] != s[j]:
        return False
    return palindrome_tr(s, i + 1, j - 1)

# ---------------------------------------------------------------------------
# 19) Fusion de deux listes triées – terminal via accumulateur
# ---------------------------------------------------------------------------

def fusion_tr(a: Sequence[int], b: Sequence[int], i: int = 0, j: int = 0, acc: Optional[List[int]] = None) -> List[int]:
    """Fusionne deux listes triées.

    >>> fusion_tr([1,3,5], [2,4,6])
    [1, 2, 3, 4, 5, 6]
    """
    if acc is None:
        acc = []
    if i == len(a):
        acc.extend(b[j:])
        return acc
    if j == len(b):
        acc.extend(a[i:])
        return acc
    if a[i] <= b[j]:
        acc.append(a[i])
        return fusion_tr(a, b, i + 1, j, acc)
    else:
        acc.append(b[j])
        return fusion_tr(a, b, i, j + 1, acc)

# ---------------------------------------------------------------------------
# 20) Décodage RLE simple (run-length encoding) – terminal
# ---------------------------------------------------------------------------

def rle_decode_tr(paires: Sequence[Tuple[int, T]], i: int = 0, acc: Optional[List[T]] = None) -> List[T]:
    """Décodage RLE : [(compte, valeur)] -> liste.

    >>> rle_decode_tr([(3, 'A'), (1, 'B'), (2, 'C')])
    ['A', 'A', 'A', 'B', 'C', 'C']
    """
    if acc is None:
        acc = []
    if i == len(paires):
        return acc
    count, val = paires[i]
    acc.extend([val] * count)
    return rle_decode_tr(paires, i + 1, acc)

# ---------------------------------------------------------------------------
# Exemples d'utilisation du trampoline (pour grandes entrées)
# ---------------------------------------------------------------------------

def demo_trampoline():
    """Démos rapides (ne rien renvoyer)."""
    print("Factorielle 2000 via trampoline (long à calculer) :")
    print(trampoline(factorielle_tr_bounce, 2000))  # évite RecursionError
    print("Fibonacci 2000 via trampoline (linéaire) :")
    print(trampoline(fibonacci_tr_bounce, 2000))

if __name__ == "__main__":
    # Mini‑tests rapides
    assert factorielle_tr(5) == 120
    assert fibonacci_tr(10) == 55
    assert pgcd_tr(54, 24) == 6
    assert puissance_tr(2, 10) == 1024
    assert somme_tr([1,2,3,4]) == 10
    assert produit_tr([1,2,3,4]) == 24
    assert longueur_tr("abc") == 3
    assert maximum_tr([3, 9, 2, 7]) == 9
    assert inverse_tr([1,2,3]) == [3,2,1]
    assert inverse_tr2([1,2,3]) == [3,2,1]
    assert map_tr(lambda x: x*x, [1,2,3]) == [1,4,9]
    assert filter_tr(lambda x: x%2==0, [1,2,3,4]) == [2,4]
    assert recherche_binaire_tr([1,3,5,7,9], 7) == 3
    assert recherche_binaire_tr([1,3,5,7,9], 2) == -1
    assert flatten_tr([1, [2, (3, 4)], 5]) == [1,2,3,4,5]
    assert somme_chiffres_tr(942) == 15
    assert en_base_tr(13, 2) == [1,1,0,1]
    assert collatz_steps_tr(6) == 8
    assert partitions_count_tr(5, 5) == 7
    assert inverse_chaine_tr("abc") == "cba"
    assert supprime_doublons_tr([1,2,1,3,2,4]) == [1,2,3,4]
    assert group_by_k_tr([1,2,3,4,5], 2) == [[1,2],[3,4],[5]]
    assert palindrome_tr("kayak") is True
    assert palindrome_tr("bonjour") is False
    assert fusion_tr([1,3,5], [2,4,6]) == [1,2,3,4,5,6]
    assert rle_decode_tr([(3,'A'),(1,'B'),(2,'C')]) == ['A','A','A','B','C','C']
    print("Tous les tests rapides sont OK ✅")
    # Conseil : pour très grandes tailles, utilisez le trampoline :
    # demo_trampoline()
