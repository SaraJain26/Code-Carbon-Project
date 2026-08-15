def process_data(data):
    # Energy smell: Nested loops (complexity O(N^2))
    for item in data:
        for sub_item in item:
            print(sub_item)
