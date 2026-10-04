# 🛍️ Allegro MultiSearch

Kompletna aplikacja desktopowa w języku Python służąca do jednoczesnego wyszukiwania wielu produktów na Allegro i automatycznego znajdowania sprzedawców oferujących pełne zestawy w najniższych cenach.

---

## 🚀 Główne Funkcje

- **Równoległe wyszukiwanie zestawu produktów**: Podaj dowolną liczbę poszukiwanych przedmiotów (np. *LEGO Technic 42154*, *Raspberry Pi 5 8GB*, *karta microSD 256GB*, *kabel HDMI 2.1*).
- **Ranking sprzedawców wg pokrycia i ceny**:
  1. Największa liczba dostępnych produktów ($N/M$).
  2. Najniższa cena łączna wraz z szacowanym kosztem dostawy (z uwzględnieniem Allegro Smart!).
- **Analiza kombinacji wielu sprzedawców**: Jeśli żaden sprzedawca nie posiada 100% produktów, aplikacja wyznacza optymalne połączenie (np. *Sprzedawca A + Sprzedawca B = 100% zestawu*) przy najniższym łącznym koszcie.
- **Bezpieczne przechowywanie kluczy API**: Obsługa zmiennych środowiskowych `.env` oraz lokalnego szyfrowania konfiguracji. Pole Client Secret jest ukryte i nigdy nie trafia do kodu źródłowego.
- **Test połączenia z Allegro API**: Przycisk pozwalający błyskawicznie sprawdzić poprawność Client ID, Client Secret oraz tokena OAuth.
- **Dopasowywanie ofert i filtrowanie**: Ocenianie jakości dopasowania (*Dopasowanie wysokie*, *Dopasowanie średnie*, *Dopasowanie niskie*), opcjonalny budżet, słowa wymagane, słowa wykluczone oraz kod EAN.
- **Eksport wyników**: Zapis wyników do formatów **CSV**, **Excel (.xlsx)**, **JSON** oraz **Kopiowanie do schowka**.
- **Wymagania Allegro REST API**: Komunikacja wyłącznie przez oficjalne REST API. Zerowe użycie scrapowania HTML czy Selenium.

---

## ⚙️ Wymagania i Konfiguracja Allegro API

Aplikacja wymaga oficjalnych kluczy dostępowych zarejestrowanych w [Allegro Developer Apps](https://apps.developer.allegro.pl/):

1. **ALLEGRO_CLIENT_ID**
2. **ALLEGRO_CLIENT_SECRET**
3. **ALLEGRO_USER_AGENT**

### Konfiguracja w pliku `.env` (Opcjonalnie)

Utwórz plik `.env` na podstawie `.env.example`:
```env
ALLEGRO_CLIENT_ID=twój_client_id
ALLEGRO_CLIENT_SECRET=twój_client_secret
ALLEGRO_USER_AGENT=AllegroMultiSearch/1.0 (Windows NT 10.0; Win64; x64)
```

Wszystkie parametry można także wygodnie podać bezpośrednio w zakładce **⚙️ Konfiguracja Allegro API** w aplikacji i kliknąć **„Zapamiętaj Konfigurację”**.

---

## 🪟 Plik Wykonywalny (.exe) dla Windows x64

Dla użytkowników systemu Windows, aplikację można uruchomić bez instalowania Pythona:

1. **Automatyczna kompilacja na GitHubie**:
   - Po opublikowaniu na GitHubie plik `AllegroMultiItemFinderGUI.exe` jest automatycznie budowany przez **GitHub Actions** i dostępny w zakładce **Actions -> Artifacts**.

2. **Samodzielna kompilacja na Windows**:
   - Uruchom plik `build_windows.bat`:
     ```cmd
     build_windows.bat
     ```
   - Gotowy plik okienkowy znajdziesz w `dist/AllegroMultiItemFinderGUI.exe`.

---

## 💻 Uruchamianie z kodu źródłowego

Instalacja wymaganych bibliotek:
```bash
pip install -r requirements.txt
```

Uruchomienie interfejsu graficznego (GUI):
```bash
python3 gui.py
```

Uruchomienie interfejsu webowego (Streamlit):
```bash
streamlit run app.py
```

Uruchomienie konsolowe (CLI):
```bash
python3 cli.py --client-id "twój_id" --client-secret "twój_secret" "LEGO Technic" "Raspberry Pi"
```

---

## 🧪 Testy Jednostkowe

Uruchomienie testów z mockowaniem zapytań API:
```bash
python3 -m unittest discover tests
```

---

## 📄 Licencja

MIT License
