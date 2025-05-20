import random
import re
import time
import requests
from bs4 import BeautifulSoup
import logging
import uuid
import warnings
from .helper import load_links, save_links, save_csv
from config import USER_AGENTS, REFERERS, URL_ETD_USK

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


def get_article_links(year):
    """Mengambil semua link artikel dari halaman indeks untuk tahun tertentu."""
    article_links = set()
    page = 1
    base_url = f"{URL_ETD_USK}?publish_year={year}&prodi=&searchtype=advance&search=search&page="

    while True:
        url = f"{base_url}{page}"
        logging.info(f"Scraping {url}")

        user_agent = random.choice(USER_AGENTS)
        referer = random.choice(REFERERS)
        headers = {
            "User-Agent": user_agent,
            "Referer": referer,
        }

        try:
            logging.warning(
                "Verifikasi SSL dinonaktifkan untuk testing. Ini tidak aman untuk produksi."
            )
            response = requests.get(url, headers=headers, timeout=15, verify=False)
            response.raise_for_status()

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
                        href = URL_ETD_USK + href
                    href = href.rstrip("/")  # normalisasi akhir URL
                    article_links.add(href)

            added_count = len(article_links) - initial_count
            logging.info(
                f"Halaman {page}: Ditambahkan {added_count} link unik, total: {len(article_links)}"
            )
            page += 1
            time.sleep(random.uniform(1, 3))

            # Cek apakah ada tombol 'Next' untuk lanjut ke halaman berikutnya
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


def get_article_content(link):
    """Mengambil konten artikel dari link: judul, abstrak Indonesia, dan kata kunci."""
    try:
        user_agent = random.choice(USER_AGENTS)
        referer = random.choice(REFERERS)
        headers = {
            "User-Agent": user_agent,
            "Referer": referer,
        }

        logging.warning(
            "Verifikasi SSL dinonaktifkan untuk testing. Ini tidak aman untuk produksi."
        )
        response = requests.get(link, headers=headers, timeout=15, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Mengambil judul artikel
        title_elem = soup.find("h4", class_="mb-2", style="text-align: justify;")
        title = title_elem.text.strip() if title_elem else ""
        print("title", title)

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

        print("abstract_text", abstract_text)
        print("keywords", keywords)
        return title, abstract_text, keywords

    except Exception as e:
        logging.error(f"Error saat mengambil konten artikel dari {link}: {e}")
        return None, None, None


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
        article_data = []

        for idx, link in enumerate(all_links, 1):
            logging.info(f"[{idx}/{len(all_links)}] Mengambil artikel: {link}")
            title, abstract, keywords = get_article_content(link)

            if title and abstract and keywords:
                keyword_str = ", ".join(keywords) if keywords else "-"
                article_data.append((title, abstract, keyword_str))
            else:
                logging.warning(f"Artikel gagal diambil: {link}")

        save_csv(article_data, source="etd_usk")
        logging.info(
            f"Scraping selesai, total {len(article_data)} artikel disimpan ke CSV"
        )
