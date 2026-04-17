import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# (selectbox label, dataframe column) for map coloring
MAP_COLOR_COLUMN_OPTIONS: list[tuple[str, str]] = [
    ("Cluster", "cluster_label"),
    ("Sub-Cluster", "cluster_sub_label"),
    ("Recommendation score", "recommendation_score"),
    ("Affordability", "affordability_score"),
    ("Job Growth", "job_growth_score"),
    ("Safety", "safety_score"),
    ("Education", "education_score"),
    ("Health", "health_score"),
    ("Walkability", "walkability_score"),
    ("Diversity", "diversity_score"),
    ("Urban", "urban_score"),
    ("Warmth", "weather_warmth_score"),
    ("Mildness", "weather_mildness_score"),
]

MAP_COLOR_LABEL_TO_COLUMN: dict[str, str] = dict(MAP_COLOR_COLUMN_OPTIONS)
MAP_COLUMN_TO_LABEL: dict[str, str] = {col: lab for lab, col in MAP_COLOR_COLUMN_OPTIONS}

# Detail table column order (matches app wording: … health before safety …)
TABLE_DETAIL_SCORE_COLS: tuple[str, ...] = (
    "affordability_score",
    "job_growth_score",
    "health_score",
    "safety_score",
    "education_score",
    "walkability_score",
    "diversity_score",
    "urban_score",
    "weather_warmth_score",
    "weather_mildness_score",
)

MAP_SCORE_GRADIENT_COLUMNS: frozenset = frozenset(
    {
        "affordability_score",
        "job_growth_score",
        "safety_score",
        "education_score",
        "health_score",
        "walkability_score",
        "diversity_score",
        "urban_score",
        "weather_warmth_score",
        "weather_mildness_score",
        "recommendation_score",
    }
)


class Visualization:
    def __init__(self, user_inputs):
        # Same 0–5 scale as sliders and `recommend_cities` output
        self.user_inputs_scaled = {k: round(float(v), 2) for k, v in user_inputs.items()}
        self.RADAR_COLS = list(self.user_inputs_scaled.keys())
        self.BASE_FONT_SIZE = 12
        self.CHART_FONT_SIZE = self.BASE_FONT_SIZE + 2

        self.DISPLAY_LABELS = {
            "affordability_score": "Affordability",
            "job_growth_score": "Job Growth",
            "safety_score": "Safety",
            "education_score": "Education",
            "health_score": "Health",
            "walkability_score": "Walkability",
            "diversity_score": "Diversity",
            "urban_score": "Urban",
            "weather_warmth_score": "Warmth",
            "weather_mildness_score": "Mildness",
        }

    def apply_chart_theme(self, fig):
        fig.update_layout(
            font=dict(size=self.CHART_FONT_SIZE),
            paper_bgcolor="#ffffff",
            plot_bgcolor="#ffffff",
        )
        return fig

    def round_df_numeric(self, df_in, decimals=2):
        df_out = df_in.copy()
        numeric_cols = df_out.select_dtypes(include=[np.number]).columns
        df_out[numeric_cols] = df_out[numeric_cols].round(decimals)
        return df_out

    def apply_geo_theme(self, fig):
        fig.update_geos(
            scope="usa",

            bgcolor="#ffffff",
        
            showland=False,
            showocean=False,
        
            showcountries=False,
        
            showsubunits=True,                
            subunitcolor="rgba(15,23,42,0.25)",
            subunitwidth=1,
        
            showcoastlines=False,
            showframe=False,
        )
    
        fig.update_layout(
            paper_bgcolor="#ffffff",
            plot_bgcolor="#ffffff",
            margin=dict(l=0, r=0, t=0, b=0),
        )
    
        return self.apply_chart_theme(fig)

    def prepare_plot_df(self, df):
        df = df.copy()
        df["city_state"] = df["city"].astype(str) + ", " + df["state"].astype(str)

        df["cluster_final_name"] = df["cluster_final_name"].fillna("").astype(str).str.strip().replace("", "—")
        df["sub_cluster_text"] = df["sub_cluster_text"].fillna("").astype(str).str.strip().replace("", "—")

        # UI aliases: K=5 final cluster name + concise sub-cluster text.
        df["cluster_label"] = df["cluster_final_name"]
        df["cluster_sub_label"] = df["sub_cluster_text"]

        return self.round_df_numeric(df, 2)


    def get_top_n(self, df, n=25):
        return df.sort_values("recommendation_score", ascending=False).head(n).copy()

    def plot_radar(self, df, rank: int = 1):
        df = self.prepare_plot_df(df)
        ranked_df = df.sort_values("recommendation_score", ascending=False).reset_index(drop=True)
        safe_rank = max(1, min(int(rank), len(ranked_df)))
        row = ranked_df.iloc[safe_rank - 1]

        categories = [self.DISPLAY_LABELS[c] for c in self.RADAR_COLS]
        user_vals = [round(self.user_inputs_scaled[c], 2) for c in self.RADAR_COLS]
        city_vals = [round(row[c], 2) for c in self.RADAR_COLS]

        categories += [categories[0]]
        user_vals += [user_vals[0]]
        city_vals += [city_vals[0]]

        ht = "<b>%{fullData.name}</b><br>%{theta}: %{r:.2f}<extra></extra>"
        # Color-blind-friendly (Okabe-Ito inspired): blue (city) vs vermillion (user)
        city_line, city_fill = "#0072B2", "rgba(0,114,178,0.22)"
        user_line, user_fill = "#D55E00", "rgba(213,94,0,0.18)"
        fig = go.Figure()
        fig.add_trace(
            go.Scatterpolar(
                r=city_vals,
                theta=categories,
                fill="toself",
                name=row["city_state"],
                hovertemplate=ht,
                line=dict(color=city_line, width=3.5),
                fillcolor=city_fill,
                marker=dict(color=city_line, size=11, line=dict(color="#0f172a", width=1.5)),
            )
        )
        fig.add_trace(
            go.Scatterpolar(
                r=user_vals,
                theta=categories,
                fill="toself",
                name="User preferences",
                hovertemplate=ht,
                line=dict(color=user_line, width=3.5, dash="dash"),
                fillcolor=user_fill,
                marker=dict(color=user_line, size=11, line=dict(color="#7f3b08", width=1.5)),
            )
        )
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    range=[0, 5],
                    tickformat=".2f",
                    gridcolor="rgba(15,23,42,0.12)",
                    tickfont=dict(size=self.CHART_FONT_SIZE),
                ),
                angularaxis=dict(
                    linecolor="rgba(15,23,42,0.25)",
                    gridcolor="rgba(15,23,42,0.08)",
                    tickfont=dict(size=self.CHART_FONT_SIZE),
                ),
                bgcolor="#ffffff",
            ),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            paper_bgcolor="#ffffff",
            plot_bgcolor="#ffffff",
        )
        return self.apply_chart_theme(fig)

    def plot_contributions(self, df, top_n=1):
        df = self.prepare_plot_df(df)
        row = self.get_top_n(df, top_n).iloc[0]
    
        data = []
    
        for col in self.RADAR_COLS:
            city_val = row[col]
            user_val = self.user_inputs_scaled[col]
    
            # Convert to similarity score (0–1)
            gap = abs(city_val - user_val)
            match_score = max(0.0, 1.0 - gap / 5.0)
    
            data.append({
                "feature": self.DISPLAY_LABELS[col],
                "match_score": round(match_score, 3),
                "city_value": city_val,
                "user_value": user_val,
            })
    
        cdf = pd.DataFrame(data).sort_values("match_score", ascending=True)
    
        import plotly.express as px
    
        fig = px.bar(
            cdf,
            x="match_score",
            y="feature",
            orientation="h",
            color="match_score",
            color_continuous_scale="RdYlBu",
            range_color=(0, 1),
        )
    
        fig.update_layout(
            title="",
            xaxis_title="Match Score (0 = poor fit, 1 = perfect fit)",
            yaxis_title=None,
            coloraxis_showscale=False,
            paper_bgcolor="#ffffff",
            plot_bgcolor="#ffffff",
        )
    
        fig.update_traces(
            hovertemplate="<b>%{y}</b><br>Match: %{x:.2f}<br>"
                          "City: %{customdata[0]:.2f}<br>"
                          "You: %{customdata[1]:.2f}<extra></extra>",
            customdata=cdf[["city_value", "user_value"]].values,
        )
    
        return self.apply_chart_theme(fig)

    def plot_map(self, df, color_column: str = "cluster_label"):
        df = self.prepare_plot_df(df)
        top = self.get_top_n(df, 5)

        map_marker_px = 9
        star_marker_px = max(2, map_marker_px - 2)

        col = color_column if color_column in df.columns else "cluster_label"
        categorical_cluster_cols = {"cluster_label", "cluster_sub_label", "cluster_text", "sub_cluster_text"}
        is_cluster = col in categorical_cluster_cols

        if is_cluster:
            fig = px.scatter_geo(
                df,
                lat="centroid_lat",
                lon="centroid_lon",
                color=col,
                hover_name="city_state",
                scope="usa",
                color_discrete_sequence=px.colors.qualitative.Safe,
            )
        else:
            series = pd.to_numeric(df[col], errors="coerce")
            if col in MAP_SCORE_GRADIENT_COLUMNS:
                rng: tuple[float, float] | list[float] = (0.0, 5.0)
            else:
                lo = float(np.nanmin(series.to_numpy()))
                hi = float(np.nanmax(series.to_numpy()))
                if not np.isfinite(lo) or not np.isfinite(hi):
                    lo, hi = 0.0, 1.0
                if hi <= lo:
                    hi = lo + 1e-6
                rng = (lo, hi)

            fig = px.scatter_geo(
                df,
                lat="centroid_lat",
                lon="centroid_lon",
                color=series,
                hover_name="city_state",
                color_continuous_scale="Cividis",
                range_color=rng,
                scope="usa",
            )
            fig.update_layout(
                coloraxis_colorbar=dict(
                    title=MAP_COLUMN_TO_LABEL.get(col, col),
                    tickformat=".2f",
                ),
                geo=dict(
                    scope="usa",
                    bgcolor="#ffffff",
                
                    showland=False,  
                    showocean=False,
                
                    showcountries=False,
                
                    showsubunits=True,             
                    subunitcolor="rgba(15,23,42,0.25)", 
                    subunitwidth=1,
                
                    showcoastlines=False,
                    showframe=False,
                ),

                paper_bgcolor="#ffffff",
                plot_bgcolor="#ffffff",
                            
            )

        fig.update_traces(hovertemplate="<b>%{hovertext}</b><extra></extra>")

        fig.add_trace(
            go.Scattergeo(
                lat=top["centroid_lat"],
                lon=top["centroid_lon"],
                text=top["city_state"],
                mode="markers+text",
                marker=dict(size=star_marker_px, symbol="star", color="#E69F00", line=dict(width=0.6, color="#292524")),
                textfont=dict(color="#020617", size=self.CHART_FONT_SIZE, family="system-ui, sans-serif"),
                textposition="top center",
                name="Top picks",
                customdata=np.stack([top["city_state"]], axis=-1),
                hovertemplate="<b>%{customdata[0]}</b><extra></extra>",
            )
        )

        # px maps `size` through sizeref; pin marker pixel size to match scattergeo `marker.size` (10).
        for tr in fig.data:
            if getattr(tr, "name", None) != "Top picks":
                tr.marker.size = map_marker_px

        return self.apply_geo_theme(fig)

