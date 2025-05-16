import time
import random
import requests
from bs4 import BeautifulSoup
import logging
from .helper import save_links, load_links, save_csv  # pastikan fungsi ini tersedia
from config import MEDIUM_URL, USER_AGENTS, REFERERS
import re
import unicodedata
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager


MAX_LINKS = 10
categories = [
    "life",
    "self-improvement",
    # "work",
    # "technology",
    # "software-development",
    # "media",
    # "society",
    # "culture",
    # "world",
]

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def get_article_links_medium(category):
    """
    Extract article links from Medium's tag archive page using Selenium.

    Args:
        category (str): The Medium tag/category to scrape (e.g., 'life', 'self-improvement').

    Returns:
        list: A sorted list of unique, valid article URLs.
    """
    MAX_LINKS = 10
    url = f"{MEDIUM_URL}/tag/{category}/archive"

    # Configure Selenium with headless Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")

    # Initialize WebDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    links = set()
    scroll_attempts = 0
    max_scroll_attempts = 30  # Reduced max attempts for efficiency with Selenium

    try:
        # Navigate to the archive page
        driver.get(url)
        logging.info(f"Navigated to {url}")

        while len(links) < MAX_LINKS and scroll_attempts < max_scroll_attempts:
            # Get the current page source and parse with BeautifulSoup
            soup = BeautifulSoup(driver.page_source, "html.parser")
            article_blocks = soup.find_all(
                "article", attrs={"data-testid": "post-preview"}
            )

            if not article_blocks:
                logging.info(f"No articles found on page {url}")
                break

            valid_link_found = False

            for block in article_blocks:
                # Skip member-only articles
                if block.find("button", attrs={"aria-label": "Member-only story"}):
                    continue

                anchor = block.find("div", attrs={"data-href": True})
                h2 = block.find("h2")

                if anchor and h2:
                    raw_link = anchor.get("data-href")
                    # Normalize link to remove tracking parameters
                    if "?" in raw_link:
                        raw_link = raw_link.split("?")[0]
                    if raw_link.startswith(MEDIUM_URL):
                        raw_path = raw_link.replace(MEDIUM_URL, "")
                    else:
                        raw_path = raw_link

                    if raw_link not in links:
                        slug = raw_link.rstrip("/").split("/")[-1]

                        # Skip if slug is a hash ID (hex digits and dashes)
                        if re.fullmatch(r"[\da-f\-]{10,}", slug, re.IGNORECASE):
                            logging.warning(
                                f"Skipped link due to hash slug: {raw_link}"
                            )
                            continue

                        # Skip if slug contains non-Latin characters
                        if not all(
                            "LATIN" in unicodedata.name(char, "")
                            for char in slug
                            if char.isalpha()
                        ):
                            logging.warning(
                                f"Skipped link due to non-Latin characters: {raw_link}"
                            )
                            continue

                        # Skip if slug lacks Latin words (minimum 3 letters)
                        if not re.search(r"[a-zA-Z]{3,}", slug):
                            logging.warning(
                                f"Skipped link due to no Latin words: {raw_link}"
                            )
                            continue

                        full_link = f"{MEDIUM_URL}{raw_path}"
                        links.add(full_link)
                        logging.info(f"Added link: {full_link}")
                        valid_link_found = True

                        if len(links) >= MAX_LINKS:
                            break

            if not valid_link_found:
                logging.warning(
                    "No valid links found in this iteration. Stopping to prevent stagnation."
                )
                break

            # Scroll to the bottom of the page
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            scroll_attempts += 1
            logging.info(f"Scroll attempt {scroll_attempts}, total links: {len(links)}")

            # Wait for new content to load
            time.sleep(random.uniform(2.0, 4.0))  # Increased delay for dynamic loading

            # Check if new articles are loaded
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.TAG_NAME, "article"))
                )
            except TimeoutException:
                logging.warning("No new articles loaded after scrolling.")
                break

    except Exception as e:
        logging.error(f"Error during Selenium scraping: {e}")

    finally:
        driver.quit()
        logging.info("Selenium WebDriver closed.")

    return sorted(links)


def get_article_content_medium(link):
    try:
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Referer": random.choice(REFERERS),
        }

        response = requests.get(link, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")

        # Judul
        title_tag = soup.find("h1")
        if title_tag:
            title = title_tag.text.strip()
        else:
            slug = link.rstrip("/").split("/")[-1]
            # Hilangkan post ID hash 12 karakter di akhir (jika ada)
            # Misalnya: "judul-artikel-86a385890b3e"
            match = re.match(r"(.+)-[a-f0-9]{12}$", slug)
            cleaned_slug = match.group(1) if match else slug
            title = cleaned_slug.replace("-", " ")

        # Konten
        content_paragraphs = soup.find_all("p", class_="pw-post-body-paragraph")
        content = " ".join(p.text.strip() for p in content_paragraphs if p.text.strip())

        # Tag
        tags = []
        for a in soup.find_all("a", href=True):
            if a["href"].startswith("/tag/"):
                inner_div = a.find("div")
                if inner_div and inner_div.text.strip():
                    tags.append(inner_div.text.strip())
                elif a.text.strip():
                    tags.append(a.text.strip())

        return title, content, tags

    except Exception as e:
        logging.error(f"Gagal mengambil konten dari {link}: {e}")
        return None, None


def run(option):
    if option == 1:
        all_links = []
        for category in categories:
            logging.info(f"Mulai crawl kategori: {category}")
            links = get_article_links_medium(category)
            all_links.extend(links)
            logging.info(f"{len(links)} link ditemukan di kategori {category}")
        save_links(all_links, source="medium")
        logging.info(f"Total {len(all_links)} link disimpan dari semua kategori")

    elif option == 2:
        all_links = load_links("medium")
        article_data = []

        for idx, link in enumerate(all_links, 1):
            logging.info(f"[{idx}/{len(all_links)}] Scraping: {link}")
            title, content, tags = get_article_content_medium(link)
            if content:
                tag_str = ", ".join(tags) if tags else "-"
                article_data.append((title, content, tag_str))
            else:
                logging.warning(f"Gagal scraping: {link}")

        save_csv(article_data, source="medium")
        logging.info(f"{len(article_data)} artikel berhasil disimpan ke CSV")
