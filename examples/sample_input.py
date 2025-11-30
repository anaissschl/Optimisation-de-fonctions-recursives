def fact(n, acc=1):
    if n <= 1:
        return acc
    return fact(n - 1, acc * n)

def fact_non_tail(n):
    if n <= 1:
        return 1
    return n * fact_non_tail(n - 1)

def fib(n, a=0, b=1):
    if n == 0:
        return a
    if n == 1:
        return b
    return fib(n - 1, b, a + b)
