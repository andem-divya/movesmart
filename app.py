import streamlit as st
import pandas as pd
# Assuming these exist in your local project
from src import recommender
from src import visualizations

SLIDER_MIN = 0.0
SLIDER_MAX = 5.0
SLIDER_DEFAULT = 2.5
SLIDER_STEP = 0.01

def round_prefs(d: dict) -> dict:
    return {k: round(float(v), 2) for k, v in d.items()}

def metro_label(city: dict) -> str:
    return str(city.get("cbsa_name_y") or city.get("cbsa_name") or "Unknown")

def fmt_score(x) -> str:
    try:
        return f"{float(x):.2f}"
    except (TypeError, ValueError):
        return "—"

# --- Page Config ---
st.set_page_config(page_title="MoveSmart", layout="wide")

# -------------------------
# 🎨 GLOBAL STYLING
# -------------------------
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
    :root {
        --ink: #0f1c1a;
        --ink-light: #5a7672;
        --paper: #f5f2eb;
        --paper-warm: #ede8de;
        --accent: #1a6b56;
        --accent-bright: #23956e;
    }
    .stApp { background-color: var(--paper); font-family: 'DM Sans', sans-serif; }
    h1, h2, h3 { font-family: 'DM Serif Display', serif !important; color: var(--ink); }
    section[data-testid="stSidebar"] { background-color: var(--paper-warm); }
    .stButton > button {
        background-color: var(--accent); color: white; border-radius: 10px;
        padding: 0.6rem 1.2rem; font-weight: 600; border: none;
    }
    .stButton > button:hover { background-color: var(--accent-bright); color: white; }
    .navbar {
        background: rgba(245,242,235,0.9); backdrop-filter: blur(10px);
        padding: 1rem 2rem; border-radius: 14px; margin-bottom: 2rem;
        border-bottom: 1px solid rgba(15, 28, 26, 0.1);
    }
    .city-card {
        background: #ffffff; border-radius: 16px; padding: 1.5rem;
        border: 1px solid rgba(0,0,0,0.06); shadow: 0 10px 30px rgba(0,0,0,0.06);
        margin-bottom: 10px;
    }
    .city-name { font-size: 1.2rem; font-weight: 600; color: var(--ink); }
    .city-desc { color: var(--ink-light); font-size: 0.9rem; margin-bottom: 8px; }
    .section-title { font-family: 'DM Serif Display', serif; font-size: 2rem; margin-bottom: 1rem; }
</style>
""", unsafe_allow_html=True)

# -------------------------
# Navbar
# -------------------------
st.markdown("""
<div class="navbar" style="display:flex; justify-content:space-between; align-items:center;">
    <div style="font-family:'DM Serif Display'; font-size:1.5rem;">
        Move<span style="color:#23956e;">Smart</span>
    </div>
    <div>
        <a href="https://capstone-movesmart.netlify.app" target="_blank" style="margin-left:20px; text-decoration:none; color:#2d4442;">About</a>
    </div>
</div>
""", unsafe_allow_html=True)

# -------------------------
# Hero Section
# -------------------------
st.markdown("""
<h1 style="font-size:3rem; line-height:1.1; margin-bottom:10px;">
    Find the city that fits <span style="color:#23956e;">your life</span>
</h1>
<p style="color:#5a7672; font-size:1.05rem; margin-bottom:40px;">
    Adjust your preferences and discover cities that match your lifestyle — 
    powered by real data across affordability, jobs, safety, and more.
</p>
""", unsafe_allow_html=True)

# -------------------------
# Load Data & State
# -------------------------
@st.cache_data
def load_data():
    return pd.read_csv("data/final/Final_Enriched_Dataset.csv")

standardized_indicies_df = load_data()

for key in ["recommendations", "page", "selected_cluster", "user_inputs", "results_df"]:
    if key not in st.session_state:
        st.session_state[key] = None if key != "page" else "home"
        if key == "recommendations":
            st.session_state[key] = []

# -------------------------
# Card UI Helper
# -------------------------
def city_card_html(city):
    name = metro_label(city)
    tag = city.get("tagline") or "A great place to call home."
    score = fmt_score(city.get('recommendation_score'))
    summary = city.get("summary", "No additional details available.")
    
    return f"""<div class="city-card">
<div style="display: flex; justify-content: space-between; align-items: flex-start;">
    <div class="city-name" style="font-weight: 600; font-size: 1.25rem; color: #0f1c1a;">{name}</div>
</div>
<p class="city-desc" style="color: #5a7672; font-size: 0.9rem; margin-top: 4px; margin-bottom: 12px; font-style: italic;">{tag}</p>
<div class="stat-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; font-size: 0.8rem; border-top: 1px solid #eee; padding-top: 10px; margin-bottom: 12px;">
    <span class="stat-item">💰 Affordability: {fmt_score(city.get("affordability_score"))}</span>
    <span class="stat-item">💼 Jobs: {fmt_score(city.get("job_growth_score"))}</span>
    <span class="stat-item">❤️ Health: {fmt_score(city.get("health_score"))}</span>
    <span class="stat-item">🌍 Diversity: {fmt_score(city.get("diversity_score"))}</span>
    <span class="stat-item">🌡️ Climate (Warmth): {fmt_score(city.get("weather_warmth_score"))}</span>
    <span class="stat-item">🌤️ Climate (Mildness): {fmt_score(city.get("weather_mildness_score"))}</span>
    <span class="stat-item">🛡️ Safety: {fmt_score(city.get("safety_score"))}</span>
    <span class="stat-item">🎓 Education: {fmt_score(city.get("education_score"))}</span>
    <span class="stat-item">🚶 Walkability: {fmt_score(city.get("walkability_score"))}</span>
    <span class="stat-item">🏙️ Urban: {fmt_score(city.get("urban_score"))}</span>
</div>
<div style="font-size: 0.85rem; color: #5a7672; margin-bottom: 4px;">
    Match score: <span style="font-weight: 700; color: #1a6b56;">{score}</span> / {SLIDER_MAX:.2f}
</div>
<details style="cursor: pointer; font-size: 0.85rem; color: #1a6b56; border-top: 1px solid #f0f0f0; padding-top: 8px;">
    <summary style="font-weight: 600; margin-bottom: 5px;">📖 About this metro</summary>
    <div style="color: #444; line-height: 1.4; padding: 5px 0;">{summary}</div>
</details>
</div>"""
# -------------------------
# HOME PAGE
# -------------------------
if st.session_state.page == "home":
    col1, col2 = st.columns([1, 4], gap="large")

    with col1:
        st.subheader("🎛 Preferences")
        user_income = st.number_input("Annual Income", min_value=0, value=None)
        search_query = st.text_area("Search keywords (optional)", placeholder="e.g. sunny, tech hub...")
        
        # Sliders
        prefs = {}
        metrics = ["affordability", "safety", "job_growth", "education", "health", 
                   "walkability", "diversity", "urban", "weather_warmth", "weather_mildness"]
        
        for m in metrics:
            prefs[f"{m}_score"] = st.slider(m.replace("_", " ").title(), SLIDER_MIN, SLIDER_MAX, SLIDER_DEFAULT)

        if st.button("Find My City", use_container_width=True):
            st.session_state.show_balloons = True
            user_inputs = round_prefs(prefs)
            results_df = recommender.recommend_cities(
                df=standardized_indicies_df,
                user_inputs=user_inputs,
                user_query=search_query,
                user_income=user_income,
                top_n=15,
            )

            # Add text and convert to dict
            results = recommender.add_text_to_cbsa(results_df).to_dict(orient="records")

            # Persist for reruns
            st.session_state.recommendations = results
            st.session_state.user_inputs = user_inputs
            st.session_state.results_df = results_df

    if st.session_state.get("show_balloons"):
        st.balloons()
        st.session_state.show_balloons = False

    # ----------------- RIGHT PANEL (2×2 charts) -----------------
    with col2:
        if st.session_state.results_df is not None:
            # viz = visualizations.Visualization(st.session_state.user_inputs)
            # st.plotly_chart(viz.plot_radar(st.session_state.results_df), use_container_width=True)
            # st.plotly_chart(viz.plot_map(st.session_state.results_df), use_container_width=True)
            viz = visualizations.Visualization(st.session_state.user_inputs)

            map_color_labels = [lab for lab, _ in visualizations.MAP_COLOR_COLUMN_OPTIONS]
            map_label_to_col = visualizations.MAP_COLOR_LABEL_TO_COLUMN
            map_color_label = st.selectbox(
                "Color map by",
                map_color_labels,
                index=0,
                key="viz_map_color_by",
                help="Cluster: categorical colors. Scores: 0–5 Viridis gradient on the map pane.",
            )
            map_color_col = map_label_to_col[map_color_label]

            row1a, row1b = st.columns(2, gap="medium")
            row2a, row2b = st.columns(2, gap="medium")

            with row1a:
                st.markdown("##### Reccomendation vs Input Radar Chart")
                st.plotly_chart(
                    viz.plot_radar(st.session_state.results_df),
                    use_container_width=True,
                    theme="streamlit",
                )

            with row1b:
                st.markdown("##### Ranked Contributions")
                st.plotly_chart(
                    viz.plot_contributions(st.session_state.results_df),
                    use_container_width=True,
                    theme="streamlit",
                )

            with row2a:
                st.markdown("##### Map")
                st.plotly_chart(
                    viz.plot_map(st.session_state.results_df, color_column=map_color_col),
                    use_container_width=True,
                    theme="streamlit",
                )

            with row2b:
                st.markdown("##### Details")
                st.plotly_chart(
                    viz.plot_table(st.session_state.results_df),
                    use_container_width=True,
                    theme="streamlit",
                )
        else:
            st.info("Adjust the sliders and click 'Find My City' to see your personalized matches.")

    if st.session_state.recommendations:
        top_city = st.session_state.recommendations[0]
        score_val = fmt_score(top_city.get('recommendation_score'))
        city_label = metro_label(top_city)

        st.markdown(
            f"""
    <div style="background-color: #e8f4f1; padding: 1rem; border-radius: 12px; border: 1px solid #c9e6e1; max-width: 500px; margin-bottom: 2rem; display: flex; align-items: center; gap: 15px;">
    <div style="font-size: 1.5rem;">🏆</div>
    <div>
    <h3 style="margin: 0; font-family: 'DM Sans', sans-serif; font-size: 1.1rem; color: #1a6b56; font-weight: 600;">Your Top Match: {city_label}</h3>
    <p style="margin: 2px 0 0; font-family: 'DM Sans', sans-serif; font-size: 0.9rem; color: #5a7672;">
    Match Score: <span style="font-weight: 700; color: #1a6b56;">{score_val}</span> / {SLIDER_MAX:.2f}
    </p>
    </div>
    </div>
    """,
            unsafe_allow_html=True,
        )

    # -------------------------
    # Recommendation Cards
    # -------------------------
    if st.session_state.recommendations:
        st.markdown("---")
        st.markdown('<div class="section-title">Recommended Matches</div>', unsafe_allow_html=True)

        rec = st.session_state.recommendations

        for i in range(0, len(rec), 3):
            cols = st.columns(3)
            for j, city in enumerate(rec[i : i + 3]):
                with cols[j]:
                    # Render the complete card (HTML handles score and summary)
                    st.markdown(city_card_html(city), unsafe_allow_html=True)