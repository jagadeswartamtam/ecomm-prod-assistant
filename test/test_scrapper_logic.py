from prod_assistant.etl.data_scrapper import FlipkartScraper


def test_extract_product_links_from_page_source_returns_multiple_links():
    scraper = FlipkartScraper(output_dir="data")
    html = """
    <html><body>
      <a href="https://www.flipkart.com/product-1/p/itm111">Product 1</a>
      <a href="https://www.flipkart.com/product-2/p/itm222">Product 2</a>
      <a href="https://www.flipkart.com/search?q=phone">Search link</a>
    </body></html>
    """

    links = scraper._extract_product_links_from_page_source(html, max_products=3)

    assert len(links) == 2
    assert links[0].endswith("/p/itm111")
    assert links[1].endswith("/p/itm222")


def test_extract_review_texts_ignores_filter_text():
    scraper = FlipkartScraper(output_dir="data")
    html = """
    <html><body>
      <div>Filters CATEGORIES Mobiles Battery Capacity</div>
      <div>Overall Camera Battery Display Value for Money</div>
      <div class='review'>This phone has a great battery and the display is very sharp. I am very happy with the performance.</div>
    </body></html>
    """

    reviews = scraper._extract_review_texts_from_html(html)

    assert len(reviews) == 1
    assert "great battery" in reviews[0]


def test_clean_review_text_removes_pipe_delimited_header():
    scraper = FlipkartScraper(output_dir="data")
    text = "Overall Camera Battery Display Design Performance Build Quality Value for Money || I just loving this phone❤️ Thank you, Flipkart"

    cleaned = scraper._clean_review_text(text)

    assert "Overall Camera Battery Display Design Performance Build Quality Value for Money" not in cleaned
    assert "I just loving this phone" in cleaned


def test_extract_rating_from_page_prefers_structured_rating_metadata_over_generic_decimal():
    scraper = FlipkartScraper(output_dir="data")
    html = """
    <html><body>
      <div class="_3LWZlK">1.2</div>
      <meta itemprop="ratingValue" content="4.6" />
      <meta itemprop="reviewCount" content="1234" />
    </body></html>
    """

    rating = scraper._extract_rating_from_page(html)

    assert rating == "4.6"
