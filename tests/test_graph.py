import unittest
from grail.graph import CollectorGraph, Edge


class GraphTests(unittest.TestCase):
    def test_semantic_path(self):
        g = CollectorGraph()
        g.add_node("mint:1962", "mint", "#1962")
        g.add_node("year:1962", "year", "1962")
        g.add_node("character:spider-man", "character", "Spider-Man")
        g.add_edge(Edge("mint:1962", "matches_year", "year:1962", 1, "edition number"))
        g.add_edge(Edge("year:1962", "first_appearance_of", "character:spider-man", 1, "Amazing Fantasy #15"))
        self.assertEqual([x.relation for x in g.shortest_semantic_path("mint:1962", "character:spider-man")], ["matches_year", "first_appearance_of"])


if __name__ == "__main__": unittest.main()
