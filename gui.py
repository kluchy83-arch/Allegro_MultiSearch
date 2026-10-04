"""Tkinter GUI application for Allegro Multi-Item Finder."""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import json
import csv
import webbrowser
import os
from typing import List, Optional

from allegro_search import AllegroAPIClient, AllegroAPIError, MultiItemFinder, SellerMatch


class AllegroFinderGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Allegro Multi-Item Finder (Wyszukiwarka Ofert u Jednego Sprzedawcy)")
        self.root.geometry("900" + "x" + "700")
        self.root.minsize(800, 600)

        self.matches: List[SellerMatch] = []
        self._setup_ui()

    def _setup_ui(self):
        # Apply style
        style = ttk.Style()
        style.theme_use('clam')

        # Main Container
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. API Credentials Section
        cred_frame = ttk.LabelFrame(main_frame, text=" 🔑 Dane Logowania Allegro API ", padding="10")
        cred_frame.pack(fill=tk.X, pady=(0, 10))

        # Client ID
        ttk.Label(cred_frame, text="Client ID:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.client_id_entry = ttk.Entry(cred_frame, width=40, show="*")
        self.client_id_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

        # Pre-fill from environment if exists
        env_client_id = os.environ.get("ALLEGRO_CLIENT_ID", "")
        if env_client_id:
            self.client_id_entry.insert(0, env_client_id)

        # Client Secret
        ttk.Label(cred_frame, text="Client Secret:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.client_secret_entry = ttk.Entry(cred_frame, width=40, show="*")
        self.client_secret_entry.grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)

        env_client_secret = os.environ.get("ALLEGRO_CLIENT_SECRET", "")
        if env_client_secret:
            self.client_secret_entry.insert(0, env_client_secret)

        # Sandbox Checkbox
        self.sandbox_var = tk.BooleanVar(value=False)
        self.sandbox_chk = ttk.Checkbutton(cred_frame, text="Użyj Allegro Sandbox", variable=self.sandbox_var)
        self.sandbox_chk.grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)

        # 2. Search Settings & Keywords Section
        search_frame = ttk.LabelFrame(main_frame, text=" 🔍 Poszukiwane Przedmioty & Ustawienia ", padding="10")
        search_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(search_frame, text="Wpisz szukane przedmioty (po jednym w nowej linii):").pack(anchor=tk.W, pady=(0, 5))

        self.keywords_text = tk.Text(search_frame, height=4, width=80)
        self.keywords_text.pack(fill=tk.X, pady=(0, 10))
        self.keywords_text.insert(tk.END, "wiedźmin\ndiuna\nwładca pierścieni")

        options_subframe = ttk.Frame(search_frame)
        options_subframe.pack(fill=tk.X)

        self.match_mode_var = tk.StringVar(value="all")
        ttk.Radiobutton(options_subframe, text="Wszystkie przedmioty u jednego sprzedawcy (100% dopasowania)", variable=self.match_mode_var, value="all", command=self._toggle_min_items).pack(anchor=tk.W, side=tk.LEFT, padx=(0, 15))
        ttk.Radiobutton(options_subframe, text="Częściowe dopasowanie (min. N przedmiotów)", variable=self.match_mode_var, value="partial", command=self._toggle_min_items).pack(anchor=tk.W, side=tk.LEFT)

        self.min_items_frame = ttk.Frame(options_subframe)
        ttk.Label(self.min_items_frame, text="Min. przedmiotów:").pack(side=tk.LEFT, padx=(10, 5))
        self.min_items_spin = ttk.Spinbox(self.min_items_frame, from_=2, to=10, width=5)
        self.min_items_spin.set(2)
        self.min_items_spin.pack(side=tk.LEFT)

        # Action Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        self.search_btn = ttk.Button(btn_frame, text="🔎 Rozpocznij Wyszukiwanie", command=self._start_search_thread)
        self.search_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.progress_bar = ttk.Progressbar(btn_frame, mode="indeterminate")
        self.status_label = ttk.Label(btn_frame, text="Gotowy.")
        self.status_label.pack(side=tk.LEFT, padx=10)

        # 3. Results Section
        results_frame = ttk.LabelFrame(main_frame, text=" 📊 Wyniki Wyszukiwania ", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True)

        # Treeview for results
        columns = ("rank", "seller", "super", "matches", "total_price")
        self.tree = ttk.Treeview(results_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("rank", text="#")
        self.tree.heading("seller", text="Sprzedawca")
        self.tree.heading("super", text="Super Sprzedawca")
        self.tree.heading("matches", text="Liczba Przedmiotów")
        self.tree.heading("total_price", text="Min. Suma (PLN)")

        self.tree.column("rank", width=40, anchor=tk.CENTER)
        self.tree.column("seller", width=200, anchor=tk.W)
        self.tree.column("super", width=120, anchor=tk.CENTER)
        self.tree.column("matches", width=130, anchor=tk.CENTER)
        self.tree.column("total_price", width=130, anchor=tk.E)

        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self._on_seller_selected)
        self.tree.bind("<Double-1>", self._on_tree_double_click)

        # Details Panel
        details_frame = ttk.LabelFrame(main_frame, text=" 🛍️ Oferty wybranego sprzedawcy ", padding="10")
        details_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self.details_text = tk.Text(details_frame, height=8, wrap=tk.WORD)
        details_scrollbar = ttk.Scrollbar(details_frame, orient=tk.VERTICAL, command=self.details_text.yview)
        self.details_text.configure(yscroll=details_scrollbar.set)

        self.details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        details_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Export Buttons
        export_frame = ttk.Frame(main_frame)
        export_frame.pack(fill=tk.X, pady=(10, 0))

        self.export_json_btn = ttk.Button(export_frame, text="💾 Eksportuj do JSON", command=self._export_json, state=tk.DISABLED)
        self.export_json_btn.pack(side=tk.RIGHT, padx=5)

        self.export_csv_btn = ttk.Button(export_frame, text="💾 Eksportuj do CSV", command=self._export_csv, state=tk.DISABLED)
        self.export_csv_btn.pack(side=tk.RIGHT, padx=5)

    def _toggle_min_items(self):
        if self.match_mode_var.get() == "partial":
            self.min_items_frame.pack(side=tk.LEFT, padx=(10, 0))
        else:
            self.min_items_frame.pack_forget()

    def _start_search_thread(self):
        client_id = self.client_id_entry.get().strip()
        client_secret = self.client_secret_entry.get().strip()

        if not client_id or not client_secret:
            messagebox.showwarning("Brak kluczy API", "Proszę podać Client ID oraz Client Secret do Allegro API.")
            return

        raw_kw = self.keywords_text.get("1.0", tk.END).strip()
        keywords = [k.strip() for k in raw_kw.split("\n") if k.strip()]

        if not keywords:
            messagebox.showwarning("Brak słów kluczowych", "Wpisz przynajmniej jeden przedmiot do wyszukania.")
            return

        self.search_btn.config(state=tk.DISABLED)
        self.progress_bar.pack(side=tk.LEFT, padx=10)
        self.progress_bar.start(10)
        self.status_label.config(text="Wyszukiwanie w Allegro API...")

        # Clear existing
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.details_text.delete("1.0", tk.END)
        self.matches = []
        self.export_json_btn.config(state=tk.DISABLED)
        self.export_csv_btn.config(state=tk.DISABLED)

        thread = threading.Thread(target=self._run_search, args=(client_id, client_secret, keywords))
        thread.daemon = True
        thread.start()

    def _run_search(self, client_id: str, client_secret: str, keywords: List[str]):
        try:
            client = AllegroAPIClient(client_id=client_id, client_secret=client_secret, sandbox=self.sandbox_var.get())
            client.authenticate()

            require_all = (self.match_mode_var.get() == "all")
            min_items = int(self.min_items_spin.get()) if not require_all else 2

            finder = MultiItemFinder(client)
            results = finder.find_sellers(keywords=keywords, require_all=require_all, min_items=min_items)

            self.root.after(0, self._display_results, results)
        except Exception as e:
            self.root.after(0, self._handle_error, str(e))

    def _display_results(self, results: List[SellerMatch]):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.search_btn.config(state=tk.NORMAL)
        self.matches = results

        if not results:
            self.status_label.config(text="Nie znaleziono sprzedawców spełniających kryteria.")
            messagebox.showinfo("Brak wyników", "Nie znaleziono sprzedawców oferujących podane przedmioty jednocześnie.")
            return

        self.status_label.config(text=f"Znaleziono {len(results)} sprzedawców.")

        for idx, match in enumerate(results, 1):
            super_str = "Tak" if match.seller.is_super_seller else "Nie"
            self.tree.insert(
                "",
                tk.END,
                iid=str(idx - 1),
                values=(idx, match.seller.login, super_str, match.matched_keywords_count, f"{match.min_total_price:.2f}")
            )

        self.export_json_btn.config(state=tk.NORMAL)
        self.export_csv_btn.config(state=tk.NORMAL)

    def _handle_error(self, err_msg: str):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.search_btn.config(state=tk.NORMAL)
        self.status_label.config(text="Błąd wyszukiwania.")
        messagebox.showerror("Błąd Allegro API", f"Wystąpił błąd podczas wyszukiwania:\n\n{err_msg}")

    def _on_seller_selected(self, event):
        selected = self.tree.selection()
        if not selected:
            return

        idx = int(selected[0])
        match = self.matches[idx]

        self.details_text.delete("1.0", tk.END)
        self.details_text.insert(tk.END, f"Sprzedawca: {match.seller.login}\n")
        self.details_text.insert(tk.END, f"Suma min: {match.min_total_price:.2f} PLN\n")
        self.details_text.insert(tk.END, "=" * 60 + "\n\n")

        for kw, offer in match.best_offers.items():
            smart = "[SMART!]" if offer.is_smart else ""
            self.details_text.insert(tk.END, f"• [{kw}] {offer.title}\n")
            self.details_text.insert(tk.END, f"  Cena: {offer.price:.2f} {offer.currency} {smart}\n")
            self.details_text.insert(tk.END, f"  URL: {offer.url}\n\n")

    def _on_tree_double_click(self, event):
        selected = self.tree.selection()
        if not selected:
            return

        idx = int(selected[0])
        match = self.matches[idx]
        best_offers = match.best_offers
        if best_offers:
            # Open first best offer in default browser
            first_offer = next(iter(best_offers.values()))
            webbrowser.open(first_offer.url)

    def _export_json(self):
        if not self.matches:
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if not file_path:
            return

        data = []
        for m in self.matches:
            s_info = {
                "seller_login": m.seller.login,
                "is_super_seller": m.seller.is_super_seller,
                "matched_keywords_count": m.matched_keywords_count,
                "min_total_price": m.min_total_price,
                "items": {kw: {"title": o.title, "price": o.price, "url": o.url, "is_smart": o.is_smart} for kw, o in m.best_offers.items()}
            }
            data.append(s_info)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        messagebox.showinfo("Eksport", f"Zapisano wyniki do pliku:\n{file_path}")

    def _export_csv(self):
        if not self.matches:
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not file_path:
            return

        with open(file_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Sprzedawca", "SuperSprzedawca", "Liczba Dopasowań", "Łączna Cena Min (PLN)", "Fraza", "Tytuł Oferty", "Cena (PLN)", "Smart", "URL"])

            for m in self.matches:
                for kw, offer in m.best_offers.items():
                    writer.writerow([
                        m.seller.login,
                        "Tak" if m.seller.is_super_seller else "Nie",
                        m.matched_keywords_count,
                        m.min_total_price,
                        kw,
                        offer.title,
                        offer.price,
                        "Tak" if offer.is_smart else "Nie",
                        offer.url
                    ])

        messagebox.showinfo("Eksport", f"Zapisano wyniki do pliku:\n{file_path}")


def main():
    root = tk.Tk()
    app = AllegroFinderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
