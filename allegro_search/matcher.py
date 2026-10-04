"""Product matching engine for filtering and scoring Allegro offers."""

import re
from typing import Tuple, List, Optional
from .models import ProductQuery, Offer, MatchConfidence, MatchedOffer


class ProductMatcher:
    """Evaluates how accurately an Allegro offer matches a target product query."""

    @staticmethod
    def match(query: ProductQuery, offer: Offer) -> Tuple[bool, MatchConfidence, str]:
        """
        Check if an offer matches the query and assign a confidence level.
        Returns: (is_valid_match, confidence, notes)
        """
        title_lower = offer.title.lower()

        # 1. Budget check
        if query.max_budget and offer.price > query.max_budget:
            return False, MatchConfidence.LOW, f"Przekroczony budżet ({offer.price} > {query.max_budget})"

        # 2. Excluded words check
        for exc in query.excluded_words:
            exc_clean = exc.strip().lower()
            if exc_clean and exc_clean in title_lower:
                return False, MatchConfidence.LOW, f"Zawiera wykluczone słowo: '{exc_clean}'"

        # 3. Required words check
        for req in query.required_words:
            req_clean = req.strip().lower()
            if req_clean and req_clean not in title_lower:
                return False, MatchConfidence.LOW, f"Brak wymaganego słowa: '{req_clean}'"

        # 4. Strong Identifiers (EAN / Model)
        if query.ean and query.ean in offer.title:
            return True, MatchConfidence.HIGH, f"Dopasowanie po numerze EAN ({query.ean})"

        if query.model and query.model.lower() in title_lower:
            return True, MatchConfidence.HIGH, f"Dopasowanie po modelu ({query.model})"

        # 5. Fuzzy / Token matching based on main query name
        query_words = [w.lower() for w in re.findall(r'\w+', query.name) if len(w) > 2]
        if not query_words:
            return True, MatchConfidence.MEDIUM, "Ogólne dopasowanie po frazie"

        matched_tokens = [w for w in query_words if w in title_lower]
        match_ratio = len(matched_tokens) / len(query_words)

        if match_ratio >= 0.8:
            return True, MatchConfidence.HIGH, f"Wysoka zgodność słów kluczowych ({int(match_ratio * 100)}%)"
        elif match_ratio >= 0.5:
            return True, MatchConfidence.MEDIUM, f"Średnia zgodność słów kluczowych ({int(match_ratio * 100)}%)"
        else:
            return True, MatchConfidence.LOW, f"Niska zgodność słów kluczowych ({int(match_ratio * 100)}%)"

    @classmethod
    def filter_and_wrap(cls, query: ProductQuery, offers: List[Offer]) -> List[MatchedOffer]:
        """Filter a list of offers and return valid MatchedOffer instances."""
        results = []
        for offer in offers:
            is_valid, confidence, notes = cls.match(query, offer)
            if is_valid:
                # Update offer match metadata
                offer.match_confidence = confidence
                offer.match_notes = notes
                results.append(MatchedOffer(query=query, offer=offer, quantity=query.quantity))
        return results
