import unittest

from grail.inventory import update_inventory_state


class InventoryStateTest(unittest.TestCase):
    def row(self):
        return {"source_url":"u","mint":851,"collectible":"Goofy","ask_usd":3,"ask_omi":100,"floor_usd":5,"signal_class":"EDGE"}

    def test_seen_then_missing_then_stale(self):
        first = update_inventory_state(None, {"candidates":[self.row()]}, [], now="2026-09-09T00:00:00+00:00")
        self.assertEqual(first["items"][0]["status"], "live")
        second = update_inventory_state(first, {"candidates":[]}, [], now="2026-09-09T01:00:00+00:00")
        self.assertEqual(second["items"][0]["status"], "not-seen")
        third = update_inventory_state(second, {"candidates":[]}, [], now="2026-09-09T02:00:00+00:00")
        self.assertEqual(third["items"][0]["status"], "stale")

    def test_missing_is_not_sale(self):
        first = update_inventory_state(None, {"candidates":[self.row()]}, [], now="2026-09-09T00:00:00+00:00")
        nxt = update_inventory_state(first, {"candidates":[]}, [], now="2026-09-09T01:00:00+00:00")
        self.assertNotEqual(nxt["items"][0]["status"], "sold")


if __name__ == "__main__": unittest.main()
