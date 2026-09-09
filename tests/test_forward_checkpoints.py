import unittest

from grail.forward import update_forward_state


class ForwardCheckpointTest(unittest.TestCase):
    def row(self):
        return {"source_url":"u","mint":1962,"collectible":"Spider-Man","signal_class":"GRAIL","live_status":"live","availability_status":"provider-current-unverified","ask_usd":100,"ask_omi":1000,"floor_usd":110,"premium_to_floor_pct":-9,"mint_score":100,"opportunity_score":80,"confidence":90}

    def test_one_hour_checkpoint_is_market_observation_not_sale(self):
        first=update_forward_state(None,{"candidates":[self.row()]},[],now="2026-09-09T00:00:00+00:00")
        second=update_forward_state(first,{"candidates":[self.row()]},[],now="2026-09-09T01:05:00+00:00")
        a=second["alerts"][0]
        self.assertIn("1h",a["checkpoints"])
        self.assertEqual(a["status"],"open")
        self.assertEqual(second["summary"]["resolved_sales"],0)

    def test_non_live_row_does_not_enter_new_cohort(self):
        r=self.row();r["live_status"]="stale"
        state=update_forward_state(None,{"candidates":[r]},[],now="2026-09-09T00:00:00+00:00")
        self.assertEqual(state["summary"]["tracked_alerts"],0)


if __name__ == "__main__": unittest.main()
