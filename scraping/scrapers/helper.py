import os
import logging
import csv


def setup_logging(source):
    """Mengatur logging dengan file log spesifik untuk setiap sumber."""
    log_dir = "../log/scraping/"
    os.makedirs(log_dir, exist_ok=True)
    log_file = f"{log_dir}/{source}.log"

    # Ambil logger root
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Hapus semua handler lama agar konfigurasi ulang berhasil
    if logger.hasHandlers():
        logger.handlers.clear()

    # Tambahkan handler baru
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    console_handler = logging.StreamHandler()

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info(f"Logging diatur untuk sumber: {source}")


def save_links(links, source):
    """Menyimpan semua link ke satu file teks dengan nama berdasarkan sumber."""
    output_dir = f"../data/raw"
    os.makedirs(output_dir, exist_ok=True)
    output_file = f"{output_dir}/{source}.txt"

    with open(output_file, "w", encoding="utf-8") as f:
        for link in links:
            f.write(link + "\n")

    logging.info(f"Semua link dari sumber '{source}' disimpan ke {output_file}")


def load_links(source):
    """
    Membaca semua link dari file teks yang sebelumnya disimpan berdasarkan nama sumber.
    Mengembalikan list berisi URL.
    """
    input_file = f"../data/raw/{source}.txt"

    if not os.path.exists(input_file):
        logging.warning(f"File tidak ditemukan: {input_file}")
        return []

    with open(input_file, "r", encoding="utf-8") as f:
        links = [line.strip() for line in f if line.strip()]

    logging.info(f"Muat {len(links)} link dari file {input_file}")
    return links


def save_csv(data, source):
    """Menyimpan data ke dalam file CSV dengan nama berdasarkan sumber."""
    output_dir = f"../data/raw"
    os.makedirs(output_dir, exist_ok=True)
    output_file = f"{output_dir}/{source}.csv"

    with open(output_file, "w", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["title", "content", "tag"])
        for title, content, tag in data:
            writer.writerow([title, content, tag])

    logging.info(f"Data dari sumber '{source}' disimpan ke {output_file}")
