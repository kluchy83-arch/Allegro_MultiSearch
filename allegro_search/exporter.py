"""Exporter module for saving search results in CSV, Excel, JSON and clipboard formats."""

import json
import csv
from typing import List, Dict, Any
from .models import SellerMatch, MultiSellerCombination


class DataExporter:
    """Exports Allegro MultiSearch results to various file formats."""

    @staticmethod
    def to_json_data(matches: List[SellerMatch]) -> List[Dict[str, Any]]:
        data = []
        for m in matches:
            data.append({
                "seller": m.seller.login,
                "is_super_seller": m.seller.is_super_seller,
                "matched_count": m.matched_count,
                "items_total_price": m.items_total_price,
                "delivery_cost": m.delivery_cost,
                "grand_total": m.total_price_with_delivery,
                "offers": {k: {"title": v.offer.title, "price": v.offer.price, "url": v.offer.url, "confidence": v.offer.match_confidence.value} for k, v in m.best_offers.items()}
            })
        return data

    @classmethod
    def export_json(cls, matches: List[SellerMatch], filepath: str):
        data = cls.to_json_data(matches)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def export_csv(cls, matches: List[SellerMatch], filepath: str):
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Sprzedawca", "SuperSprzedawca", "Liczba Produktów", "Suma Produktów (zł)", "Dostawa (zł)", "Łącznie (zł)", "Fraza", "Tytuł Oferty", "Cena (zł)", "Status Dopasowania", "URL"])

            for m in matches:
                for q_name, m_offer in m.best_offers.items():
                    writer.writerow([
                        m.seller.login,
                        "Tak" if m.seller.is_super_seller else "Nie",
                        m.matched_count,
                        m.items_total_price,
                        m.delivery_cost,
                        m.total_price_with_delivery,
                        q_name,
                        m_offer.offer.title,
                        m_offer.offer.price,
                        m_offer.offer.match_confidence.value,
                        m_offer.offer.url
                    ])

    @classmethod
    def export_excel(cls, matches: List[SellerMatch], filepath: str):
        import pandas as pd
        rows = []
        for m in matches:
            for q_name, m_offer in m.best_offers.items():
                rows.append({
                    "Sprzedawca": m.seller.login,
                    "SuperSprzedawca": "Tak" if m.seller.is_super_seller else "Nie",
                    "Dopasowania": m.matched_count,
                    "Suma Produktów (zł)": m.items_total_price,
                    "Dostawa (zł)": m.delivery_cost,
                    "Łącznie (zł)": m.total_price_with_delivery,
                    "Szukana Fraza": q_name,
                    "Tytuł Oferty": m_offer.offer.title,
                    "Cena Oferty (zł)": m_offer.offer.price,
                    "Status Dopasowania": m_offer.offer.match_confidence.value,
                    "URL": m_offer.offer.url
                })
        df = pd.DataFrame(rows)
        df.to_excel(filepath, index=False)
