"""Comprehensive unit tests for Allegro MultiSearch."""

import unittest
from unittest.mock import MagicMock, patch
from allegro_search.models import (
    Seller,
    Offer,
    ProductQuery,
    MatchConfidence,
    SellerMatch,
    MultiSellerCombination
)
from allegro_search.config import AllegroConfig
from allegro_search.allegro_api import AllegroAPIClient, AllegroAPIError
from allegro_search.matcher import ProductMatcher
from allegro_search.finder import MultiItemFinder
from allegro_search.combiner import MultiSellerCombiner


class TestModelsAndMatcher(unittest.TestCase):
    def test_seller_equality(self):
        s1 = Seller(id="123", login="SellerA")
        s2 = Seller(id="123", login="SellerA_Diff")
        s3 = Seller(id="456", login="SellerB")
        self.assertEqual(s1, s2)
        self.assertNotEqual(s1, s3)

    def test_product_matcher_budget_and_keywords(self):
        query = ProductQuery(
            name="Raspberry Pi 5",
            max_budget=400.0,
            required_words=["8gb"],
            excluded_words=["używany", "etui"]
        )

        valid_offer = Offer("1", "Raspberry Pi 5 8GB Oryginalny", 380.0, "PLN", Seller("1", "S1"), "http://a")
        over_budget_offer = Offer("2", "Raspberry Pi 5 8GB Oryginalny", 450.0, "PLN", Seller("1", "S1"), "http://b")
        excluded_word_offer = Offer("3", "Raspberry Pi 5 8GB etui", 350.0, "PLN", Seller("1", "S1"), "http://c")
        missing_req_offer = Offer("4", "Raspberry Pi 5 4GB", 320.0, "PLN", Seller("1", "S1"), "http://d")

        is_v1, conf1, _ = ProductMatcher.match(query, valid_offer)
        self.assertTrue(is_v1)
        self.assertEqual(conf1, MatchConfidence.HIGH)

        is_v2, _, _ = ProductMatcher.match(query, over_budget_offer)
        self.assertFalse(is_v2)

        is_v3, _, _ = ProductMatcher.match(query, excluded_word_offer)
        self.assertFalse(is_v3)

        is_v4, _, _ = ProductMatcher.match(query, missing_req_offer)
        self.assertFalse(is_v4)


class TestMultiItemFinderAndCombiner(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock(spec=AllegroAPIClient)
        self.seller_a = Seller(id="101", login="SuperSklep_A", is_super_seller=True)
        self.seller_b = Seller(id="102", login="Sklep_B", is_super_seller=False)

        self.q1 = ProductQuery(name="LEGO Technic")
        self.q2 = ProductQuery(name="Raspberry Pi")

        self.offer_lego_a = Offer("l1", "LEGO Technic Zestaw", 200.0, "PLN", self.seller_a, "http://l1", is_smart=True, delivery_cost=15.0)
        self.offer_raspi_a = Offer("r1", "Raspberry Pi 5", 350.0, "PLN", self.seller_a, "http://r1", is_smart=True, delivery_cost=15.0)

        self.offer_lego_b = Offer("l2", "LEGO Technic Zestaw", 190.0, "PLN", self.seller_b, "http://l2", is_smart=False, delivery_cost=12.0)

    def test_finder_grouping_and_ranking(self):
        def mock_search(phrase, seller_id=None, limit=60, **kwargs):
            if phrase == "LEGO Technic":
                return [self.offer_lego_a, self.offer_lego_b]
            elif phrase == "Raspberry Pi":
                if seller_id == "101" or seller_id is None:
                    return [self.offer_raspi_a]
                return []
            return []

        self.mock_client.search_offers.side_effect = mock_search

        finder = MultiItemFinder(self.mock_client)
        results = finder.find_sellers([self.q1, self.q2], include_delivery=True)

        self.assertEqual(len(results), 2)
        # Seller A has 2/2 products, Seller B has 1/2 products
        self.assertEqual(results[0].seller.login, "SuperSklep_A")
        self.assertEqual(results[0].matched_count, 2)
        self.assertEqual(results[0].items_total_price, 550.0)
        self.assertEqual(results[0].delivery_cost, 0.0)  # Smart >= 45 PLN

    def test_multi_seller_combiner(self):
        match_a = SellerMatch(
            seller=self.seller_a,
            offers_by_query={"LEGO Technic": [ProductMatcher.filter_and_wrap(self.q1, [self.offer_lego_a])[0]]}
        )
        match_b = SellerMatch(
            seller=self.seller_b,
            offers_by_query={"Raspberry Pi": [ProductMatcher.filter_and_wrap(self.q2, [self.offer_raspi_a])[0]]}
        )

        combos = MultiSellerCombiner.find_best_combinations([self.q1, self.q2], [match_a, match_b], max_sellers=2)
        self.assertGreaterEqual(len(combos), 1)
        self.assertEqual(combos[0].covered_count, 2)


class TestAllegroAPIClient(unittest.TestCase):
    @patch("requests.post")
    def test_authentication_error_handling(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        cfg = AllegroConfig(client_id="bad_id", client_secret="bad_secret")
        client = AllegroAPIClient(cfg)

        with self.assertRaises(AllegroAPIError):
            client.authenticate()


if __name__ == "__main__":
    unittest.main()
