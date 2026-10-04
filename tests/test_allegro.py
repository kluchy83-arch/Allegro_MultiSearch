"""Unit tests for Allegro Multi-Item Finder."""

import unittest
from allegro_search.models import Seller, Offer, SellerMatch, SearchResult
from allegro_search.allegro_api import DemoAllegroClient, AllegroAPIClient, AllegroAPIError
from allegro_search.finder import MultiItemFinder


class TestModels(unittest.TestCase):
    def test_seller_equality(self):
        s1 = Seller(id="123", login="SellerA")
        s2 = Seller(id="123", login="SellerA_DifferentName")
        s3 = Seller(id="456", login="SellerB")

        self.assertEqual(s1, s2)
        self.assertNotEqual(s1, s3)
        self.assertEqual(len({s1, s2}), 1)

    def test_seller_match_calculations(self):
        seller = Seller(id="1", login="TestSeller")
        o1 = Offer("1", "Książka 1", 30.0, "PLN", seller, "http://a")
        o2 = Offer("2", "Książka 1 wyd B", 25.0, "PLN", seller, "http://b")
        o3 = Offer("3", "Książka 2", 40.0, "PLN", seller, "http://c")

        match = SellerMatch(
            seller=seller,
            offers_by_keyword={
                "książka 1": [o1, o2],
                "książka 2": [o3]
            }
        )

        self.assertEqual(match.matched_keywords_count, 2)
        self.assertEqual(match.min_total_price, 65.0)  # 25.0 + 40.0
        best = match.best_offers
        self.assertEqual(best["książka 1"].id, "2")
        self.assertEqual(best["książka 2"].id, "3")


class TestDemoAllegroClient(unittest.TestCase):
    def setUp(self):
        self.client = DemoAllegroClient()

    def test_search_known_catalog(self):
        offers = self.client.search_offers("wiedźmin")
        self.assertGreater(len(offers), 0)
        self.assertTrue(all("wiedźmin" in o.title.lower() or "w1" in o.id or "w2" in o.id or "w3" in o.id for o in offers))

    def test_search_with_seller_filter(self):
        offers = self.client.search_offers("wiedźmin", seller_id="101")
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0].seller.id, "101")


class TestMultiItemFinder(unittest.TestCase):
    def setUp(self):
        self.client = DemoAllegroClient()
        self.finder = MultiItemFinder(self.client)

    def test_find_sellers_require_all(self):
        matches = self.finder.find_sellers(["wiedźmin", "diuna"], require_all=True)
        self.assertGreater(len(matches), 0)
        for m in matches:
            self.assertEqual(m.matched_keywords_count, 2)

    def test_find_sellers_partial_match(self):
        matches = self.finder.find_sellers(["wiedźmin", "diuna", "myszka"], require_all=False, min_items=2)
        self.assertGreater(len(matches), 0)
        for m in matches:
            self.assertGreaterEqual(m.matched_keywords_count, 2)

    def test_empty_keywords(self):
        matches = self.finder.find_sellers([])
        self.assertEqual(matches, [])


class TestAllegroAPIClient(unittest.TestCase):
    def test_missing_credentials_raises_error(self):
        client = AllegroAPIClient(client_id="", client_secret="")
        with self.assertRaises(AllegroAPIError):
            client.authenticate()


if __name__ == "__main__":
    unittest.main()
