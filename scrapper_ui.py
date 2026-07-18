
import streamlit as st

from prod_assistant.etl.data_ingestion import DataIngestion
from prod_assistant.etl.data_scrapper import FlipkartScraper
from prod_assistant.logger import GLOBAL_LOGGER as log

flipkart_scraper = FlipkartScraper()
output_path = "data/product_reviews.csv"
st.title("📦 Product Review Scraper")

if "product_inputs" not in st.session_state:
    st.session_state.product_inputs = [""]

log.info("Loaded scraper UI")

def add_product_input():
    st.session_state.product_inputs.append("")

st.subheader("📝 Optional Product Description")
product_description = st.text_area("Enter product description (used as an extra search keyword):")

st.subheader("🛒 Product Names")
updated_inputs = []
for i, val in enumerate(st.session_state.product_inputs):
    input_val = st.text_input(f"Product {i+1}", value=val, key=f"product_{i}")
    updated_inputs.append(input_val)
st.session_state.product_inputs = updated_inputs

st.button("➕ Add Another Product", on_click=add_product_input)

max_products = st.number_input("How many products per search?", min_value=1, max_value=10, value=1)
review_count = st.number_input("How many reviews per product?", min_value=1, max_value=10, value=2)

if st.button("🚀 Start Scraping"):
    product_inputs = [p.strip() for p in st.session_state.product_inputs if p.strip()]
    if product_description.strip():
        product_inputs.append(product_description.strip())

    if not product_inputs:
        st.warning("⚠️ Please enter at least one product name or a product description.")
        log.warning("No product inputs supplied by the user")
    else:
        final_data = []
        log.info("Starting new scrape batch", queries=product_inputs, max_products=max_products, review_count=review_count)
        for query in product_inputs:
            try:
                st.write(f"🔍 Searching for: {query}")
                log.info("Scraping query", query=query)

                results = flipkart_scraper.scrape_flipkart_products(
                    query,
                    max_products=max_products,
                    review_count=review_count
                )

                final_data.extend(results)
                log.info("Completed scrape query", query=query, results_count=len(results))

            except Exception as e:
                st.error(f"Error while scraping {query}")
                st.exception(e)
                log.error("UI scrape failed", query=query, error=str(e))

        unique_products = {}
        for row in final_data:
            if row[1] not in unique_products:
                unique_products[row[1]] = row

        final_data = list(unique_products.values())
        st.session_state["scraped_data"] = final_data
        log.info("Deduplicated scrape results", result_count=len(final_data))
        flipkart_scraper.save_to_csv(final_data, output_path)

        with open(output_path, "rb") as fh:
            csv_bytes = fh.read()

        st.success("✅ Data saved to `data/product_reviews.csv`")
        st.download_button(
            "📥 Download CSV",
            data=csv_bytes,
            file_name="product_reviews.csv",
            mime="text/csv",
        )

# This stays OUTSIDE "if st.button('Start Scraping')"
if "scraped_data" in st.session_state and st.button("🧠 Store in Vector DB (AstraDB)"):
    with st.spinner("📡 Initializing ingestion pipeline..."):
        try:
            ingestion = DataIngestion()
            st.info("🚀 Running ingestion pipeline...")
            ingestion.run_pipeline()
            st.success("✅ Data successfully ingested to AstraDB!")
        except Exception as e:
            st.error("❌ Ingestion failed!")
            st.exception(e)