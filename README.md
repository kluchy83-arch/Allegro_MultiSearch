# 🛍️ Allegro Multi-Item Finder

Narzędzie w języku Python służące do jednoczesnego wyszukiwania 2 lub więcej przedmiotów u **jednego sprzedawcy na Allegro**.
Pozwala to zaoszczędzić czas oraz koszty dostawy (np. skorzystać z jednej paczki w ramach Allegro Smart!).

Narzędzie oferuje okienkowy interfejs graficzny (**Desktop GUI** w Tkinter), interfejs webowy (**Streamlit**) oraz linię poleceń (**CLI**).

---

## 🚀 Funkcje

- **Wyszukiwanie jednoczesne**: Podaj listę produktów (np. `Wiedźmin`, `Diuna`, `Myszka`), a narzędzie znajdzie sprzedawców posiadających je wszystkie.
- **Interfejs Graficzny GUI (Desktop)**: Wpisz swoje `Client ID` oraz `Client Secret` z Allegro Developer bezpośrednio w formularzu okienkowym.
- **Obsługa częściowego dopasowania**: Możliwość znalezienia sprzedawców posiadających np. min. 2 z 3 szukanych przedmiotów.
- **Obliczanie najniższej łącznej ceny**: Automatyczny wybór najtańszego zestawu ofert u każdego ze sprzedawców.
- **Eksport wyników**: Zapis wyników do plików **JSON** i **CSV**.
- **Kompilacja do EXE (Windows x64)**: Gotowa wersja bez konieczności instalowania Pythona.

---

## 🪟 Plik Wykonywalny (.exe) dla Windows x64

Dla użytkowników systemu Windows, narzędzie działa jako samodzielna aplikacja okienkowa `.exe`:

1. **Automatyczna kompilacja na GitHubie**:
   - Po opublikowaniu na GitHubie plik `AllegroMultiItemFinderGUI.exe` jest automatycznie budowany przez **GitHub Actions** i dostępny do pobrania w zakładce **Actions -> Artifacts**.

2. **Samodzielna kompilacja na Windows**:
   - Uruchom skrypt `build_windows.bat` lub wykonaj komendę w konsoli:
     ```cmd
     pip install -r requirements.txt pyinstaller
     pyinstaller --noconsole --onefile --name="AllegroMultiItemFinderGUI" gui.py
     ```
   - Gotowy plik okienkowy `.exe` znajdziesz w folderze `dist/AllegroMultiItemFinderGUI.exe`.

---

## 💻 Uruchamianie z kodu źródłowego

### 1. Aplikacja Okienkowa GUI (Tkinter)
```bash
python3 gui.py
```

### 2. Aplikacja Webowa (Streamlit)
```bash
streamlit run app.py
```

### 3. Interfejs Konsolowy (CLI)
```bash
python3 cli.py --client-id "twój_client_id" --client-secret "twój_client_secret" "ksiazka" "kawiarka"
```

---

## 🔑 Jak uzyskać Client ID oraz Client Secret?

1. Zaloguj się na swoje konto Allegro na stronie [Allegro Developer Apps](https://apps.developer.allegro.pl/).
2. Kliknij **Zarejestruj nową aplikację**.
3. Wybierz typ aplikacji (np. *Aplikacja osobista / REST API*).
4. Skopiuj wygenerowany **Client ID** oraz **Client Secret** i wklej w pola aplikacji.

---

## 🧪 Testy

Aby uruchomić testy jednostkowe:
```bash
python3 -m unittest discover tests
```

---

## 📄 Licencja

MIT License
