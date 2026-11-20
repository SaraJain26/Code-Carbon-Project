from energy.loop_ops import loop_weighted_ops
from recommendation.transformer import ASTCodeTransformer


def test_hoisted_loop_invariant_reduces_loop_weighted_operations():
    before = """def compute_data(numbers, scale):
    total = 0
    for i in numbers:
        factor = scale * 2
        total += i * factor
    return total
"""
    after = ASTCodeTransformer().transform(before).optimized_code

    assert loop_weighted_ops(after) < loop_weighted_ops(before)


def test_constant_only_binops_are_ignored():
    assert loop_weighted_ops("for _ in range(5):\n    x = 3 * 4\n") == loop_weighted_ops(
        "for _ in range(5):\n    pass\n"
    )


def test_depth_two_hoist_has_larger_weighted_savings_than_depth_one():
    one_loop = """def work(items, scale):
    total = 0
    for i in items:
        factor = scale * 2
        total += i * factor
    return total
"""
    two_loops = """def work(items, scale):
    total = 0
    for i in items:
        for j in items:
            factor = scale * 2
            total += i * j * factor
    return total
"""

    one_after = ASTCodeTransformer().transform(one_loop).optimized_code
    two_after = ASTCodeTransformer().transform(two_loops).optimized_code
    one_savings = loop_weighted_ops(one_loop) - loop_weighted_ops(one_after)
    two_savings = loop_weighted_ops(two_loops) - loop_weighted_ops(two_after)

    assert two_savings > one_savings
