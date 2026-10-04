# 🛍️ Allegro Multi-Item Finder

Narzędzie w języku Python służące do jednoczesnego wyszukiwania 2 lub więcej przedmiotów u **jednego sprzedawcy na Allegro**.
Pozwala to zaoszczędzić czas oraz koszty dostawy (np. skorzystać z jednej paczki w ramach Allegro Smart!).

Narzędzie oferuje interfejs wiersza poleceń (**CLI**) oraz interfejs graficzny w przeglądarce (**Web UI / Streamlit**).

---

## 🚀 Funkcje

- **Wyszukiwanie jednoczesne**: Podaj listę produktów (np. `Wiedźmin`, `Diuna`, `Myszka`), a narzędzie znajdzie sprzedawców posiadających je wszystkie.
- **Obsługa częściowego dopasowania**: Możliwość znalezienia sprzedawców posiadających np. min. 2 z 3 szukanych przedmiotów.
- **Obliczanie najniższej łącznej ceny**: Automatyczny wybór najtańszego zestawu ofert u każdego ze sprzedawców.
- **Eksport wyników**: Zapis wyników do plików **JSON** i **CSV**.
- **Tryb DEMO / Offline**: Działa od razu bez podawania kluczy API Allegro na przykładowych danych testowych.
- **Wsparcie dla oficjalnego Allegro REST API**: Obsługa autoryzacji OAuth (`client_credentials`) i pobieranie na żywo ofert z Allegro.

---

## 📦 Instalacja

1. Sklonuj repozytorium:
   ```bash
   git clone https://github.com/twoj-login/allegro-multi-item-finder.git
   cd allegro-multi-item-finder
   ```

2. Zainstaluj wymagane zależności:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🪟 Wersja Plik Wykonywalny (.exe) dla Windows x64

Dla użytkowników systemu Windows, narzędzie można uruchomić jako gotowy plik `.exe` bez konieczności instalowania Pythona:

1. **Automatyczna kompilacja na GitHubie**:
   - Po wysłaniu kodu na GitHub, plik `AllegroMultiItemFinder.exe` jest automatycznie budowany przez **GitHub Actions** i dostępny do pobrania w zakładce **Actions -> Artifacts**.

2. **Samodzielna kompilacja na Windows**:
   - Uruchom skrypt `build_windows.bat` lub wykonaj komendę:
     ```cmd
     pip install pyinstaller -r requirements.txt
     pyinstaller --onefile --name="AllegroMultiItemFinder" cli.py
     ```
   - Gotowy plik `.exe` znajdziesz w folderze `dist/AllegroMultiItemFinder.exe`.

---

## 💻 Użycie

### 1. Interfejs konsolowy (CLI)

#### Tryb Demo (bez kluczy API):
```bash
python3 cli.py --demo "wiedźmin" "diuna"
```

#### Z eksportem do JSON / CSV:
```bash
python3 cli.py --demo --export-json wyniki.json --export-csv wyniki.csv "wiedźmin" "diuna"
```

#### Częściowe dopasowanie (min. 2 z podanych przedmiotów):
```bash
python3 cli.py --demo --allow-partial --min-items 2 "wiedźmin" "diuna" "władca pierścieni"
```

#### Użycie z oficjalnym API Allegro:
Ustaw zmienne środowiskowe z kluczami aplikacji zarejestrowanej w [Allegro Developer](https://apps.developer.allegro.pl/):
```bash
export ALLEGRO_CLIENT_ID="twój_client_id"
export ALLEGRO_CLIENT_SECRET="twój_client_secret"

python3 cli.py "ksiazka" "kawiarka"
```

---

### 2. Aplikacja Webowa (Streamlit)

Uruchom interfejs w przeglądarce:
```bash
streamlit run app.py
```
Aplikacja otworzy się automatycznie pod adresem `http://localhost:8501`.

W interfejsie możesz:
- Wprowadzać szukane frazy w polu tekstowym.
- Wybierać między trybem Demo a produkcyjnym Allegro API.
- Dostosowywać parametry dopasowania.
- Przeglądać sugerowane zestawy oraz eksportować wyniki do pliku JSON.

---

## 🧪 Testy

Aby uruchomić testy jednostkowe:
```bash
python3 -m unittest discover tests
```

---

## 📄 Licencja

MIT License
