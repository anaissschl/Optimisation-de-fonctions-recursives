# PGCD d'Euclide (classique tail)
def gcd(a, b):
    if b == 0:
        return a
    return gcd(b, a % b)

# Puissance avec accumulateur
def pow_tail(x, n, acc=1):
    if n == 0:
        return acc
    return pow_tail(x, n-1, acc*x)

# Somme d'une liste avec accumulateur
def sum_tail(xs, acc=0, i=0):
    if i == len(xs):
        return acc
    return sum_tail(xs, acc + xs[i], i+1)

# Inversion de liste (construction tail)
def reverse_tail(xs, acc=None, i=0):
    if acc is None:
        acc = []
    if i == len(xs):
        return acc
    acc.insert(0, xs[i])      # effet avant l'appel (OK en V1)
    return reverse_tail(xs, acc, i+1)


# Factorielle non terminale
def fact_non_tail(n):
    if n <= 1:
        return 1
    return n * fact_non_tail(n-1)  # calcul APRES l'appel => non tail

# Somme récursive naïve
def sum_rec(xs):
    if not xs:
        return 0
    return xs[0] + sum_rec(xs[1:])  # + après l'appel => non tail


# AVANT (non-tail)
def fact(n):
    if n <= 1:
        return 1
    return n * fact(n-1)

# APRES (tail)
def fact_tail(n, acc=1):
    if n <= 1:
        return acc
    return fact_tail(n-1, acc*n)

