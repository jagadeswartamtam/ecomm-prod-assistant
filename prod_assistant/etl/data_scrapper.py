import csv
import os
import re
import time

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from prod_assistant.logger import GLOBAL_LOGGER as log

try:
    import undetected_chromedriver as uc
except ImportError:  # pragma: no cover - exercised when dependency is absent
    uc = None

class FlipkartScraper:
    def __init__(self, output_dir="data"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        log.info("Initialized Flipkart scraper", output_dir=self.output_dir)

    def _get_driver(self):
        if uc is None:
            raise ImportError(
                "undetected-chromedriver is required for scraping. Install it with 'pip install undetected-chromedriver'."
            )

        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled")
        return uc.Chrome(options=options, version_main=150, use_subprocess=True)

    def scrape_flipkart_products(self, query, max_products=1, review_count=2):
        """Scrape Flipkart products based on a search query."""
        log.info("Starting Flipkart scrape", query=query, max_products=max_products, review_count=review_count)
        driver = self._get_driver()
        search_url = f"https://www.flipkart.com/search?q={query.replace(' ', '+')}"
        log.info("Opening search URL", url=search_url)
        driver.get(search_url)
        time.sleep(4)

        try:
            driver.find_element(By.XPATH, "//button[contains(text(), '✕')]").click()
        except Exception:
            pass

        time.sleep(2)
        products = []

        product_links = self._extract_product_links_from_page_source(driver.page_source, max_products=max_products)
        log.info("Search results loaded", query=query, items_found=len(product_links))

        for index, product_link in enumerate(product_links, start=1):
            try:
                product_url = product_link if product_link.startswith("http") else "https://www.flipkart.com" + product_link
                log.info("Processing product card", query=query, item_number=index, url=product_url)

                driver.get(product_url)
                time.sleep(3)
                self._wait_for_page_ready(driver)

                title = self._extract_title_from_page(driver.page_source)
                price = self._extract_price_from_page(driver.page_source)
                rating = self._extract_rating_from_page(driver.page_source)
                total_reviews = self._extract_review_count_from_page(driver.page_source)
                top_reviews = self.get_top_reviews(driver, product_url, count=review_count)

                product_id = self._extract_product_id(product_url)
            except Exception as e:
                log.error("Failed to parse product card", query=query, error=str(e))
                continue

            products.append([product_id, title, rating, total_reviews, price, top_reviews])
            log.info("Saved product result", query=query, product_id=product_id, title=title, price=price, rating=rating)

        driver.quit()
        return products
    @staticmethod
    def _clean_review_text(text):
        if not text:
            return ""

        cleaned = re.sub(r"\s+", " ", text).strip()
        for suffix in ["READ MORE", "Read More"]:
            if cleaned.endswith(suffix):
                cleaned = cleaned[: -len(suffix)].strip()

        cleaned = re.sub(r"^\d+\.\d+\s*•?\s*", "", cleaned)
        cleaned = re.sub(r"^\d+\s*•?\s*", "", cleaned)
        cleaned = re.sub(r"\bReview for:\s*[^|]+\s*", "", cleaned)
        cleaned = re.sub(r"\bHelpful for\s*\d+\b", "", cleaned)
        cleaned = re.sub(r"\bVerified Purchase\b", "", cleaned)
        cleaned = re.sub(r"\b\d+\s+months ago\b", "", cleaned)
        cleaned = re.sub(r"\b\d+\s+days ago\b", "", cleaned)
        cleaned = re.sub(r"\b\d+\s+weeks ago\b", "", cleaned)
        cleaned = re.sub(r"\bFlipkart\s+Customer\b", "", cleaned)
        cleaned = re.sub(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\s*,\s*[A-Za-z\s]+", "", cleaned)

        if "||" in cleaned:
            cleaned = cleaned.split("||", 1)[1].strip()
        elif "|" in cleaned:
            parts = [part.strip() for part in cleaned.split("|")]
            if len(parts) > 1 and len(parts[0].split()) >= 3:
                cleaned = parts[-1].strip()

        cleaned = re.sub(r"^(?:Overall|Camera|Battery|Display|Design|Performance|Build Quality|Value for Money|Build|Quality|Value|for|Money|Sound|Service|Delivery|Packaging|Size|Screen|Processor|Storage|RAM|Color|Model|Features|Pros|Cons)(?:\s+(?:Overall|Camera|Battery|Display|Design|Performance|Build Quality|Value for Money|Build|Quality|Value|for|Money|Sound|Service|Delivery|Packaging|Size|Screen|Processor|Storage|RAM|Color|Model|Features|Pros|Cons))+\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"^\s*[|•·]+\s*", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    @staticmethod
    def _looks_like_review(text):
        if not text:
            return False

        cleaned = re.sub(r"\s+", " ", text).strip()
        if len(cleaned) < 20 or len(cleaned) > 1500:
            return False

        lower = cleaned.lower()
        if lower.startswith(("review for:", "read more", "was this review helpful", "customer review", "all reviews", "write a review")):
            return False
        if lower.startswith(("price:", "specification", "description", "highlights", "seller", "brand", "model", "color", "ram", "storage", "battery")):
            return False
        if any(token in lower for token in ["login", "sign up", "wishlist", "become a seller", "cart", "download app", "advertise", "notifications", "search icon", "filters", "categories", "user reviews sorted by", "most helpful", "latest", "positive", "negative"]):
            return False
        if lower.count(" ") < 4:
            return False
        if re.fullmatch(r"[\W\d]+", cleaned):
            return False

        positive_markers = ["good", "great", "excellent", "bad", "worth", "quality", "battery", "camera", "performance", "value", "love", "disappointed", "smooth", "fast", "best", "durable", "okay", "average", "poor", "nice", "superb", "happy", "recommend", "thank you", "amazing", "awesome", "perfect", "fantastic", "loving"]
        if not any(marker in lower for marker in positive_markers):
            return False

        return True

    @staticmethod
    def _extract_product_id(product_url):
        match = re.findall(r"/p/(itm[0-9A-Za-z]+)", product_url)
        return match[0] if match else "N/A"

    @staticmethod
    def _extract_product_links_from_page_source(page_source, max_products=5):
        soup = BeautifulSoup(page_source, "html.parser")
        links = []
        seen = set()

        for a_tag in soup.find_all("a", href=True):
            href = a_tag.get("href", "")
            if "/p/" not in href:
                continue
            if "flipkart.com" not in href and "https://" not in href and not href.startswith("/"):
                continue
            if href.startswith("//"):
                href = "https:" + href
            if href.startswith("/"):
                href = "https://www.flipkart.com" + href
            if href in seen:
                continue
            seen.add(href)
            links.append(href)
            if len(links) >= max_products:
                break

        return links

    @staticmethod
    def _extract_title_from_page(page_source):
        soup = BeautifulSoup(page_source, "html.parser")
        for selector in ["h1", "span._35KyD6", "div._4rR01T", "span.B_NuCI", "h2", "meta[property='og:title']"]:
            if selector.startswith("meta"):
                element = soup.select_one(selector)
                if element and element.get("content"):
                    text = element.get("content", "").strip()
                    if text and len(text) > 4:
                        return text
            else:
                elements = soup.select(selector)
                if elements:
                    text = elements[0].get_text(" ", strip=True)
                    if text and len(text) > 4:
                        return text

        for pattern in [r'"title":"([^"]+)"', r'"name":"([^"]+)"', r'<title>(.*?)</title>']:
            m = re.search(pattern, page_source, re.I | re.S)
            if m:
                text = re.sub(r"\s+", " ", m.group(1)).strip()
                if text and len(text) > 4:
                    return text

        return "N/A"

    @staticmethod
    def _extract_price_from_page(page_source):
        soup = BeautifulSoup(page_source, "html.parser")
        for selector in ["div._30jeq3", "div._1vC4OE", "span._30jeq3", "div._25b18c", "div._1xZuAn", "div._1vC4OE"]:
            elements = soup.select(selector)
            if elements:
                text = elements[0].get_text(" ", strip=True)
                if text and re.search(r"[0-9]", text):
                    return text

        for pattern in [r'₹\s*([0-9,]+)', r'([0-9,]+)\s*(?:₹|Rs\.)']:
            m = re.search(pattern, page_source, re.I | re.S)
            if m:
                return m.group(0)

        return "N/A"

    @staticmethod
    def _extract_rating_from_page(page_source):
        soup = BeautifulSoup(page_source, "html.parser")

        for selector in [
            "meta[itemprop='ratingValue']",
            "meta[name='ratingValue']",
            "meta[property='ratingValue']",
            "meta[itemprop='aggregateRating']",
        ]:
            element = soup.select_one(selector)
            if not element:
                continue
            value = element.get("content") or element.get("value") or ""
            m = re.search(r"([0-9]+(?:\.[0-9]+)?)", value)
            if m:
                rating = m.group(1)
                if 0 < float(rating) <= 5:
                    return rating

        for pattern in [
            r'"ratingValue"\s*:\s*"([0-9]+(?:\.[0-9]+)?)"',
            r'"aggregateRating"\s*:\s*\{[^{}]*"ratingValue"\s*:\s*"([0-9]+(?:\.[0-9]+)?)"',
            r'itemprop="ratingValue"[^>]*content="([0-9]+(?:\.[0-9]+)?)"',
        ]:
            m = re.search(pattern, page_source, re.I | re.S)
            if m:
                rating = m.group(1)
                if 0 < float(rating) <= 5:
                    return rating

        for selector in ["div._3LWZlK", "span.W1Z989", "div.XQD2XT", "div._2d4LTz", "div._3LWZlK"]:
            elements = soup.select(selector)
            if elements:
                text = elements[0].get_text(" ", strip=True)
                if text:
                    m = re.search(r"\b([0-9]+(?:\.[0-9]+)?)\b", text)
                    if m:
                        rating = m.group(1)
                        if 0 < float(rating) <= 5:
                            return rating

        for pattern in [r'\b([0-9]\.[0-9])\b', r'\b([1-5])\s*out of\s*5\b']:
            m = re.search(pattern, page_source, re.I | re.S)
            if m:
                rating = m.group(1)
                if 0 < float(rating) <= 5:
                    return rating

        return "N/A"

    @staticmethod
    def _extract_review_count_from_page(page_source):
        soup = BeautifulSoup(page_source, "html.parser")
        for selector in ["span._2_R_DZ", "span._2_R3Z6", "span.W1Z989", "span._38sUEc", "div._2d4LTz"]:
            elements = soup.select(selector)
            if elements:
                text = elements[0].get_text(" ", strip=True)
                if text:
                    m = re.search(r"[\d,]+", text)
                    if m:
                        return m.group(0)

        for pattern in [r'([\d,]+)\s*Reviews', r'([\d,]+)\s*reviews', r'([\d,]+)\s*ratings']:
            m = re.search(pattern, page_source, re.I | re.S)
            if m:
                return m.group(1)

        return "N/A"

    @staticmethod
    def _extract_review_texts_from_html(page_source):
        soup = BeautifulSoup(page_source, "html.parser")
        reviews = []
        seen = set()

        for selector in ["div[data-testid='review-body']", "div[class*='review']", "div[class*='comment']", "div[class*='rating']", "p[class*='review']", "div[class*='RATINGS']", "div[class*='customer']", "div[class*='col-12-12']"]:
            for block in soup.select(selector):
                text = FlipkartScraper._clean_review_text(block.get_text(" ", strip=True))
                if FlipkartScraper._looks_like_review(text) and text not in seen:
                    reviews.append(text)
                    seen.add(text)

        if reviews:
            return reviews

        for block in soup.find_all(["div", "span", "p"], recursive=True):
            text = FlipkartScraper._clean_review_text(block.get_text(" ", strip=True))
            if "Verified Purchase" in text or "Helpful for" in text or "•" in text:
                if len(text) > 40 and len(text) < 500:
                    candidate = re.sub(r"\s+", " ", text).strip()
                    candidate = re.sub(r"\s*(Verified Purchase|Helpful for|·|•)\s*", " ", candidate)
                    if FlipkartScraper._looks_like_review(candidate) and candidate not in seen:
                        reviews.append(candidate)
                        seen.add(candidate)

        if reviews:
            return reviews

        for tag in soup.find_all(["div", "span", "p", "li"], recursive=True):
            text = FlipkartScraper._clean_review_text(tag.get_text(" ", strip=True))
            if FlipkartScraper._looks_like_review(text) and text not in seen:
                reviews.append(text)
                seen.add(text)
            if len(reviews) >= 5:
                break

        if reviews:
            return reviews

        for text in re.findall(r'([A-Z][^.!?]{20,250}[.!?])', page_source):
            candidate = FlipkartScraper._clean_review_text(text)
            if FlipkartScraper._looks_like_review(candidate) and candidate not in seen:
                reviews.append(candidate)
                seen.add(candidate)

        return reviews

    @staticmethod
    def _wait_for_page_ready(driver, timeout=20):
        WebDriverWait(driver, timeout).until(lambda d: d.execute_script("return document.readyState") == "complete")
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)

    def get_top_reviews(self,driver,product_url,count):
        log.info("Fetching top reviews", product_url=product_url, review_count=count)
        if not product_url.startswith("http"):
            log.warning("Invalid product URL for review scrape", product_url=product_url)
            return "No reviews found"

        try:
            review_url = None
            if "/p/" in product_url:
                review_url = product_url.replace("/p/", "/product-reviews/")
                log.info("Constructed review URL", review_url=review_url)

            if not review_url:
                driver.get(product_url)
                log.info("Opened product page", url=driver.current_url)
                self._wait_for_page_ready(driver)

                body = driver.find_element(By.TAG_NAME, "body")
                for _ in range(4):
                    body.send_keys(Keys.PAGE_DOWN)
                    time.sleep(0.6)

                wait = WebDriverWait(driver, 15)
                log.info("Loaded product page title", title=driver.title)

                try:
                    close_btn = wait.until(
                        EC.element_to_be_clickable(
                            (By.XPATH, "//button[contains(text(),'✕')]")
                        )
                    )
                    close_btn.click()
                    time.sleep(1)
                except Exception:
                    pass

                review_btn = None
                try:
                    review_btn = wait.until(
                        EC.presence_of_element_located(
                            (
                                By.XPATH,
                                "//a[contains(@href,'product-reviews') or contains(@href,'ratings-reviews-details-page')]"
                            )
                        )
                    )
                except Exception:
                    review_btn = None

                log.info("Searching for review button on product page")
                if review_btn:
                    log.info("Review button found", button_text=review_btn.text)
                    review_url = review_btn.get_attribute("href")
                    if review_url.startswith("/"):
                        review_url = "https://www.flipkart.com" + review_url
                else:
                    log.warning("Review button not found on product page")

            if not review_url:
                log.warning("No review URL available after fallback")
                return "No reviews found"

            log.info("Navigating to review page", review_url=review_url)
            driver.get(review_url)
            self._wait_for_page_ready(driver)

            with open("review_page.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)

            reviews = self._extract_review_texts_from_html(driver.page_source)[:count]
            if reviews:
                log.info("Collected reviews", review_count=len(reviews), product_url=product_url)
                return " || ".join(reviews)

            log.warning("No review text matched the available selectors", product_url=product_url)
            return "No reviews found"

        except Exception as e:
            log.error("Review scraping error", product_url=product_url, error=str(e))
            return "No reviews found"
    def save_to_csv(self,data,filename="product_reviews.csv"):
        """Save the scraped product reviews to a CSV file."""
        if os.path.isabs(filename):
            path = filename
        elif os.path.dirname(filename):  # filename includes subfolder like 'data/product_reviews.csv'
            path = filename
            os.makedirs(os.path.dirname(path), exist_ok=True)
        else:
            # plain filename like 'output.csv'
            path = os.path.join(self.output_dir, filename)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["product_id", "product_title", "rating", "total_reviews", "price", "top_reviews"])
            writer.writerows(data)

