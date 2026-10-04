"""Streamlit Web UI for Allegro Multi-Item Finder."""

import streamlit as st
import pandas as pd
import json
import os
from allegro_search import MultiItemFinder, AllegroAPIClient, DemoAllegroClient, AllegroAPIError

st.set_page_config(
    page_title="Allegro Multi-Item Finder",
    page_icon="🛍️",
    layout="wide"
)

st.title("🛍️ Allegro Multi-Item Finder")
st.markdown("Znajdź sprzedawcę na Allegro, który posiada **wszystkie lub większość** poszukiwanych przez Ciebie przedmiotów! Zaoszczędź na wysyłce.")

st.sidebar.header("⚙️ Ustawienia API & Wyszukiwania")

mode = st.sidebar.radio(
    "Tryb działania",
    ["Demo (Dane testowe)", "Allegro API (Wymaga kluczy API)"]
)

client_id = ""
client_secret = ""

if mode == "Allegro API (Wymaga kluczy API)":
    client_id = st.sidebar.text_input("Client ID", value=os.environ.get("ALLEGRO_CLIENT_ID", ""), type="password")
    client_secret = st.sidebar.text_input("Client Secret", value=os.environ.get("ALLEGRO_CLIENT_SECRET", ""), type="password")
    use_sandbox = st.sidebar.checkbox("Użyj środowiska Sandbox", value=False)

st.sidebar.subheader("Filtry dopasowania")
match_mode = st.sidebar.selectbox(
    "Tryb szukania",
    ["Wszystkie przedmioty u jednego sprzedawcy (100% dopasowania)", "Częściowe dopasowanie (min. N przedmiotów)"]
)

require_all = (match_mode == "Wszystkie przedmioty u jednego sprzedawcy (100% dopasowania)")
min_items = 2
if not require_all:
    min_items = st.sidebar.number_input("Minimalna liczba dopasowanych przedmiotów", min_value=2, max_value=10, value=2)

st.subheader("1. Wprowadź poszukiwane przedmioty")

col1, col2 = st.columns([3, 1])

with col1:
    raw_input = st.text_area(
        "Wpisz nazwy/fraze przedmiotów (rozdziel odnośnikami, przecinkami lub nową linią):",
        value="wiedźmin\ndiuna\nwładca pierścieni",
        height=120
    )

keywords = [k.strip() for k in raw_input.replace(",", "\n").split("\n") if k.strip()]

search_button = st.button("🔎 Szukaj Sprzedawców", type="primary")

if search_button:
    if not keywords:
        st.warning("⚠️ Proszę wprowadzić przynajmniej jeden przedmiot.")
    else:
        st.info(f"Szukanie dla {len(keywords)} przedmiotów: **{', '.join(keywords)}**")

        client = None
        if mode == "Demo (Dane testowe)":
            client = DemoAllegroClient()
        else:
            if not client_id or not client_secret:
                st.error("❌ Musisz podać Client ID oraz Client Secret dla Allegro API!")
            else:
                try:
                    client = AllegroAPIClient(client_id=client_id, client_secret=client_secret, sandbox=use_sandbox)
                except Exception as e:
                    st.error(f"❌ Błąd inicjalizacji klienta Allegro: {e}")

        if client:
            finder = MultiItemFinder(client)
            with st.spinner("Przeszukiwanie ofert na Allegro..."):
                try:
                    matches = finder.find_sellers(
                        keywords=keywords,
                        require_all=require_all,
                        min_items=min_items
                    )
                except Exception as e:
                    st.error(f"❌ Błąd wyszukiwania: {e}")
                    matches = []

            if not matches:
                st.warning("Nie znaleziono sprzedawców spełniających kryteria.")
            else:
                st.success(f"Znaleziono **{len(matches)}** sprzedawców z pasującymi przedmiotami!")

                for idx, match in enumerate(matches, 1):
                    seller_name = match.seller.login
                    super_badge = "⭐ Super Sprzedawca" if match.seller.is_super_seller else ""

                    with st.expander(f"#{idx} Sprzedawca: **{seller_name}** {super_badge} | Dopasowania: **{match.matched_keywords_count}/{len(keywords)}** | Min. łączna cena: **{match.min_total_price:.2f} PLN**", expanded=(idx == 1)):

                        st.markdown(f"**Sugerowany zestaw od sprzedawcy {seller_name}:**")

                        table_data = []
                        for kw, offer in match.best_offers.items():
                            table_data.append({
                                "Poszukiwana fraza": kw,
                                "Tytuł oferty": offer.title,
                                "Cena": f"{offer.price:.2f} {offer.currency}",
                                "Smart": "TAK" if offer.is_smart else "NIE",
                                "Link": offer.url
                            })

                        df = pd.DataFrame(table_data)
                        st.dataframe(df, use_container_width=True)

                        st.markdown("---")
                        # Detailed offers drop down if seller has multiple for a keyword
                        st.caption("Wszystkie oferty od tego sprzedawcy podzielone na frazy:")
                        for kw, offers_list in match.offers_by_keyword.items():
                            st.write(f"• **{kw}** ({len(offers_list)} ofert):")
                            for off in offers_list:
                                smart_tag = "🚀 [SMART]" if off.is_smart else ""
                                st.markdown(f"  - [{off.title}]({off.url}) — **{off.price:.2f} {off.currency}** {smart_tag}")

                # Export section
                st.subheader("📥 Eksportuj wyniki")
                export_data = []
                for m in matches:
                    s_info = {
                        "seller": m.seller.login,
                        "is_super_seller": m.seller.is_super_seller,
                        "matched_keywords_count": m.matched_keywords_count,
                        "min_total_price": m.min_total_price,
                        "best_offers": {k: {"title": o.title, "price": o.price, "url": o.url} for k, o in m.best_offers.items()}
                    }
                    export_data.append(s_info)

                json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
                st.download_button(
                    label="Pobierz wyniki jako JSON",
                    data=json_str,
                    file_name="allegro_multi_item_results.json",
                    mime="application/json"
                )
