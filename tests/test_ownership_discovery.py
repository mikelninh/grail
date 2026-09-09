import unittest
from unittest.mock import patch

from grail.ownership_discovery import discover_mapping, metadata_editions


class OwnershipDiscoveryTest(unittest.TestCase):
    def test_extracts_explicit_edition_traits_only(self):
        meta = {"name":"X", "attributes":[{"trait_type":"Edition Number","value":"#851"},{"trait_type":"Year","value":2025}]}
        self.assertEqual(metadata_editions(meta), {851})

    @patch("grail.ownership_discovery.iter_instances")
    def test_unique_name_and_edition_resolves(self, it):
        it.return_value = iter([
            {"id":"13500001","metadata":{"name":"Other thing","edition":851},"owner":{"hash":"0x"+"1"*40}},
            {"id":"13500002","metadata":{"name":"Marvel & Disney: What If…? Goofy Became Spider-Man #1","attributes":[{"trait_type":"Edition","value":851}]},"owner":{"hash":"0x"+"2"*40}},
        ])
        mapping, proof = discover_mapping(source_url="https://vevealpha.com/c/goofy", mint=851, expected_name="Goofy Became Spider-Man #1")
        self.assertIsNotNone(mapping)
        self.assertEqual(mapping.token_id, "13500002")
        self.assertEqual(proof.status, "resolved")

    @patch("grail.ownership_discovery.iter_instances")
    def test_name_match_without_edition_never_resolves(self, it):
        it.return_value = iter([{"id":"851","metadata":{"name":"Goofy Became Spider-Man #1"}}])
        mapping, proof = discover_mapping(source_url="https://vevealpha.com/c/goofy", mint=851, expected_name="Goofy Became Spider-Man #1")
        self.assertIsNone(mapping)
        self.assertEqual(proof.status, "not-found")


if __name__ == "__main__":
    unittest.main()
