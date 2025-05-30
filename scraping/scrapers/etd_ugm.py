import random
import re
import time
import requests
from bs4 import BeautifulSoup
import logging
import uuid
import warnings
import aiohttp
import asyncio
from aiohttp import ClientTimeout
from aiohttp_retry import RetryClient, ExponentialRetry
from .helper import load_links, save_links, save_csv
from config import USER_AGENTS, REFERERS, ETD_UGM_URL

# Nonaktifkan peringatan SSL untuk testing
warnings.filterwarnings(
    "ignore", category=requests.packages.urllib3.exceptions.InsecureRequestWarning
)

# Mengatur logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Base URL dan rentang ID
BASE_URL = ETD_UGM_URL + "/penelitian/detail/"
ID_RANGE = range(190000, 250001)


async def get_article_content(article_id, session=None):
    """Mengambil konten artikel dari ID tertentu secara asynchronous dengan retry."""
    url = f"{BASE_URL}{article_id}"
    try:
        user_agent = random.choice(USER_AGENTS)
        referer = random.choice(REFERERS)
        headers = {
            "User-Agent": user_agent,
            "Referer": referer,
        }

        # Setup retry strategy
        retry_options = ExponentialRetry(
            attempts=3,  # Jumlah percobaan maksimal
            start_timeout=1,  # Waktu tunggu awal
            max_timeout=10,  # Waktu tunggu maksimal
            factor=2,  # Faktor pengali untuk exponential backoff
            statuses={500, 502, 503, 504},  # Status code yang akan di-retry
        )

        # Use provided session or create new one
        if session is None:
            connector = aiohttp.TCPConnector(
                limit=5, ssl=False
            )  # Disable SSL verification
            timeout = ClientTimeout(total=30)
            async with aiohttp.ClientSession(
                connector=connector, timeout=timeout
            ) as session:
                return await _fetch_content(session, url, headers, retry_options)
        else:
            return await _fetch_content(session, url, headers, retry_options)

    except Exception as e:
        logging.error(f"Error saat mengakses {url}: {e}")
        return None, None, None


async def _fetch_content(session, url, headers, retry_options):
    """Helper function untuk mengambil konten dengan retry."""
    async with RetryClient(
        client_session=session, retry_options=retry_options
    ) as retry_client:
        async with retry_client.get(url, headers=headers) as response:
            response.raise_for_status()
            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")

            # Mengambil judul artikel
            title_elem = soup.find("p", class_="title")
            title = title_elem.text.strip() if title_elem else ""
            if not title:
                logging.info(
                    f"Tidak ada judul ditemukan di {url}. Halaman mungkin kosong."
                )
                return None, None, None

            # Mengambil abstrak dan kata kunci dari panel-body pertama
            panel_bodies = soup.find_all("div", class_="panel-body")
            abstract_text = ""
            keywords = []

            if panel_bodies:
                first_panel = panel_bodies[0]  # Hanya ambil panel-body pertama
                abstract_elem = first_panel.find("p", class_="abstrak")
                if abstract_elem:
                    abstract_text = abstract_elem.get_text(strip=True)

                keyword_elem = first_panel.find("p", class_="keyword")
                if keyword_elem:
                    keyword_raw = keyword_elem.get_text(strip=True)
                    # Pisahkan kata kunci berdasarkan koma atau titik koma
                    keywords = [
                        k.strip() for k in re.split(r"[;,]", keyword_raw) if k.strip()
                    ]

            return title, abstract_text, keywords


async def scrape_articles_etd(links):
    """Scrape multiple ETD articles concurrently with rate limiting."""
    article_data = []
    semaphore = asyncio.Semaphore(5)  # Limit concurrent scraping to 5 articles

    async def scrape_with_semaphore(link):
        async with semaphore:
            article_id = link.split("/")[-1]
            logging.info(f"Mengambil artikel: {link}")
            title, abstract, keywords = await get_article_content(article_id)
            if title and abstract:
                keyword_str = ", ".join(keywords) if keywords else "-"
                logging.info(f"Artikel berhasil diambil: {title}")
                return (title, abstract, keyword_str)
            else:
                logging.info(f"Artikel kosong atau gagal diambil: {link}")
                return None

    # Create tasks for all links
    tasks = [scrape_with_semaphore(link) for link in links]

    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks)

    # Filter out None results and add to article_data
    article_data.extend([r for r in results if r is not None])

    return article_data


def run(option):
    """Menjalankan proses crawling atau scraping berdasarkan opsi."""
    logging.info("Memulai proses untuk ETD UGM")

    if option == 1:
        all_links = []
        for article_id in ID_RANGE:
            url = f"{BASE_URL}{article_id}"
            all_links.append(url)
            logging.info(f"Menambahkan link: {url}")

        save_links(all_links, source="etd_ugm")
        logging.info(f"Scraping selesai, total {len(all_links)} link dikumpulkan")

    elif option == 2:
        all_links = load_links("etd_ugm")

        # Run the async scraping
        article_data = asyncio.run(scrape_articles_etd(all_links))

        save_csv(article_data, source="etd_ugm")
        logging.info(
            f"Scraping selesai, total {len(article_data)} artikel disimpan ke CSV"
        )
