def fact(n, acc=1):
    while True:
        if n <= 1:
            return acc
        n, acc = (n - 1, acc * n)
        continue

def fact_non_tail(n):
    if n <= 1:
        return 1
    return n * fact_non_tail(n - 1)

def fib(n, a=0, b=1):
    while True:
        if n == 0:
            return a
        if n == 1:
            return b
        n, a, b = (n - 1, b, a + b)
        continue