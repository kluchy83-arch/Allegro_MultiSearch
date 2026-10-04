"""Combiner optimization module for finding best multi-seller coverage."""

import itertools
from typing import List, Dict, Optional
from .models import Seller, Offer, MatchedOffer, ProductQuery, MultiSellerCombination, SellerMatch


class MultiSellerCombiner:
    """Finds optimal combinations of sellers when no single seller offers all products."""

    @staticmethod
    def find_best_combinations(
        all_queries: List[ProductQuery],
        seller_matches: List[SellerMatch],
        max_sellers: int = 3,
        top_n: int = 5
    ) -> List[MultiSellerCombination]:
        """
        Find combinations of up to `max_sellers` sellers that maximize product coverage at minimum total cost.
        Uses greedy set cover heuristic and pruned combination search for efficiency.
        """
        query_names = [q.name for q in all_queries]
        total_queries_count = len(query_names)

        if not seller_matches or not query_names:
            return []

        # Filter out sellers with zero matches
        active_matches = [m for m in seller_matches if m.offers_by_query]

        combinations_results: List[MultiSellerCombination] = []

        # Evaluate combinations from 2 up to max_sellers
        for k in range(2, min(max_sellers + 1, len(active_matches) + 1)):
            # Pick top candidate matches to avoid combinatorial explosion
            candidates = active_matches[:25]

            for combo in itertools.combinations(candidates, k):
                # Build best offer coverage for this combination
                combined_coverage: Dict[str, MatchedOffer] = {}

                for match in combo:
                    for q_name, offers_list in match.offers_by_query.items():
                        if not offers_list:
                            continue
                        best_for_q = min(offers_list, key=lambda m: m.offer.price)
                        if q_name not in combined_coverage or best_for_q.offer.price < combined_coverage[q_name].offer.price:
                            combined_coverage[q_name] = best_for_q

                if combined_coverage:
                    sellers_list = [m.seller for m in combo]
                    combo_res = MultiSellerCombination(
                        sellers=sellers_list,
                        coverage=combined_coverage,
                        total_queries_count=total_queries_count
                    )
                    combinations_results.append(combo_res)

        # Sort combinations: 1) Most products covered, 2) Lowest grand total
        combinations_results.sort(key=lambda c: (-c.covered_count, c.grand_total))

        # Deduplicate identical combinations
        unique_combinations: List[MultiSellerCombination] = []
        seen_keys = set()

        for c in combinations_results:
            key = (c.covered_count, c.grand_total, tuple(sorted(s.id for s in c.sellers)))
            if key not in seen_keys:
                seen_keys.add(key)
                unique_combinations.append(c)
                if len(unique_combinations) >= top_n:
                    break

        return unique_combinations
