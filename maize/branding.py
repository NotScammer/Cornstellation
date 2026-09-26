"""Shared team identity for the FieldSignal dashboard views."""
from pathlib import Path

import streamlit as st


LOGO = Path(__file__).resolve().parents[1] / "Cornstellation SyDAg.png"


def render_team_branding():
    with st.container(horizontal=True, vertical_alignment="center", gap="medium"):
        if LOGO.exists():
            st.image(str(LOGO), width=180)
        with st.container():
            st.markdown("### Cornstellation")
            st.caption("The team behind FieldSignal")

