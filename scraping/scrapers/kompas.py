import random
import time
import requests
from bs4 import BeautifulSoup
import logging
from config import KOMPAS_URL, USER_AGENTS, REFERERS
from .helper import save_links, load_links, save_csv

MAX_LINKS = 5  # Maksimal link yang akan diambil perkategori

# Mengatur logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Daftar kategori
categories = [
    "nasional",
    "regional",
    # "megapolitan",
    # "tren",
    # "food",
    # "edukasi",
    # "money",
    # "umkm",
    # "tekno",
    # "lifestyle",
    # "homey",
    # "properti",
    # "bola",
    # "travel",
    # "otomotif",
    # "sains",
    # "hype",
    # "health",
    # "skola",
    # "stori",
    # "konsultasihukum",
    # "wiken",
    # "ikn",
    # "nusaraya",
]


def get_article_links(category):
    """Mengambil hingga max_links artikel dari halaman indeks kategori, dengan cek duplikat."""
    article_links = set()
    page = 1
    base_url = f"https://indeks.kompas.com/?site={category}&page="

    while len(article_links) < MAX_LINKS:
        url = f"{base_url}{page}"
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
            article_items = soup.find_all("a", class_="article-link")

            if not article_items:
                logging.info(f"Tidak ada artikel ditemukan di {url}. Berhenti.")
                break

            initial_count = len(article_links)

            for item in article_items:
                href = item.get("href")
                if href:
                    href = href.strip()
                    if not href.startswith("http"):
                        href = KOMPAS_URL + href

                    href = href.rstrip("/")  # normalisasi akhir URL

                    if href not in article_links:
                        article_links.add(href)

            added_count = len(article_links) - initial_count
            logging.info(
                f"Halaman {page}: Ditambahkan {added_count} link unik, total: {len(article_links)}"
            )
            page += 1
            time.sleep(random.uniform(1, 3))

            if len(article_items) < 10:
                logging.info(f"Halaman hampir kosong di {url}. Berhenti.")
                break

        except requests.exceptions.HTTPError as http_err:
            logging.error(f"HTTP Error saat mengakses {url}: {http_err}")
            break
        except requests.exceptions.ConnectionError as conn_err:
            logging.error(f"Connection Error saat mengakses {url}: {conn_err}")
            break
        except requests.exceptions.Timeout as timeout_err:
            logging.error(f"Timeout Error saat mengakses {url}: {timeout_err}")
            break
        except requests.exceptions.RequestException as e:
            logging.error(f"Error saat mengakses {url}: {e}")
            break

    return sorted(article_links)


def get_article_content(link):
    """Mengambil konten artikel dari link, termasuk judul, konten, dan tag."""
    try:
        # Memilih User-Agent dan Referer secara acak
        user_agent = random.choice(USER_AGENTS)
        referer = random.choice(REFERERS)
        headers = {
            "User-Agent": user_agent,
            "Referer": referer,
        }

        response = requests.get(link, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Mengambil judul artikel
        title = soup.find("h1", class_="read__title").text.strip()

        # Mengambil konten artikel
        content_div = soup.find("div", class_="read__content")
        clearfix_blocks = content_div.find_all("div", class_="clearfix", recursive=True)
        sentences = []
        for block in clearfix_blocks:
            paragraphs = block.find_all("p")
            for p in paragraphs:
                if "Baca juga:" not in p.text:
                    sentences.append(p.text.strip())
        # Gabungkan semua kalimat menjadi satu baris
        content = " ".join(sentences)
        content = " ".join(content.split())  # Hapus whitespace berlebih

        # Mengambil tag artikel
        tags_wrap = soup.find("ul", class_="tag__article__wrap")
        tags = []
        if tags_wrap:  # Pastikan elemennya ada
            tag_items = tags_wrap.find_all("li", class_="tag__article__item")
            for item in tag_items:
                tag_link = item.find("a", class_="tag__article__link")
                if tag_link:
                    tags.append(tag_link.text.strip())

        return title, content, tags

    except Exception as e:
        logging.error(f"Error saat mengambil konten artikel dari {link}: {e}")
        return None, None, None


def run(option):
    """Mengumpulkan semua link dari semua kategori dan menyimpannya dalam satu file."""
    logging.info("Memulai scraping Kompas")

    if option == 1:
        all_links = []

        for category in categories:
            logging.info(f"Kategori: {category}")
            links = get_article_links(category)
            for link in links:
                all_links.append(link)
            logging.info(f"Kategori {category} selesai, {len(links)} link ditemukan")

        save_links(all_links, source="kompas")
        logging.info(f"Scraping selesai, total {len(all_links)} link disimpan")

    elif option == 2:
        all_links = load_links("kompas")
        article_data = []

        for idx, link in enumerate(all_links, 1):
            logging.info(f"[{idx}/{len(all_links)}] Mengambil artikel: {link}")
            title, content, tags = get_article_content(link)

            if title and content and tags:
                tag_str = ", ".join(tags) if tags else "-"
                article_data.append((title, content, tag_str))
            else:
                logging.warning(f"Artikel gagal diambil: {link}")

        save_csv(article_data, source="kompas")
        logging.info(
            f"Scraping selesai, total {len(article_data)} artikel disimpan ke CSV"
        )
