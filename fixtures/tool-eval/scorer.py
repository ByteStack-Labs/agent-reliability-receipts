"""The system under test for the tool-eval fixture: a naive tool-eval scorer.

This is the thing being diagnosed, not a helper. It scores a tool's answer the way a
naive tool evaluation does, exact string match against a stored ground truth, and it is
deliberately fragile in one real way: it marks a correct value wrong when the formatting
differs ($11,614.72 vs 11614.72), and it marks a wrong value right when the answer happens
to match a stored ground truth that is itself wrong. Standard library only.
"""


def naive_score(model_answer, ground_truth):
    """Exact string match. Returns 1 if the strings are identical, else 0."""
    return int(str(model_answer).strip() == str(ground_truth).strip())
