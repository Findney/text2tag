import streamlit as st
import requests
import json
from streamlit_lottie import st_lottie

# === CONFIG ===
st.set_page_config(page_title="SENTRA", layout="wide", initial_sidebar_state="collapsed")
API_URL = "http://localhost:8000"

# === GLOBAL STYLES ===
st.markdown("""
<style>
div[data-testid="stHorizontalBlock"] > div {
    display: flex !important;
    align-items: flex-start !important; 
    flex-wrap: nowrap !important;
}

/* Style untuk div pertama */
div[data-testid="stHorizontalBlock"] > div:nth-child(1) {
    justify-content: right !important;
}

/* Style untuk div kedua */
div[data-testid="stHorizontalBlock"] > div:nth-child(2) {
    justify-content: center !important;
}

/* Style untuk div ketiga */
div[data-testid="stHorizontalBlock"] > div:nth-child(3) {
    justify-content: left !important;
}

div[data-testid="stHorizontalBlock"] div[data-testid^="stVerticalBlock"] button {
    display: inline-block !important;
    width: auto !important; /* Biarkan lebar menyesuaikan konten, melawan use_container_width */
    /* --- UBAH BARIS INI MENJADI MARGIN 0 --- */
    margin: 0 !important; /* HAPUS margin horizontal pada tombol itu sendiri */
    /* --------------------------------------- */
    padding: 0.6rem 1.2rem !important; /* Padding internal tombol tetap ada */
    border-radius: 12px !important;
    font-weight: 500 !important;
    transition: all 0.2s ease-in-out !important;
    border: none !important; 
    line-height: 1.5; 
}

div[data-testid="stHorizontalBlock"] div[data-testid^="stVerticalBlock"] button[kind="secondary"] {
    background-color: transparent !important;
    color: #fff !important;
}

div[data-testid="stHorizontalBlock"] div[data-testid^="stVerticalBlock"] button[kind="secondary"]:hover {
    background-color: #e0e7ff !important;
    color: black !important;
    transform: scale(1.05) !important;
}

div[data-testid="stHorizontalBlock"] div[data-testid^="stVerticalBlock"] button[kind="secondary"]:focus {
    box-shadow: 0 0 0 0.2rem rgba(224, 231, 255, 0.5) !important;
}

div[data-testid="stHorizontalBlock"] div[data-testid^="stVerticalBlock"] button[kind="primary"] {
    background-color: #c7d2fe !important;
    font-weight: bold !important;
    color: #000 !important;
    box-shadow: 0 3px 10px rgba(0, 0, 0, 0.1) !important;
}

div[data-testid="stHorizontalBlock"] div[data-testid^="stVerticalBlock"] button[kind="primary"]:hover {
    background-color: #b0c0f0 !important;
    transform: scale(1.05) !important;
}

div[data-testid="stHorizontalBlock"] div[data-testid^="stVerticalBlock"] button[kind="primary"]:focus {
    box-shadow: 0 3px 10px rgba(0, 0, 0, 0.1), 0 0 0 0.2rem rgba(199, 210, 254, 0.7) !important;
}

footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# === LOTTIE ===
def load_lottie_url(url: str):
    try:
        r = requests.get(url, timeout=10) # Tambahkan timeout
        return r.json() if r.status_code == 200 else None
    except requests.exceptions.RequestException as e:
        st.error(f"Gagal memuat animasi Lottie: {e}")
        return None

# === NAVIGATION ===
def navigation_menu():
    current_page_key = st.session_state.get("page", "home")
    pages = {
        "home": "🏠 Beranda",
        "keyword": "🔍 Kata Kunci",
        "tag": "🏷️ Tag"
    }

    cols = st.columns(len(pages), gap="small")

    for i, (page_key, page_label) in enumerate(pages.items()):
        with cols[i]:
            is_active = (current_page_key == page_key)
            button_type = "primary" if is_active else "secondary"

            if st.button(page_label, key=f"nav_{page_key}", type=button_type, use_container_width=True):
                st.session_state.page = page_key
                st.rerun()


# === UI - Keyword ===
def keyword_ui():
    st.subheader("🔍 Generate Kata Kunci dari Abstrak")
    text = st.text_area("📝 Input Abstrak", height=250, placeholder="Paste abstrak akademis di sini...")

    if st.button("🚀 Generate Keywords"):
        if not text.strip():
            st.warning("Silakan masukkan abstrak.")
            return
        with st.spinner("Membuat..."):
            try:
                response = requests.post(f"{API_URL}/generate_keywords", json={"text": text}, timeout=30)
                if response.status_code == 200:
                    result = response.json().get("keywords")
                    if result:
                        st.success("✅ Kata kunci berhasil dibuat!")
                        st.markdown("### 🔑 Kata Kunci:")
                        st.markdown(" ".join([f"`{kw}`" for kw in result]))
                        st.download_button("⬇️ Download sebagai .txt", "\n".join(result), file_name="keywords.txt")
                        st.download_button("⬇️ Download sebagai .json", json.dumps(result), file_name="keywords.json")
                    else:
                        st.error("Tidak ada kata kunci yang diterima dari server.")
                else:
                    st.error(f"Gagal membuat kata kunci. Status: {response.status_code} - {response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"Permintaan API gagal: {e}")

# === UI - Tag ===
def tag_ui():
    st.subheader("🏷️ Membuat Tag dari Artikel Berita")
    judul = st.text_input("📰 Judul Berita", placeholder="Contoh: Pemerintah Luncurkan Program Energi Baru")
    konten = st.text_area("📝 Konten Berita", height=250)

    if st.button("🚀 Generate Tags"):
        if not judul.strip() or not konten.strip():
            st.warning("Silakan isi keduanya.")
            return

        # if len(konten.split()) > 200:
        #     st.error(f"Konten melebihi 200 kata. Input Anda memiliki {len(konten.split())} kata.")
        #     return

        with st.spinner("Membuat..."):
            combined_text = f"judul: {judul} konten: {konten}"
            try:
                response = requests.post(f"{API_URL}/generate_tags", json={"text": combined_text}, timeout=30)
                if response.status_code == 200:
                    result = response.json().get("tags")
                    if result:
                        st.success("✅ Tag berhasil dibuat!")
                        st.markdown("### 🏷️ Tag:")
                        tag_html = "".join([
                            f"<span style='display:inline-block;background:#DFF0D8;color:#3C763D;padding:6px 10px;"
                            f"margin:4px;border-radius:20px;font-size:15px;'>{tag}</span>"
                            for tag in result
                        ])
                        st.markdown(tag_html, unsafe_allow_html=True)
                        st.download_button("⬇️ Download sebagai .json", json.dumps(result, indent=2), file_name="tags.json")
                        st.download_button("⬇️ Download sebagai .txt", "\n".join(result), file_name="tags.txt")
                    else:
                        st.error("Tidak ada tag yang dihasilkan.")
                else:
                    st.error(f"Gagal membuat tag. Status: {response.status_code} - {response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"Permintaan API gagal: {e}")


# === UI - Landing Page ===
def landing_page():
    st.markdown("<h1 style='text-align:center;'>SENTRA</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align:center;color:gray;'>Unlock keywords & tags with AI precision</h4>", unsafe_allow_html=True)

    lottie_url = "https://assets6.lottiefiles.com/packages/lf20_zrqthn6o.json"
    animation = load_lottie_url(lottie_url)
    if animation:
        st_lottie(animation, height=300, speed=1, loop=True, quality="high")
    else:
        st.warning("Tidak dapat memuat animasi. Menampilkan konten statis.")


    st.markdown("---")
    st.markdown("### ✨ Fitur:")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("- 🔍 Ekstrak **kata kunci** akademis dari abstrak")
        st.markdown("- 📄 Simpan hasil sebagai `.txt` atau `.json`")
    with col2:
        st.markdown("- 🏷️ Membuat **tag** dari artikel berita")
        st.markdown("- 🧠 Dibangun dengan model NLP yang di-fine-tuning")

# === FOOTER ===
def render_footer():
    st.markdown("""
    <hr style="margin-top:3rem;margin-bottom:1rem;">
    <div style="text-align:center;color:gray;font-size:0.9rem;">
        © 2025 SENTRA (Smart Extraction and Tagging for Nusantara) — Built by Agil Mughni & Akhsania Maisa Rahmah
    </div>
    """, unsafe_allow_html=True)


# === MAIN ===
def main():
    if "page" not in st.session_state:
        query_params = st.query_params.to_dict()
        st.session_state.page = query_params.get("page", ["home"])[0]

    navigation_menu()

    st.markdown("---") 
    
    active_page = st.session_state.page
    if active_page == "home":
        landing_page()
    elif active_page == "keyword":
        keyword_ui()
    elif active_page == "tag":
        tag_ui()
    else: 
        st.session_state.page = "home"
        st.rerun()

    render_footer()

if __name__ == "__main__":
    main()