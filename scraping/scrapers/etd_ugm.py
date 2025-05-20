import random
import re
import time
import requests
from bs4 import BeautifulSoup
import logging
import uuid
import warnings
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


def get_article_content(article_id):
    """Mengambil konten artikel dari ID tertentu."""
    url = f"{BASE_URL}{article_id}"
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
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Mengambil judul artikel
        title_elem = soup.find("p", class_="title")
        title = title_elem.text.strip() if title_elem else ""
        if not title:
            logging.info(f"Tidak ada judul ditemukan di {url}. Halaman mungkin kosong.")
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

    except requests.exceptions.HTTPError as http_err:
        logging.info(f"HTTP Error di {url}, mungkin halaman kosong: {http_err}")
        return None, None, None
    except requests.exceptions.ConnectionError as conn_err:
        logging.error(f"Connection Error di {url}: {conn_err}")
        return None, None, None
    except requests.exceptions.Timeout as timeout_err:
        logging.error(f"Timeout Error di {url}: {timeout_err}")
        return None, None, None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error saat mengakses {url}: {e}")
        return None, None, None


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
        article_data = []

        for idx, link in enumerate(all_links, 1):
            logging.info(f"[{idx}/{len(all_links)}] Mengambil artikel: {link}")
            article_id = link.split("/")[-1]
            title, abstract, keywords = get_article_content(article_id)

            if title and abstract:
                keyword_str = ", ".join(keywords) if keywords else "-"
                article_data.append((title, abstract, keyword_str))
                logging.info(f"Artikel berhasil diambil: {title}")
            else:
                logging.info(f"Artikel kosong atau gagal diambil: {link}")

            time.sleep(random.uniform(1, 3))  # Delay untuk menghindari pemblokiran

        save_csv(article_data, source="etd_ugm")
        logging.info(
            f"Scraping selesai, total {len(article_data)} artikel disimpan ke CSV"
        )
