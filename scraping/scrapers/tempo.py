import random
import time
import requests
import logging
import aiohttp
import asyncio
from aiohttp import ClientTimeout
from aiohttp_retry import RetryClient, ExponentialRetry
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


async def get_article_content_tempo(link, session=None):
    """Ambil judul, isi, dan tag artikel dari Tempo secara asynchronous dengan retry."""
    try:
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Referer": random.choice(REFERERS),
        }

        # Setup retry strategy
        retry_options = ExponentialRetry(
            attempts=5,  # Tambah jumlah percobaan
            start_timeout=2,  # Tambah waktu tunggu awal
            max_timeout=30,  # Tambah waktu tunggu maksimal
            factor=2,  # Faktor pengali untuk exponential backoff
            statuses={
                429,  # Too Many Requests
                403,  # Forbidden
                500,  # Internal Server Error
                502,  # Bad Gateway
                503,  # Service Unavailable
                504,  # Gateway Timeout
            },
        )

        # Use provided session or create new one
        if session is None:
            connector = aiohttp.TCPConnector(
                limit=5,  # Limit concurrent connections
                force_close=True,  # Force close connection after each request
                enable_cleanup_closed=True,  # Clean up closed connections
            )
            timeout = ClientTimeout(
                total=60,  # Total timeout
                connect=10,  # Connection timeout
                sock_read=30,  # Socket read timeout
            )
            async with aiohttp.ClientSession(
                connector=connector, timeout=timeout
            ) as session:
                return await _fetch_content_tempo(session, link, headers, retry_options)
        else:
            return await _fetch_content_tempo(session, link, headers, retry_options)

    except Exception as e:
        logging.error(f"Error scraping {link}: {e}")
        return None, None, None


async def _fetch_content_tempo(session, link, headers, retry_options):
    """Helper function untuk mengambil konten Tempo dengan retry."""
    try:
        async with RetryClient(
            client_session=session, retry_options=retry_options
        ) as retry_client:
            async with retry_client.get(link, headers=headers) as response:
                response.raise_for_status()
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")

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
    except aiohttp.ClientError as e:
        logging.error(f"Network error saat mengambil {link}: {e}")
        return None, None, None
    except Exception as e:
        logging.error(f"Unexpected error saat mengambil {link}: {e}")
        return None, None, None


async def scrape_articles_tempo(links):
    """Scrape multiple Tempo articles concurrently with rate limiting."""
    article_data = []
    semaphore = asyncio.Semaphore(5)  # Naikkan limit ke 5 concurrent requests

    async def scrape_with_semaphore(link):
        async with semaphore:
            try:
                logging.info(f"Scraping {link}")
                # Tambah delay random antara requests
                await asyncio.sleep(random.uniform(1, 3))
                title, content, tags = await get_article_content_tempo(link)
                if title and content:
                    tag_str = ", ".join(tags) if tags else "-"
                    return (title, content, tag_str)
                else:
                    logging.warning(f"Gagal scrape: {link}")
                    return None
            except Exception as e:
                logging.error(f"Error dalam scrape_with_semaphore untuk {link}: {e}")
                return None

    # Create tasks for all links
    tasks = [scrape_with_semaphore(link) for link in links]

    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out None results and exceptions
    article_data.extend(
        [r for r in results if r is not None and not isinstance(r, Exception)]
    )

    return article_data


def run(option):
    """Menjalankan crawler/scraper berdasarkan pilihan."""
    logging.info("Memulai scraping Tempo.co")

    if option == 1:  # CRAWL
        links = get_article_links_tempo()
        save_links(links, source="tempo")
        logging.info(f"Selesai crawling. Total link: {len(links)}")

    elif option == 2:  # SCRAPE
        links = load_links("tempo")

        # Run the async scraping
        articles = asyncio.run(scrape_articles_tempo(links))

        save_csv(articles, source="tempo")
        logging.info(f"Selesai scraping. Artikel berhasil: {len(articles)}")
