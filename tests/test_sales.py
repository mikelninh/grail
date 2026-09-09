import unittest

from grail.sales import parse_recent_sales_html


HTML = """
<html><body>
<h3>Recent sales</h3>
<div>4 Sept, 05:27 · #825 VEVE 0xc174…120f @iroc4141 $6.00</div>
<div>4 Sept, 03:04 · #323 STACKR 0xd19b…bed6 @Sfriedl6969 7,500 OMI · $1.79</div>
<div>3 Sept, 21:10 · #111 STACKR @seller @buyer 20,000 OMI · $4.76</div>
<h3>Never miss a deal</h3>
</body></html>
"""


class SalesTests(unittest.TestCase):
    def test_parse_recent_sales(self):
        rows = parse_recent_sales_html(
            HTML,
            collectible_id="goofy",
            collectible="Goofy Spider-Man",
            source_url="https://example.test/goofy",
            observed_at="2026-09-08T12:00:00+00:00",
        )
        self.assertEqual([r.mint for r in rows], [825, 323, 111])
        self.assertEqual(rows[0].price_usd, 6.0)
        self.assertEqual(rows[1].price_omi, 7500)
        self.assertEqual(rows[1].price_usd, 1.79)
        self.assertEqual(rows[1].seller, "0xd19b…bed6")
        self.assertEqual(rows[1].buyer, "@Sfriedl6969")
        self.assertEqual(rows[1].sold_date, "2026-09-04")

    def test_participant_handles(self):
        rows = parse_recent_sales_html(
            HTML,
            collectible_id="goofy",
            collectible="Goofy Spider-Man",
            source_url="u",
            observed_at="2026-09-08T12:00:00+00:00",
        )
        self.assertEqual(rows[2].seller, "@seller")
        self.assertEqual(rows[2].buyer, "@buyer")


if __name__ == "__main__":
    unittest.main()
