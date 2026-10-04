"""Init file for allegro_search package."""

from .models import Seller, Offer, SearchResult, SellerMatch
from .allegro_api import AllegroAPIClient, DemoAllegroClient, AllegroAPIError
from .finder import MultiItemFinder

__all__ = [
    "Seller",
    "Offer",
    "SearchResult",
    "SellerMatch",
    "AllegroAPIClient",
    "DemoAllegroClient",
    "AllegroAPIError",
    "MultiItemFinder"
]
