"""Allegro API client module."""

import requests
import json
import os
import urllib.parse
from typing import List, Optional, Dict, Any
from .models import Offer, Seller, SearchResult


class AllegroAPIError(Exception):
    """Exception raised for Allegro API errors."""
    pass


class AllegroAPIClient:
    """Client for Allegro REST API (Web API v1)."""

    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None, sandbox: bool = False):
        self.client_id = client_id or os.environ.get("ALLEGRO_CLIENT_ID", "")
        self.client_secret = client_secret or os.environ.get("ALLEGRO_CLIENT_SECRET", "")
        self.sandbox = sandbox

        if self.sandbox:
            self.auth_url = "https://allegro.pl.allegro-sandbox.io/auth/oauth/token"
            self.api_url = "https://api.allegro.pl.allegro-sandbox.io"
        else:
            self.auth_url = "https://allegro.pl/auth/oauth/token"
            self.api_url = "https://api.allegro.pl"

        self._access_token: Optional[str] = None

    def authenticate(self) -> str:
        """Obtain client_credentials access token."""
        if not self.client_id or not self.client_secret:
            raise AllegroAPIError("Brak ID klienta lub sekretu Allegro API (Client ID, Client Secret).")

        data = {'grant_type': 'client_credentials'}
        try:
            resp = requests.post(
                self.auth_url,
                auth=(self.client_id, self.client_secret),
                data=data,
                timeout=10
            )
            resp.raise_for_status()
            token_data = resp.json()
            self._access_token = token_data.get('access_token')
            return self._access_token
        except Exception as e:
            raise AllegroAPIError(f"Błąd uwierzytelniania w Allegro API: {e}")

    def get_headers(self) -> Dict[str, str]:
        if not self._access_token:
            self.authenticate()
        return {
            'Authorization': f'Bearer {self._access_token}',
            'Accept': 'application/vnd.allegro.public.v1+json',
            'Content-Type': 'application/vnd.allegro.public.v1+json'
        }

    def search_offers(self, phrase: str, seller_id: Optional[str] = None, limit: int = 60) -> List[Offer]:
        """Search offers for a phrase, optionally filtered by seller.id."""
        headers = self.get_headers()
        params = {
            'phrase': phrase,
            'limit': limit,
            'fallback': 'false'
        }
        if seller_id:
            params['seller.id'] = seller_id

        url = f"{self.api_url}/offers/listing"
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return self._parse_offers_response(data)
        except Exception as e:
            raise AllegroAPIError(f"Błąd podczas wyszukiwania 'phrase={phrase}': {e}")

    def _parse_offers_response(self, data: Dict[str, Any]) -> List[Offer]:
        offers = []
        items_groups = data.get('items', {})

        # Combine regular items and promoted items
        all_items = items_groups.get('promoted', []) + items_groups.get('regular', [])

        for item in all_items:
            try:
                offer_id = item.get('id', '')
                title = item.get('name', '')
                price_val = float(item.get('sellingMode', {}).get('price', {}).get('amount', 0.0))
                currency = item.get('sellingMode', {}).get('price', {}).get('currency', 'PLN')

                seller_data = item.get('seller', {})
                seller_id = seller_data.get('id', 'unknown')
                seller_login = seller_data.get('login', seller_id)
                is_super = seller_data.get('superSeller', False)

                seller = Seller(
                    id=seller_id,
                    login=seller_login,
                    is_super_seller=is_super
                )

                images = item.get('images', [])
                image_url = images[0].get('url') if images else None

                # Construct direct URL
                offer_url = f"https://allegro.pl/oferta/{offer_id}"

                delivery = item.get('delivery', {})
                is_smart = delivery.get('isSmart', False)

                offers.append(Offer(
                    id=offer_id,
                    title=title,
                    price=price_val,
                    currency=currency,
                    seller=seller,
                    url=offer_url,
                    image_url=image_url,
                    is_smart=is_smart
                ))
            except Exception:
                continue
        return offers
