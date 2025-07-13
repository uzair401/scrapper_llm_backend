import streamlit as st
import requests
import json
from scrapper import site_scrapper, extract_body_content, clean_body_content
from configuration import FASTAPI_URL

st.set_page_config(page_title="AI Web Scraper", layout="wide")
st.title("AI Web Scraper by Uzair")

if 'linkedin_token' not in st.session_state:
    st.session_state.linkedin_token = None

if 'scraped_result' not in st.session_state:
    st.session_state.scraped_result = None

if 'show_scraped' not in st.session_state:
    st.session_state.show_scraped = False

url = st.text_input("Enter Website URL")
prompt = st.text_area("What do you want to know about this website?")

if st.button("Scrape and Analyze"):
    if url and prompt:
        try:
            html = site_scrapper(url)
            body = extract_body_content(html)
            cleaned = clean_body_content(body)

            response = requests.post(f"{FASTAPI_URL}/ask", json={"prompt": prompt, "data": cleaned})
            response.raise_for_status()
            result_json = response.json()
            cleaned_response = result_json.get("response", "No response field found.")

            st.markdown("### AI Analysis")
            st.markdown(cleaned_response)

            st.session_state.scraped_result = {
                'url': url,
                'prompt': prompt,
                'analysis': cleaned_response,
                'scraped_content': cleaned
            }
            st.session_state.show_scraped = False

        except Exception as e:
            st.error(f"Scraping failed: {e}")
    else:
        st.warning("Please enter both URL and prompt")

if st.session_state.scraped_result:
    col1, col2 = st.columns([3, 1])

    with col1:
        if st.button("Show Scraped Content"):
            st.session_state.show_scraped = not st.session_state.show_scraped

    with col2:
        if st.button("Post to LinkedIn"):
            headers = {}
            if st.session_state.linkedin_token:
                headers["Authorization"] = f"Bearer {st.session_state.linkedin_token}"

            try:
                response = requests.post(f"{FASTAPI_URL}/api/linkedin/check-auth/", headers=headers, json={"content": st.session_state.scraped_result['analysis']})
                if response.status_code == 200:
                    st.success("✅ LinkedIn is connected. Post logic will be implemented here.")
                elif response.status_code == 401:
                    data = response.json()
                    login_url = data.get("login_url")
                    st.warning("🔗 Please login to LinkedIn first.")
                    st.markdown(f"[Click here to login to LinkedIn]({login_url})")
                else:
                    st.error("LinkedIn auth check failed.")
            except Exception as e:
                st.error(f"LinkedIn auth check failed: {e}")

if st.session_state.show_scraped:
    st.markdown("### Scraped Content")
    st.text_area("", st.session_state.scraped_result['scraped_content'], height=300)

auth_code = st.text_input("Enter LinkedIn Auth Code (after login):")
if st.button("Exchange Auth Code"):
    resp = requests.post(f"{FASTAPI_URL}/api/linkedin/token-exchange/", json={"auth_code": auth_code})
    if resp.status_code == 200:
        st.session_state.linkedin_token = resp.json()["access_token"]
        st.success("Access token saved.")
    else:
        st.error("Failed to exchange auth code.")
