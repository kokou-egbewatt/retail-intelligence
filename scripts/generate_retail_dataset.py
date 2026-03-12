"""
Generate a synthetic global retail dataset for the Global Retail Intelligence Engine.
Output: CSV with Product_ID, Country, Category, Item_Name, Price_Local, Currency,
        Technical_Specs, Internal_Notes (confidential supplier/margin data).

Usage:
  python scripts/generate_retail_dataset.py                    # 5000 records -> data/raw/products_raw.csv
  python scripts/generate_retail_dataset.py --records 500     # 500 records for testing
  python scripts/generate_retail_dataset.py --records 500 --output data/raw/products_test.csv
"""
import argparse
import csv
import random
from pathlib import Path

# Countries and currencies (realistic regional coverage)
COUNTRIES = [
    ("Ghana", "GHS"),
    ("Nigeria", "NGN"),
    ("Côte d'Ivoire", "XOF"),
    ("South Africa", "ZAR"),
    ("Kenya", "KES"),
    ("Germany", "EUR"),
    ("United Kingdom", "GBP"),
    ("France", "EUR"),
    ("Netherlands", "EUR"),
    ("United States", "USD"),
    ("Canada", "CAD"),
]

# Electronics and kitchen product catalog with base prices in USD for scaling
ELECTRONICS = [
    ("LED TV 55 inch", "TV & Display", 450, "55\" FHD LED, Smart TV, 3x HDMI, USB, built-in WiFi"),
    ("Solar Inverter TS-9000-X", "Solar & Power", 1200, "5kW capacity, IP65 rated, 10-year warranty, MPPT tracking"),
    ("Smart Kettle Pro", "Kitchen Appliances", 45, "1.7L, 3000W, boil-dry protection, LED display"),
    ("Wireless Bluetooth Earbuds", "Audio", 35, "ANC, 24h battery, IPX5, USB-C"),
    ("LED Desk Lamp", "Lighting", 28, "Dimmable, USB port, 5 brightness levels"),
    ("Portable Power Bank 20K", "Power & Batteries", 25, "20000mAh, dual USB, 18W PD"),
    ("Smart Watch Sport", "Wearables", 89, "GPS, heart rate, 5ATM, 7-day battery"),
    ("Mechanical Keyboard", "Computing", 75, "Cherry MX, RGB, wired, UK layout"),
    ("Webcam HD Pro", "Computing", 55, "1080p 60fps, built-in mic, auto-focus"),
    ("Electric Toothbrush", "Personal Care", 42, "Sonic, 3 modes, 2-week battery"),
    ("Air Purifier Compact", "Home Appliances", 95, "HEPA H13, 3 speeds, 25m² coverage"),
    ("Coffee Maker Drip", "Kitchen Appliances", 38, "12-cup, programmable, thermal carafe"),
    ("Bluetooth Speaker", "Audio", 48, "20W, waterproof IPX7, 15h playback"),
    ("Tablet 10\"", "Computing", 199, "128GB, 10.1\" FHD, 4GB RAM, WiFi"),
    ("Fitness Tracker Band", "Wearables", 29, "Steps, sleep, HR, 14-day battery"),
    ("Electric Fan Tower", "Home Appliances", 52, "Oscillating, 3 speeds, remote, timer"),
]

# Internal notes templates (confidential - supplier names, margins, warehouse)
SUPPLIER_NAMES = [
    "Acme Electronics Ltd", "Global Sourcing Co", "Pacific Imports Inc",
    "EuroTech Suppliers", "Africa Direct Trading", "Nordic Wholesale",
]
MARGIN_NOTES = [
    "Margin 22%", "Target margin 18%", "Bulk discount applies 15%",
    "VIP margin 25%", "Promo margin 12%",
]
WAREHOUSE_NOTES = [
    "Warehouse A-12", "Stock in WH3 Berlin", "Fulfilled from NL depot",
    "Backorder until 02/15", "Low stock alert",
]


def generate_product_id(country_code: str, index: int) -> str:
    """Generate a country-prefixed product ID."""
    prefix = "".join(c[0] for c in country_code.split()[:2]).upper()[:2]
    if len(prefix) < 2:
        prefix = country_code[:2].upper()
    return f"{prefix}-{chr(65 + (index % 26))}-{index:04d}"


def price_for_country(base_usd: float, country: str, currency: str) -> float:
    """Convert base USD to local price (simplified regional multipliers)."""
    # Rough conversion and regional adjustment
    rates = {
        "GHS": 12.5, "NGN": 1550, "XOF": 600, "ZAR": 18, "KES": 128,
        "EUR": 0.92, "GBP": 0.79, "USD": 1.0, "CAD": 1.36,
    }
    rate = rates.get(currency, 1.0)
    local = base_usd * rate * random.uniform(0.95, 1.15)
    return round(local, 2)


def generate_internal_notes() -> str:
    """Confidential internal notes (supplier, margin, warehouse)."""
    parts = [
        random.choice(SUPPLIER_NAMES),
        random.choice(MARGIN_NOTES),
        random.choice(WAREHOUSE_NOTES),
    ]
    random.shuffle(parts)
    return " | ".join(parts)


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic retail product data for the Global Retail Intelligence Engine.",
    )
    parser.add_argument(
        "--records",
        type=int,
        default=5000,
        help="Number of records to generate (default: 5000). Use 500 for testing.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output CSV path (default: data/raw/products_raw.csv). Use e.g. data/raw/products_test.csv for test data.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible data (optional).",
    )
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    raw_dir = project_root / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_path = Path(args.output) if args.output else raw_dir / "products_raw.csv"
    if not output_path.is_absolute():
        output_path = project_root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    target_records = max(1, args.records)
    rows = []
    seen_ids = set()

    for i in range(target_records):
        country, currency = random.choice(COUNTRIES)
        item_name, category, base_usd, specs = random.choice(ELECTRONICS)
        product_id = generate_product_id(country, i)
        while product_id in seen_ids:
            i += 1
            product_id = generate_product_id(country, i)
        seen_ids.add(product_id)

        price = price_for_country(base_usd, country, currency)
        internal_notes = generate_internal_notes()

        rows.append({
            "Product_ID": product_id,
            "Country": country,
            "Category": category,
            "Item_Name": item_name,
            "Price_Local": price,
            "Currency": currency,
            "Technical_Specs": specs,
            "Internal_Notes": internal_notes,
        })

    fieldnames = ["Product_ID", "Country", "Category", "Item_Name", "Price_Local", "Currency", "Technical_Specs", "Internal_Notes"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} records -> {output_path}")


if __name__ == "__main__":
    main()
