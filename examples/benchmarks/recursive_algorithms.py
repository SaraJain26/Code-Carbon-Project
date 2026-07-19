"""Recursive benchmark."""


def fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


def is_even(value: int) -> bool:
    if value == 0:
        return True
    return is_odd(value - 1)


def is_odd(value: int) -> bool:
    if value == 0:
        return False
    return is_even(value - 1)
