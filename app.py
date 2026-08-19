import csv
import ipaddress
import json
import os
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse

from flask import Flask, jsonify, render_template, request, send_file

from scraper import scrape_url


app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_FILE = os.path.join(
    BASE_DIR,
    "latest_data.json"
)

CSV_FILE = os.path.join(
    BASE_DIR,
    "products.csv"
)

HISTORY_FILE = os.path.join(
    BASE_DIR,
    "scrape_history.json"
)


FIELD_LABELS = {
    "name": "Name",
    "price": "Price",
    "rating": "Rating",
    "description": "Description",
    "link": "Link",
    "image": "Image",
    "author": "Author",
    "date": "Date",
    "text": "Text"
}


DEFAULT_FIELDS = [
    "name",
    "price",
    "rating",
    "description",
    "link"
]


def load_json(path, fallback):

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except (
        FileNotFoundError,
        json.JSONDecodeError
    ):

        return fallback


def save_json(path, data):

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )


def save_csv(records):

    if not records:

        with open(
            CSV_FILE,
            "w",
            encoding="utf-8",
            newline=""
        ) as file:

            file.write("")

        return


    columns = []

    for record in records:

        for key in record:

            if key not in columns:

                columns.append(key)


    with open(
        CSV_FILE,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=columns,
            extrasaction="ignore"
        )

        writer.writeheader()

        writer.writerows(records)


def validate_public_url(url):

    try:

        parsed = urlparse(url)

        if parsed.scheme not in [
            "http",
            "https"
        ]:

            return (
                False,
                "Only HTTP and HTTPS URLs are supported."
            )


        if not parsed.hostname:

            return (
                False,
                "Invalid URL."
            )


        hostname = parsed.hostname.lower()


        blocked_hosts = {
            "localhost",
            "localhost.localdomain",
            "127.0.0.1",
            "0.0.0.0",
            "::1"
        }


        if hostname in blocked_hosts:

            return (
                False,
                "Local addresses are not allowed."
            )


        if hostname.endswith(".local"):

            return (
                False,
                "Local network addresses are not allowed."
            )


        try:

            addresses = socket.getaddrinfo(
                hostname,
                None
            )

        except socket.gaierror:

            return (
                False,
                "Unable to resolve hostname."
            )


        for address in addresses:

            ip = ipaddress.ip_address(
                address[4][0]
            )

            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_multicast
                or ip.is_reserved
                or ip.is_unspecified
            ):

                return (
                    False,
                    "Private network addresses are not allowed."
                )


        return True, ""


    except Exception:

        return (
            False,
            "Invalid URL."
        )


def get_latest_data():

    return load_json(
        DATA_FILE,
        {
            "records": [],
            "fields": [],
            "page_type": "—",
            "title": "",
            "url": "",
            "elapsed": 0,
            "status": None
        }
    )


@app.route("/")
def home():

    data = get_latest_data()

    records = data.get(
        "records",
        []
    )


    columns = []

    for record in records:

        for key in record:

            if key not in columns:

                columns.append(key)


    return render_template(
        "index.html",
        data=data,
        records=records,
        columns=columns,
        field_labels=FIELD_LABELS,
        default_fields=DEFAULT_FIELDS,
        history=load_json(
            HISTORY_FILE,
            []
        )
    )


@app.route(
    "/scrape",
    methods=["POST"]
)
def scrape():

    payload = request.get_json(
        silent=True
    ) or {}


    url = str(
        payload.get(
            "url",
            ""
        )
    ).strip()


    fields = payload.get(
        "fields",
        DEFAULT_FIELDS
    )


    selectors = payload.get(
        "selectors",
        {}
    )


    if not url:

        return jsonify({
            "success": False,
            "message": "Please enter a website URL."
        }), 400


    valid, reason = validate_public_url(
        url
    )


    if not valid:

        return jsonify({
            "success": False,
            "message": reason
        }), 400


    allowed_fields = set(
        FIELD_LABELS.keys()
    )


    fields = [
        str(field).lower().strip()
        for field in fields
        if str(field).lower().strip()
        in allowed_fields
    ]


    if not fields:

        return jsonify({
            "success": False,
            "message": "Select at least one field."
        }), 400


    selectors = {
        str(key): str(value).strip()
        for key, value in selectors.items()
        if key in allowed_fields
        and str(value).strip()
    }


    try:

        result = scrape_url(
            url=url,
            fields=fields,
            selectors=selectors,
            max_records=100
        )


        data = {
            **result,
            "fields": fields,
            "scraped_at": datetime.now(
                timezone.utc
            ).isoformat()
        }


        save_json(
            DATA_FILE,
            data
        )


        save_csv(
            result.get(
                "records",
                []
            )
        )


        history = load_json(
            HISTORY_FILE,
            []
        )


        history.insert(
            0,
            {
                "url": result.get(
                    "url",
                    url
                ),
                "title": result.get(
                    "title",
                    ""
                ),
                "page_type": result.get(
                    "page_type",
                    "Web page"
                ),
                "records": len(
                    result.get(
                        "records",
                        []
                    )
                ),
                "elapsed": result.get(
                    "elapsed",
                    0
                ),
                "scraped_at": data[
                    "scraped_at"
                ]
            }
        )


        save_json(
            HISTORY_FILE,
            history[:10]
        )


        return jsonify({
            "success": True,
            "message": (
                "Extraction completed — "
                f"{len(result.get('records', []))} "
                "records found."
            ),
            "count": len(
                result.get(
                    "records",
                    []
                )
            ),
            "page_type": result.get(
                "page_type"
            ),
            "elapsed": result.get(
                "elapsed"
            )
        })


    except Exception as error:

        app.logger.exception(
            "Scraping failed"
        )


        return jsonify({
            "success": False,
            "message": (
                f"Scraping failed: "
                f"{type(error).__name__}: "
                f"{error}"
            )
        }), 500


@app.route("/products.csv")
def download_csv():

    if not os.path.exists(
        CSV_FILE
    ):

        save_csv(
            get_latest_data().get(
                "records",
                []
            )
        )


    return send_file(
        CSV_FILE,
        mimetype="text/csv",
        as_attachment=True,
        download_name="products.csv"
    )


@app.route("/data.json")
def download_json():

    return send_file(
        DATA_FILE,
        mimetype="application/json",
        as_attachment=True,
        download_name="products.json"
    )


@app.route("/health")
def health():

    return jsonify({
        "status": "ok"
    })


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        ),
        debug=True
    )