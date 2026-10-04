"""Desktop GUI Application for Allegro MultiSearch (Tkinter)."""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import json
import csv
import webbrowser
import os
from typing import List, Optional, Dict, Any

from allegro_search import (
    AllegroConfig,
    AllegroAPIClient,
    AllegroAPIError,
    ProductQuery,
    MultiItemFinder,
    MultiSellerCombiner,
    SellerMatch,
    MultiSellerCombination
)


class ProductRowUI:
    """UI Widget representing a single product row in the search list."""

    def __init__(self, parent: ttk.Frame, index: int, on_remove, on_move_up, on_move_down):
        self.parent = parent
        self.index = index
        self.on_remove = on_remove
        self.on_move_up = on_move_up
        self.on_move_down = on_move_down

        self.frame = ttk.LabelFrame(parent, text=f" Przedmiot #{index + 1} ", padding="5")
        self.frame.pack(fill=tk.X, pady=4, anchor=tk.N)

        # Row 1: Main Product Name + Controls
        r1 = ttk.Frame(self.frame)
        r1.pack(fill=tk.X, pady=2)

        ttk.Label(r1, text="Nazwa:").pack(side=tk.LEFT, padx=(0, 5))
        self.name_entry = ttk.Entry(r1, width=32)
        self.name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        ttk.Label(r1, text="Ilość:").pack(side=tk.LEFT, padx=(0, 2))
        self.qty_spin = ttk.Spinbox(r1, from_=1, to=99, width=4)
        self.qty_spin.set(1)
        self.qty_spin.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(r1, text="Max budżet (zł):").pack(side=tk.LEFT, padx=(0, 2))
        self.budget_entry = ttk.Entry(r1, width=8)
        self.budget_entry.pack(side=tk.LEFT, padx=(0, 10))

        # Reorder / Delete buttons
        btn_del = ttk.Button(r1, text="➖ Usuń", width=8, command=lambda: self.on_remove(self))
        btn_del.pack(side=tk.RIGHT, padx=2)

        btn_dn = ttk.Button(r1, text="↓", width=3, command=lambda: self.on_move_down(self))
        btn_dn.pack(side=tk.RIGHT, padx=2)

        btn_up = ttk.Button(r1, text="↑", width=3, command=lambda: self.on_move_up(self))
        btn_up.pack(side=tk.RIGHT, padx=2)

        # Row 2: Options (Required, Excluded, EAN)
        r2 = ttk.Frame(self.frame)
        r2.pack(fill=tk.X, pady=2)

        ttk.Label(r2, text="Wymagane słowa:").pack(side=tk.LEFT, padx=(0, 2))
        self.req_entry = ttk.Entry(r2, width=20)
        self.req_entry.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(r2, text="Wykluczone słowa:").pack(side=tk.LEFT, padx=(0, 2))
        self.exc_entry = ttk.Entry(r2, width=20)
        self.exc_entry.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(r2, text="Kod EAN / Model:").pack(side=tk.LEFT, padx=(0, 2))
        self.ean_entry = ttk.Entry(r2, width=15)
        self.ean_entry.pack(side=tk.LEFT)

    def get_query(self) -> Optional[ProductQuery]:
        name = self.name_entry.get().strip()
        if not name:
            return None

        try:
            qty = int(self.qty_spin.get())
        except ValueError:
            qty = 1

        budget_raw = self.budget_entry.get().strip()
        budget = float(budget_raw) if budget_raw else None

        req_words = [w.strip() for w in self.req_entry.get().split(",") if w.strip()]
        exc_words = [w.strip() for w in self.exc_entry.get().split(",") if w.strip()]
        ean = self.ean_entry.get().strip() or None

        return ProductQuery(
            name=name,
            quantity=qty,
            max_budget=budget,
            required_words=req_words,
            excluded_words=exc_words,
            ean=ean
        )


class AllegroMultiSearchGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Allegro MultiSearch — Wyszukiwarka Zestawów Ofert")
        self.root.geometry("1050x800")
        self.root.minsize(900, 650)

        self.config = AllegroConfig.load()
        self.product_rows: List[ProductRowUI] = []
        self.single_seller_matches: List[SellerMatch] = []
        self.combo_matches: List[MultiSellerCombination] = []
        self.current_queries: List[ProductQuery] = []

        self._setup_ui()

    def _setup_ui(self):
        style = ttk.Style()
        style.theme_use('clam')

        # Main notebook tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.tab_search = ttk.Frame(self.notebook, padding="10")
        self.tab_results = ttk.Frame(self.notebook, padding="10")
        self.tab_config = ttk.Frame(self.notebook, padding="10")

        self.notebook.add(self.tab_search, text=" 🔍 Wyszukiwanie ")
        self.notebook.add(self.tab_results, text=" 📊 Wyniki & Ranking ")
        self.notebook.add(self.tab_config, text=" ⚙️ Konfiguracja Allegro API ")

        self._build_config_tab()
        self._build_search_tab()
        self._build_results_tab()

    # --- TAB 1: CONFIGURATION ---
    def _build_config_tab(self):
        frame = ttk.LabelFrame(self.tab_config, text=" 🔑 Parametry Dostępowe Allegro REST API ", padding="15")
        frame.pack(fill=tk.X, pady=10)

        ttk.Label(frame, text="Client ID:").grid(row=0, column=0, sticky=tk.W, pady=8)
        self.cfg_client_id = ttk.Entry(frame, width=50)
        self.cfg_client_id.grid(row=0, column=1, sticky=tk.W, pady=8, padx=10)
        self.cfg_client_id.insert(0, self.config.client_id)

        ttk.Label(frame, text="Client Secret:").grid(row=1, column=0, sticky=tk.W, pady=8)
        self.cfg_client_secret = ttk.Entry(frame, width=50, show="*")
        self.cfg_client_secret.grid(row=1, column=1, sticky=tk.W, pady=8, padx=10)
        self.cfg_client_secret.insert(0, self.config.client_secret)

        ttk.Label(frame, text="User-Agent:").grid(row=2, column=0, sticky=tk.W, pady=8)
        self.cfg_user_agent = ttk.Entry(frame, width=50)
        self.cfg_user_agent.grid(row=2, column=1, sticky=tk.W, pady=8, padx=10)
        self.cfg_user_agent.insert(0, self.config.user_agent)

        self.cfg_sandbox_var = tk.BooleanVar(value=self.config.use_sandbox)
        ttk.Checkbutton(frame, text="Użyj Allegro Sandbox (Środowisko Testowe)", variable=self.cfg_sandbox_var).grid(row=3, column=1, sticky=tk.W, pady=8, padx=10)

        # Buttons
        btn_box = ttk.Frame(frame)
        btn_box.grid(row=4, column=1, sticky=tk.W, pady=15, padx=10)

        self.save_cfg_btn = ttk.Button(btn_box, text="💾 Zapamiętaj Konfigurację", command=self._save_configuration)
        self.save_cfg_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.test_cfg_btn = ttk.Button(btn_box, text="🔌 Test Połączenia z Allegro API", command=self._test_api_connection)
        self.test_cfg_btn.pack(side=tk.LEFT)

    def _save_configuration(self):
        self.config.client_id = self.cfg_client_id.get().strip()
        self.config.client_secret = self.cfg_client_secret.get().strip()
        self.config.user_agent = self.cfg_user_agent.get().strip() or "AllegroMultiSearch/1.0"
        self.config.use_sandbox = self.cfg_sandbox_var.get()

        try:
            self.config.save()
            messagebox.showinfo("Konfiguracja", "Dane konfiguracyjne zostały pomyślnie zapisane!")
        except Exception as e:
            messagebox.showerror("Błąd Zapisu", str(e))

    def _test_api_connection(self):
        self.save_cfg_btn.invoke()
        client = AllegroAPIClient(self.config)

        try:
            res = client.test_connection()
            messagebox.showinfo("Test Połączenia API", f"SUCCESS:\n\n{res['message']}")
        except Exception as e:
            messagebox.showerror("Test Połączenia API", f"ERROR:\n\n{e}")

    # --- TAB 2: SEARCH & PRODUCTS LIST ---
    def _build_search_tab(self):
        top_frame = ttk.Frame(self.tab_search)
        top_frame.pack(fill=tk.BOTH, expand=True)

        # Left Column: Product List
        left_box = ttk.LabelFrame(top_frame, text=" 🛍️ Lista Poszukiwanych Produktów ", padding="10")
        left_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # Scrollable container for products
        self.canvas = tk.Canvas(left_box, borderwidth=0, highlightthickness=0)
        self.scroll_y = ttk.Scrollbar(left_box, orient=tk.VERTICAL, command=self.canvas.yview)
        self.products_container = ttk.Frame(self.canvas)

        self.products_container.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.products_container, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scroll_y.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        # Product Action Buttons
        p_btn_box = ttk.Frame(left_box)
        p_btn_box.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(p_btn_box, text="➕ Dodaj Produkt", command=self._add_product_row).pack(side=tk.LEFT, padx=5)

        # Right Column: Search Options
        right_box = ttk.LabelFrame(top_frame, text=" ⚙️ Opcje & Filtry Wyszukiwania ", padding="10")
        right_box.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))

        # Include Delivery
        self.inc_del_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(right_box, text="Uwzględniaj koszty dostawy", variable=self.inc_del_var).pack(anchor=tk.W, pady=5)

        # Max Delivery Cost
        ttk.Label(right_box, text="Maks. koszt dostawy (zł):").pack(anchor=tk.W, pady=(5, 0))
        self.max_del_entry = ttk.Entry(right_box, width=15)
        self.max_del_entry.pack(anchor=tk.W, pady=(0, 10))

        # Condition
        ttk.Label(right_box, text="Stan produktu:").pack(anchor=tk.W, pady=(5, 0))
        self.condition_combo = ttk.Combobox(right_box, values=["Wszystkie", "Nowe", "Używane"], state="readonly")
        self.condition_combo.current(0)
        self.condition_combo.pack(anchor=tk.W, pady=(0, 10))

        # Sort Order
        ttk.Label(right_box, text="Sortowanie ofert na Allegro:").pack(anchor=tk.W, pady=(5, 0))
        self.sort_combo = ttk.Combobox(right_box, values=["Trafność", "Cena: od najniższej", "Cena: od najwyższej"], state="readonly")
        self.sort_combo.current(1)
        self.sort_combo.pack(anchor=tk.W, pady=(0, 15))

        # Bottom Frame: Search Action + Progress
        bottom_box = ttk.Frame(self.tab_search, padding="10")
        bottom_box.pack(fill=tk.X, pady=(10, 0))

        self.start_btn = ttk.Button(bottom_box, text="🚀 Rozpocznij Wyszukiwanie MultiSearch", command=self._start_search)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 15))

        self.pbar = ttk.Progressbar(bottom_box, mode="determinate")
        self.pbar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        self.status_lbl = ttk.Label(bottom_box, text="Gotowy do wyszukiwania.")
        self.status_lbl.pack(side=tk.RIGHT)

        # Initial default products
        self._add_product_row_with_text("LEGO Technic 42154")
        self._add_product_row_with_text("Raspberry Pi 5 8GB")
        self._add_product_row_with_text("karta microSD 256GB")

    def _add_product_row(self):
        idx = len(self.product_rows)
        row = ProductRowUI(self.products_container, idx, self._remove_product_row, self._move_up, self._move_down)
        self.product_rows.append(row)

    def _add_product_row_with_text(self, text: str):
        self._add_product_row()
        self.product_rows[-1].name_entry.insert(0, text)

    def _remove_product_row(self, row: ProductRowUI):
        if len(self.product_rows) <= 1:
            messagebox.showwarning("Uwaga", "Lista musi zawierać przynajmniej jeden produkt.")
            return
        row.frame.destroy()
        self.product_rows.remove(row)
        self._reindex_rows()

    def _reindex_rows(self):
        for idx, row in enumerate(self.product_rows):
            row.index = idx
            row.frame.config(text=f" Przedmiot #{idx + 1} ")

    def _move_up(self, row: ProductRowUI):
        idx = row.index
        if idx > 0:
            self.product_rows[idx], self.product_rows[idx - 1] = self.product_rows[idx - 1], self.product_rows[idx]
            self._redraw_rows()

    def _move_down(self, row: ProductRowUI):
        idx = row.index
        if idx < len(self.product_rows) - 1:
            self.product_rows[idx], self.product_rows[idx + 1] = self.product_rows[idx + 1], self.product_rows[idx]
            self._redraw_rows()

    def _redraw_rows(self):
        for row in self.product_rows:
            row.frame.pack_forget()
        for idx, row in enumerate(self.product_rows):
            row.index = idx
            row.frame.config(text=f" Przedmiot #{idx + 1} ")
            row.frame.pack(fill=tk.X, pady=4, anchor=tk.N)

    # --- SEARCH LOGIC THREAD ---
    def _start_search(self):
        queries = [r.get_query() for r in self.product_rows]
        queries = [q for q in queries if q is not None]

        if not queries:
            messagebox.showwarning("Brak produktów", "Wprowadź przynajmniej jedną nazwę produktu.")
            return

        if not self.config.client_id or not self.config.client_secret:
            messagebox.showwarning("Brak Konfiguracji", "Przejdź do zakładki 'Konfiguracja' i wprowadź Client ID oraz Client Secret.")
            self.notebook.select(self.tab_config)
            return

        self.current_queries = queries
        self.start_btn.config(state=tk.DISABLED)
        self.pbar['value'] = 0

        # Sort map
        sort_map = {"Trafność": None, "Cena: od najniższej": "p", "Cena: od najwyższej": "pd"}
        sort_val = sort_map.get(self.sort_combo.get())

        # Condition map
        cond_map = {"Wszystkie": None, "Nowe": "NEW", "Używane": "USED"}
        cond_val = cond_map.get(self.condition_combo.get())

        max_del_raw = self.max_del_entry.get().strip()
        max_del = float(max_del_raw) if max_del_raw else None

        thread = threading.Thread(
            target=self._execute_search_thread,
            args=(queries, self.inc_del_var.get(), max_del, sort_val, cond_val)
        )
        thread.daemon = True
        thread.start()

    def _execute_search_thread(self, queries, inc_del, max_del, sort_val, cond_val):
        try:
            client = AllegroAPIClient(self.config)
            client.authenticate()

            finder = MultiItemFinder(client)

            def progress_cb(idx, total, q_name, offers_count):
                pct = int((idx / total) * 100)
                msg = f"Produkt {idx}/{total}: '{q_name}' (Ofert: {offers_count})"
                self.root.after(0, self._update_progress, pct, msg)

            matches = finder.find_sellers(
                queries=queries,
                include_delivery=inc_del,
                max_delivery_cost=max_del,
                sort_by_price=sort_val,
                condition=cond_val,
                progress_callback=progress_cb
            )

            # Compute multi-seller combinations if needed
            combos = MultiSellerCombiner.find_best_combinations(queries, matches, max_sellers=3, top_n=5)

            self.root.after(0, self._on_search_complete, matches, combos)

        except Exception as e:
            self.root.after(0, self._on_search_error, str(e))

    def _update_progress(self, pct: int, status_msg: str):
        self.pbar['value'] = pct
        self.status_lbl.config(text=status_msg)

    def _on_search_complete(self, matches: List[SellerMatch], combos: List[MultiSellerCombination]):
        self.start_btn.config(state=tk.NORMAL)
        self.status_lbl.config(text=f"Zakończono. Znaleziono {len(matches)} sprzedawców.")
        self.single_seller_matches = matches
        self.combo_matches = combos

        self._render_results()
        self.notebook.select(self.tab_results)

    def _on_search_error(self, err_msg: str):
        self.start_btn.config(state=tk.NORMAL)
        self.status_lbl.config(text="Błąd wyszukiwania.")
        messagebox.showerror("Błąd Wyszukiwania Allegro", err_msg)

    # --- TAB 3: RESULTS & RANKING ---
    def _build_results_tab(self):
        # Top Action Bar (Export / Filter buttons)
        top_bar = ttk.Frame(self.tab_results)
        top_bar.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(top_bar, text="💾 Eksportuj do CSV", command=self._export_csv).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_bar, text="💾 Eksportuj do Excel (.xlsx)", command=self._export_excel).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_bar, text="💾 Eksportuj do JSON", command=self._export_json).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_bar, text="📋 Kopiuj Wyniki do Schowka", command=self._copy_results_to_clipboard).pack(side=tk.LEFT, padx=5)

        # Sub-Notebook for Results Types
        self.res_notebook = ttk.Notebook(self.tab_results)
        self.res_notebook.pack(fill=tk.BOTH, expand=True)

        self.sub_tab_ranking = ttk.Frame(self.res_notebook, padding="5")
        self.sub_tab_combos = ttk.Frame(self.res_notebook, padding="5")

        self.res_notebook.add(self.sub_tab_ranking, text=" 🏆 Ranking Jednego Sprzedawcy ")
        self.res_notebook.add(self.sub_tab_combos, text=" 🧩 Najlepsze Kombinacje (Wielu Sprzedawców) ")

        # --- Ranking Subtab UI ---
        r_split = ttk.PanedWindow(self.sub_tab_ranking, orient=tk.HORIZONTAL)
        r_split.pack(fill=tk.BOTH, expand=True)

        # Left: Treeview Ranking
        left_f = ttk.Frame(r_split)
        r_split.add(left_f, weight=1)

        cols = ("rank", "seller", "super", "count", "items_price", "del_price", "total")
        self.ranking_tree = ttk.Treeview(left_f, columns=cols, show="headings", selectmode="browse")

        self.ranking_tree.heading("rank", text="#")
        self.ranking_tree.heading("seller", text="Sprzedawca")
        self.ranking_tree.heading("super", text="SuperSprzedawca")
        self.ranking_tree.heading("count", text="Dopasowania")
        self.ranking_tree.heading("items_price", text="Produkty (zł)")
        self.ranking_tree.heading("del_price", text="Dostawa (zł)")
        self.ranking_tree.heading("total", text="RAZEM (zł)")

        self.ranking_tree.column("rank", width=35, anchor=tk.CENTER)
        self.ranking_tree.column("seller", width=160, anchor=tk.W)
        self.ranking_tree.column("super", width=100, anchor=tk.CENTER)
        self.ranking_tree.column("count", width=100, anchor=tk.CENTER)
        self.ranking_tree.column("items_price", width=100, anchor=tk.E)
        self.ranking_tree.column("del_price", width=90, anchor=tk.E)
        self.ranking_tree.column("total", width=100, anchor=tk.E)

        r_scroll = ttk.Scrollbar(left_f, orient=tk.VERTICAL, command=self.ranking_tree.yview)
        self.ranking_tree.configure(yscroll=r_scroll.set)

        self.ranking_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        r_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.ranking_tree.bind("<<TreeviewSelect>>", self._on_ranking_selected)

        # Right: Card Detailed View
        right_f = ttk.LabelFrame(r_split, text=" 💳 Karta Sprzedawcy & Zestaw Ofert ", padding="10")
        r_split.add(right_f, weight=2)

        self.card_text = tk.Text(right_f, wrap=tk.WORD, height=15)
        c_scroll = ttk.Scrollbar(right_f, orient=tk.VERTICAL, command=self.card_text.yview)
        self.card_text.configure(yscroll=c_scroll.set)

        self.card_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        c_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # --- Combos Subtab UI ---
        c_split = ttk.PanedWindow(self.sub_tab_combos, orient=tk.HORIZONTAL)
        c_split.pack(fill=tk.BOTH, expand=True)

        left_c = ttk.Frame(c_split)
        c_split.add(left_c, weight=1)

        c_cols = ("rank", "sellers", "covered", "total")
        self.combo_tree = ttk.Treeview(left_c, columns=c_cols, show="headings", selectmode="browse")

        self.combo_tree.heading("rank", text="#")
        self.combo_tree.heading("sellers", text="Kombinacja Sprzedawców")
        self.combo_tree.heading("covered", text="Pokrycie Produktów")
        self.combo_tree.heading("total", text="Łącznie (zł)")

        self.combo_tree.column("rank", width=35, anchor=tk.CENTER)
        self.combo_tree.column("sellers", width=250, anchor=tk.W)
        self.combo_tree.column("covered", width=120, anchor=tk.CENTER)
        self.combo_tree.column("total", width=110, anchor=tk.E)

        combo_scroll = ttk.Scrollbar(left_c, orient=tk.VERTICAL, command=self.combo_tree.yview)
        self.combo_tree.configure(yscroll=combo_scroll.set)

        self.combo_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        combo_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.combo_tree.bind("<<TreeviewSelect>>", self._on_combo_selected)

        right_c = ttk.LabelFrame(c_split, text=" 🧩 Podział Produktów w Kombinacji ", padding="10")
        c_split.add(right_c, weight=2)

        self.combo_card_text = tk.Text(right_c, wrap=tk.WORD, height=15)
        cc_scroll = ttk.Scrollbar(right_c, orient=tk.VERTICAL, command=self.combo_card_text.yview)
        self.combo_card_text.configure(yscroll=cc_scroll.set)

        self.combo_card_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cc_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _render_results(self):
        # Clear Ranking
        for item in self.ranking_tree.get_children():
            self.ranking_tree.delete(item)
        self.card_text.delete("1.0", tk.END)

        total_q = len(self.current_queries)

        for idx, match in enumerate(self.single_seller_matches, 1):
            super_str = "⭐ Tak" if match.seller.is_super_seller else "Nie"
            cnt_str = f"{match.matched_count}/{total_q}"
            self.ranking_tree.insert(
                "",
                tk.END,
                iid=str(idx - 1),
                values=(
                    idx,
                    match.seller.login,
                    super_str,
                    cnt_str,
                    f"{match.items_total_price:.2f}",
                    f"{match.delivery_cost:.2f}",
                    f"{match.total_price_with_delivery:.2f}"
                )
            )

        if self.single_seller_matches:
            self.ranking_tree.selection_set("0")

        # Clear Combos
        for item in self.combo_tree.get_children():
            self.combo_tree.delete(item)
        self.combo_card_text.delete("1.0", tk.END)

        for idx, combo in enumerate(self.combo_matches, 1):
            s_logins = " + ".join(s.login for s in combo.sellers)
            cov_str = f"{combo.covered_count}/{total_q}"
            self.combo_tree.insert(
                "",
                tk.END,
                iid=str(idx - 1),
                values=(
                    idx,
                    s_logins,
                    cov_str,
                    f"{combo.grand_total:.2f}"
                )
            )

        if self.combo_matches:
            self.combo_tree.selection_set("0")

    def _on_ranking_selected(self, event):
        sel = self.ranking_tree.selection()
        if not sel:
            return

        idx = int(sel[0])
        match = self.single_seller_matches[idx]

        self.card_text.delete("1.0", tk.END)
        self.card_text.insert(tk.END, f"--------------------------------------------------\n")
        self.card_text.insert(tk.END, f"# {idx}. Sprzedawca: {match.seller.login}\n")
        if match.seller.is_super_seller:
            self.card_text.insert(tk.END, "⭐ SuperSprzedawca Allegro\n")
        self.card_text.insert(tk.END, f"Znaleziono: {match.matched_count}/{len(self.current_queries)} produktów\n")
        self.card_text.insert(tk.END, f"Suma produktów: {match.items_total_price:.2f} zł\n")
        self.card_text.insert(tk.END, f"Dostawa: {match.delivery_cost:.2f} zł\n")
        self.card_text.insert(tk.END, f"RAZEM: {match.total_price_with_delivery:.2f} zł\n")
        self.card_text.insert(tk.END, f"--------------------------------------------------\n\n")

        for query in self.current_queries:
            q_name = query.name
            if q_name in match.offers_by_query and match.offers_by_query[q_name]:
                m_offer = min(match.offers_by_query[q_name], key=lambda x: x.offer.price)
                off = m_offer.offer
                smart = "🚀 [SMART!]" if off.is_smart else ""
                self.card_text.insert(tk.END, f"✓ {q_name} (x{query.quantity})\n")
                self.card_text.insert(tk.END, f"   Tytuł: {off.title}\n")
                self.card_text.insert(tk.END, f"   Cena: {off.price:.2f} zł {smart} | Status: {off.match_confidence.value}\n")
                self.card_text.insert(tk.END, f"   Link: {off.url}\n\n")
            else:
                self.card_text.insert(tk.END, f"✗ {q_name} — BRAK OFERTY U TEGO SPRZEDAWCY\n\n")

    def _on_combo_selected(self, event):
        sel = self.combo_tree.selection()
        if not sel:
            return

        idx = int(sel[0])
        combo = self.combo_matches[idx]

        self.combo_card_text.delete("1.0", tk.END)
        self.combo_card_text.insert(tk.END, f"--------------------------------------------------\n")
        self.combo_card_text.insert(tk.END, f"Kombinacja #{idx}: {len(combo.sellers)} sprzedawców\n")
        self.combo_card_text.insert(tk.END, f"Pokrycie: {combo.covered_count}/{len(self.current_queries)} produktów\n")
        self.combo_card_text.insert(tk.END, f"Cena produktów: {combo.items_total_price:.2f} zł\n")
        self.combo_card_text.insert(tk.END, f"Szacowana dostawa: {combo.total_delivery_cost:.2f} zł\n")
        self.combo_card_text.insert(tk.END, f"ŁĄCZNIE: {combo.grand_total:.2f} zł\n")
        self.combo_card_text.insert(tk.END, f"--------------------------------------------------\n\n")

        for q_name, m_offer in combo.coverage.items():
            off = m_offer.offer
            self.combo_card_text.insert(tk.END, f"• [{q_name}] od sprzedawcy: {off.seller.login}\n")
            self.combo_card_text.insert(tk.END, f"  Oferta: {off.title}\n")
            self.combo_card_text.insert(tk.END, f"  Cena: {off.price:.2f} zł | URL: {off.url}\n\n")

    # --- EXPORT HANDLERS ---
    def _export_json(self):
        if not self.single_seller_matches:
            messagebox.showwarning("Brak danych", "Najpierw przeprowadź wyszukiwanie.")
            return

        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if not path:
            return

        data = []
        for m in self.single_seller_matches:
            data.append({
                "seller": m.seller.login,
                "is_super_seller": m.seller.is_super_seller,
                "matched_count": m.matched_count,
                "items_total_price": m.items_total_price,
                "delivery_cost": m.delivery_cost,
                "grand_total": m.total_price_with_delivery,
                "offers": {k: {"title": v.offer.title, "price": v.offer.price, "url": v.offer.url} for k, v in m.best_offers.items()}
            })

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        messagebox.showinfo("Eksport JSON", f"Zapisano dane do pliku:\n{path}")

    def _export_csv(self):
        if not self.single_seller_matches:
            messagebox.showwarning("Brak danych", "Najpierw przeprowadź wyszukiwanie.")
            return

        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not path:
            return

        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Sprzedawca", "SuperSprzedawca", "Liczba Produktów", "Suma Produktów (zł)", "Dostawa (zł)", "Łącznie (zł)", "Fraza", "Tytuł Oferty", "Cena (zł)", "URL"])

            for m in self.single_seller_matches:
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
                        m_offer.offer.url
                    ])

        messagebox.showinfo("Eksport CSV", f"Zapisano dane do pliku:\n{path}")

    def _export_excel(self):
        if not self.single_seller_matches:
            messagebox.showwarning("Brak danych", "Najpierw przeprowadź wyszukiwanie.")
            return

        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
        if not path:
            return

        try:
            import pandas as pd
            rows = []
            for m in self.single_seller_matches:
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
                        "URL": m_offer.offer.url
                    })
            df = pd.DataFrame(rows)
            df.to_excel(path, index=False)
            messagebox.showinfo("Eksport Excel", f"Zapisano dane do pliku:\n{path}")
        except Exception as e:
            messagebox.showerror("Błąd Eksportu Excel", f"Wystąpił błąd podczas zapisu: {e}")

    def _copy_results_to_clipboard(self):
        if not self.single_seller_matches:
            return

        lines = ["=== Allegro MultiSearch - Wyniki ==="]
        for idx, m in enumerate(self.single_seller_matches[:5], 1):
            lines.append(f"#{idx} {m.seller.login} | Dopasowania: {m.matched_count}/{len(self.current_queries)} | Suma: {m.total_price_with_delivery:.2f} zł")

        txt = "\n".join(lines)
        self.root.clipboard_clear()
        self.root.clipboard_append(txt)
        messagebox.showinfo("Schowek", "Skopiowano najistotniejsze wyniki do schowka!")


def main():
    root = tk.Tk()
    app = AllegroMultiSearchGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
