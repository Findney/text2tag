import streamlit as st
import requests
import json
from streamlit_lottie import st_lottie

API_URL = "http://localhost:8000"

def load_lottie_url(url: str):
    r = requests.get(url)
    return r.json() if r.status_code == 200 else None

def keyword_ui():
    st.header("🔍 Generate Keywords from Abstract")
    # Inputan berupa abstract
    text = st.text_area("Input Abstract")
    if st.button("Generate Keywords"):
        if not text.strip():
            st.warning("Please input an abstract.")
            return
        with st.spinner("Generating..."):
            response = requests.post(f"{API_URL}/generate_keywords", json={"text": text})
            if response.status_code == 200:
                result = response.json().get("keywords") # Use .get() for safety
                if result is not None:
                    st.subheader("🔑 Keywords:")
                    st.markdown(" ".join([f"`{kw}`" for kw in result]))
                    st.download_button("📄 Download .txt", "\n".join(result), file_name="keywords.txt")
                else:
                    st.error("Received no keywords from the server.")
            else:
                st.error(f"Failed to generate keywords. Status code: {response.status_code} - {response.text}")

def tag_ui():
    st.header("🏷️ Generate Tags from News Article")
    judul = st.text_input("Judul Berita")
    konten = st.text_area("Konten Berita (max. 200 words)")

    if st.button("Generate Tags"):
        if not judul.strip() and not konten.strip():
            st.warning("Please input news title and content.")
            return
        if not judul.strip():
            st.warning("Please input news title.")
            return
        if not konten.strip():
            st.warning("Please input news content.")
            return

        word_count = len(konten.split())
        if word_count > 200:
            st.error(f"Konten Berita should not exceed 200 words. You have {word_count} words.")
            return

        with st.spinner("Generating..."):
            # Gabungkan judul + konten → kirim ke backend sebagai satu field "text"
            combined_text = f"judul: {judul} konten: {konten}"
            response = requests.post(
                f"{API_URL}/generate_tags",
                json={"text": combined_text}
            )

            if response.status_code == 200:
                result = response.json().get("tags")
                if result:
                    st.subheader("🏷️ Tags:")
                    tags_html = "".join([
                        f"<span style='display:inline-block;background-color:#d4edda;color:#155724;padding:0.3em 0.6em;margin:0.2em;border-radius:10px;font-size:0.9em;'>{tag}</span>"
                        for tag in result
                    ])
                    st.markdown(tags_html, unsafe_allow_html=True)
                    st.download_button("📁 Save as .json", json.dumps(result, indent=2), file_name="tags.json")
                else:
                    st.error("No tags were generated.")
            else:
                st.error(f"Failed to generate tags. Status code: {response.status_code} - {response.text}")

def main():
    st.set_page_config(page_title="Smart Text Tagger", layout="centered", initial_sidebar_state="collapsed")
    st.title("🧠 Smart Text Tagger")

    # Attempt to load Lottie animation, handle potential errors gracefully
    try:
        lottie_url = "https://assets10.lottiefiles.com/packages/lf20_lz5mt5vd.json"
        lottie_animation = load_lottie_url(lottie_url)
        if lottie_animation:
            st_lottie(lottie_animation, height=150, speed=1, reverse=False, loop=True, quality="high", key="lottie_animation")
    except requests.exceptions.RequestException as e:
        st.warning(f"Could not load animation: {e}")
    except Exception as e: # Catch any other potential errors during Lottie loading/rendering
        st.warning(f"An error occurred with the animation: {e}")


    page = st.selectbox("Choose Feature", ["🏠 Landing Page", "🔍 Text-to-Keyword", "🏷️ Text-to-Tag"], label_visibility="collapsed")

    if page == "🔍 Text-to-Keyword":
        keyword_ui()
    elif page == "🏷️ Text-to-Tag":
        tag_ui()
    else: # Landing Page
        st.markdown("### Welcome to Smart Text Tagger 🚀")
        st.markdown("Select a feature from the dropdown menu above to get started:")
        st.markdown("- **🔍 Generate Keywords from Abstract**: Input an academic abstract to extract relevant keywords.")
        st.markdown("- **🏷️ Generate Tags from News Article**: Provide a news title and content (up to 200 words) to generate appropriate tags.")

if __name__ == "__main__":
    main()