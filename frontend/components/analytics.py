import streamlit as st


def inject_google_analytics() -> None:
    measurement_id = st.secrets.get("GA4_MEASUREMENT_ID", "")

    if not measurement_id:
        return

    st.markdown(
        f"""
        <!-- Google Analytics 4 -->
        <script async src="https://www.googletagmanager.com/gtag/js?id={measurement_id}"></script>
        <script>
          window.dataLayer = window.dataLayer || [];
          function gtag(){{dataLayer.push(arguments);}}
          gtag('js', new Date());
          gtag('config', '{measurement_id}');
        </script>
        """,
        unsafe_allow_html=True,
    )