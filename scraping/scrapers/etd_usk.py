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
from config import USER_AGENTS, REFERERS, ETD_USK_URL

# Nonaktifkan peringatan SSL untuk testing
warnings.filterwarnings(
    "ignore", category=requests.packages.urllib3.exceptions.InsecureRequestWarning
)

# Mengatur logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Daftar tahun
years = range(2021, 2026)


from tenacity import retry, stop_after_attempt, wait_exponential
import requests
from requests import Session


def get_article_links(year):
    """Mengambil semua link artikel dari halaman indeks untuk tahun tertentu."""
    article_links = set()
    page = 1
    base_url = f"{ETD_USK_URL}?publish_year={year}&prodi=&searchtype=advance&search=search&page="
    session = Session()  # Gunakan session untuk konsistensi

    while True:
        url = f"{base_url}{page}"
        logging.info(f"Scraping {url}")

        user_agent = random.choice(USER_AGENTS)
        referer = random.choice(REFERERS)
        headers = {
            "User-Agent": user_agent,
            "Referer": referer,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
        }

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=4, max=10),
        )
        def fetch_page(url, headers):
            logging.warning("Verifikasi SSL dinonaktifkan untuk testing.")
            response = session.get(url, headers=headers, timeout=15, verify=False)
            response.raise_for_status()
            return response

        try:
            response = fetch_page(url, headers)
            soup = BeautifulSoup(response.text, "html.parser")
            article_items = soup.find_all("a", class_="btn_1 small", href=True)

            if not article_items:
                logging.info(f"Tidak ada artikel ditemukan di {url}. Berhenti.")
                break

            initial_count = len(article_links)
            for item in article_items:
                href = item.get("href")
                if href and "p=show_detail" in href:
                    href = href.strip()
                    if not href.startswith("http"):
                        href = ETD_USK_URL + href
                    href = href.rstrip("/")
                    article_links.add(href)

            added_count = len(article_links) - initial_count
            logging.info(
                f"Halaman {page}: Ditambahkan {added_count} link unik, total: {len(article_links)}"
            )
            page += 1
            time.sleep(random.uniform(2, 5))  # Delay lebih besar
            if page % 10 == 0:
                time.sleep(random.uniform(5, 11))  # Delay tambahan setiap 10 halaman

            next_button = soup.find("a", class_="next_link")
            if not next_button or "disabled" in next_button.get("class", []):
                logging.info(f"Tidak ada halaman berikutnya di {url}. Berhenti.")
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


async def get_article_content(link, session=None):
    """Mengambil konten artikel dari link: judul, abstrak Indonesia, dan kata kunci secara asynchronous."""
    try:
        user_agent = random.choice(USER_AGENTS)
        referer = random.choice(REFERERS)
        headers = {
            "User-Agent": user_agent,
            "Referer": referer,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
        }

        # Setup retry strategy
        retry_options = ExponentialRetry(
            attempts=3,  # Jumlah percobaan maksimal
            start_timeout=2,  # Waktu tunggu awal
            max_timeout=10,  # Waktu tunggu maksimal
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
                limit=3,  # Limit concurrent connections
                force_close=True,
                enable_cleanup_closed=True,
                ssl=False,  # Nonaktifkan SSL verification
            )
            timeout = ClientTimeout(
                total=30,  # Total timeout
                connect=10,  # Connection timeout
                sock_read=20,  # Socket read timeout
            )
            async with aiohttp.ClientSession(
                connector=connector, timeout=timeout
            ) as session:
                return await _fetch_content(session, link, headers, retry_options)
        else:
            return await _fetch_content(session, link, headers, retry_options)

    except Exception as e:
        logging.error(f"Error saat mengambil konten artikel dari {link}: {e}")
        return None, None, None


async def _fetch_content(session, link, headers, retry_options):
    """Helper function untuk mengambil konten dengan retry."""
    try:
        async with RetryClient(
            client_session=session, retry_options=retry_options
        ) as retry_client:
            async with retry_client.get(link, headers=headers, ssl=False) as response:
                response.raise_for_status()
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")

                # Mengambil judul artikel
                title_elem = soup.find(
                    "h4", class_="mb-2", style="text-align: justify;"
                )
                title = title_elem.text.strip() if title_elem else ""
                logging.debug(f"Title: {title}")

                # Mengambil abstrak dan kata kunci dari paragraf yang sama
                abstract_div = soup.find("div", id="collapseTwo_abstrak")
                abstract_text = ""
                keywords = []

                if abstract_div:
                    abstract_body = abstract_div.find("div", class_="card-body")
                    if abstract_body:
                        abstract_p = abstract_body.find("p", class_="text-grey-darker")
                        if abstract_p:
                            full_text = abstract_p.get_text(strip=True)
                            # Pisahkan berdasarkan penanda 'Kata kunci' atau 'Keywords'
                            match = re.search(
                                r"(Kata kunci|Keywords)\s*[:：]\s*(.+)",
                                full_text,
                                re.IGNORECASE,
                            )
                            if match:
                                abstract_text = full_text[: match.start()].strip()
                                keyword_raw = match.group(2)
                                keywords = [
                                    k.strip()
                                    for k in re.split(r"[;,]", keyword_raw)
                                    if k.strip()
                                ]
                            else:
                                abstract_text = full_text.strip()

                logging.debug(f"Abstract: {abstract_text[:100]}...")
                logging.debug(f"Keywords: {keywords}")
                return title, abstract_text, keywords

    except aiohttp.ClientError as e:
        logging.error(f"Network error saat mengambil {link}: {e}")
        return None, None, None
    except Exception as e:
        logging.error(f"Unexpected error saat mengambil {link}: {e}")
        return None, None, None


async def scrape_articles_etd(links):
    """Scrape multiple ETD articles concurrently with rate limiting."""
    article_data = []
    semaphore = asyncio.Semaphore(100)  # Limit concurrent scraping to 100 articles

    async def scrape_with_semaphore(link):
        async with semaphore:
            try:
                logging.info(f"Mengambil artikel: {link}")
                # Tambah delay random antara requests
                await asyncio.sleep(random.uniform(1, 5))

                title, abstract, keywords = await get_article_content(link)
                if title and abstract and keywords:
                    keyword_str = ", ".join(keywords) if keywords else "-"
                    logging.info(f"Artikel berhasil diambil: {title[:50]}...")
                    return (title, abstract, keyword_str)
                else:
                    logging.warning(f"Artikel gagal diambil: {link}")
                    # Tambah delay setelah kegagalan
                    await asyncio.sleep(random.uniform(1, 3))
                    return None
            except Exception as e:
                logging.error(f"Error dalam scrape_with_semaphore untuk {link}: {e}")
                await asyncio.sleep(random.uniform(1, 3))
                return None

    # Proses links dalam batch untuk menghindari overload
    batch_size = 100  # Batch size kecil karena ini server ETD
    for i in range(0, len(links), batch_size):
        batch = links[i : i + batch_size]
        logging.info(
            f"Processing batch {i//batch_size + 1} of {(len(links) + batch_size - 1)//batch_size}"
        )

        # Create tasks for current batch
        tasks = [scrape_with_semaphore(link) for link in batch]

        # Wait for current batch to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out None results and exceptions
        batch_results = [
            r for r in results if r is not None and not isinstance(r, Exception)
        ]
        article_data.extend(batch_results)

        # Add delay between batches
        if i + batch_size < len(links):
            delay = random.uniform(1, 4)  # Delay 5-10 detik antara batch
            logging.info(f"Waiting {delay:.1f} seconds before next batch...")
            await asyncio.sleep(delay)

    return article_data


def run(option):
    """Menjalankan proses crawling atau scraping berdasarkan opsi."""
    logging.info("Memulai proses untuk ETD USK")

    if option == 1:
        all_links = []

        for year in years:
            logging.info(f"Tahun: {year}")
            links = get_article_links(year)
            for link in links:
                all_links.append(link)
            logging.info(f"Tahun {year} selesai, {len(links)} link ditemukan")

        save_links(all_links, source="etd_usk")
        logging.info(f"Scraping selesai, total {len(all_links)} link dikumpulkan")

    elif option == 2:
        all_links = load_links("etd_usk")

        # Run the async scraping
        article_data = asyncio.run(scrape_articles_etd(all_links))

        save_csv(article_data, source="etd_usk")
        logging.info(
            f"Scraping selesai, total {len(article_data)} artikel disimpan ke CSV"
        )
