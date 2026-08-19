from flask import Flask, render_template, jsonify, send_file
import pandas as pd

from scraper import scrape_products


app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/static"
)

CSV_FILE = "products.csv"


@app.route("/")
def home():

    try:
        df = pd.read_csv(CSV_FILE)
        products = df.to_dict(orient="records")

    except (FileNotFoundError, pd.errors.EmptyDataError):
        products = []

    return render_template(
        "index.html",
        products=products
    )


@app.route("/scrape", methods=["POST"])
def run_scraper():

    try:

        products = scrape_products(limit=20)

        if not products:
            return jsonify({
                "success": False,
                "message": "No products were scraped."
            })

        df = pd.DataFrame(products)

        df = df.drop_duplicates(
            subset=["Name"]
        )

        df.to_csv(
            CSV_FILE,
            index=False
        )

        return jsonify({
            "success": True,
            "message": f"Successfully scraped {len(df)} products."
        })

    except Exception as error:

        return jsonify({
            "success": False,
            "message": str(error)
        })


@app.route("/products.csv")
def download_csv():

    return send_file(
        CSV_FILE,
        as_attachment=True,
        download_name="products.csv"
    )


if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )