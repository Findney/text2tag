import pandas as pd


def transform_csv(csv_path, dropna=True, encoding="utf-8"):
    """
    Membaca file CSV dan melakukan transformasi awal pada data.

    Parameters:
    - csv_path (str): path ke file CSV.
    - dropna (bool): jika True, akan menghapus baris yang memiliki nilai kosong.
    - encoding (str): encoding file CSV, default 'utf-8'.

    Returns:
    - df (pandas.DataFrame): DataFrame hasil pembacaan dan transformasi awal.
    """
    try:
        df = pd.read_csv(csv_path, encoding=encoding)
        print(f"[INFO] Data berhasil dibaca. Jumlah baris: {len(df)}")

        # Normalisasi nama kolom
        df.columns = [col.strip().lower() for col in df.columns]

        # Rename kolom jika ada
        df = df.rename(
            columns={
                "title": "judul",
                "abstract": "abstrak",
                "content": "konten",
                "tag_str": "tag",
                "keyword_str": "kata_kunci",
            }
        )

        required_cols = ["judul"]

        # Drop baris kosong dan duplikat berdasarkan kolom penting
        df = df.dropna(subset=required_cols)
        df = df.drop_duplicates(subset=required_cols)

        # Pembersihan konten string
        if "kata_kunci" in df.columns:
            df["kata_kunci"] = (
                df["kata_kunci"]
                .str.removeprefix("Kata kunci: ")
                .str.removeprefix("Keywords: ")
            )
        if "tag" in df.columns:
            df["tag"] = (
                df["tag"]
                .str.removeprefix("Tag: ")
                .str.removeprefix("Tags: ")
                .str.removeprefix("Kata Kunci : ")
                .str.removeprefix("Keywords: ")
            )

        print(
            f"[INFO] Data berhasil diproses. Total baris setelah transformasi: {len(df)}"
        )

        return df

    except Exception as e:
        print(f"[ERROR] Gagal membaca atau memproses file: {e}")
        return None
