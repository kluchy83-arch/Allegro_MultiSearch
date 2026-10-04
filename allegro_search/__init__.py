"""Init file for allegro_search package."""

from .models import (
    Seller,
    Offer,
    ProductQuery,
    MatchedOffer,
    SellerMatch,
    MultiSellerCombination,
    MatchConfidence
)
from .config import AllegroConfig
from .allegro_api import AllegroAPIClient, AllegroAPIError
from .matcher import ProductMatcher
from .finder import MultiItemFinder
from .combiner import MultiSellerCombiner

__all__ = [
    "Seller",
    "Offer",
    "ProductQuery",
    "MatchedOffer",
    "SellerMatch",
    "MultiSellerCombination",
    "MatchConfidence",
    "AllegroConfig",
    "AllegroAPIClient",
    "AllegroAPIError",
    "ProductMatcher",
    "MultiItemFinder",
    "MultiSellerCombiner"
]
