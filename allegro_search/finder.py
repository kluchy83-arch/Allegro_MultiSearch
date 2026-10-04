"""Core finder logic for multi-item search across sellers."""

from typing import List, Dict, Union, Optional
from .models import Offer, Seller, SellerMatch, SearchResult
from .allegro_api import AllegroAPIClient, DemoAllegroClient


class MultiItemFinder:
    """Finds sellers that have multiple desired items in stock."""

    def __init__(self, client: Optional[Union[AllegroAPIClient, DemoAllegroClient]] = None):
        self.client = client or DemoAllegroClient()

    def find_sellers(
        self,
        keywords: List[str],
        require_all: bool = True,
        min_items: int = 2,
        limit_per_keyword: int = 60
    ) -> List[SellerMatch]:
        """
        Search for items across keywords and group results by seller.

        :param keywords: List of item query strings.
        :param require_all: If True, only return sellers that have ALL keywords available.
        :param min_items: Minimum number of keywords a seller must match (used if require_all is False).
        :param limit_per_keyword: Max number of offers to fetch per keyword.
        :return: Sorted list of SellerMatch objects.
        """
        # Clean and deduplicate keywords preserving order
        clean_keywords = []
        for kw in keywords:
            kw_stripped = kw.strip()
            if kw_stripped and kw_stripped not in clean_keywords:
                clean_keywords.append(kw_stripped)

        if not clean_keywords:
            return []

        # Map seller_key -> { seller: Seller, offers_by_kw: { kw: [Offer, ...] } }
        seller_map: Dict[str, Dict] = {}

        # Phase 1: Search first keyword to establish candidate sellers
        first_kw = clean_keywords[0]
        first_offers = self.client.search_offers(first_kw, limit=limit_per_keyword)

        for offer in first_offers:
            seller = offer.seller
            seller_key = seller.id or seller.login

            if seller_key not in seller_map:
                seller_map[seller_key] = {
                    "seller": seller,
                    "offers_by_kw": {k: [] for k in clean_keywords}
                }

            seller_map[seller_key]["offers_by_kw"][first_kw].append(offer)

        # Phase 2: For remaining keywords, search general + targeted queries for candidate sellers
        for kw in clean_keywords[1:]:
            offers = self.client.search_offers(kw, limit=limit_per_keyword)
            for offer in offers:
                seller = offer.seller
                seller_key = seller.id or seller.login

                if seller_key not in seller_map:
                    seller_map[seller_key] = {
                        "seller": seller,
                        "offers_by_kw": {k: [] for k in clean_keywords}
                    }

                seller_map[seller_key]["offers_by_kw"][kw].append(offer)

            # If live API client, directly query candidate sellers for this keyword to maximize matches
            if isinstance(self.client, AllegroAPIClient) and seller_map:
                for seller_key, entry in list(seller_map.items()):
                    if not entry["offers_by_kw"][kw]:
                        targeted_offers = self.client.search_offers(kw, seller_id=entry["seller"].id, limit=20)
                        entry["offers_by_kw"][kw].extend(targeted_offers)

        # Convert to SellerMatch list and filter
        results: List[SellerMatch] = []
        target_min_items = len(clean_keywords) if require_all else max(1, min_items)

        for seller_key, entry in seller_map.items():
            offers_by_kw = entry["offers_by_kw"]
            # Filter out keywords with no offers
            active_offers_by_kw = {kw: offers for kw, offers in offers_by_kw.items() if offers}

            if len(active_offers_by_kw) >= target_min_items:
                match = SellerMatch(
                    seller=entry["seller"],
                    offers_by_keyword=active_offers_by_kw
                )
                results.append(match)

        # Sort: first by number of matched keywords (descending), then by min total price (ascending)
        results.sort(key=lambda m: (-m.matched_keywords_count, m.min_total_price))

        return results
