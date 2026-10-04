"""Allegro REST API client with full OAuth2 support (Authorization Code Flow, Device Flow, Refresh Token, Client Credentials), retry logic, rate limiting and caching."""

import requests
import json
import time
import logging
import urllib.parse
import http.server
import socketserver
import webbrowser
import threading
from typing import List, Optional, Dict, Any, Tuple
from .models import Offer, Seller, SearchResult
from .config import AllegroConfig

logger = logging.getLogger("AllegroMultiSearch")

DEFAULT_VALID_USER_AGENT = "AllegroMultiSearch/1.0"


class AllegroAPIError(Exception):
    """Exception raised for Allegro API errors."""
    pass


class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    """HTTP Request Handler for OAuth Authorization Code Flow Redirect."""
    auth_code: Optional[str] = None
    error_msg: Optional[str] = None

    def log_message(self, format, *args):
        pass  # Suppress console logging

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        # Ignore favicon requests
        if parsed.path == "/favicon.ico":
            self.send_response(404)
            self.end_headers()
            return

        if "code" in params:
            OAuthCallbackHandler.auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                "<html><body style='font-family:sans-serif; text-align:center; padding-top:50px;'>"
                "<h1 style='color:green;'>✅ Logowanie powiodło się!</h1>"
                "<p>Możesz zamknąć tę kartę i wrócić do aplikacji <b>Allegro MultiSearch</b>.</p>"
                "</body></html>".encode("utf-8")
            )
        else:
            err = params.get("error_description", ["Brak kodu autoryzacyjnego"])[0]
            OAuthCallbackHandler.error_msg = err
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"<html><body><h1>Błąd autoryzacji: {err}</h1></body></html>".encode("utf-8"))


class AllegroAPIClient:
    """Client for official Allegro REST API."""

    def __init__(self, config: Optional[AllegroConfig] = None):
        self.config = config or AllegroConfig.load()

        if self.config.use_sandbox:
            self.domain = "allegro.pl.allegro-sandbox.io"
            self.auth_url = f"https://{self.domain}/auth/oauth/token"
            self.authorize_url = f"https://{self.domain}/auth/oauth/authorize"
            self.device_auth_url = f"https://{self.domain}/auth/oauth/device"
            self.api_url = f"https://api.{self.domain}"
        else:
            self.domain = "allegro.pl"
            self.auth_url = f"https://{self.domain}/auth/oauth/token"
            self.authorize_url = f"https://{self.domain}/auth/oauth/authorize"
            self.device_auth_url = f"https://{self.domain}/auth/oauth/device"
            self.api_url = f"https://api.{self.domain}"

        self._offers_cache: Dict[str, Any] = {}

    def get_user_agent(self) -> str:
        ua = (self.config.user_agent or "").strip()
        if not ua:
            return DEFAULT_VALID_USER_AGENT
        return ua

    # --- OAUTH REFRESH & AUTH ---
    def refresh_user_token(self) -> str:
        """Refresh user access token using refresh_token."""
        if not self.config.user_refresh_token:
            raise AllegroAPIError("Brak user_refresh_token. Zaloguj konto Allegro ponownie.")

        headers = {
            'User-Agent': self.get_user_agent(),
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.config.user_refresh_token
        }

        try:
            resp = requests.post(
                self.auth_url,
                auth=(self.config.client_id, self.config.client_secret),
                data=data,
                headers=headers,
                timeout=12
            )
            token_data = resp.json()
            if resp.status_code == 200:
                self.config.user_access_token = token_data.get('access_token', '')
                self.config.user_refresh_token = token_data.get('refresh_token', self.config.user_refresh_token)
                self.config.save()
                return self.config.user_access_token
            else:
                err_desc = token_data.get('error_description') or token_data.get('error') or resp.text
                raise AllegroAPIError(f"Błąd odświeżania tokena: {err_desc}")
        except AllegroAPIError:
            raise
        except Exception as e:
            raise AllegroAPIError(f"Nie udało się odświeżyć tokena: {e}")

    # --- OAUTH METHOD 1: Authorization Code Flow ---
    def start_authorization_code_flow(self, redirect_uri: str = "http://localhost:8080/callback", port: int = 8080) -> str:
        """Start local HTTP server, open browser for user login, and exchange code for token."""
        OAuthCallbackHandler.auth_code = None
        OAuthCallbackHandler.error_msg = None

        params = {
            "response_type": "code",
            "client_id": self.config.client_id,
            "redirect_uri": redirect_uri
        }
        url = f"{self.authorize_url}?{urllib.parse.urlencode(params)}"
        webbrowser.open(url)

        try:
            class ReusableTCPServer(socketserver.TCPServer):
                allow_reuse_address = True

            with ReusableTCPServer(("localhost", port), OAuthCallbackHandler) as httpd:
                httpd.timeout = 1.0
                start_time = time.time()
                while time.time() - start_time < 120.0:
                    httpd.handle_request()
                    if OAuthCallbackHandler.auth_code or OAuthCallbackHandler.error_msg:
                        break
        except Exception as e:
            raise AllegroAPIError(f"Nie udało się uruchomić lokalnego serwera autoryzacji na porcie {port}: {e}")

        if OAuthCallbackHandler.error_msg:
            raise AllegroAPIError(f"Błąd logowania: {OAuthCallbackHandler.error_msg}")

        code = OAuthCallbackHandler.auth_code
        if not code:
            raise AllegroAPIError("Przekroczono czas oczekiwania (2 minuty) na logowanie w przeglądarce.")

        return self._exchange_code_for_token(code, redirect_uri)

    def _exchange_code_for_token(self, code: str, redirect_uri: str) -> str:
        headers = {
            'User-Agent': self.get_user_agent(),
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri
        }

        try:
            resp = requests.post(
                self.auth_url,
                auth=(self.config.client_id, self.config.client_secret),
                data=data,
                headers=headers,
                timeout=12
            )
            token_data = resp.json()
            if resp.status_code == 200:
                self.config.user_access_token = token_data.get('access_token', '')
                self.config.user_refresh_token = token_data.get('refresh_token', '')
                self.config.save()
                return self.config.user_access_token
            else:
                err_desc = token_data.get('error_description') or token_data.get('error') or resp.text
                raise AllegroAPIError(f"Błąd wymiany kodu na token: {err_desc}")
        except AllegroAPIError:
            raise
        except Exception as e:
            raise AllegroAPIError(f"Błąd podczas uzyskiwania tokena: {e}")

    # --- OAUTH METHOD 2: Device Flow ---
    def initiate_device_flow(self) -> Dict[str, Any]:
        """Initiate OAuth Device Flow."""
        if not self.config.client_id or not self.config.client_secret:
            raise AllegroAPIError("Brak Client ID lub Client Secret.")

        headers = {
            'User-Agent': self.get_user_agent(),
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {'client_id': self.config.client_id}

        try:
            resp = requests.post(
                self.device_auth_url,
                auth=(self.config.client_id, self.config.client_secret),
                data=data,
                headers=headers,
                timeout=12
            )
            data_res = resp.json()
            if resp.status_code != 200:
                err_desc = data_res.get('error_description') or data_res.get('error') or resp.text
                raise AllegroAPIError(
                    f"Błąd Allegro Device Flow (HTTP {resp.status_code}): {err_desc}\n\n"
                    "Wskazówka: Jeśli Twoja aplikacja w Allegro Developer Portal ma typ 'Aplikacja Webowa', "
                    "użyj logowania metodą 'Przeglądarka (Web Flow)'."
                )
            return data_res
        except AllegroAPIError:
            raise
        except Exception as e:
            raise AllegroAPIError(f"Błąd inicjalizacji OAuth Device Flow: {e}")

    def poll_device_token(self, device_code: str) -> Dict[str, Any]:
        headers = {
            'User-Agent': self.get_user_agent(),
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
            'device_code': device_code
        }

        try:
            resp = requests.post(
                self.auth_url,
                auth=(self.config.client_id, self.config.client_secret),
                data=data,
                headers=headers,
                timeout=12
            )
            token_data = resp.json()
            if resp.status_code == 200:
                self.config.user_access_token = token_data.get('access_token', '')
                self.config.user_refresh_token = token_data.get('refresh_token', '')
                self.config.save()
                return token_data
            else:
                error = token_data.get('error', 'authorization_pending')
                return {'error': error, 'message': token_data.get('error_description', '')}
        except Exception as e:
            raise AllegroAPIError(f"Błąd sprawdzania statusu autoryzacji: {e}")

    # --- TEST CONNECTION ---
    def test_connection(self) -> Dict[str, Any]:
        """Test OAuth credentials validity and API connection."""
        if not self.config.client_id or not self.config.client_secret:
            raise AllegroAPIError("Brak Client ID lub Client Secret.")

        # First verify client_credentials token request
        data = {'grant_type': 'client_credentials'}
        headers = {
            'User-Agent': self.get_user_agent(),
            'Accept': 'application/json'
        }
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
                f"dla środowiska {'Sandbox' if self.config.use_sandbox else 'Produkcyjnego'}."
            )
        resp.raise_for_status()

        # If user access token exists, test GET /offers/listing
        if self.config.user_access_token:
            try:
                headers = self.get_headers()
                url = f"{self.api_url}/offers/listing"
                params = {'phrase': 'test', 'limit': 1}
                r_list = requests.get(url, headers=headers, params=params, timeout=10)

                # If token expired, try refreshing once
                if (r_list.status_code in (401, 403)) and self.config.user_refresh_token:
                    try:
                        self.refresh_user_token()
                        headers = self.get_headers()
                        r_list = requests.get(url, headers=headers, params=params, timeout=10)
                    except Exception:
                        pass

                if r_list.status_code == 200:
                    return {"status": "SUCCESS", "message": "Połączenie z Allegro REST API powiodło się! Token użytkownika jest aktywny i ma dostęp do serwisu."}
                elif r_list.status_code == 403:
                    err_json = r_list.json() if r_list.headers.get("content-type", "").startswith("application/") else {}
                    err_msg = err_json.get("error_description") or err_json.get("message") or r_list.text[:200]
                    raise AllegroAPIError(
                        f"Błąd 403 na /offers/listing: {err_msg}\n\n"
                        "Wskazówka: Zaloguj się ponownie przyciskiem 'Zaloguj w Przeglądarce (Web Flow)'."
                    )
                else:
                    r_list.raise_for_status()
            except AllegroAPIError:
                raise
            except Exception as e:
                raise AllegroAPIError(f"Błąd weryfikacji tokena użytkownika: {e}")

        return {
            "status": "SUCCESS",
            "message": "Client ID oraz Client Secret są poprawne!\n\n"
                       "Uwaga: Zaloguj konto Allegro przyciskiem 'Zaloguj w Przeglądarce (Web Flow)', "
                       "aby powiązać token użytkownika dla pełnego dostępu do ofert."
        }

    def authenticate(self, force: bool = False) -> str:
        if self.config.user_access_token and not force:
            return self.config.user_access_token

        if self.config.user_refresh_token:
            try:
                return self.refresh_user_token()
            except Exception:
                pass

        data = {'grant_type': 'client_credentials'}
        headers = {
            'User-Agent': self.get_user_agent(),
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
                    f"dla środowiska {'Sandbox' if self.config.use_sandbox else 'Produkcyjnego'}."
                )
            resp.raise_for_status()
            token_data = resp.json()
            return token_data.get('access_token', '')
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
            'User-Agent': self.get_user_agent()
        }

    def _execute_request(self, url: str, params: Dict[str, Any], max_retries: int = 3) -> Dict[str, Any]:
        cache_key = f"{url}?{urllib.parse.urlencode(params)}"
        if cache_key in self._offers_cache:
            return self._offers_cache[cache_key]

        headers = self.get_headers()
        backoff = 1.0

        for attempt in range(1, max_retries + 1):
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=12)

                if resp.status_code == 401:
                    if self.config.user_refresh_token:
                        try:
                            self.refresh_user_token()
                        except Exception:
                            self.authenticate(force=True)
                    else:
                        self.authenticate(force=True)

                    headers = self.get_headers()
                    resp = requests.get(url, headers=headers, params=params, timeout=12)

                if resp.status_code == 429:
                    retry_after = float(resp.headers.get('Retry-After', backoff))
                    logger.warning(f"Rate limit (429) na Allegro API. Czekanie {retry_after}s...")
                    time.sleep(retry_after)
                    backoff *= 2
                    continue

                if resp.status_code == 403:
                    # Try refreshing user token if available
                    if self.config.user_refresh_token and attempt == 1:
                        try:
                            self.refresh_user_token()
                            headers = self.get_headers()
                            resp = requests.get(url, headers=headers, params=params, timeout=12)
                            if resp.status_code == 200:
                                data = resp.json()
                                self._offers_cache[cache_key] = data
                                return data
                        except Exception:
                            pass

                    err_json = resp.json() if resp.headers.get("content-type", "").startswith("application/") else {}
                    err_msg = err_json.get("error_description") or err_json.get("message") or resp.text[:200]
                    raise AllegroAPIError(
                        f"Błąd 403 Forbidden na endpointzie GET /offers/listing ({err_msg}).\n"
                        "Sprawdź pole User-Agent w Konfiguracji lub zaloguj konto przyciskiem 'Zaloguj w Przeglądarce (Web Flow)'."
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
            params['parameter.11323'] = condition

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
