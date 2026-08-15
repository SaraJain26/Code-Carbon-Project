"""
Best practice knowledge definitions mapped to EKB rules.
"""

from __future__ import annotations

from typing import Any


RULE_BEST_PRACTICES: dict[str, dict[str, Any]] = {
    "EKB-COMP-001": {
        "title": "Flatten or Vectorize Nested Loops",
        "explanation": "Deeply nested iteration scales execution cycles exponentially O(N^2 or worse) relative to input size, severely draining processor energy.",
        "optimization_recommendation": "Use hash maps for lookups, flatten nested loops, or employ vectorized libraries like NumPy for batch arithmetic operations.",
        "expected_benefit": "Reduces computational complexity from quadratic/cubic to linear O(N), saving up to 99% of CPU time on large inputs.",
        "code_example": (
            "# Before:\n"
            "for x in list_a:\n"
            "    for y in list_b:\n"
            "        if x.id == y.ref_id:\n"
            "            process(x, y)\n\n"
            "# After:\n"
            "b_map = {y.ref_id: y for y in list_b}\n"
            "for x in list_a:\n"
            "    if x.id in b_map:\n"
            "        process(x, b_map[x.id])"
        ),
        "references": [
            {"title": "Green Software Patterns", "url": "https://patterns.greensoftware.foundation/"}
        ]
    },
    "EKB-IO-001": {
        "title": "Buffer and Bulk File Operations",
        "explanation": "Opening, reading, or writing files inside a loop triggers repeated kernel calls, disk controller spin-ups, and storage write cycles.",
        "optimization_recommendation": "Buffer data in memory and write in batches, or move the file context manager (e.g. `with open(...)`) outside the loop.",
        "expected_benefit": "Minimizes disk controller active power state duration and reduces filesystem context switching overhead.",
        "code_example": (
            "# Before:\n"
            "for row in dataset:\n"
            "    with open('out.txt', 'a') as f:\n"
            "        f.write(str(row) + '\\n')\n\n"
            "# After:\n"
            "with open('out.txt', 'w') as f:\n"
            "    f.writelines(f'{str(row)}\\n' for row in dataset)"
        ),
        "references": [
            {"title": "Green Software Patterns", "url": "https://patterns.greensoftware.foundation/"}
        ]
    },
    "EKB-NET-001": {
        "title": "Batch and Cache Network Queries",
        "explanation": "Issuing individual HTTP requests or API calls inside a loop creates substantial network latency, TLS handshake CPU costs, and keeps network adapters at high-power states.",
        "optimization_recommendation": "Combine queries into a bulk/batch API request, cache responses, or use HTTP connection pooling.",
        "expected_benefit": "Eliminates redundant HTTP/TCP handshake overhead, dramatically reducing network interface active power duration.",
        "code_example": (
            "# Before:\n"
            "for user_id in user_ids:\n"
            "    user = fetch_http(f'/user/{user_id}')\n\n"
            "# After:\n"
            "users = fetch_http('/users', params={'ids': ','.join(user_ids)})"
        ),
        "references": [
            {"title": "Green Software Patterns", "url": "https://patterns.greensoftware.foundation/"}
        ]
    },
    "EKB-COMP-002": {
        "title": "Precompute Loop Invariants",
        "explanation": "Re-evaluating invariant mathematical computations or querying static properties within an iteration wastes CPU clock cycles.",
        "optimization_recommendation": "Move loop-invariant statements outside of loop bodies, or use caching/memoization (`functools.lru_cache`).",
        "expected_benefit": "Reduces redundant calculations and frees up processor pipeline slots.",
        "code_example": (
            "# Before:\n"
            "for item in items:\n"
            "    limit = complex_calculation(config.factor)\n"
            "    process(item, limit)\n\n"
            "# After:\n"
            "limit = complex_calculation(config.factor)\n"
            "for item in items:\n"
            "    process(item, limit)"
        ),
        "references": [
            {"title": "Energy Efficiency across Programming Languages", "url": "https://greenlab.di.uminho.pt/wp-content/uploads/2017/10/sleFinal.pdf"}
        ]
    },
    "EKB-NET-002": {
        "title": "Replace Polling with Push or Adaptive Backoff",
        "explanation": "Continuous constant-interval polling keeps CPUs and network sockets active even when state updates are non-existent.",
        "optimization_recommendation": "Implement webhooks, event streams (WebSockets/SSE), or use exponential backoff intervals for status checking.",
        "expected_benefit": "Reduces idle carbon emissions by allowing client and server hardware to fall back to low-power sleep states.",
        "code_example": (
            "# Before:\n"
            "while not job.done:\n"
            "    check_status(job.id)\n"
            "    time.sleep(1)  # Fixed short interval\n\n"
            "# After:\n"
            "# Prefer Webhooks/SSE. Or adaptive backoff:\n"
            "delay = 1\n"
            "while not job.done:\n"
            "    check_status(job.id)\n"
            "    time.sleep(delay)\n"
            "    delay = min(delay * 2, 60)"
        ),
        "references": [
            {"title": "Green Software Patterns", "url": "https://patterns.greensoftware.foundation/"}
        ]
    },
    "EKB-CFLOW-001": {
        "title": "Use Blocking or Event-Driven Sleep",
        "explanation": "Busy waiting locks the CPU execution thread in a 100% active state, preventing processor cores from down-clocking or entering low-power sleep states.",
        "optimization_recommendation": "Replace empty busy-loops with sync events (`threading.Event`), queue listening (`queue.Queue`), or sleeping intervals.",
        "expected_benefit": "Drops CPU load from 100% to near 0%, conserving system thermal and active power consumption.",
        "code_example": (
            "# Before:\n"
            "while not self.ready:\n"
            "    pass\n\n"
            "# After:\n"
            "# Use threading event\n"
            "self.event.wait()"
        ),
        "references": [
            {"title": "Energy Patterns for Mobile Application Development"}
        ]
    },
    "EKB-COMP-003": {
        "title": "Prefer Iterative Approaches over Deep Recursion",
        "explanation": "Deep recursion allocations call stack frames dynamically for every recursion level, adding memory pressure and execution time compared to iterative loops.",
        "optimization_recommendation": "Convert recursive algorithms to use iterative structures with manual stacks or queue list operations.",
        "expected_benefit": "Reduces call stack execution overhead and avoids stack overflow faults.",
        "code_example": (
            "# Before:\n"
            "def factorial(n):\n"
            "    return 1 if n <= 1 else n * factorial(n - 1)\n\n"
            "# After:\n"
            "def factorial(n):\n"
            "    res = 1\n"
            "    for i in range(2, n + 1):\n"
            "        res *= i\n"
            "    return res"
        ),
        "references": [
            {"title": "Energy Efficiency across Programming Languages", "url": "https://greenlab.di.uminho.pt/wp-content/uploads/2017/10/sleFinal.pdf"}
        ]
    },
    "EKB-ASYNC-001": {
        "title": "Avoid Blocking Sockets/Files in Event Loops",
        "explanation": "Blocking operations inside async functions stall the single event loop thread, causing concurrent tasks to block and increasing average power execution time.",
        "optimization_recommendation": "Delegate blocking libraries to executors (`asyncio.to_thread` or thread pools) or use native async equivalents.",
        "expected_benefit": "Preserves cooperative concurrency responsiveness and minimizes system compute resource active state.",
        "code_example": (
            "# Before:\n"
            "async def fetch_user(uid):\n"
            "    time.sleep(1)  # Blocks event loop!\n"
            "    return fetch_data(uid)\n\n"
            "# After:\n"
            "async def fetch_user(uid):\n"
            "    await asyncio.sleep(1)  # Non-blocking\n"
            "    return await fetch_data_async(uid)"
        ),
        "references": [
            {"title": "Python asyncio documentation", "url": "https://docs.python.org/3/library/asyncio.html"}
        ]
    },
    "EKB-EXC-001": {
        "title": "Avoid Using Exceptions for Ordinary Control Flow",
        "explanation": "Raising exceptions requires capturing stack frames and traversing local scopes, which adds processing cycles when thrown in hot loops.",
        "optimization_recommendation": "Check conditions explicitly (Look Before You Leap) rather than relying on Try-Except blocks for predictable path outcomes.",
        "expected_benefit": "Saves processing overhead on paths that frequently execute.",
        "code_example": (
            "# Before:\n"
            "for x in data:\n"
            "    try:\n"
            "        res = 100 / x\n"
            "    except ZeroDivisionError:\n"
            "        res = 0\n\n"
            "# After:\n"
            "for x in data:\n"
            "    res = 100 / x if x != 0 else 0"
        ),
        "references": [
            {"title": "Python Design FAQ", "url": "https://docs.python.org/3/faq/design.html"}
        ]
    },
    "EKB-IO-002": {
        "title": "Utilize Async or Buffered I/O inside Loops",
        "explanation": "Synchronous, unbuffered I/O operations block thread executions sequentially, extending the total CPU active power state.",
        "optimization_recommendation": "Batch I/O, utilize buffered streams (e.g., standard `BufferedWriter`), or use async file handling libraries.",
        "expected_benefit": "Reduces idle wait times of threads, allowing execution pipelines to finish faster and enter low-power states.",
        "code_example": (
            "# Before:\n"
            "for chunk in chunks:\n"
            "    f.write(chunk)\n"
            "    f.flush()  # Forces immediate slow disk write\n\n"
            "# After:\n"
            "for chunk in chunks:\n"
            "    f.write(chunk)\n"
            "# Flush once at the end"
        ),
        "references": [
            {"title": "Green Software Patterns", "url": "https://patterns.greensoftware.foundation/"}
        ]
    },
    "EKB-MEM-001": {
        "title": "Avoid Excessive Allocation in Loops",
        "explanation": "Repeatedly allocating large objects inside loops causes frequent garbage collection sweeps, consuming additional CPU and memory cycles.",
        "optimization_recommendation": "Reuse buffers, use generator expressions (lazy processing), or allocate array structures beforehand.",
        "expected_benefit": "Reduces peak memory usage and limits garbage collector CPU overhead.",
        "code_example": (
            "# Before:\n"
            "for i in range(1000):\n"
            "    arr = [0] * 1000000\n"
            "    process(arr)\n\n"
            "# After:\n"
            "arr = [0] * 1000000\n"
            "for i in range(1000):\n"
            "    process(arr)"
        ),
        "references": [
            {"title": "Energy Efficiency across Programming Languages", "url": "https://greenlab.di.uminho.pt/wp-content/uploads/2017/10/sleFinal.pdf"}
        ]
    },
    "EKB-CONC-001": {
        "title": "Limit Concurrency Bounds",
        "explanation": "Unbounded thread spawning or task launching causes context switching contention, lock starvation, and system memory exhaustion.",
        "optimization_recommendation": "Use task queues, bounded semaphores (`asyncio.Semaphore`), thread pools, or client-side rate limits.",
        "expected_benefit": "Stabilizes CPU utilization and prevents context switching overhead from degrading overall hardware efficiency.",
        "code_example": (
            "# Before:\n"
            "tasks = [fetch(url) for url in urls]\n"
            "await asyncio.gather(*tasks)\n\n"
            "# After:\n"
            "sem = asyncio.Semaphore(10)\n"
            "async def safe_fetch(url):\n"
            "    async with sem:\n"
            "        return await fetch(url)\n"
            "tasks = [safe_fetch(url) for url in urls]\n"
            "await asyncio.gather(*tasks)"
        ),
        "references": [
            {"title": "Green Software Patterns", "url": "https://patterns.greensoftware.foundation/"}
        ]
    }
}
