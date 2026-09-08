import unittest
from grail.mint import analyse_mint, mint_score
from grail.models import Collectible


class MintTests(unittest.TestCase):
    def setUp(self):
        self.spidey = Collectible("spidey", "Spider-Man", "Marvel", total_editions=10000, first_appearance_year=1962, semantic_numbers=(1962,))

    def test_first_appearance_is_grail_signal(self):
        score, signals = mint_score(1962, self.spidey)
        self.assertGreaterEqual(score, 100)
        self.assertTrue(any(x.kind == "first_appearance_year" for x in signals))

    def test_lucky_eights_detected(self):
        self.assertTrue(any(x.kind == "cultural_pattern" for x in analyse_mint(8880, self.spidey)))

    def test_random_mint_has_no_signal(self):
        self.assertEqual(mint_score(4273, self.spidey)[0], 0)


if __name__ == "__main__": unittest.main()
