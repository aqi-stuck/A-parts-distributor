# Thresholds will later move to a config file
LOW_CONFIDENCE = 0.6
TOO_CLOSE = 0.05


def decide_route(results: list[dict]) -> tuple[str, str | None]:
    """Decide whether to auto-answer or send to human review based on results."""
    if not results:
        return ("review", "no matches")
    top = results[0]["score"]
    if top < LOW_CONFIDENCE:
        return ("review", "low confidence")
    if len(results) > 1 and top - results[1]["score"] < TOO_CLOSE:
        return ("review", "top candidates too close")
    return ("auto", None)
