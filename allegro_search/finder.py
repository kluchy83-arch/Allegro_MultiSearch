"""Search finder module for aggregating offers across sellers."""

import logging
from typing import List, Dict, Optional, Callable
from .models import ProductQuery, SellerMatch, MatchedOffer, Seller
from .allegro_api import AllegroAPIClient
from .matcher import ProductMatcher

logger = logging.getLogger("AllegroMultiSearch")


class MultiItemFinder:
    """Finds sellers that offer multiple requested products."""

    def __init__(self, client: AllegroAPIClient):
        self.client = client

    def find_sellers(
        self,
        queries: List[ProductQuery],
        include_delivery: bool = True,
        max_delivery_cost: Optional[float] = None,
        sort_by_price: Optional[str] = None,
        condition: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str, int], None]] = None
    ) -> List[SellerMatch]:
        """
        Search for all product queries and group results by seller.

        :param queries: List of ProductQuery items.
        :param include_delivery: Whether to compute delivery costs.
        :param max_delivery_cost: Maximum acceptable delivery cost filter.
        :param sort_by_price: Optional sorting for Allegro API (e.g., 'p' for price ascending).
        :param condition: Optional condition filter (e.g. 'NEW').
        :param progress_callback: Optional callback(current_idx, total_queries, query_name, total_offers_found).
        :return: List of SellerMatch instances sorted by product coverage (desc) and price (asc).
        """
        clean_queries = [q for q in queries if q.name.strip()]
        if not clean_queries:
            return []

        # Map seller_key -> { seller: Seller, offers_by_query: { query_name: [MatchedOffer, ...] } }
        seller_map: Dict[str, Dict] = {}
        total_queries = len(clean_queries)
        total_offers_count = 0

        # Phase 1: Search and match each query
        for idx, query in enumerate(clean_queries, 1):
            if progress_callback:
                progress_callback(idx, total_queries, query.name, total_offers_count)

            # Retrieve raw offers from Allegro API
            raw_offers = self.client.search_offers(
                phrase=query.name,
                limit=query.min_offers_to_analyze,
                sort=sort_by_price,
                price_to=query.max_budget,
                condition=condition
            )
            total_offers_count += len(raw_offers)

            # Filter & match offers
            matched_offers = ProductMatcher.filter_and_wrap(query, raw_offers)

            for m_offer in matched_offers:
                seller = m_offer.offer.seller
                s_key = seller.id or seller.login

                if s_key not in seller_map:
                    seller_map[s_key] = {
                        "seller": seller,
                        "offers_by_query": {q.name: [] for q in clean_queries}
                    }

                seller_map[s_key]["offers_by_query"][query.name].append(m_offer)

        # Phase 2: Direct targeted query for candidate sellers missing some products
        if seller_map and len(clean_queries) > 1:
            for s_key, entry in list(seller_map.items()):
                seller_id = entry["seller"].id
                for query in clean_queries:
                    if not entry["offers_by_query"][query.name]:
                        try:
                            targeted_raw = self.client.search_offers(
                                phrase=query.name,
                                seller_id=seller_id,
                                limit=20,
                                price_to=query.max_budget,
                                condition=condition
                            )
                            targeted_matched = ProductMatcher.filter_and_wrap(query, targeted_raw)
                            entry["offers_by_query"][query.name].extend(targeted_matched)
                        except Exception:
                            pass

        # Phase 3: Build SellerMatch list
        results: List[SellerMatch] = []
        for s_key, entry in seller_map.items():
            offers_by_q = entry["offers_by_query"]
            active_offers = {q_name: offers for q_name, offers in offers_by_q.items() if offers}

            if active_offers:
                match = SellerMatch(
                    seller=entry["seller"],
                    offers_by_query=active_offers,
                    include_delivery=include_delivery,
                    max_delivery_cost=max_delivery_cost
                )

                # Apply max delivery cost filter if set
                if max_delivery_cost is not None and match.delivery_cost > max_delivery_cost:
                    continue

                results.append(match)

        # Ranking Priority:
        # 1) Most covered products (desc)
        # 2) Lowest total price with delivery (asc)
        # 3) Lowest delivery cost (asc)
        results.sort(key=lambda m: (-m.matched_count, m.total_price_with_delivery, m.delivery_cost))

        return results
