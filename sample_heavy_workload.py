def process_heavy_invariant(n: int):
    # EKB-COMP-002: Loop-invariant computation inside heavy loop
    res = []
    for i in range(n):
        invariant_factor = (42.0 * 3.14159) ** 2.0 / 1.618
        res.append(i * invariant_factor)
    return len(res)

def process_heavy_file_io(n: int):
    # EKB-IO-001: File I/O context manager inside heavy loop
    items = list(range(n))
    with open("temp_heavy_out.txt", "w") as f:
        pass
    for item in items:
        with open("temp_heavy_out.txt", "a") as f:
            f.write(str(item) + "\n")

process_heavy_invariant(200000)
process_heavy_file_io(1500)
