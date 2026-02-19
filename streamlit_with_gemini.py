import os
import streamlit as st
import requests

st.set_page_config(page_title="Virtual Try-On", layout="wide")
st.title("Virtual Try-On – Gemini + IDM-VTON + Overlay Fallback")

# Prefer environment variable in deployment (Streamlit Cloud supports secrets/env vars)
DEFAULT_API_BASE = os.getenv("API_BASE", "http://3.88.24.123:8000").rstrip("/")

api_base = st.sidebar.text_input("Backend URL", DEFAULT_API_BASE).rstrip("/")
timeout = st.sidebar.slider("Timeout (s)", 30, 600, 240)
prefer_idm = st.sidebar.checkbox("Prefer IDM-VTON (photorealistic)", value=True)

def health():
    r = requests.get(f"{api_base}/health", timeout=10)
    r.raise_for_status()
    return r.json()

def post_tryon(path: str, files: dict, garment_des: str):
    data = {
        "garment_des": garment_des,
        "prefer_idm": 1 if prefer_idm else 0,
    }
    r = requests.post(
        f"{api_base}{path}",
        files=files,
        data=data,
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()

def show_result(data: dict):
    st.write("Mode used:", data.get("mode_used"))
    st.info("Garment description: " + str(data.get("garment_description")))
    st.json(data.get("scores", {}))

    urls = data.get("output_urls") or []
    if not urls:
        st.warning("No output images returned from backend.")
        return

    for u in urls:
        # Replacement for deprecated use_column_width
        st.image(u, use_container_width=True)

# Sidebar: health check
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

            with st.spinner("Processing..."):
                try:
                    data = post_tryon("/v1/tryon/actress-to-user", files, garment_des)
                    show_result(data)
                except requests.exceptions.RequestException as e:
                    st.error(f"Request failed: {e}")
                except Exception as e:
                    st.error(f"Unexpected error: {e}")

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

            with st.spinner("Processing..."):
                try:
                    data = post_tryon("/v1/tryon/garment-to-user", files, garment_des2)
                    show_result(data)
                except requests.exceptions.RequestException as e:
                    st.error(f"Request failed: {e}")
                except Exception as e:
                    st.error(f"Unexpected error: {e}")
