"""Unit tests for Allegro Multi-Item Finder."""

import unittest
from unittest.mock import MagicMock
from allegro_search.models import Seller, Offer, SellerMatch
from allegro_search.allegro_api import AllegroAPIClient, AllegroAPIError
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


class TestMultiItemFinder(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock(spec=AllegroAPIClient)
        self.seller_a = Seller(id="101", login="SellerA", is_super_seller=True)
        self.seller_b = Seller(id="102", login="SellerB", is_super_seller=False)

        self.offer_w1 = Offer("w1", "Wiedźmin 1", 30.0, "PLN", self.seller_a, "http://w1")
        self.offer_w2 = Offer("w2", "Wiedźmin 2", 35.0, "PLN", self.seller_b, "http://w2")

        self.offer_d1 = Offer("d1", "Diuna 1", 40.0, "PLN", self.seller_a, "http://d1")

    def test_find_sellers_require_all(self):
        def mock_search(phrase, seller_id=None, limit=60):
            if phrase == "wiedźmin":
                return [self.offer_w1, self.offer_w2]
            elif phrase == "diuna":
                if seller_id == "101":
                    return [self.offer_d1]
                elif seller_id == "102":
                    return []
                return [self.offer_d1]
            return []

        self.mock_client.search_offers.side_effect = mock_search

        finder = MultiItemFinder(self.mock_client)
        matches = finder.find_sellers(["wiedźmin", "diuna"], require_all=True)

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].seller.login, "SellerA")
        self.assertEqual(matches[0].min_total_price, 70.0)

    def test_empty_keywords(self):
        finder = MultiItemFinder(self.mock_client)
        matches = finder.find_sellers([])
        self.assertEqual(matches, [])


class TestAllegroAPIClient(unittest.TestCase):
    def test_missing_credentials_raises_error(self):
        client = AllegroAPIClient(client_id="", client_secret="")
        with self.assertRaises(AllegroAPIError):
            client.authenticate()


if __name__ == "__main__":
    unittest.main()
