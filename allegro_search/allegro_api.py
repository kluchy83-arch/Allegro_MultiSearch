"""Allegro API client and demo provider."""

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
            raise AllegroAPIError("Brak ID klienta lub sekretu Allegro API (client_id, client_secret).")

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


class DemoAllegroClient:
    """Mock/Demo client providing rich sample data for testing and offline usage."""

    def __init__(self):
        self.sellers = [
            Seller(id="101", login="Ksiegarnia_Przecena", is_super_seller=True, rating=4.95),
            Seller(id="102", login="SuperSklep_PL", is_super_seller=True, rating=4.88),
            Seller(id="103", login="Antykwariat_Online", is_super_seller=False, rating=4.70),
            Seller(id="104", login="Tech_Komputer_Store", is_super_seller=True, rating=4.99),
        ]

        # Preset catalog of offers per query keyword and seller
        self.catalog = {
            "wiedźmin": [
                Offer("w1", "Wiedźmin Tom 1 Ostatnie Życzenie - A. Sapkowski", 34.90, "PLN", self.sellers[0], "https://allegro.pl/oferta/w1", is_smart=True),
                Offer("w2", "Wiedźmin Ostatnie Życzenie twarda oprawa", 39.00, "PLN", self.sellers[1], "https://allegro.pl/oferta/w2", is_smart=True),
                Offer("w3", "Wiedźmin Tom 1 wydanie kieszonkowe", 29.99, "PLN", self.sellers[2], "https://allegro.pl/oferta/w3", is_smart=False),
            ],
            "diuna": [
                Offer("d1", "Diuna Tom 1 - Frank Herbert - Książka", 42.50, "PLN", self.sellers[0], "https://allegro.pl/oferta/d1", is_smart=True),
                Offer("d2", "Diuna Wydanie Ilustrowane Frank Herbert", 55.00, "PLN", self.sellers[1], "https://allegro.pl/oferta/d2", is_smart=True),
                Offer("d3", "Diuna - Klasyka SF", 38.00, "PLN", self.sellers[2], "https://allegro.pl/oferta/d3", is_smart=False),
            ],
            "władca pierścieni": [
                Offer("p1", "Władca Pierścieni Drużyna Pierścienia", 45.00, "PLN", self.sellers[0], "https://allegro.pl/oferta/p1", is_smart=True),
                Offer("p2", "Władca Pierścieni Trylogia w 1 tomie", 89.90, "PLN", self.sellers[1], "https://allegro.pl/oferta/p2", is_smart=True),
            ],
            "myszka": [
                Offer("m1", "Myszka Bezprzewodowa Logitech M185", 49.99, "PLN", self.sellers[3], "https://allegro.pl/oferta/m1", is_smart=True),
                Offer("m2", "Myszka komputerowa USB Ergonomiczna", 25.00, "PLN", self.sellers[1], "https://allegro.pl/oferta/m2", is_smart=True),
            ],
            "klawiatura": [
                Offer("k1", "Klawiatura Mechaniczna RGB USB", 129.00, "PLN", self.sellers[3], "https://allegro.pl/oferta/k1", is_smart=True),
                Offer("k2", "Klawiatura Przewodowa Buro", 35.00, "PLN", self.sellers[1], "https://allegro.pl/oferta/k2", is_smart=True),
            ]
        }

    def search_offers(self, phrase: str, seller_id: Optional[str] = None, limit: int = 60) -> List[Offer]:
        phrase_lower = phrase.lower().strip()
        matched_offers = []

        for key, offers in self.catalog.items():
            if key in phrase_lower or phrase_lower in key:
                matched_offers.extend(offers)

        # Fallback dynamic mock offer generator if custom query isn't in standard mock catalog
        if not matched_offers:
            matched_offers = [
                Offer(f"gen_1_{phrase_lower}", f"Przedmiot {phrase.title()} - Najlepsza Cena", 29.99, "PLN", self.sellers[0], f"https://allegro.pl/oferta/gen1-{phrase_lower}", is_smart=True),
                Offer(f"gen_2_{phrase_lower}", f"{phrase.title()} - Okazja Promocja", 32.50, "PLN", self.sellers[1], f"https://allegro.pl/oferta/gen2-{phrase_lower}", is_smart=True),
            ]

        if seller_id:
            matched_offers = [o for o in matched_offers if o.seller.id == seller_id or o.seller.login == seller_id]

        return matched_offers[:limit]
