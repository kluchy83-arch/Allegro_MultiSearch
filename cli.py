"""CLI Application for Allegro Multi-Item Finder."""

import argparse
import json
import csv
import sys
import os
from typing import List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree

from allegro_search import MultiItemFinder, AllegroAPIClient, DemoAllegroClient, AllegroAPIError

console = Console()


def export_json(matches, filename: str):
    data = []
    for m in matches:
        seller_info = {
            "seller_id": m.seller.id,
            "seller_login": m.seller.login,
            "is_super_seller": m.seller.is_super_seller,
            "matched_keywords_count": m.matched_keywords_count,
            "min_total_price": m.min_total_price,
            "items": {}
        }
        for kw, offer in m.best_offers.items():
            seller_info["items"][kw] = {
                "offer_id": offer.id,
                "title": offer.title,
                "price": offer.price,
                "currency": offer.currency,
                "url": offer.url,
                "is_smart": offer.is_smart
            }
        data.append(seller_info)

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    console.print(f"[green]Wyniki wyeksportowano do pliku JSON: [bold]{filename}[/bold][/green]")


def export_csv(matches, filename: str):
    with open(filename, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Sprzedawca", "SuperSprzedawca", "Liczba Dopasowań", "Łączna Cena Min (PLN)", "Fraza", "Tytuł Oferty", "Cena (PLN)", "Smart", "URL"])

        for m in matches:
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
    console.print(f"[green]Wyniki wyeksportowano do pliku CSV: [bold]{filename}[/bold][/green]")


def main():
    parser = argparse.ArgumentParser(
        description="Wyszukiwarka wielu przedmiotów jednocześnie u jednego sprzedawcy na Allegro."
    )
    parser.add_argument(
        "keywords",
        nargs="*",
        help="Fraze/przedmioty do wyszukania (np. 'wiedźmin' 'diuna')"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Użyj trybu demonstracyjnego (przykładowe dane bez wymaganych kluczy API)"
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Pozwól na częściowe dopasowania (nie wszyscy sprzedawcy muszą mieć wszystkie przedmioty)"
    )
    parser.add_argument(
        "--min-items",
        type=int,
        default=2,
        help="Minimalna liczba dopasowanych przedmiotów u sprzedawcy w trybie częściowym (domyślnie: 2)"
    )
    parser.add_argument(
        "--export-json",
        type=str,
        help="Ścieżka pliku do eksportu w formacie JSON"
    )
    parser.add_argument(
        "--export-csv",
        type=str,
        help="Ścieżka pliku do eksportu w formacie CSV"
    )

    args = parser.parse_args()

    keywords = args.keywords
    if not keywords:
        console.print("[yellow]Nie podano przedmiotów. Podaj je jako argumenty w wierszu poleceń.[/yellow]")
        prompt_input = console.input("[bold cyan]Wpisz poszukiwane przedmioty oddzielone przecinkami: [/bold cyan]")
        keywords = [k.strip() for k in prompt_input.split(",") if k.strip()]

    if not keywords:
        console.print("[bold red]Brak słów kluczowych do wyszukania. Zakończono.[/bold red]")
        sys.exit(1)

    console.print(Panel.fit(
        f"[bold blue]Allegro Multi-Item Finder[/bold blue]\n\n"
        f"Poszukiwane przedmioty ({len(keywords)}): [yellow]{', '.join(keywords)}[/yellow]\n"
        f"Wymóg pełnego dopasowania: [cyan]{'Tak' if not args.allow_partial else 'Nie (min. ' + str(args.min_items) + ')'}[/cyan]",
        title="Wyszukiwanie"
    ))

    # Determine client
    client_id = os.environ.get("ALLEGRO_CLIENT_ID")
    client_secret = os.environ.get("ALLEGRO_CLIENT_SECRET")

    if args.demo or not (client_id and client_secret):
        if not args.demo and not (client_id and client_secret):
            console.print("[yellow]Brak zmiennych środowiskowych ALLEGRO_CLIENT_ID i ALLEGRO_CLIENT_SECRET. Uruchamianie w trybie DEMO z danymi testowymi.[/yellow]\n")
        client = DemoAllegroClient()
    else:
        try:
            client = AllegroAPIClient(client_id, client_secret)
        except Exception as e:
            console.print(f"[red]Błąd inicjalizacji klienta API: {e}. Przełączanie na tryb DEMO.[/red]\n")
            client = DemoAllegroClient()

    finder = MultiItemFinder(client)

    with console.status("[bold green]Wyszukiwanie ofert na Allegro...[/bold green]"):
        try:
            matches = finder.find_sellers(
                keywords=keywords,
                require_all=not args.allow_partial,
                min_items=args.min_items
            )
        except Exception as e:
            console.print(f"[bold red]Błąd podczas wyszukiwania: {e}[/bold red]")
            sys.exit(1)

    if not matches:
        console.print("[bold red]Nie znaleziono sprzedawców oferujących podane przedmioty jednocześnie.[/bold red]")
        sys.exit(0)

    console.print(f"\n[bold green]Znaleziono {len(matches)} sprzedawców z pasującymi przedmiotami:[/bold green]\n")

    for idx, match in enumerate(matches, 1):
        super_tag = " [bold gold1][Super Sprzedawca][/bold gold1]" if match.seller.is_super_seller else ""
        tree = Tree(f"[bold magenta]{idx}. Sprzedawca: {match.seller.login}{super_tag}[/bold magenta]")
        tree.add(f"Dopasowane przedmioty: [bold cyan]{match.matched_keywords_count} / {len(keywords)}[/bold cyan]")
        tree.add(f"Szacowana min. suma: [bold green]{match.min_total_price:.2f} PLN[/bold green]")

        offers_node = tree.add("Sugerowany zestaw (najtańsze oferty):")
        for kw, offer in match.best_offers.items():
            smart_str = " [bold blue][SMART!][/bold blue]" if offer.is_smart else ""
            offers_node.add(
                f"[yellow]{kw}[/yellow]: [bold]{offer.title}[/bold] - [green]{offer.price:.2f} {offer.currency}[/green]{smart_str}\n"
                f"   [dim]{offer.url}[/dim]"
            )

        console.print(tree)
        console.print("-" * 60)

    if args.export_json:
        export_json(matches, args.export_json)
    if args.export_csv:
        export_csv(matches, args.export_csv)


if __name__ == "__main__":
    main()
