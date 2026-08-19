import json
import re
import time

from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


FIELD_ALIASES = {

    "name": [
        "name",
        "title",
        "product",
        "item",
        "headline"
    ],

    "price": [
        "price",
        "cost",
        "amount",
        "sale-price"
    ],

    "rating": [
        "rating",
        "stars",
        "score"
    ],

    "description": [
        "description",
        "summary",
        "excerpt",
        "details"
    ],

    "link": [
        "link",
        "url",
        "href"
    ],

    "image": [
        "image",
        "img",
        "thumbnail",
        "photo"
    ],

    "author": [
        "author",
        "byline",
        "writer"
    ],

    "date": [
        "date",
        "published",
        "time",
        "timestamp"
    ],

    "text": [
        "text",
        "content",
        "body"
    ]
}


def clean(value):

    return re.sub(
        r"\s+",
        " ",
        value or ""
    ).strip()


# =========================================================
# BASIC ELEMENT HELPERS
# =========================================================

def get_link(element, base_url):

    if not element:

        return ""


    if (
        element.name == "a"
        and element.get("href")
    ):

        return urljoin(
            base_url,
            element["href"]
        )


    anchor = element.find(
        "a",
        href=True
    )


    if anchor:

        return urljoin(
            base_url,
            anchor["href"]
        )


    return ""


def get_image(element, base_url):

    if not element:

        return ""


    image = (
        element
        if element.name == "img"
        else element.find("img")
    )


    if not image:

        return ""


    source = (
        image.get("src")
        or image.get("data-src")
        or image.get("data-lazy-src")
        or image.get("data-original")
    )


    if not source:

        return ""


    return urljoin(
        base_url,
        source
    )


def element_value(
    element,
    field,
    base_url
):

    if not element:

        return ""


    if field == "link":

        return get_link(
            element,
            base_url
        )


    if field == "image":

        return get_image(
            element,
            base_url
        )


    return clean(
        element.get_text(
            " ",
            strip=True
        )
    )


# =========================================================
# CSS SELECTOR EXTRACTION
# =========================================================

def selector_value(
    container,
    selector,
    field,
    base_url
):

    if not selector:

        return ""


    try:

        element = container.select_one(
            selector
        )

    except Exception:

        return ""


    return element_value(
        element,
        field,
        base_url
    )


# =========================================================
# HEURISTIC EXTRACTION
# =========================================================

def heuristic_value(
    container,
    field,
    base_url
):

    if not container:

        return ""


    if field == "link":

        return get_link(
            container,
            base_url
        )


    if field == "image":

        return get_image(
            container,
            base_url
        )


    if field == "text":

        return clean(
            container.get_text(
                " ",
                strip=True
            )
        )[:2000]


    aliases = FIELD_ALIASES.get(
        field,
        [field]
    )


    elements = container.find_all(
        [
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "p",
            "span",
            "div",
            "strong",
            "b",
            "a",
            "time"
        ],
        limit=150
    )


    best = None
    best_score = 0


    for element in elements:

        attributes = " ".join([

            str(
                element.get(
                    "class",
                    ""
                )
            ),

            str(
                element.get(
                    "id",
                    ""
                )
            ),

            str(
                element.get(
                    "itemprop",
                    ""
                )
            ),

            str(
                element.get(
                    "data-testid",
                    ""
                )
            ),

            str(
                element.get(
                    "aria-label",
                    ""
                )
            )

        ]).lower()


        score = 0


        for alias in aliases:

            if alias in attributes:

                score += 3


        text = element.get_text(
            " ",
            strip=True
        )


        if (
            field == "price"
            and re.search(
                r"(₹|\$|€|£)\s?\d",
                text
            )
        ):

            score += 5


        if (
            field == "rating"
            and re.search(
                r"\b[0-5](?:\.\d)?\s*(?:/5|stars?|out of 5)?\b",
                text,
                re.I
            )
        ):

            score += 3


        if score > best_score:

            best = element
            best_score = score


    if best:

        value = element_value(
            best,
            field,
            base_url
        )


        if value:

            return value


    text = clean(
        container.get_text(
            " ",
            strip=True
        )
    )


    if field == "price":

        match = re.search(
            r"(?:₹|\$|€|£)\s?\d[\d,]*(?:\.\d{1,2})?",
            text
        )


        return (
            match.group(0)
            if match
            else ""
        )


    if field == "rating":

        match = re.search(
            r"\b([0-5](?:\.\d)?)\s*(?:/5|stars?|out of 5)\b",
            text,
            re.I
        )


        return (
            match.group(1)
            if match
            else ""
        )


    if field == "name":

        heading = container.find(
            [
                "h1",
                "h2",
                "h3",
                "h4"
            ]
        )


        if heading:

            return clean(
                heading.get_text(
                    " ",
                    strip=True
                )
            )


    if field == "description":

        paragraph = container.find(
            "p"
        )


        if paragraph:

            return clean(
                paragraph.get_text(
                    " ",
                    strip=True
                )
            )


    if field == "author":

        match = re.search(
            r"(?:by|author)\s*[:\-]?\s*([A-Za-z][A-Za-z .'-]{2,60})",
            text,
            re.I
        )


        return (
            clean(
                match.group(1)
            )
            if match
            else ""
        )


    if field == "date":

        time_element = container.find(
            "time"
        )


        if time_element:

            return clean(
                time_element.get(
                    "datetime"
                )
                or time_element.get_text(
                    " ",
                    strip=True
                )
            )


    return ""


# =========================================================
# PAGE TYPE DETECTION
# =========================================================

def detect_page_type(soup):

    text = clean(
        soup.get_text(
            " ",
            strip=True
        )
    ).lower()


    if soup.find("table"):

        return "table"


    if (
        soup.find(
            attrs={
                "itemtype": re.compile(
                    "Product",
                    re.I
                )
            }
        )
        or "add to basket" in text
        or "add to cart" in text
        or "buy now" in text
        or "shopping cart" in text
    ):

        return "e-commerce"


    if soup.find("article"):

        return "article"


    if (
        "job description" in text
        or "apply now" in text
        or "salary" in text
    ):

        return "jobs"


    return "web page"


# =========================================================
# SPECIALIZED E-COMMERCE EXTRACTION
# =========================================================

def extract_product_cards(
    soup,
    base_url,
    fields,
    selectors
):

    containers = soup.select(
        """
        article.product_pod,
        .product_pod,
        .product-card,
        .product-item,
        .product,
        [class*="product-card"],
        [class*="product-item"],
        [class*="product_pod"],
        [data-product-id]
        """
    )


    records = []


    for container in containers[:100]:

        record = {}


        # -------------------------------------------------
        # NAME
        # -------------------------------------------------

        if "name" in fields:

            value = ""


            if selectors.get("name"):

                value = selector_value(
                    container,
                    selectors["name"],
                    "name",
                    base_url
                )


            if not value:

                # Books to Scrape
                element = container.select_one(
                    "h3 a"
                )


                if element:

                    value = (
                        element.get("title")
                        or element.get_text(
                            " ",
                            strip=True
                        )
                    )


            if not value:

                element = container.select_one(
                    "h2 a, "
                    "h3 a, "
                    "[class*='title'] a, "
                    "[class*='name']"
                )


                if element:

                    value = clean(
                        element.get_text(
                            " ",
                            strip=True
                        )
                    )


            if not value:

                value = heuristic_value(
                    container,
                    "name",
                    base_url
                )


            record["name"] = clean(
                value
            )


        # -------------------------------------------------
        # PRICE
        # -------------------------------------------------

        if "price" in fields:

            value = ""


            if selectors.get("price"):

                value = selector_value(
                    container,
                    selectors["price"],
                    "price",
                    base_url
                )


            if not value:

                # Books to Scrape
                element = container.select_one(
                    ".price_color"
                )


                if element:

                    value = clean(
                        element.get_text(
                            " ",
                            strip=True
                        )
                    )


            if not value:

                text = container.get_text(
                    " ",
                    strip=True
                )


                match = re.search(
                    r"(?:₹|\$|€|£)\s?\d[\d,]*(?:\.\d{1,2})?",
                    text
                )


                if match:

                    value = match.group(0)


            record["price"] = clean(
                value
            )


        # -------------------------------------------------
        # RATING
        # -------------------------------------------------

        if "rating" in fields:

            value = ""


            if selectors.get("rating"):

                value = selector_value(
                    container,
                    selectors["rating"],
                    "rating",
                    base_url
                )


            if not value:

                element = container.select_one(
                    ".star-rating"
                )


                if element:

                    classes = element.get(
                        "class",
                        []
                    )


                    rating_map = {

                        "One": "1",

                        "Two": "2",

                        "Three": "3",

                        "Four": "4",

                        "Five": "5"

                    }


                    for class_name in classes:

                        if (
                            class_name
                            in rating_map
                        ):

                            value = (
                                rating_map[
                                    class_name
                                ]
                            )

                            break


            if not value:

                value = heuristic_value(
                    container,
                    "rating",
                    base_url
                )


            record["rating"] = clean(
                value
            )


        # -------------------------------------------------
        # DESCRIPTION
        # -------------------------------------------------

        if "description" in fields:

            value = ""


            if selectors.get(
                "description"
            ):

                value = selector_value(
                    container,
                    selectors["description"],
                    "description",
                    base_url
                )


            if not value:

                element = container.select_one(
                    ".description, "
                    "[class*='description'], "
                    "[class*='summary']"
                )


                if element:

                    value = clean(
                        element.get_text(
                            " ",
                            strip=True
                        )
                    )


            record["description"] = value


        # -------------------------------------------------
        # LINK
        # -------------------------------------------------

        if "link" in fields:

            value = ""


            if selectors.get("link"):

                value = selector_value(
                    container,
                    selectors["link"],
                    "link",
                    base_url
                )


            if not value:

                element = container.select_one(
                    "h3 a, "
                    "h2 a, "
                    "a[href]"
                )


                if element:

                    value = urljoin(
                        base_url,
                        element.get(
                            "href",
                            ""
                        )
                    )


            record["link"] = value


        # -------------------------------------------------
        # IMAGE
        # -------------------------------------------------

        if "image" in fields:

            value = ""


            if selectors.get("image"):

                value = selector_value(
                    container,
                    selectors["image"],
                    "image",
                    base_url
                )


            if not value:

                value = get_image(
                    container,
                    base_url
                )


            record["image"] = value


        # -------------------------------------------------
        # AUTHOR
        # -------------------------------------------------

        if "author" in fields:

            record["author"] = heuristic_value(
                container,
                "author",
                base_url
            )


        # -------------------------------------------------
        # DATE
        # -------------------------------------------------

        if "date" in fields:

            record["date"] = heuristic_value(
                container,
                "date",
                base_url
            )


        # -------------------------------------------------
        # TEXT
        # -------------------------------------------------

        if "text" in fields:

            record["text"] = clean(
                container.get_text(
                    " ",
                    strip=True
                )
            )


        if any(
            str(value).strip()
            for value in record.values()
        ):

            records.append(
                record
            )


    return records


# =========================================================
# REPEATED HTML CONTAINERS
# =========================================================

def find_repeated_containers(
    soup
):

    candidates = []


    for tag in soup.find_all(
        [
            "article",
            "li",
            "div",
            "section"
        ]
    ):

        classes = tag.get(
            "class",
            []
        )


        if not classes:

            continue


        marker = " ".join(
            classes
        ).lower()


        keywords = [

            "card",
            "product",
            "item",
            "result",
            "listing",
            "article",
            "post",
            "job",
            "entry",
            "tile",
            "row"

        ]


        if not any(
            word in marker
            for word in keywords
        ):

            continue


        key = (
            tag.name,
            " ".join(classes)
        )


        candidates.append(
            (
                key,
                tag
            )
        )


    groups = {}


    for key, tag in candidates:

        groups.setdefault(
            key,
            []
        ).append(tag)


    groups = [

        group
        for group in groups.values()
        if len(group) >= 2

    ]


    if not groups:

        return []


    groups.sort(
        key=lambda group: len(group),
        reverse=True
    )


    return groups[0][:100]


# =========================================================
# TABLE EXTRACTION
# =========================================================

def extract_table(soup):

    table = soup.find(
        "table"
    )


    if not table:

        return []


    rows = table.find_all(
        "tr"
    )


    if not rows:

        return []


    headers = [

        clean(
            cell.get_text(
                " ",
                strip=True
            )
        )

        for cell in rows[0].find_all(
            ["th", "td"]
        )

    ]


    records = []


    for row in rows[1:101]:

        cells = row.find_all(
            ["td", "th"]
        )


        if not cells:

            continue


        values = [

            clean(
                cell.get_text(
                    " ",
                    strip=True
                )
            )

            for cell in cells

        ]


        record = {}


        for index, value in enumerate(
            values
        ):

            key = (

                headers[index]

                if (
                    index < len(headers)
                    and headers[index]
                )

                else
                f"column_{index + 1}"

            )


            record[key] = value


        if record:

            records.append(
                record
            )


    return records


# =========================================================
# JSON-LD EXTRACTION
# =========================================================

def extract_jsonld(
    soup,
    base_url
):

    records = []


    scripts = soup.find_all(
        "script",
        type="application/ld+json"
    )


    for script in scripts:

        raw = (
            script.string
            or script.get_text()
        )


        try:

            data = json.loads(
                raw
            )

        except Exception:

            continue


        items = (

            data

            if isinstance(
                data,
                list
            )

            else [data]

        )


        queue = list(
            items
        )


        while queue:

            item = queue.pop(0)


            if not isinstance(
                item,
                dict
            ):

                continue


            graph = item.get(
                "@graph"
            )


            if isinstance(
                graph,
                list
            ):

                queue.extend(
                    graph
                )


            item_type = str(
                item.get(
                    "@type",
                    ""
                )
            ).lower()


            supported = {

                "product",
                "article",
                "newsarticle",
                "jobposting",
                "event",
                "recipe"

            }


            if item_type not in supported:

                continue


            record = {}


            for key in [

                "name",
                "description",
                "url",
                "image",
                "author",
                "datePublished",
                "datePosted",
                "aggregateRating"

            ]:

                if key not in item:

                    continue


                value = item[key]


                if isinstance(
                    value,
                    dict
                ):

                    value = (

                        value.get(
                            "name"
                        )

                        or value.get(
                            "ratingValue"
                        )

                        or value.get(
                            "price"
                        )

                        or ""

                    )


                if isinstance(
                    value,
                    list
                ):

                    value = (

                        value[0]
                        if value
                        else ""

                    )


                if (
                    key in [
                        "url",
                        "image"
                    ]
                    and value
                ):

                    value = urljoin(
                        base_url,
                        str(value)
                    )


                record[key] = str(
                    value
                )


            if record:

                records.append(
                    record
                )


    return records[:100]


# =========================================================
# NORMALIZE JSON-LD DATA
# =========================================================

def normalize_record(
    record
):

    aliases = {

        "name": [
            "name",
            "title",
            "product",
            "headline"
        ],

        "price": [
            "price",
            "cost",
            "amount"
        ],

        "rating": [
            "rating",
            "aggregaterating"
        ],

        "description": [
            "description",
            "summary",
            "excerpt"
        ],

        "link": [
            "link",
            "url"
        ],

        "image": [
            "image",
            "img"
        ],

        "author": [
            "author"
        ],

        "date": [
            "date",
            "datepublished",
            "dateposted"
        ]

    }


    lower = {

        str(key).lower():
        value

        for key, value
        in record.items()

    }


    output = {}


    for canonical, keys in aliases.items():

        for key in keys:

            if key in lower:

                value = lower[key]


                if isinstance(
                    value,
                    dict
                ):

                    value = (

                        value.get(
                            "ratingValue"
                        )

                        or value.get(
                            "name"
                        )

                        or ""

                    )


                output[
                    canonical
                ] = clean(
                    str(value)
                )


                break


    return output


# =========================================================
# MAIN SCRAPER
# =========================================================

def scrape_url(
    url,
    fields,
    selectors=None,
    max_records=100
):

    selectors = selectors or {}

    started = time.perf_counter()


    with sync_playwright() as playwright:

        browser = playwright.chromium.launch(

            headless=True,

            args=[

                "--no-sandbox",

                "--disable-dev-shm-usage"

            ]

        )


        page = browser.new_page(

            viewport={

                "width": 1440,

                "height": 900

            }

        )


        try:

            response = page.goto(

                url,

                wait_until="domcontentloaded",

                timeout=30000

            )


            try:

                page.wait_for_load_state(
                    "networkidle",
                    timeout=5000
                )

            except Exception:

                pass


            page.wait_for_timeout(
                1000
            )


            html = page.content()

            final_url = page.url


            status = (

                response.status

                if response

                else 200

            )


        finally:

            browser.close()


    soup = BeautifulSoup(
        html,
        "lxml"
    )


    page_type = detect_page_type(
        soup
    )


    records = []


    # =====================================================
    # METHOD 1: E-COMMERCE PRODUCT CARDS
    # =====================================================

    if page_type == "e-commerce":

        records = extract_product_cards(

            soup,

            final_url,

            fields,

            selectors

        )


    # =====================================================
    # METHOD 2: HTML TABLE
    # =====================================================

    if not records:

        table_records = extract_table(
            soup
        )


        if table_records:

            records = table_records


    # =====================================================
    # METHOD 3: JSON-LD
    # =====================================================

    if not records:

        json_records = extract_jsonld(

            soup,

            final_url

        )


        records = [

            normalize_record(
                record
            )

            for record
            in json_records

        ]


    # =====================================================
    # METHOD 4: REPEATED CARDS
    # =====================================================

    if not records:

        containers = find_repeated_containers(
            soup
        )


        for container in containers:

            record = {}


            for field in fields:

                value = selector_value(

                    container,

                    selectors.get(
                        field
                    ),

                    field,

                    final_url

                )


                if not value:

                    value = heuristic_value(

                        container,

                        field,

                        final_url

                    )


                record[field] = value


            if any(
                record.values()
            ):

                records.append(
                    record
                )


    # =====================================================
    # METHOD 5: WHOLE PAGE FALLBACK
    # =====================================================

    if not records:

        container = (

            soup.find("main")

            or soup.find("article")

            or soup.body

            or soup

        )


        record = {}


        for field in fields:

            value = selector_value(

                container,

                selectors.get(
                    field
                ),

                field,

                final_url

            )


            if not value:

                value = heuristic_value(

                    container,

                    field,

                    final_url

                )


            record[field] = value


        records = [
            record
        ]


    # =====================================================
    # FINAL NORMALIZATION
    # =====================================================

    cleaned_records = []


    for record in records[
        :max_records
    ]:

        normalized = normalize_record(
            record
        )


        output = {}


        for field in fields:

            value = (

                record.get(
                    field
                )

                or normalized.get(
                    field
                )

                or ""

            )


            output[field] = clean(
                str(value)
            )


        if any(
            output.values()
        ):

            cleaned_records.append(
                output
            )


    elapsed = round(

        time.perf_counter()
        - started,

        2

    )


    title = ""


    if soup.title:

        title = clean(

            soup.title.get_text(
                " ",
                strip=True
            )

        )


    return {

        "records":
            cleaned_records,

        "page_type":
            page_type,

        "title":
            title,

        "url":
            final_url,

        "status":
            status,

        "elapsed":
            elapsed

    }