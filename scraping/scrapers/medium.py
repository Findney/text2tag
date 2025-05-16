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
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def get_article_links_medium():
    links = set()

    # Konfigurasi opsi Chrome
    options = Options()
    options.add_argument("--headless")  # Jalankan di mode headless
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument(
        "--disable-dev-shm-usage"
    )  # Mengatasi masalah memori di container
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )

    try:
        # Inisialisasi driver dengan ChromeDriverManager
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )

        try:
            # Buka halaman Medium
            driver.get(f"{MEDIUM_URL}/komunitas-blogger-m")
            SCROLL_PAUSE_TIME = 2
            last_height = driver.execute_script("return document.body.scrollHeight")

            # Lakukan scrolling untuk memuat konten
            for _ in range(10):  # Scroll sebanyak 10 kali
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(SCROLL_PAUSE_TIME)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

            # Parsing halaman dengan BeautifulSoup
            soup = BeautifulSoup(driver.page_source, "html.parser")

            # Cari div utama yang memuat artikel
            target_div = soup.find("div", class_="u-marginBottom40 js-collectionStream")
            if not target_div:
                logging.warning(
                    "Div dengan kelas 'u-marginBottom40 js-collectionStream' tidak ditemukan."
                )
                return []

            # Ambil semua tag <a> dengan atribut href
            anchor_tags = target_div.find_all("a", href=True)

            for a in anchor_tags:
                raw_link = a["href"]
                clean_link = raw_link.split("?")[0].rstrip("/")

                # Lewati link ke profil pengguna
                if clean_link.startswith(f"{MEDIUM_URL}/@"):
                    logging.info(f"Link profil dilewati: {clean_link}")
                    continue

                # Hanya proses link yang relevan dengan komunitas
                if clean_link.startswith(f"{MEDIUM_URL}/komunitas-blogger-m"):
                    if clean_link not in links:
                        slug = clean_link.split("/")[-1]

                        # Lewati slug acak berbentuk hash ID
                        if re.fullmatch(r"[\da-f\-]{10,}", slug, re.IGNORECASE):
                            continue

                        # Lewati slug non-Latin
                        if not all(
                            "LATIN" in unicodedata.name(char, "")
                            for char in slug
                            if char.isalpha()
                        ):
                            continue

                        # Pastikan slug mengandung cukup huruf Latin
                        if not re.search(r"[a-zA-Z]{3,}", slug):
                            continue

                        links.add(clean_link)
                        logging.info(f"Link ditambahkan: {clean_link}")

            time.sleep(random.uniform(1.5, 3.0))  # Delay untuk menghindari ban

        except Exception as e:
            logging.error(f"Terjadi kesalahan saat memproses halaman: {str(e)}")
            return []

        finally:
            driver.quit()

    except Exception as e:
        logging.error(f"Gagal menginisialisasi driver: {str(e)}")
        return []

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
        logging.info("Mulai proses crawling link artikel dari Medium...")
        links = get_article_links_medium()  # Diasumsikan sudah tidak butuh kategori
        if not links:
            logging.warning("Tidak ada link ditemukan.")
            return
        save_links(links, source="medium")
        logging.info(f"Total {len(links)} link disimpan dari Medium.")

    elif option == 2:
        all_links = load_links("medium")
        if not all_links:
            logging.warning("Tidak ada link yang dimuat dari file.")
            return

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
