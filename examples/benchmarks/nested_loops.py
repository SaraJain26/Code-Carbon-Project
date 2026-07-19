"""Nested-loop benchmark."""


def bubble_sort(values: list[int]) -> list[int]:
    """Sort values using a deliberately loop-heavy algorithm."""

    numbers = values[:]
    for i in range(len(numbers)):
        for j in range(0, len(numbers) - i - 1):
            if numbers[j] > numbers[j + 1]:
                numbers[j], numbers[j + 1] = numbers[j + 1], numbers[j]
    return numbers


def matrix_sum(matrix: list[list[int]]) -> int:
    total = 0
    row_index = 0
    while row_index < len(matrix):
        for value in matrix[row_index]:
            total += value
        row_index += 1
    return total
