import logging
import importlib
from scrapers import helper
from scrapers import transform
import os
from scrapers.helper import save_csv

SOURCES = ["kompas", "tempo", "medium", "mojok", "etd_usk", "etd_ugm"]


def show_main_menu():
    print("\n=== MENU SCRAPER ===")
    print("1. Crawl URL")
    print("2. Scrape Data")
    print("3. Transform Data")
    print("4. Keluar")
    return input("Pilih opsi (1/2/3/4): ").strip()


def show_source_menu():
    print("\nPilih sumber media:")
    for idx, source in enumerate(SOURCES, start=1):
        print(f"{idx}. {source.capitalize()}")
    print(f"{len(SOURCES) + 1}. Kembali ke menu utama")
    return input(f"Pilih sumber (1-{len(SOURCES)}): ").strip()


def main():
    while True:
        main_choice = show_main_menu()

        if main_choice in ["1", "2"]:
            source_choice = show_source_menu()
            if source_choice in [str(i) for i in range(1, len(SOURCES) + 1)]:
                selected_source = SOURCES[int(source_choice) - 1]
                helper.setup_logging(selected_source)

                action = "Crawl URL" if main_choice == "1" else "Scrape Data"
                logging.info(f"Opsi dipilih: {action} untuk sumber: {selected_source}")

                try:
                    scraper_module = importlib.import_module(
                        f"scrapers.{selected_source}"
                    )
                    scraper_module.run(int(main_choice))
                except Exception as e:
                    logging.error(
                        f"Error saat menjalankan {action.lower()} untuk {selected_source}: {e}"
                    )
            elif source_choice == str(len(SOURCES) + 1):
                logging.info("Kembali ke menu utama.")
                print("Kembali ke menu utama.")
                continue
            else:
                print("Pilihan sumber tidak valid.")

        elif main_choice == "3":
            csv_name = input("Masukkan nama file CSV untuk ditransformasi: ").strip()

            if not os.path.exists(f"../data/raw/{csv_name}.csv"):
                print(f"[ERROR] File '{csv_name}.csv' tidak ditemukan.")
                logging.error(f"File tidak ditemukan: {csv_name}.csv")
                continue

            try:
                df_transformed = transform(f"../data/raw/{csv_name}.csv")
                if df_transformed is not None:
                    print("\n[INFO] Preview hasil transformasi:")
                    logging.info(
                        f"Preview hasil transformasi: {df_transformed.head(5)}"
                    )
                    print(df_transformed.head(5))
                    print(
                        f"\nJumlah total baris setelah transformasi: {len(df_transformed)}"
                    )
                    logging.info(
                        f"Jumlah total baris setelah transformasi: {len(df_transformed)}"
                    )
                    logging.info(
                        f"Transformasi selesai. Data disimpan ke '../data/processed/{csv_name}.csv'"
                    )
                    save_csv(df_transformed, f"../data/processed/{csv_name}.csv")
                else:
                    print("[ERROR] Transformasi gagal. Cek log untuk detail.")
            except Exception as e:
                logging.error(f"Error saat transformasi data: {e}")
                print(f"[ERROR] Terjadi kesalahan saat transformasi: {e}")

        elif main_choice == "4":
            logging.info("Keluar dari program.")
            print("Terima kasih. Program selesai.")
            break

        else:
            print("Pilihan tidak valid. Silakan pilih 1, 2, atau 3.")


if __name__ == "__main__":
    main()
