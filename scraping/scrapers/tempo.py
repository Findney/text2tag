import random
import time
import requests
import logging
from bs4 import BeautifulSoup
from config import USER_AGENTS, REFERERS, TEMPO_URL
from .helper import save_links, load_links, save_csv

MAX_LINKS = 20000


def get_article_links_tempo():
    """Crawl link artikel dari Tempo.co indeks"""
    article_links = set()
    page = 1
    base_url = "https://www.tempo.co/indeks?page={}&category=newsAccess&access=FREE"

    while len(article_links) < MAX_LINKS:
        url = base_url.format(page)
        logging.info(f"[CRAWL] {url}")
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Referer": random.choice(REFERERS),
        }

        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            articles = soup.select("figure.flex a[href]")
            if not articles:
                logging.info("Tidak ditemukan artikel lagi. Berhenti.")
                break

            initial_count = len(article_links)

            for a in articles:
                href = a.get("href")
                if href:
                    if not href.startswith("http"):
                        href = TEMPO_URL.rstrip("/") + href
                    href = href.strip().rstrip("/")
                    article_links.add(href)

            added_count = len(article_links) - initial_count
            logging.info(
                f"Halaman {page}: +{added_count} link, total: {len(article_links)}"
            )

            if added_count == 0:
                break

            page += 1
            time.sleep(random.uniform(1, 2))

        except Exception as e:
            logging.error(f"Error saat mengakses {url}: {e}")
            break

    return sorted(article_links)


def get_article_content_tempo(link):
    """Ambil judul, isi, dan tag artikel dari Tempo."""
    try:
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Referer": random.choice(REFERERS),
        }
        response = requests.get(link, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Judul
        title_tag = soup.find("h1", class_="text-[26px]")
        title = title_tag.get_text(strip=True) if title_tag else None

        # Konten
        content_divs = soup.find_all("div", id="content-wrapper")
        content_list = []
        for content_div in content_divs:
            paragraphs = content_div.find_all("p", recursive=True)
            for p in paragraphs:
                text = p.get_text(strip=True)
                if "Pilihan Editor:" not in text:
                    content_list.append(text)
        # Gabungkan semua paragraf menjadi satu baris teks
        content = " ".join(content_list).strip()
        content = " ".join(content.split())  # Hapus spasi dan newline berlebih

        # Tags
        tags_div = soup.find("div", id="article-tags")
        tags = []
        if tags_div:
            tags = [
                span.get_text(strip=True)
                for span in tags_div.select("span.text-primary-main")
            ]

        return title, content, tags
    except Exception as e:
        logging.error(f"Error scraping {link}: {e}")
        return None, None, None


def run(option):
    """Menjalankan crawler/scraper berdasarkan pilihan."""
    logging.info("Memulai scraping Tempo.co")

    if option == 1:  # CRAWL
        links = get_article_links_tempo()
        save_links(links, source="tempo")
        logging.info(f"Selesai crawling. Total link: {len(links)}")

    elif option == 2:  # SCRAPE
        links = load_links("tempo")
        articles = []
        for i, link in enumerate(links, 1):
            logging.info(f"[{i}/{len(links)}] Scraping {link}")
            title, content, tags = get_article_content_tempo(link)
            if title and content:
                tag_str = ", ".join(tags) if tags else "-"
                articles.append((title, content, tag_str))
            else:
                logging.warning(f"Gagal scrape: {link}")
        save_csv(articles, source="tempo")
        logging.info(f"Selesai scraping. Artikel berhasil: {len(articles)}")
