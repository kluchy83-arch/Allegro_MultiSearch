"""CLI Application for Allegro MultiSearch."""

import argparse
import json
import csv
import sys
import os
from typing import List
from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree

from allegro_search import MultiItemFinder, AllegroAPIClient, AllegroConfig, ProductQuery, AllegroAPIError

console = Console()


def export_json(matches, filename: str):
    data = []
    for m in matches:
        data.append({
            "seller": m.seller.login,
            "is_super_seller": m.seller.is_super_seller,
            "matched_count": m.matched_count,
            "items_total_price": m.items_total_price,
            "delivery_cost": m.delivery_cost,
            "grand_total": m.total_price_with_delivery,
            "offers": {k: {"title": v.offer.title, "price": v.offer.price, "url": v.offer.url} for k, v in m.best_offers.items()}
        })

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    console.print(f"[green]Wyniki wyeksportowano do pliku JSON: [bold]{filename}[/bold][/green]")


def export_csv(matches, filename: str):
    with open(filename, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Sprzedawca", "SuperSprzedawca", "Liczba Produktów", "Suma Produktów (zł)", "Dostawa (zł)", "Łącznie (zł)", "Fraza", "Tytuł Oferty", "Cena (zł)", "URL"])

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
                    m_offer.offer.url
                ])
    console.print(f"[green]Wyniki wyeksportowano do pliku CSV: [bold]{filename}[/bold][/green]")


def main():
    parser = argparse.ArgumentParser(
        description="Allegro MultiSearch CLI — Wyszukiwarka ofert u jednego sprzedawcy."
    )
    parser.add_argument(
        "keywords",
        nargs="*",
        help="Fraze/przedmioty do wyszukania (np. 'wiedźmin' 'diuna')"
    )
    parser.add_argument(
        "--client-id",
        type=str,
        help="Client ID dla Allegro API"
    )
    parser.add_argument(
        "--client-secret",
        type=str,
        help="Client Secret dla Allegro API"
    )
    parser.add_argument(
        "--sandbox",
        action="store_true",
        help="Użyj środowiska Allegro Sandbox"
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

    config = AllegroConfig.load()
    if args.client_id:
        config.client_id = args.client_id
    if args.client_secret:
        config.client_secret = args.client_secret
    if args.sandbox:
        config.use_sandbox = True

    if not config.client_id or not config.client_secret:
        console.print("[bold red]Brak ID klienta i sekretu Allegro API (Client ID, Client Secret).[/bold red]")
        sys.exit(1)

    console.print(Panel.fit(
        f"[bold blue]Allegro MultiSearch CLI[/bold blue]\n\n"
        f"Poszukiwane przedmioty ({len(keywords)}): [yellow]{', '.join(keywords)}[/yellow]",
        title="Wyszukiwanie"
    ))

    try:
        client = AllegroAPIClient(config)
        client.authenticate()
    except Exception as e:
        console.print(f"[bold red]Błąd autoryzacji Allegro API: {e}[/bold red]")
        sys.exit(1)

    queries = [ProductQuery(name=k) for k in keywords]
    finder = MultiItemFinder(client)

    with console.status("[bold green]Wyszukiwanie ofert na Allegro...[/bold green]"):
        try:
            matches = finder.find_sellers(queries=queries)
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
        tree.add(f"Dopasowane przedmioty: [bold cyan]{match.matched_count} / {len(keywords)}[/bold cyan]")
        tree.add(f"Szacowana min. suma: [bold green]{match.total_price_with_delivery:.2f} PLN[/bold green]")

        offers_node = tree.add("Sugerowany zestaw (najtańsze oferty):")
        for kw, m_offer in match.best_offers.items():
            offer = m_offer.offer
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
