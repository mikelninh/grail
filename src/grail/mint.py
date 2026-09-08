from .models import Collectible, MintSignal


def _digits(n: int) -> str:
    return str(abs(int(n)))


def analyse_mint(mint: int, collectible: Collectible) -> tuple[MintSignal, ...]:
    """Return explainable mint-number signals. Scores are 0..100 signal strengths.

    Generic visual patterns are deliberately modest. GRAIL should reserve its strongest
    scores for low editions and sourced IP / historical significance.
    """
    if mint <= 0:
        return ()
    s = _digits(mint)
    signals: list[MintSignal] = []

    if mint <= 100:
        strength = 100 if mint <= 10 else 94 if mint <= 50 else 86
        signals.append(MintSignal("low_mint", strength, f"low edition #{mint}"))
    elif collectible.total_editions and mint <= max(200, int(collectible.total_editions * 0.01)):
        signals.append(MintSignal("low_percentile", 74, "top ~1% low edition"))

    if len(s) >= 3 and len(set(s)) == 1:
        signals.append(MintSignal("repeating", min(82, 62 + 5 * len(s)), f"repeating digits #{mint}"))

    # Pretty is not the same as historically significant. A random palindrome is a bonus,
    # not a grail thesis by itself.
    if len(s) >= 4 and s == s[::-1]:
        signals.append(MintSignal("palindrome", 38, f"palindromic edition #{mint}"))

    ascending = "123456789"
    descending = ascending[::-1]
    if len(s) >= 3 and (s in ascending or s in descending):
        signals.append(MintSignal("sequence", 48, f"sequential digits #{mint}"))

    if collectible.release_year and mint == collectible.release_year:
        signals.append(MintSignal("release_year", 94, f"matches release year {mint}"))
    if collectible.first_appearance_year and mint == collectible.first_appearance_year:
        signals.append(MintSignal("first_appearance_year", 100, f"matches first-appearance year {mint}"))

    if mint in collectible.semantic_numbers:
        label = collectible.semantic_labels.get(mint, "IP-significant number")
        signals.append(MintSignal("semantic", 100, label))

    if len(s) >= 3 and s.count("8") >= 3:
        signals.append(MintSignal("cultural_pattern", 68 + min(10, s.count("8") * 2), "strong lucky-8 pattern"))

    unique = {(x.kind, x.reason): x for x in signals}
    return tuple(sorted(unique.values(), key=lambda x: (-x.score, x.kind)))


def mint_score(mint: int, collectible: Collectible) -> tuple[float, tuple[MintSignal, ...]]:
    signals = analyse_mint(mint, collectible)
    if not signals:
        return 0.0, signals
    strongest = signals[0].score
    reinforcement = min(12.0, sum(x.score for x in signals[1:]) * 0.05)
    return min(100.0, strongest + reinforcement), signals
