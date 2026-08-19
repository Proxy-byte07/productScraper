from playwright.sync_api import sync_playwright
import re


BASE_URL = "https://scrapingsandbox.com"


def scrape_products(limit=20):
    products = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            print("Opening Scraping Sandbox...")

            # Open main product listing
            page.goto(
                BASE_URL,
                wait_until="networkidle",
                timeout=30000
            )

            # Find all product links
            links = page.locator('a[href^="/product/"]')

            total = links.count()

            print(f"Products found: {total}")

            # Collect URLs before navigating away
            product_urls = []

            for i in range(total):
                href = links.nth(i).get_attribute("href")

                if href:
                    url = BASE_URL + href

                    if url not in product_urls:
                        product_urls.append(url)

            # Limit number of products
            product_urls = product_urls[:limit]

            print(
                f"Products to scrape: {len(product_urls)}"
            )

            # Scrape each product
            for index, product_url in enumerate(
                product_urls,
                start=1
            ):

                print(
                    f"Scraping product "
                    f"{index}/{len(product_urls)}..."
                )

                try:

                    page.goto(
                        product_url,
                        wait_until="networkidle",
                        timeout=30000
                    )

                    # -------------------------
                    # Product Name
                    # -------------------------

                    name = "Not available"

                    title = page.locator("h1")

                    if title.count() > 0:
                        name = (
                            title.first
                            .inner_text()
                            .strip()
                        )

                    # -------------------------
                    # Page text
                    # -------------------------

                    body_text = (
                        page.locator("body")
                        .inner_text()
                    )

                    # -------------------------
                    # Price
                    # -------------------------

                    price_match = re.search(
                        r"\$(\d+(?:\.\d{2})?)",
                        body_text
                    )

                    if price_match:
                        price = (
                            "$" +
                            price_match.group(1)
                        )
                    else:
                        price = "Not available"

                    # -------------------------
                    # Rating
                    # -------------------------

                    rating_match = re.search(
                        r"\b([0-5](?:\.\d+)?)\s*"
                        r"\(\d+\s+reviews?\)",
                        body_text,
                        re.IGNORECASE
                    )

                    if rating_match:
                        rating = rating_match.group(1)
                    else:
                        rating = "Not available"

                    # -------------------------
                    # Save product
                    # -------------------------

                    products.append({
                        "Name": name,
                        "Price": price,
                        "Rating": rating
                    })

                    print(
                        f"  ✓ {name} | "
                        f"{price} | "
                        f"Rating: {rating}"
                    )

                except Exception as error:

                    print(
                        f"  ✗ Product failed: "
                        f"{error}"
                    )

            print("\nScraping completed.")

        except Exception as error:

            print(
                f"\nScraping error: {error}"
            )

        finally:
            browser.close()

    return products