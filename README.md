# 🛍️ Allegro MultiSearch

Kompletna aplikacja desktopowa w języku Python służąca do jednoczesnego wyszukiwania wielu produktów na Allegro i automatycznego znajdowania sprzedawców oferujących pełne zestawy w najniższych cenach.

---

## 🔑 Dlaczego występował błąd HTTP 403 Forbidden?

Endpoint wyszukiwania ofert **`GET /offers/listing`** w oficjalnym REST API Allegro:
- **Wymaga tokena użytkownika (`bearer-token-for-user`)**, uzyskiwanego np. za pomocą przepływu **OAuth Device Flow**.
- **Odrzuca tokeny aplikacji (`client_credentials` / `bearer-token-for-application`)** i zwraca dla nich status **HTTP 403 Forbidden**.

Aplikacja wspiera pełny przepływ **OAuth Device Flow**, umożliwiający jednorazową autoryzację konta Allegro w przeglądarce bez podawania haseł w aplikacji!

---

## 🚀 Główne Funkcje

- **Równoległe wyszukiwanie zestawu produktów**: Podaj dowolną liczbę poszukiwanych przedmiotów (np. *LEGO Technic 42154*, *Raspberry Pi 5 8GB*, *karta microSD 256GB*, *kabel HDMI 2.1*).
- **Obsługa OAuth Device Flow**: Wygodny przycisk **„Zaloguj konto Allegro (Device Flow)”** w zakładce Konfiguracja.
- **Ranking sprzedawców wg pokrycia i ceny**:
  1. Największa liczba dostępnych produktów ($N/M$).
  2. Najniższa cena łączna wraz z szacowanym kosztem dostawy (z uwzględnieniem Allegro Smart!).
- **Analiza kombinacji wielu sprzedawców**: Jeśli żaden sprzedawca nie posiada 100% produktów, aplikacja wyznacza optymalne połączenie (np. *Sprzedawca A + Sprzedawca B = 100% zestawu*) przy najniższym łącznym koszcie.
- **Eksport wyników**: Zapis wyników do formatów **CSV**, **Excel (.xlsx)**, **JSON** oraz **Kopiowanie do schowka**.

---

## ⚙️ Wymagania i Konfiguracja Allegro API

1. Zarejestruj aplikację w [Allegro Developer Apps](https://apps.developer.allegro.pl/).
2. W zakładce **⚙️ Konfiguracja Allegro API** wklej swój `Client ID` oraz `Client Secret`.
3. Kliknij **„🔐 Zaloguj konto Allegro (Device Flow)”** i zaakceptuj dostęp w przeglądarce.

---

## 💻 Uruchamianie z kodu źródłowego

```bash
pip install -r requirements.txt
python3 gui.py
```

---

## 🧪 Testy Jednostkowe

```bash
python3 -m unittest discover tests
```

---

## 📄 Licencja

MIT License
