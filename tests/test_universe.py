import unittest

from grail.universe import UniverseAsset, normalise_item, select_for_deep_scan, triage_score


class UniverseTests(unittest.TestCase):
    def test_comic_normalisation(self):
        a=normalise_item({"collectible_id":"abc","collectible_name":"Amazing Fantasy #15","slug":"amazing-fantasy-common","element_type":"COMIC_COVER","is_comic":True,"rarity":"COMMON","floor_usd":339.69,"floor_omi":890000,"mcap":1173892,"is_top200_veve":True,"is_grail":True})
        self.assertEqual(a.kind,"comic")
        self.assertTrue(a.source_url.endswith("/amazing-fantasy-common"))
        self.assertEqual(a.floor_usd,339.69)

    def test_collectible_normalisation(self):
        a=normalise_item({"collectible_id":"def","collectible_name":"Superman","slug":"superman","element_type":"COLLECTIBLE_TYPE","rarity":"UNCOMMON"})
        self.assertEqual(a.kind,"collectible")
        self.assertFalse(a.is_comic)

    def test_missing_identity_fails_closed(self):
        with self.assertRaises(ValueError):
            normalise_item({"collectible_name":"Mystery"})

    def test_triage_is_not_grail_label(self):
        a=UniverseAsset("1","Comic #1","comic-1","https://vevealpha.com/c/comic-1",None,"SECRET_RARE","comic",10,None,100000,True,False)
        self.assertGreater(triage_score(a),0)
        self.assertFalse(a.provider_grail)

    def test_deep_scan_reserves_comics(self):
        assets=[]
        for i in range(10):
            assets.append(UniverseAsset(f"c{i}",f"Comic #{i+1}",f"comic-{i}",f"https://vevealpha.com/c/comic-{i}",None,"COMMON","comic",10,None,1000,False,False))
        for i in range(20):
            assets.append(UniverseAsset(f"x{i}",f"Collectible {i}",f"x-{i}",f"https://vevealpha.com/c/x-{i}",None,"SECRET_RARE","collectible",10,None,1_000_000,True,True))
        picked=select_for_deep_scan(assets,limit=12,min_comics=5)
        self.assertEqual(len(picked),12)
        self.assertGreaterEqual(sum(a.is_comic for a in picked),5)


if __name__=="__main__": unittest.main()
