from decimal import Decimal


def estimate_token_cost(
    *,
    input_tokens: int | None,
    output_tokens: int | None,
    input_cost_per_million: Decimal | None,
    output_cost_per_million: Decimal | None,
) -> Decimal | None:
    """Estimate cost only when both usage and explicitly configured prices exist."""
    if (
        input_tokens is None
        or output_tokens is None
        or input_cost_per_million is None
        or output_cost_per_million is None
    ):
        return None
    one_million = Decimal(1_000_000)
    cost = (
        Decimal(input_tokens) * input_cost_per_million
        + Decimal(output_tokens) * output_cost_per_million
    ) / one_million
    return cost.quantize(Decimal("0.00000001"))
