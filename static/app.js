const scrapeButton =
    document.getElementById("scrapeButton");

const message =
    document.getElementById("message");

const urlInput =
    document.getElementById("url");

const searchInput =
    document.getElementById("searchInput");

const selectAllButton =
    document.getElementById("selectAll");


function showMessage(
    text,
    type = "info"
) {

    message.textContent = text;

    message.className =
        `message ${type}`;
}


function getSelectedFields() {

    return [
        ...document.querySelectorAll(
            'input[name="field"]:checked'
        )
    ].map(
        input => input.value
    );
}


function getSelectors() {

    const selectors = {};


    document
        .querySelectorAll(
            ".selector-input"
        )
        .forEach(
            input => {

                const value =
                    input.value.trim();


                if (value) {

                    selectors[
                        input.dataset.field
                    ] = value;

                }

            }
        );


    return selectors;
}


selectAllButton.addEventListener(
    "click",
    () => {

        const checkboxes =
            document.querySelectorAll(
                'input[name="field"]'
            );


        const allChecked =
            [...checkboxes].every(
                checkbox =>
                    checkbox.checked
            );


        checkboxes.forEach(
            checkbox => {

                checkbox.checked =
                    !allChecked;

            }
        );


        selectAllButton.textContent =
            allChecked
                ? "Select all"
                : "Clear all";

    }
);


scrapeButton.addEventListener(
    "click",
    async () => {

        const url =
            urlInput.value.trim();


        const fields =
            getSelectedFields();


        const selectors =
            getSelectors();


        if (!url) {

            showMessage(
                "Enter a website URL first.",
                "error"
            );


            urlInput.focus();

            return;
        }


        if (!fields.length) {

            showMessage(
                "Select at least one field.",
                "error"
            );

            return;
        }


        scrapeButton.disabled =
            true;


        scrapeButton.innerHTML =
            '<span class="spinner"></span> Extracting...';


        showMessage(
            "Loading webpage and analyzing its structure...",
            "info"
        );


        try {

            const response =
                await fetch(
                    "/scrape",
                    {

                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({

                            url,

                            fields,

                            selectors

                        })

                    }
                );


            const raw =
                await response.text();


            let data;


            try {

                data =
                    JSON.parse(raw);

            } catch {

                throw new Error(

                    `Server returned HTTP ${
                        response.status
                    }: ${
                        raw.slice(0, 300)
                    }`

                );

            }


            if (
                !response.ok
                || !data.success
            ) {

                throw new Error(
                    data.message
                    ||
                    `Server returned HTTP ${
                        response.status
                    }`
                );

            }


            showMessage(

                `${data.message} ` +
                `Page type: ${data.page_type}. ` +
                `Time: ${data.elapsed}s.`,

                "success"

            );


            setTimeout(
                () => {

                    window.location.reload();

                },
                900
            );


        } catch (error) {

            console.error(
                "ProductLens error:",
                error
            );


            showMessage(
                error.message,
                "error"
            );


        } finally {

            scrapeButton.disabled =
                false;


            scrapeButton.innerHTML =
                "<span>↗</span> Start Extraction";

        }

    }
);


if (searchInput) {

    searchInput.addEventListener(
        "input",
        () => {

            const query =
                searchInput.value
                    .toLowerCase()
                    .trim();


            document
                .querySelectorAll(
                    "#resultsTable tbody tr"
                )
                .forEach(
                    row => {

                        row.style.display =
                            row.textContent
                                .toLowerCase()
                                .includes(query)
                                ? ""
                                : "none";

                    }
                );

        }
    );

}


urlInput.addEventListener(
    "keydown",
    event => {

        if (
            event.key === "Enter"
        ) {

            scrapeButton.click();

        }

    }
);