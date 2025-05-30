import logging
import importlib
from scrapers import helper
from scrapers.transform import transform_csv
from pathlib import Path
from scrapers.helper import save_csv_processed

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

            # Bangun path dengan benar
            raw_data_dir = Path.cwd() / "../data" / "raw"  
            csv_path = raw_data_dir / f"{csv_name}.csv"

            if not csv_path.exists():
                print(f"[ERROR] File '{csv_name}.csv' tidak ditemukan di {raw_data_dir}.")
                logging.error(f"File tidak ditemukan: {csv_path}")
                continue

            try:
                df_transformed = transform_csv(csv_path)
                if df_transformed is not None:
                    logging.info(
                        f"Preview hasil transformasi: {df_transformed.head(5)}"
                    )
                    logging.info(
                        f"Jumlah total baris setelah transformasi: {len(df_transformed)}"
                    )
                    save_csv_processed(df_transformed, csv_name)
                    logging.info(
                        f"Transformasi selesai. Data disimpan ke {csv_path}"
                    )
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
