import unittest

from grail.premium_model import conservative_premium_pct


class PremiumModelTest(unittest.TestCase):
    def test_insufficient_samples_do_not_change_value(self):
        model={"palindrome":{"usable_for_value":False,"median_premium_pct":80}}
        self.assertEqual(conservative_premium_pct(["palindrome"], model), 0)

    def test_strongest_evidenced_positive_signal_used_conservatively(self):
        model={
            "low_mint":{"usable_for_value":True,"median_premium_pct":42},
            "semantic":{"usable_for_value":True,"median_premium_pct":65},
        }
        self.assertEqual(conservative_premium_pct(["low_mint","semantic"], model), 65)


if __name__ == "__main__": unittest.main()
