"""Data models for Allegro MultiSearch."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class MatchConfidence(str, Enum):
    HIGH = "Dopasowanie wysokie"
    MEDIUM = "Dopasowanie średnie"
    LOW = "Dopasowanie niskie"


@dataclass
class ProductQuery:
    name: str
    quantity: int = 1
    min_offers_to_analyze: int = 60
    max_budget: Optional[float] = None
    required_words: List[str] = field(default_factory=list)
    excluded_words: List[str] = field(default_factory=list)
    ean: Optional[str] = None
    model: Optional[str] = None

    def clean_keywords(self) -> List[str]:
        return [w.strip() for w in self.required_words if w.strip()]


@dataclass
class SearchResult:
    keyword: str
    offers: List['Offer'] = field(default_factory=list)


@dataclass
class Seller:
    id: str
    login: str
    is_super_seller: bool = False
    rating: Optional[float] = None

    def __hash__(self):
        return hash(self.id or self.login)

    def __eq__(self, other):
        if not isinstance(other, Seller):
            return False
        return (self.id and self.id == other.id) or (self.login and self.login == other.login)


@dataclass
class Offer:
    id: str
    title: str
    price: float
    currency: str
    seller: Seller
    url: str
    image_url: Optional[str] = None
    is_smart: bool = False
    delivery_cost: float = 0.0
    condition: Optional[str] = None
    category_id: Optional[str] = None
    match_confidence: MatchConfidence = MatchConfidence.HIGH
    match_notes: str = "Dokładne dopasowanie"


@dataclass
class MatchedOffer:
    query: ProductQuery
    offer: Offer
    quantity: int = 1

    @property
    def item_total(self) -> float:
        return round(self.offer.price * self.quantity, 2)


@dataclass
class SellerMatch:
    seller: Seller
    # Maps product query name -> list of matched offers
    offers_by_query: Dict[str, List[MatchedOffer]]
    include_delivery: bool = True
    max_delivery_cost: Optional[float] = None

    @property
    def matched_count(self) -> int:
        return len(self.offers_by_query)

    @property
    def best_offers(self) -> Dict[str, MatchedOffer]:
        """Map of query_name -> cheapest matched offer."""
        res = {}
        for q_name, matched_list in self.offers_by_query.items():
            if matched_list:
                res[q_name] = min(matched_list, key=lambda m: m.offer.price)
        return res

    @property
    def items_total_price(self) -> float:
        """Sum of lowest priced offers multiplied by required quantity."""
        total = 0.0
        for m_offer in self.best_offers.values():
            total += m_offer.item_total
        return round(total, 2)

    @property
    def delivery_cost(self) -> float:
        """Calculates delivery cost for this seller bundle."""
        if not self.include_delivery:
            return 0.0

        best = list(self.best_offers.values())
        if not best:
            return 0.0

        # If any item is Smart and bundle >= 45 PLN, delivery is 0
        has_smart = any(m.offer.is_smart for m in best)
        if has_smart and self.items_total_price >= 45.0:
            return 0.0

        # Otherwise take max delivery cost among chosen items
        max_del = max(m.offer.delivery_cost for m in best)
        return round(max_del, 2)

    @property
    def total_price_with_delivery(self) -> float:
        return round(self.items_total_price + self.delivery_cost, 2)


@dataclass
class MultiSellerCombination:
    sellers: List[Seller]
    # Maps query_name -> MatchedOffer
    coverage: Dict[str, MatchedOffer]
    total_queries_count: int

    @property
    def covered_count(self) -> int:
        return len(self.coverage)

    @property
    def items_total_price(self) -> float:
        return round(sum(m.item_total for m in self.coverage.values()), 2)

    @property
    def total_delivery_cost(self) -> float:
        # Group offers by seller and compute delivery per seller
        seller_offers: Dict[str, List[MatchedOffer]] = {}
        for m in self.coverage.values():
            s_key = m.offer.seller.id or m.offer.seller.login
            seller_offers.setdefault(s_key, []).append(m)

        tot_del = 0.0
        for s_offers in seller_offers.values():
            sum_price = sum(m.item_total for m in s_offers)
            has_smart = any(m.offer.is_smart for m in s_offers)
            if has_smart and sum_price >= 45.0:
                continue
            del_cost = max(m.offer.delivery_cost for m in s_offers)
            tot_del += del_cost

        return round(tot_del, 2)

    @property
    def grand_total(self) -> float:
        return round(self.items_total_price + self.total_delivery_cost, 2)
