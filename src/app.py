#!/usr/bin/env python3
"""
Aquatics Program Analytics — Streamlit UI

HOW TO RUN
----------
From the example_AI/ folder:
    streamlit run src/app.py
"""

import io
import sys
import zipfile
from dataclasses import replace
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

SRC_DIR      = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent
sys.path.insert(0, str(SRC_DIR))

from backend.pool_backend import (
    prepare_datasets,
    make_bar_chart,
    make_stacked_percent_chart,
    PlotStyle,
    Layout,
    INCOME_ORDER,
    ENG_ORDER,
    OUT_PDF,
    OUT_PNG,
)

DEFAULT_STYLE = PlotStyle(
    bar_color="#FA4616", title_color="#FA4616", footer_color="#929191",
    edge_color="black", grid_alpha=0.35, font_title=18, font_axis=11,
    font_tick=12, font_annot=12, legend_font=14, footer_font=10,
)
DEFAULT_LAYOUT = Layout(
    figsize=(10, 6), dpi=300, title_pad=16, ylim_pad=1.19, show_footer=True,
)

def build_style(spec):
    return replace(DEFAULT_STYLE,
        bar_color=spec["bar_color"], font_title=spec["font_title"],
        font_tick=spec["font_tick"], font_annot=spec["font_annot"])

def build_layout(spec):
    return replace(DEFAULT_LAYOUT,
        rotate_x=spec["rotate_x"],
        wrap_width=spec["wrap_width"] if spec.get("wrap_width") else None,
        ylim_pad=spec["ylim_pad"])

def render(spec, df, df_people, people_conv, pathway, org_name, preview=True):
    plt.close("all")
    style  = build_style(spec)
    layout = build_layout(spec)
    key    = spec["key"]
    kw = dict(fname_base=spec["fname_base"], line1=spec["line1"],
               line2=spec["line2"], level_label=spec["level_label"],
               org_name=org_name, style=style, layout=layout, preview=preview)

    if key == "program_mix":
        return make_bar_chart(series=df["ProgramCategory"], use_value_counts=True,
                              ylabel="Number of Enrollments", show_percent=True, **kw)
    elif key == "age_distribution":
        return make_bar_chart(series=df_people["AgeBand"], use_value_counts=True,
                              ylabel="Number of Approx-Unique People", show_percent=True, **kw)
    elif key == "income_buckets":
        inc_order = [b for b in INCOME_ORDER if b in df_people["IncomeBucket"].unique()]
        s = df_people["IncomeBucket"].astype("category").cat.set_categories(inc_order)
        return make_bar_chart(series=s, use_value_counts=True,
                              ylabel="Number of Approx-Unique People", show_percent=True, **kw)
    elif key == "race_composition":
        return make_bar_chart(series=df_people["RaceModel"], use_value_counts=True,
                              ylabel="Number of Approx-Unique People", show_percent=True, **kw)
    elif key == "engagement_frequency":
        eng_series = pd.Categorical(df_people["EngagementBin"].copy(), categories=ENG_ORDER, ordered=True)
        return make_bar_chart(series=eng_series, use_value_counts=True,
                              ylabel="Approx-Unique People", show_percent=True, **kw)
    elif key == "engagement_by_income":
        _dp = df_people.copy()
        _dp["EngagementBin"] = pd.Categorical(_dp["EngagementBin"], categories=ENG_ORDER, ordered=True)
        tab = (pd.crosstab(_dp["IncomeBucket"], _dp["EngagementBin"], normalize="index") * 100)
        tab = tab.reindex([b for b in INCOME_ORDER if b in tab.index])
        tab = tab[[c for c in ENG_ORDER if c in tab.columns]]
        # drop all-zero rows
        tab = tab.loc[(tab > 0).any(axis=1)]
        return make_stacked_percent_chart(table=tab, ylabel="Percent within Income Segment",
                                          legend_title="Total Visits Across the Year", **kw)
    elif key == "engagement_by_race":
        _dp = df_people.copy()
        _dp["EngagementBin"] = pd.Categorical(_dp["EngagementBin"], categories=ENG_ORDER, ordered=True)
        tab = (pd.crosstab(_dp["RaceModel"], _dp["EngagementBin"], normalize="index") * 100)
        tab = tab[[c for c in ENG_ORDER if c in tab.columns]]
        # drop all-zero columns
        tab = tab.loc[:, (tab > 0).any(axis=0)]
        return make_stacked_percent_chart(table=tab, ylabel="Percent within Race Segment",
                                          legend_title="Total Visits Across the Year", **kw)
    elif key == "entry_pathways":
        return make_bar_chart(series=pathway["PathwayType"], use_value_counts=True,
                              ylabel="Approx-Unique People", show_percent=True, **kw)
    elif key == "lesson_by_race":
        tab = (pd.crosstab(people_conv["RaceModel"], people_conv["LessonFlag"], normalize="index") * 100)
        if "Lesson Participant" in tab.columns:
            return make_bar_chart(series=tab["Lesson Participant"].round(1),
                                  use_value_counts=False, value_is_percent=True,
                                  ylabel="Percent Who Ever Took Lessons", show_percent=False, **kw)
    elif key == "lesson_by_income":
        tab = (pd.crosstab(people_conv["IncomeBucket"], people_conv["LessonFlag"], normalize="index") * 100)
        if "Lesson Participant" in tab.columns:
            lr = tab["Lesson Participant"].reindex(
                [b for b in INCOME_ORDER if b in tab.index]).round(1)
            return make_bar_chart(series=lr, use_value_counts=False, value_is_percent=True,
                                  ylabel="Percent Who Ever Took Lessons", show_percent=False, **kw)
    return None

def approved_zip_bytes():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for folder in (OUT_PDF, OUT_PNG):
            for f in sorted(folder.glob("*")):
                zf.write(f, arcname=f"outputs/{folder.name}/{f.name}")
    buf.seek(0)
    return buf.read()

def default_specs():
    b = dict(bar_color="#FA4616", font_title=18, font_tick=12,
             font_annot=12, ylim_pad=1.19, wrap_width=0, approved=False)
    return [
        {**b, "key":"program_mix",          "fname_base":"Figure01_program_mix",
         "line1":"What Brings Families to the Pool?",
         "line2":"Program Mix by Category",           "level_label":"Enrollment-Level", "rotate_x":25},
        {**b, "key":"age_distribution",     "fname_base":"Figure02_age_distribution",
         "line1":"Who Reaches the Pool?",
         "line2":"Participant Age Profile",            "level_label":"Person-Level",     "rotate_x":0},
        {**b, "key":"income_buckets",       "fname_base":"Figure03_income_buckets",
         "line1":"Who Can Afford to Swim?",
         "line2":"Household Income Distribution",      "level_label":"Person-Level",     "rotate_x":0},
        {**b, "key":"race_composition",     "fname_base":"Figure04_race_composition",
         "line1":"Are We Serving a Racially Diverse Community?",
         "line2":"Participant Racial Composition",     "level_label":"Person-Level",     "rotate_x":0},
        {**b, "key":"engagement_frequency", "fname_base":"Figure05_engagement_frequency",
         "line1":"How Often Do Families Return?",
         "line2":"Distribution of Repeat Engagement", "level_label":"Person-Level",     "rotate_x":0},
        {**b, "key":"engagement_by_income", "fname_base":"Figure06_engagement_by_income",
         "line1":"Do Higher-Income Families Engage More Often?",
         "line2":"Repeat Engagement by Household Income","level_label":"Person-Level",  "rotate_x":0},
        {**b, "key":"engagement_by_race",   "fname_base":"Figure07_engagement_by_race",
         "line1":"Does Retention Differ by Race?",
         "line2":"Repeat Engagement by Race Category", "level_label":"Person-Level",    "rotate_x":25},
        {**b, "key":"entry_pathways",       "fname_base":"Figure08_entry_pathways",
         "line1":"How Do Families Move Through the Pool System?",
         "line2":"Entry & Pathways Between Drop-In and Lessons","level_label":"Person-Level","rotate_x":0},
        {**b, "key":"lesson_by_race",       "fname_base":"Figure09_lesson_by_race",
         "line1":"Do All Racial Groups Access Lessons Equally?",
         "line2":"Lesson Access by Race Category",    "level_label":"Person-Level",     "rotate_x":0},
        {**b, "key":"lesson_by_income",     "fname_base":"Figure10_lesson_by_income",
         "line1":"Do Families With Higher Income Access More Lessons?",
         "line2":"Lesson Participation by Household Income","level_label":"Person-Level","rotate_x":0},
    ]

# ── Page config ───────────────────────────────────────────────────────
st.set_page_config(page_title="Aquatics Analytics", page_icon="🏊", layout="wide")
st.title("🏊 Aquatics Program Analytics")
st.caption("Upload your data → review and tune charts → download your report.")

for k, v in {"data_loaded":False,"chart_specs":[],"current_idx":0,
             "org_name":"Aquatics Program","all_approved":False}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════════════════════════════
# STEP 1 — Upload
# ══════════════════════════════════════════════════════════════════════
with st.expander("📂 Step 1 — Upload your data",
                 expanded=not st.session_state["data_loaded"]):
    org_input  = st.text_input("Organisation name", value=st.session_state["org_name"])
    use_sample = st.checkbox("Use the included sample dataset", value=True)
    uploaded   = None if use_sample else st.file_uploader("Upload your CSV", type=["csv"])

    if st.button("Load data", type="primary"):
        try:
            if use_sample:
                path = PROJECT_ROOT / "data" / "PoolDemographics_2025_SAMPLE.csv"
                df, df_people, people_conv, pathway = prepare_datasets(path)
            elif uploaded:
                import tempfile, os
                with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                    tmp.write(uploaded.read()); tmp_path = tmp.name
                df, df_people, people_conv, pathway = prepare_datasets(tmp_path)
                os.unlink(tmp_path)
            else:
                st.error("Please upload a CSV or check 'Use sample dataset'."); st.stop()

            st.session_state.update({"df":df,"df_people":df_people,"people_conv":people_conv,
                "pathway":pathway,"org_name":org_input,"chart_specs":default_specs(),
                "current_idx":0,"data_loaded":True,"all_approved":False})
            st.success(f"Loaded {len(df):,} enrollments → {len(df_people):,} approx. unique people.")
            st.rerun()
        except Exception as e:
            st.error(f"Error loading data: {e}")

# ══════════════════════════════════════════════════════════════════════
# STEP 2 — Review charts
# ══════════════════════════════════════════════════════════════════════
if st.session_state["data_loaded"] and not st.session_state["all_approved"]:
    st.divider()
    st.header("📊 Step 2 — Review standard report charts")

    specs = st.session_state["chart_specs"]
    idx   = st.session_state["current_idx"]
    spec  = specs[idx]
    total = len(specs)
    n_done = sum(1 for s in specs if s["approved"])

    st.progress(n_done / total, text=f"{n_done} of {total} charts approved")

    if not all(s["approved"] for s in specs):
        if st.button("✅ Approve all & download", type="primary"):
            for s in specs:
                render(s, st.session_state["df"], st.session_state["df_people"],
                       st.session_state["people_conv"], st.session_state["pathway"],
                       st.session_state["org_name"], preview=False)
                s["approved"] = True
            st.session_state["all_approved"] = True
            st.rerun()

    nav_cols = st.columns(total)
    for i, s in enumerate(specs):
        if nav_cols[i].button("✅" if s["approved"] else str(i+1),
                               key=f"nav_{i}", use_container_width=True):
            st.session_state["current_idx"] = i
            st.rerun()

    st.subheader(f"Chart {idx+1} of {total}  —  {spec['line2']}")

    with st.sidebar:
        st.header("🎨 Visual settings")
        st.caption(f"Chart {idx+1}: **{spec['line2']}**")
        spec["line1"]      = st.text_input("Title (line 1)",     value=spec["line1"],      key=f"l1_{idx}")
        spec["line2"]      = st.text_input("Subtitle (line 2)",  value=spec["line2"],      key=f"l2_{idx}")
        spec["bar_color"]  = st.color_picker("Bar color",        value=spec["bar_color"],  key=f"bc_{idx}")
        spec["rotate_x"]   = st.select_slider("X-axis label rotation", options=[0,15,25,35,45],
                                               value=spec["rotate_x"], key=f"rx_{idx}")
        ww = st.slider("Word-wrap labels (chars, 0=off)", 0, 30,
                       value=spec.get("wrap_width") or 0, key=f"ww_{idx}")
        spec["wrap_width"] = ww
        spec["font_title"] = st.slider("Title font size",      10, 28, spec["font_title"], key=f"ft_{idx}")
        spec["font_tick"]  = st.slider("Tick label font size",  6, 20, spec["font_tick"],  key=f"fk_{idx}")
        spec["font_annot"] = st.slider("Bar annotation size",   6, 20, spec["font_annot"], key=f"fa_{idx}")
        spec["ylim_pad"]   = st.slider("Top headroom",       1.05, 1.50, spec["ylim_pad"],
                                       step=0.01, key=f"yp_{idx}")

    with st.spinner("Rendering..."):
        try:
            img = render(spec, st.session_state["df"], st.session_state["df_people"],
                         st.session_state["people_conv"], st.session_state["pathway"],
                         st.session_state["org_name"], preview=True)
            if img:
                st.image(img, use_container_width=True)
            else:
                st.warning("No data available for this chart.")
        except Exception as e:
            st.error(f"Render error: {e}")

    col_prev, col_approve, col_next = st.columns([1, 2, 1])

    with col_prev:
        if idx > 0 and st.button("← Previous", use_container_width=True):
            st.session_state["current_idx"] = idx - 1; st.rerun()

    with col_approve:
        if spec["approved"]:
            if st.button("✅ Approved — click to un-approve", use_container_width=True):
                spec["approved"] = False; st.rerun()
        else:
            if st.button("✅ Approve this chart", type="primary", use_container_width=True):
                render(spec, st.session_state["df"], st.session_state["df_people"],
                       st.session_state["people_conv"], st.session_state["pathway"],
                       st.session_state["org_name"], preview=False)
                spec["approved"] = True
                if all(s["approved"] for s in specs):
                    st.session_state["all_approved"] = True
                elif idx < total - 1:
                    st.session_state["current_idx"] = idx + 1
                st.rerun()

    with col_next:
        if idx < total - 1 and st.button("Next →", use_container_width=True):
            st.session_state["current_idx"] = idx + 1; st.rerun()

# ══════════════════════════════════════════════════════════════════════
# STEP 3 — Download + custom builder
# ══════════════════════════════════════════════════════════════════════
if st.session_state.get("all_approved"):
    st.divider()
    st.header("✅ All 10 charts approved!")
    st.download_button("⬇️ Download all charts (.zip)", data=approved_zip_bytes(),
                       file_name="aquatics_report_charts.zip",
                       mime="application/zip", type="primary")

    st.divider()
    st.header("🛠️ Custom chart builder")
    st.caption("Pick any column, set your titles, tweak visuals, and generate a one-off chart.")

    df_people = st.session_state["df_people"]
    df        = st.session_state["df"]
    exclude   = {"PersonKey","POC","LowIncome","IsYouth","Female","HighEng",
               "HouseIncomeRaw","HouseIncome","ProgramGroup","YouthAdult",
               "ProgramCategory","Program", "Age", "GenderClean", "Race"}
    data_level  = st.radio("Data level", ["Person-level","Enrollment-level"], horizontal=True)
    src         = df_people if data_level == "Person-level" else df
    col_options = [c for c in src.columns if c not in exclude]
    chosen_col  = st.selectbox("Column to chart", col_options)

    c1, c2 = st.columns(2)
    with c1:
        cl1 = st.text_input("Title (line 1)", value=f"{chosen_col} breakdown")
        cl2 = st.text_input("Subtitle (line 2)", value="")
    with c2:
        cc  = st.color_picker("Bar color", "#FA4616", key="cc")
        crx = st.select_slider("X-label rotation", [0,15,25,35,45], value=0, key="crx")
        cww = st.slider("Word-wrap (0=off)", 0, 30, 0, key="cww")
        cft = st.slider("Title font", 10, 28, 18, key="cft")
        ctk = st.slider("Tick font",   6, 20, 12, key="ctk")
        cfa = st.slider("Annot font",  6, 20, 12, key="cfa")
        cyp = st.slider("Top headroom", 1.05, 1.50, 1.19, step=0.01, key="cyp")

    if st.button("Generate chart", type="primary"):
        try:
            fname        = f"Custom_{chosen_col.replace(' ','_')}"
            cstyle       = replace(DEFAULT_STYLE, bar_color=cc, font_title=cft,
                                   font_tick=ctk, font_annot=cfa)
            clayout      = replace(DEFAULT_LAYOUT, rotate_x=crx,
                                   wrap_width=cww or None, ylim_pad=cyp)
            shared = dict(fname_base=fname, line1=cl1, line2=cl2,
                          level_label=data_level, org_name=st.session_state["org_name"],
                          use_value_counts=True, style=cstyle, layout=clayout,
                          ylabel="Count", show_percent=True)

            img = make_bar_chart(series=src[chosen_col], preview=True,  **shared)
            if img:
                st.image(img, use_container_width=True)
                make_bar_chart(series=src[chosen_col], preview=False, **shared)
                dl1, dl2 = st.columns(2)
                if (OUT_PNG / f"{fname}.png").exists():
                    dl1.download_button("⬇️ PNG", (OUT_PNG/f"{fname}.png").read_bytes(),
                                        file_name=f"{fname}.png", mime="image/png")
                if (OUT_PDF / f"{fname}.pdf").exists():
                    dl2.download_button("⬇️ PDF", (OUT_PDF/f"{fname}.pdf").read_bytes(),
                                        file_name=f"{fname}.pdf", mime="application/pdf")
        except Exception as e:
            st.error(f"Could not generate chart: {e}")
