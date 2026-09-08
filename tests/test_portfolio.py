import unittest
from grail.portfolio import Position, value_portfolio


class PortfolioTests(unittest.TestCase):
    def test_liquidation_value_is_not_floor_value(self):
        result = value_portfolio([Position("thin", 10, 500, 200, 1)])
        self.assertEqual(result.floor_value, 5000)
        self.assertEqual(result.fair_value, 2000)
        self.assertEqual(result.liquidation_value, 1300)
        self.assertGreater(result.liquidity_haircut_pct, 30)


if __name__ == "__main__": unittest.main()
