import os
from urllib.parse import urljoin

import streamlit as st
import requests

st.set_page_config(page_title="Virtual Try-On", layout="wide")
st.title("Virtual Try-On – Gemini + IDM-VTON + Overlay Fallback")

# Prefer env var in deployment (Streamlit Cloud supports secrets/env vars)
DEFAULT_API_BASE = os.getenv("API_BASE", "http://3.88.24.123:8000").rstrip("/")

api_base = st.sidebar.text_input("Backend URL", DEFAULT_API_BASE).rstrip("/")
timeout = st.sidebar.slider("Timeout (s)", 30, 600, 240)
prefer_idm = st.sidebar.checkbox("Prefer IDM-VTON (photorealistic)", value=True)

def health():
    r = requests.get(f"{api_base}/health", timeout=10)
    r.raise_for_status()
    return r.json()

def resolve_image_url(u: str) -> str:
    """Handle absolute URLs + relative paths returned by backend."""
    u = (u or "").strip()
    if not u:
        return ""
    if u.startswith("http://") or u.startswith("https://"):
        return u
    # Convert "/outputs/x.png" or "outputs/x.png" -> "{api_base}/outputs/x.png"
    return urljoin(api_base + "/", u.lstrip("/"))

def show_result(data: dict):
    st.write("Mode used:", data.get("mode_used"))
    st.info("Garment description: " + str(data.get("garment_description")))
    st.json(data.get("scores", {}))

    urls = data.get("output_urls") or []
    st.write("output_urls:", urls)  # Debug (remove later)

    if not urls:
        st.warning("No output images returned (output_urls is empty).")
        return

    for raw_u in urls:
        img_url = resolve_image_url(raw_u)
        if not img_url:
            continue

        try:
            # Fetch bytes server-side to avoid browser mixed-content blocking (https Streamlit + http backend)
            resp = requests.get(img_url, timeout=60)
            resp.raise_for_status()

            # New Streamlit API (avoid deprecated params)
            st.image(resp.content, width="stretch")

        except Exception as e:
            st.error(f"Failed to load image from {raw_u} -> {img_url}: {e}")

if st.sidebar.button("Health Check"):
    try:
        st.sidebar.json(health())
        st.sidebar.success("Backend reachable ✅")
    except Exception as e:
        st.sidebar.error(f"Health check failed: {e}")

tab1, tab2 = st.tabs(["Actress → User", "Garment → User"])

with tab1:
    st.subheader("Actress → User")
    c1, c2 = st.columns(2)
    actress = c1.file_uploader("Upload actress image", type=["jpg", "jpeg", "png"], key="actress")
    user = c2.file_uploader("Upload user image", type=["jpg", "jpeg", "png"], key="user_a")

    garment_des = st.text_input("Garment description override (optional)", "")

    if st.button("Run Actress → User"):
        if not actress or not user:
            st.error("Upload both images.")
        else:
            files = {
                "actress_image": ("actress.jpg", actress.getvalue(), actress.type),
                "user_image": ("user.jpg", user.getvalue(), user.type),
            }
            data = {"garment_des": garment_des, "prefer_idm": 1 if prefer_idm else 0}

            with st.spinner("Processing..."):
                try:
                    r = requests.post(
                        f"{api_base}/v1/tryon/actress-to-user",
                        files=files,
                        data=data,
                        timeout=timeout,
                    )
                    r.raise_for_status()
                    show_result(r.json())
                except Exception as e:
                    st.error(str(e))

with tab2:
    st.subheader("Garment → User")
    c1, c2 = st.columns(2)
    garment = c1.file_uploader("Upload garment image", type=["jpg", "jpeg", "png"], key="garment")
    user2 = c2.file_uploader("Upload user image", type=["jpg", "jpeg", "png"], key="user_g")

    garment_des2 = st.text_input("Garment description override (optional)", "", key="gd2")

    if st.button("Run Garment → User"):
        if not garment or not user2:
            st.error("Upload both images.")
        else:
            files = {
                "garment_image": ("garment.jpg", garment.getvalue(), garment.type),
                "user_image": ("user.jpg", user2.getvalue(), user2.type),
            }
            data = {"garment_des": garment_des2, "prefer_idm": 1 if prefer_idm else 0}

            with st.spinner("Processing..."):
                try:
                    r = requests.post(
                        f"{api_base}/v1/tryon/garment-to-user",
                        files=files,
                        data=data,
                        timeout=timeout,
                    )
                    r.raise_for_status()
                    show_result(r.json())
                except Exception as e:
                    st.error(str(e))
