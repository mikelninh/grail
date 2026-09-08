from .models import Collectible, Listing
from .scoring import score_listing


def main() -> None:
    collectible = Collectible(id="spider-man-demo", name="Spider-Man Demo", brand="Marvel", character="Spider-Man", total_editions=10000, first_appearance_year=1962, semantic_numbers=(1962,), semantic_labels={1962: "Spider-Man first appeared in 1962"})
    listings = [
        Listing("floor", collectible.id, "StackR", 4273, 95, 100, (98, 100, 103), 18, 20),
        Listing("meaningful", collectible.id, "StackR", 1962, 103, 100, (98, 100, 103), 18, 20),
        Listing("cheap", collectible.id, "StackR", 5521, 78, 100, (98, 100, 103), 18, 20),
    ]
    ranked = sorted((score_listing(x, collectible) for x in listings), key=lambda x: x.total, reverse=True)
    for rank, score in enumerate(ranked, 1):
        print(f"{rank}. {score.listing_id}: {score.total}/100 (confidence {score.confidence})")
        for reason in score.reasons:
            print(f"   - {reason}")


if __name__ == "__main__":
    main()
