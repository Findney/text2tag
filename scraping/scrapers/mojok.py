import random
import time
import requests
from bs4 import BeautifulSoup
import logging
from config import MOJOK_URL, USER_AGENTS, REFERERS
from .helper import save_links, load_links, save_csv

# Mengatur logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

MAX_LINKS_PER_CATEGORY = 1000  # Maksimal link per kategori

# Daftar kategori untuk setiap jenis URL
CATEGORIES_1 = ["esai", "otomojok", "konter", "maljum"]
CATEGORIES_2 = ["aktual", "kampus", "sosok", "kuliner", "mendalam", "ragam", "catatan"]
CATEGORIES_3 = [
    "nusantara",
    "kuliner",
    "kampus",
    "ekonomi",
    "teknologi",
    "olahraga",
    "otomotif",
    "hiburan",
]


def get_article_links(
    url_template, categories, max_links_per_category, article_classes
):
    """Mengambil link artikel dari halaman indeks kategori hingga halaman terakhir atau max_links, tanpa duplikat."""
    article_links = set()

    for category in categories:
        logging.info(f"Scraping category: {category}")
        page = 1
        category_links = set()
        consecutive_errors = 0
        max_consecutive_errors = 3  # Toleransi error beruntun sebelum berhenti

        while len(category_links) < max_links_per_category:
            url = url_template.format(category=category, page=page)
            logging.info(f"Scraping {url}")

            user_agent = random.choice(USER_AGENTS)
            referer = random.choice(REFERERS)
            headers = {
                "User-Agent": user_agent,
                "Referer": referer,
            }

            try:
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")
                posts_container = soup.find(
                    "div", class_="jeg_posts jeg_load_more_flag"
                )
                if not posts_container:
                    logging.info(
                        f"No posts container found at {url}. Stopping category."
                    )
                    break

                article_items = []
                for cls in article_classes:
                    article_items.extend(
                        posts_container.find_all("article", class_=cls)
                    )

                if not article_items:
                    logging.info(f"No articles found at {url}. Stopping category.")
                    break

                initial_count = len(category_links)

                for item in article_items:
                    link = item.find("a", href=True)
                    if link:
                        href = link["href"].strip().rstrip("/")
                        if not href.startswith("http"):
                            href = MOJOK_URL + href
                        if href not in category_links and href not in article_links:
                            category_links.add(href)
                            article_links.add(href)

                added_count = len(category_links) - initial_count
                logging.info(
                    f"Page {page}: Added {added_count} unique links, total in category: {len(category_links)}"
                )

                # Reset error counter on successful page
                consecutive_errors = 0

                # Jika sudah mencapai max_links_per_category, hentikan kategori ini
                if len(category_links) >= max_links_per_category:
                    logging.info(
                        f"Reached max links ({max_links_per_category}) for {category}."
                    )
                    break

                page += 1
                time.sleep(random.uniform(1, 3))

            except requests.exceptions.HTTPError as http_err:
                logging.error(f"HTTP Error accessing {url}: {http_err}")
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    logging.error(
                        f"Too many consecutive errors ({consecutive_errors}) for {category}. Stopping category."
                    )
                    break
                time.sleep(random.uniform(2, 5))  # Tunggu lebih lama setelah error
            except requests.exceptions.ConnectionError as conn_err:
                logging.error(f"Connection Error accessing {url}: {conn_err}")
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    logging.error(
                        f"Too many consecutive errors ({consecutive_errors}) for {category}. Stopping category."
                    )
                    break
                time.sleep(random.uniform(2, 5))
            except requests.exceptions.Timeout as timeout_err:
                logging.error(f"Timeout Error accessing {url}: {timeout_err}")
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    logging.error(
                        f"Too many consecutive errors ({consecutive_errors}) for {category}. Stopping category."
                    )
                    break
                time.sleep(random.uniform(2, 5))
            except requests.exceptions.RequestException as e:
                logging.error(f"Error accessing {url}: {e}")
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    logging.error(
                        f"Too many consecutive errors ({consecutive_errors}) for {category}. Stopping category."
                    )
                    break
                time.sleep(random.uniform(2, 5))

        logging.info(
            f"Category {category} completed, {len(category_links)} links found"
        )

    return sorted(article_links)


def get_article_content(link):
    """Mengambil konten artikel dari link, termasuk judul, konten, tag, dan menangani multi-halaman."""

    def scrape_page(url):
        try:
            user_agent = random.choice(USER_AGENTS)
            referer = random.choice(REFERERS)
            headers = {
                "User-Agent": user_agent,
                "Referer": referer,
            }

            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Mengambil judul
            title_elem = soup.find("h1", class_="jeg_post_title")
            title = title_elem.text.strip() if title_elem else None

            # Mengambil konten
            content_div = soup.find("div", class_="content-inner")
            sentences = []
            if content_div:
                paragraphs = content_div.find_all("p", recursive=True)
                for p in paragraphs:
                    text = p.text.strip()
                    if not any(
                        exclude in text
                        for exclude in [
                            "Penulis:",
                            "Editor:",
                            "BACA JUGA",
                            "Baca Halaman Selanjutnya",
                        ]
                    ):
                        sentences.append(text)

            content = " ".join(sentences)
            content = " ".join(content.split())  # Hapus whitespace berlebih

            # Mengambil tag
            tags_div = soup.find("div", class_="jeg_post_tags")
            tags = []
            if tags_div:
                tag_links = tags_div.find_all("a", rel="tag")
                tags = [tag.text.strip() for tag in tag_links]

            # Cek halaman selanjutnya
            nav_link = (
                content_div.find("div", class_="nav_link") if content_div else None
            )
            next_page = None
            if nav_link:
                next_link = nav_link.find("a", class_="page_nav next")
                if next_link and next_link["href"]:
                    next_page = next_link["href"].strip().rstrip("/")
                    if not next_page.startswith("http"):
                        next_page = MOJOK_URL + next_page

            return title, content, tags, next_page

        except Exception as e:
            logging.error(f"Error scraping page {url}: {e}")
            return None, None, None, None

    # Scraping halaman pertama
    title, content, tags, next_page = scrape_page(link)
    if not title or not content:
        return None, None, None

    # Scraping halaman berikutnya jika ada
    all_content = [content]
    visited_pages = {link}

    while next_page and next_page not in visited_pages:
        _, page_content, _, next_page = scrape_page(next_page)
        if page_content:
            all_content.append(page_content)
        visited_pages.add(next_page)
        time.sleep(random.uniform(1, 3))

    # Gabungkan semua konten
    final_content = " ".join(all_content)
    final_content = " ".join(final_content.split())

    return title, final_content, tags


def run(option):
    """Menjalankan proses crawling atau scraping berdasarkan opsi."""
    logging.info("Starting Mojok scraper")

    if option == 1:
        # URL templates dan kelas artikel
        url_templates = [
            (
                "https://mojok.co/{category}/page/{page}/",
                CATEGORIES_1,
                ["jeg_post jeg_pl_lg_2 format-standard"],
            ),
            (
                "https://mojok.co/liputan/{category}/page/{page}/",
                CATEGORIES_2,
                ["jeg_post jeg_pl_lg_2 format-standard"],
            ),
            (
                "https://mojok.co/terminal/topik/{category}/page/{page}/",
                CATEGORIES_3,
                [
                    "jeg_post jeg_pl_lg_2 format-standard",
                    "jeg_post jeg_pl_md_card format-standard",
                ],
            ),
        ]

        all_links = set()
        for url_template, categories, article_classes in url_templates:
            links = get_article_links(
                url_template, categories, MAX_LINKS_PER_CATEGORY, article_classes
            )
            all_links.update(links)

        save_links(all_links, source="mojok")
        logging.info(f"Crawling completed, total {len(all_links)} links saved")

    elif option == 2:
        all_links = load_links("mojok")
        article_data = []

        for idx, link in enumerate(all_links, 1):
            logging.info(f"[{idx}/{len(all_links)}] Scraping article: {link}")
            title, content, tags = get_article_content(link)

            if title and content:
                tag_str = ", ".join(tags) if tags else "-"
                article_data.append((title, content, tag_str))
            else:
                logging.warning(f"Failed to scrape article: {link}")

            time.sleep(random.uniform(1, 3))

        save_csv(article_data, source="mojok")
        logging.info(
            f"Scraping completed, total {len(article_data)} articles saved to CSV"
        )
