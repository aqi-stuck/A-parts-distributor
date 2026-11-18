from app.config import LOW_CONFIDENCE, TOO_CLOSE


def decide_route(results: list[dict]) -> tuple[str, str | None]:
    """Decide whether to auto-answer or send to human review based on results."""
    if not results:
        return ("review", "no matches")
    top = results[0].get("confidence", results[0]["score"])
    if top < LOW_CONFIDENCE:
        return ("review", "low confidence")
    second = results[1].get("score", 0.0) if len(results) > 1 else 0.0
    if len(results) > 1 and results[0]["score"] - second < TOO_CLOSE:
        return ("review", "top candidates too close")
    return ("auto", None)
