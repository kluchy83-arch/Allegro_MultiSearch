"""Streamlit Web UI for Allegro MultiSearch."""

import streamlit as st
import pandas as pd
import json
import os
from allegro_search import MultiItemFinder, AllegroAPIClient, AllegroConfig, ProductQuery, AllegroAPIError

st.set_page_config(
    page_title="Allegro MultiSearch",
    page_icon="🛍️",
    layout="wide"
)

st.title("🛍️ Allegro MultiSearch")
st.markdown("Znajdź sprzedawcę na Allegro, który posiada **wszystkie lub większość** poszukiwanych przez Ciebie przedmiotów! Zaoszczędź na wysyłce.")

st.sidebar.header("🔑 Dane Logowania Allegro API")

config = AllegroConfig.load()

client_id = st.sidebar.text_input("Client ID", value=config.client_id, type="password")
client_secret = st.sidebar.text_input("Client Secret", value=config.client_secret, type="password")
use_sandbox = st.sidebar.checkbox("Użyj środowiska Sandbox", value=config.use_sandbox)

if client_id and client_secret:
    config.client_id = client_id
    config.client_secret = client_secret
    config.use_sandbox = use_sandbox

st.subheader("1. Wprowadź poszukiwane przedmioty")

col1, col2 = st.columns([3, 1])

with col1:
    raw_input = st.text_area(
        "Wpisz nazwy/fraze przedmiotów (rozdziel odnośnikami, przecinkami lub nową linią):",
        value="LEGO Technic 42154\nRaspberry Pi 5 8GB\nkarta microSD 256GB",
        height=120
    )

keywords = [k.strip() for k in raw_input.replace(",", "\n").split("\n") if k.strip()]

search_button = st.button("🔎 Szukaj Sprzedawców", type="primary")

if search_button:
    if not keywords:
        st.warning("⚠️ Proszę wprowadzić przynajmniej jeden przedmiot.")
    elif not config.client_id or not config.client_secret:
        st.error("❌ Musisz podać Client ID oraz Client Secret dla Allegro API!")
    else:
        st.info(f"Szukanie dla {len(keywords)} przedmiotów: **{', '.join(keywords)}**")

        try:
            client = AllegroAPIClient(config)
            client.authenticate()
            queries = [ProductQuery(name=k) for k in keywords]
            finder = MultiItemFinder(client)

            with st.spinner("Przeszukiwanie ofert na Allegro..."):
                matches = finder.find_sellers(queries=queries)

            if not matches:
                st.warning("Nie znaleziono sprzedawców spełniających kryteria.")
            else:
                st.success(f"Znaleziono **{len(matches)}** sprzedawców z pasującymi przedmiotami!")

                for idx, match in enumerate(matches, 1):
                    seller_name = match.seller.login
                    super_badge = "⭐ Super Sprzedawca" if match.seller.is_super_seller else ""

                    with st.expander(f"#{idx} Sprzedawca: **{seller_name}** {super_badge} | Pokrycie: **{match.matched_count}/{len(keywords)}** | Razem z dostawą: **{match.total_price_with_delivery:.2f} PLN**", expanded=(idx == 1)):

                        st.markdown(f"**Sugerowany zestaw od sprzedawcy {seller_name}:**")

                        table_data = []
                        for q_name, m_offer in match.best_offers.items():
                            offer = m_offer.offer
                            table_data.append({
                                "Poszukiwana fraza": q_name,
                                "Tytuł oferty": offer.title,
                                "Cena": f"{offer.price:.2f} {offer.currency}",
                                "Smart": "TAK" if offer.is_smart else "NIE",
                                "Link": offer.url
                            })

                        df = pd.DataFrame(table_data)
                        st.dataframe(df, use_container_width=True)

                st.subheader("📥 Eksportuj wyniki")
                export_data = []
                for m in matches:
                    s_info = {
                        "seller": m.seller.login,
                        "is_super_seller": m.seller.is_super_seller,
                        "matched_count": m.matched_count,
                        "grand_total": m.total_price_with_delivery,
                        "best_offers": {k: {"title": v.offer.title, "price": v.offer.price, "url": v.offer.url} for k, v in m.best_offers.items()}
                    }
                    export_data.append(s_info)

                json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
                st.download_button(
                    label="Pobierz wyniki jako JSON",
                    data=json_str,
                    file_name="allegro_multisearch_results.json",
                    mime="application/json"
                )

        except Exception as e:
            st.error(f"❌ Błąd autoryzacji lub wyszukiwania w Allegro API: {e}")
