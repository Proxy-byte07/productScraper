import pandas as pd

from scraper import scrape_products


OUTPUT_FILE = "products.csv"


def save_to_csv(products):

    if not products:
        print("No products were extracted.")
        return

    df = pd.DataFrame(products)

    # Remove duplicate products
    df = df.drop_duplicates(
        subset=["Name"]
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8"
    )

    print(
        f"\nSuccessfully saved "
        f"{len(df)} products."
    )

    print(
        f"CSV file: {OUTPUT_FILE}"
    )


def main():

    print("=" * 45)
    print("       E-COMMERCE PRODUCT SCRAPER")
    print("=" * 45)

    products = scrape_products(
        limit=20
    )

    save_to_csv(products)

    print("\nProgram completed.")


if __name__ == "__main__":
    main()