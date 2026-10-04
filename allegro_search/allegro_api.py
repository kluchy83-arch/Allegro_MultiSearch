"""Allegro REST API client with OAuth2, retry logic, rate limiting and caching."""

import requests
import json
import time
import logging
import urllib.parse
from typing import List, Optional, Dict, Any
from .models import Offer, Seller, SearchResult
from .config import AllegroConfig

logger = logging.getLogger("AllegroMultiSearch")


class AllegroAPIError(Exception):
    """Exception raised for Allegro API errors."""
    pass


class AllegroAPIClient:
    """Client for official Allegro REST API."""

    def __init__(self, config: Optional[AllegroConfig] = None):
        self.config = config or AllegroConfig.load()

        if self.config.use_sandbox:
            self.auth_url = "https://allegro.pl.allegro-sandbox.io/auth/oauth/token"
            self.api_url = "https://api.allegro.pl.allegro-sandbox.io"
        else:
            self.auth_url = "https://allegro.pl/auth/oauth/token"
            self.api_url = "https://api.allegro.pl"

        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0
        self._offers_cache: Dict[str, Any] = {}

    def test_connection(self) -> Dict[str, Any]:
        """Verify Client ID, Client Secret, OAuth token retrieval, and API ping."""
        token = self.authenticate(force=True)
        headers = self.get_headers()

        # Test request to a simple public listing query
        url = f"{self.api_url}/offers/listing"
        params = {'phrase': 'test', 'limit': 1}
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        if resp.status_code == 403:
            raise AllegroAPIError(
                "Błąd 403: Uzyskano token OAuth, ale brak dostępu do endpointu wyszukiwania.\n"
                "Upewnij się, że aplikacja została aktywowana w panelu Allegro Developer."
            )
        resp.raise_for_status()
        return {"status": "SUCCESS", "message": "Połączenie z Allegro REST API powiodło się!"}

    def authenticate(self, force: bool = False) -> str:
        """Obtain client_credentials access token."""
        if not self.config.client_id or not self.config.client_secret:
            raise AllegroAPIError("Brak ID klienta lub sekretu Allegro API (Client ID, Client Secret).")

        now = time.time()
        if not force and self._access_token and now < self._token_expires_at - 60:
            return self._access_token

        data = {'grant_type': 'client_credentials'}
        headers = {
            'User-Agent': self.config.user_agent,
            'Accept': 'application/json'
        }

        try:
            resp = requests.post(
                self.auth_url,
                auth=(self.config.client_id, self.config.client_secret),
                data=data,
                headers=headers,
                timeout=12
            )
            if resp.status_code in (401, 403):
                raise AllegroAPIError(
                    f"Błąd autoryzacji ({resp.status_code}): Nieprawidłowy Client ID lub Client Secret "
                    f"dla środowiska {'Sandbox' if self.config.use_sandbox else 'Produkcyjnego'}.\n"
                    "Sprawdź czy klucze zgadzają się z zarejestrowaną aplikacją."
                )
            resp.raise_for_status()
            token_data = resp.json()
            self._access_token = token_data.get('access_token')
            expires_in = int(token_data.get('expires_in', 43200))
            self._token_expires_at = now + expires_in
            return self._access_token
        except AllegroAPIError:
            raise
        except Exception as e:
            raise AllegroAPIError(f"Błąd uwierzytelniania w Allegro API: {e}")

    def get_headers(self) -> Dict[str, str]:
        token = self.authenticate()
        return {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.allegro.public.v1+json',
            'Content-Type': 'application/vnd.allegro.public.v1+json',
            'User-Agent': self.config.user_agent
        }

    def _execute_request(self, url: str, params: Dict[str, Any], max_retries: int = 3) -> Dict[str, Any]:
        """Execute GET request with rate limiting retry and exponential backoff."""
        cache_key = f"{url}?{urllib.parse.urlencode(params)}"
        if cache_key in self._offers_cache:
            return self._offers_cache[cache_key]

        headers = self.get_headers()
        backoff = 1.0

        for attempt in range(1, max_retries + 1):
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=12)

                # Token expired or revoked
                if resp.status_code == 401:
                    self.authenticate(force=True)
                    headers = self.get_headers()
                    resp = requests.get(url, headers=headers, params=params, timeout=12)

                # Rate limiting HTTP 429
                if resp.status_code == 429:
                    retry_after = float(resp.headers.get('Retry-After', backoff))
                    logger.warning(f"Rate limit (429) na Allegro API. Czekanie {retry_after}s...")
                    time.sleep(retry_after)
                    backoff *= 2
                    continue

                if resp.status_code == 403:
                    raise AllegroAPIError(
                        "Błąd 403 (Brak dostępu) w Allegro API. Sprawdź, czy Twoje klucze posiadają "
                        "uprawnienia do odczytu publicznych ofert Allegro."
                    )

                resp.raise_for_status()
                data = resp.json()
                self._offers_cache[cache_key] = data
                return data

            except requests.RequestException as e:
                if attempt == max_retries:
                    raise AllegroAPIError(f"Błąd połączenia z Allegro API po {max_retries} próbach: {e}")
                time.sleep(backoff)
                backoff *= 2

        raise AllegroAPIError("Błąd wykonania zapytania do Allegro API.")

    def search_offers(
        self,
        phrase: str,
        seller_id: Optional[str] = None,
        limit: int = 60,
        sort: Optional[str] = None,
        price_from: Optional[float] = None,
        price_to: Optional[float] = None,
        condition: Optional[str] = None
    ) -> List[Offer]:
        """Search offers for a phrase with optional filters."""
        params: Dict[str, Any] = {
            'phrase': phrase,
            'limit': min(limit, 100),
            'fallback': 'false'
        }
        if seller_id:
            params['seller.id'] = seller_id
        if sort:
            params['sort'] = sort
        if price_from is not None:
            params['price.from'] = str(price_from)
        if price_to is not None:
            params['price.to'] = str(price_to)
        if condition:
            params['parameter.11323'] = condition  # Allegro standard parameter id for condition

        url = f"{self.api_url}/offers/listing"
        data = self._execute_request(url, params)
        return self._parse_offers_response(data)

    def _parse_offers_response(self, data: Dict[str, Any]) -> List[Offer]:
        offers = []
        items_groups = data.get('items', {})
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
                offer_url = f"https://allegro.pl/oferta/{offer_id}"

                delivery = item.get('delivery', {})
                is_smart = delivery.get('isSmart', False)
                delivery_cost = float(delivery.get('lowestOne', {}).get('amount', 0.0)) if delivery.get('lowestOne') else 0.0

                category_id = item.get('category', {}).get('id')

                offers.append(Offer(
                    id=offer_id,
                    title=title,
                    price=price_val,
                    currency=currency,
                    seller=seller,
                    url=offer_url,
                    image_url=image_url,
                    is_smart=is_smart,
                    delivery_cost=delivery_cost,
                    category_id=category_id
                ))
            except Exception:
                continue

        return offers
