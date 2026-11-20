def total_values(items):
    totals = []
    for item in items:
        fixed = sum((1, 2, 3))
        totals.append(fixed + item)
    return totals


if __name__ == "__main__":
    print(total_values([2, 4]))
