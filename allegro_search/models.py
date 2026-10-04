"""Data models for Allegro multi-item seller search."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional


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
    condition: Optional[str] = None


@dataclass
class SearchResult:
    keyword: str
    offers: List[Offer] = field(default_factory=list)


@dataclass
class SellerMatch:
    seller: Seller
    # Maps keyword -> list of offers from this seller matching that keyword
    offers_by_keyword: Dict[str, List[Offer]]

    @property
    def matched_keywords_count(self) -> int:
        return len(self.offers_by_keyword)

    @property
    def min_total_price(self) -> float:
        """Sum of the lowest priced offer for each matched keyword."""
        total = 0.0
        for keyword, offers in self.offers_by_keyword.items():
            if offers:
                total += min(offer.price for offer in offers)
        return round(total, 2)

    @property
    def best_offers(self) -> Dict[str, Offer]:
        """Dictionary of keyword -> cheapest offer for that keyword."""
        res = {}
        for keyword, offers in self.offers_by_keyword.items():
            if offers:
                res[keyword] = min(offers, key=lambda o: o.price)
        return res
