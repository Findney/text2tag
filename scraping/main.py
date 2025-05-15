import logging
import importlib
import os
from scrapers import helper


def show_menu():
    print("\n=== MENU SCRAPER KOMPAS ===")
    print("1. Crawl URL")
    print("2. Scrape Data")
    print("3. Keluar")
    return input("Pilih opsi (1/2/3): ").strip()


def main():
    sources = ["kompas"]

    while True:
        choice = show_menu()
        if choice == "1":
            for source in sources:
                helper.setup_logging(source)
                logging.info("Opsi 1 dipilih: Crawl URL")
                try:
                    scraper_module = importlib.import_module(f"scrapers.{source}")
                    scraper_module.run(1)  # Jalankan crawling URL
                except Exception as e:
                    logging.error(f"Error saat menjalankan crawling URL: {e}")

        elif choice == "2":
            for source in sources:
                helper.setup_logging(source)
                logging.info("Opsi 2 dipilih: Scrape Data")
                try:
                    scraper_module = importlib.import_module(f"scrapers.{source}")
                    scraper_module.run(2)  # Jalankan scraping konten
                except Exception as e:
                    logging.error(f"Error saat menjalankan scraping konten: {e}")

        elif choice == "3":
            logging.info("Keluar dari program.")
            print("Terima kasih. Program selesai.")
            break

        else:
            print("Pilihan tidak valid. Silakan pilih 1, 2, atau 3.")


if __name__ == "__main__":
    main()
