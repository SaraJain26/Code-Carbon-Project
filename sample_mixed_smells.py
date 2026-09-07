import requests
import time

def process_file_io(items):
    # Fixable Smell 1: Repeated file handle initialization inside loop (EKB-IO-001)
    for item in items:
        with open("log.txt", "a") as f:
            f.write(str(item))

def process_invariant(numbers):
    # Fixable Smell 2: Loop-invariant computation (EKB-COMP-002)
    res = []
    for num in numbers:
        multiplier = 42 * 100
        res.append(num * multiplier)
    return res

def process_network(urls):
    # Unresolved Smell 1: Network request inside loop (EKB-NET-001)
    for url in urls:
        resp = requests.get(url)
        time.sleep(1)

def bucket_values(values):
    # Unresolved Smell 2: Unsafe temporary container allocation inside loop (EKB-MEM-001)
    output = []
    for v in values:
        bucket = []
        bucket.append(v * 2)
        output.append(bucket[0])
    return output

# Unresolved Smell 3: Unmemoized recursive function (EKB-COMP-003)
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

if __name__ == "__main__":
    items = [1, 2, 3]
    process_file_io(items)
    process_invariant(items)
    bucket_values(items)
