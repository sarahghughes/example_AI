#!/usr/bin/env python3
"""
Aquatics Program Analytics — backend library

Provides:
  - prepare_datasets(csv_path)         : cleans raw CSV → analysis-ready dataframes
  - make_bar_chart(...)                : single-color bar chart → PDF + PNG
  - make_stacked_percent_chart(...)    : stacked 100% bar chart → PDF + PNG
  - PlotStyle / Layout                 : dataclasses for visual configuration

Output folders (auto-created relative to project root):
  outputs/pdf/   — vector PDFs for print and grant submissions
  outputs/png/   — 300 DPI PNGs for slides, email, and web
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Union
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# -----------------------------------------------------------------------
# Paths  (backend lives at src/backend/, project root is two levels up)
# -----------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR  = PROJECT_ROOT / "outputs"
OUT_PDF  = OUT_DIR / "pdf"
OUT_PNG  = OUT_DIR / "png"
for _d in (OUT_PDF, OUT_PNG):
    _d.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------
INCOME_ORDER = ["Under $40,000", "$40,000–79,999", "$80,000+", "Not reported"]
ENG_ORDER    = ["1 visit", "2 visits", "3 visits", "4–6 visits", "7–10 visits", "10+ visits"]
AGE_BINS     = [-np.inf, 4, 9, 14, 19, 29, 44, 64, np.inf]
AGE_LABELS   = ["0–4", "5–9", "10–14", "15–19", "20–29", "30–44", "45–64", "65+"]

# -----------------------------------------------------------------------
# Styling dataclasses
# -----------------------------------------------------------------------
@dataclass
class PlotStyle:
    bar_color:        str   = "#FA4616"   # primary bar fill (brand orange)
    edge_color:       str   = "black"     # bar outline
    grid_alpha:       float = 0.35        # y-grid transparency (0=none, 1=solid)
    title_color:      str   = "#FA4616"   # chart title color
    font_title:       int   = 18          # title font size (pts)
    font_axis:        int   = 11          # axis label font size
    font_tick:        int   = 12          # tick label font size
    font_annot:       int   = 12          # bar annotation font size
    legend_font:      int   = 14          # legend item font size
    legend_title_font:int   = 12          # legend title font size
    footer_font:      int   = 10          # footer font size
    footer_color:     str   = "#929191"   # footer text color (grey)

@dataclass
class Layout:
    figsize:       Tuple[float, float] = (10, 6)   # figure size in inches (width, height)
    fig_scale:     float               = 1.00       # multiplier applied to figsize
    dpi:           int                 = 300        # output resolution

    title_pad:     float               = 16.0       # space between title and chart

    # Footer
    show_footer:      bool  = True
    footer_x:         float = 0.995
    footer_y:         float = 0.02
    footer_reserved:  float = 0.1     # fraction of figure height held for footer
    use_footer_slot:  bool  = True    # reserve a GridSpec row for the footer

    # X-axis tick labels
    rotate_x:                    Optional[int] = 0
    wrap_width:                  Optional[int] = None   # word-wrap tick labels at N chars
    truncate_after:              Optional[int] = None   # truncate tick labels at N chars
    tick_align_right_when_rotated: bool        = True

    # Y-axis limits
    ylim:     Optional[Tuple[float, float]] = None
    ylim_pad: float                         = 1.19   # auto-ceiling = max * ylim_pad

    # Legend (stacked charts)
    legend_outside:       bool               = True
    legend_loc:           str                = "upper left"
    legend_bbox_to_anchor:Tuple[float, float]= (1.02, 1.0)

    # Layout engine
    use_constrained_layout:  bool = True
    suppress_tight_warnings: bool = True
    bbox_tight:              bool = True

    # Manual margins — only used when use_constrained_layout=False
    margin_left:   Optional[float] = None
    margin_right:  Optional[float] = None
    margin_bottom: Optional[float] = None
    margin_top:    Optional[float] = None

# -----------------------------------------------------------------------
# CSV loader
# -----------------------------------------------------------------------
def _read_csv_robust(path: Union[str, Path]) -> pd.DataFrame:
    path = Path(path)
    try:
        return pd.read_csv(path)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin-1")

# -----------------------------------------------------------------------
# Cleaning helpers
# -----------------------------------------------------------------------
def standardize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.replace({"\xa0": " ", "\u202f": " "}, regex=True, inplace=True)
    df.columns = [c.strip() for c in df.columns]
    for c in df.columns:
        if df[c].dtype == "object":
            df[c] = (
                df[c].astype(str)
                .str.replace(r"\s+", " ", regex=True)
                .str.strip()
                .replace({"nan": np.nan, "None": np.nan})
            )
    return df

def clean_gender(x: str) -> Optional[str]:
    if pd.isna(x): return np.nan
    s = str(x).lower()
    if "female" in s: return "Female"
    if "male"   in s: return "Male"
    if "non"    in s: return "Non-binary"
    return np.nan

def clean_income_raw(x: str) -> Optional[str]:
    if pd.isna(x) or x == "": return np.nan
    s = str(x).replace(" ", "")
    if s.startswith("<"): return "$0-10,000"
    return str(x)

def income_bucket(h: str) -> str:
    if pd.isna(h): return "Not reported"
    low  = {"$0-10,000", "$10,001-20,000", "$20,001-30,000", "$30,001-40,000"}
    mid  = {"$40,001-50,000", "$50,001-60,000", "$60,001-70,000", "$70,001-80,000"}
    high = {"$80,001-90,000", "$90,001+"}
    if h in low:  return "Under $40,000"
    if h in mid:  return "$40,000–79,999"
    if h in high: return "$80,000+"
    return "Not reported"

def map_program_category(name: str) -> str:
    if pd.isna(name): return "Other / Unclassified"
    s = str(name).lower().strip()
    if s.startswith("family swim"):                                           return "Family Swim (Drop-In)"
    if "single gender swim" in s or "sgs" in s:                              return "Single Gender Swim"
    if "companion" in s:                                                      return "Swim Lessons — Companion"
    if "parent & child" in s or "parent and child" in s:                     return "Swim Lessons — Parent & Child"
    if "prek" in s:                                                           return "Swim Lessons — PreK"
    if "childcare" in s:                                                      return "Swim Lessons — Childcare"
    if "adult" in s:                                                          return "Swim Lessons — Adult"
    if any(l in s for l in ["level 1","level 2","level 3","level 4","level 5"]): return "Swim Lessons — Youth Levels"
    return "Other / Unclassified"

def map_race_clean(x: str) -> str:
    if pd.isna(x) or x == "": return "Some other race (write-in)"
    s = str(x).lower()
    if "white/european" in s or ("white" in s and "european" in s): return "White"
    if "black" in s or "african-american" in s or "african american" in s:   return "Black or African American"
    if "asian" in s:                                                          return "Asian"
    if "hispanic" in s or "latino" in s or "latinx" in s:                   return "Hispanic or Latino"
    if "middle eastern" in s or "north african" in s:                        return "Middle Eastern / North African"
    if any(t in s for t in ["american indian","alaskan","native american",
                             "native hawaiian","pacific islander","first nations"]):
        return "American Indian / Alaska Native / Native Hawaiian / Pacific Islander"
    if "multiracial" in s or "two or more" in s:                             return "Two or more races"
    return "Some other race (write-in)"

def collapse_race_for_model(races: pd.Series) -> str:
    uniq = set(races.dropna())
    if len(uniq) == 0:                          return "Other / Small N"
    if "Black or African American"  in uniq:    return "Black"
    if "Hispanic or Latino"         in uniq:    return "Hispanic or Latino"
    if "Asian"                      in uniq:    return "Asian"
    if "White"                      in uniq:    return "White"
    return "Other / Small N"

def engagement_bin(n: int) -> str:
    if n == 1:          return "1 visit"
    if n == 2:          return "2 visits"
    if n == 3:          return "3 visits"
    if 4  <= n <= 6:    return "4–6 visits"
    if 7  <= n <= 10:   return "7–10 visits"
    return "10+ visits"

def classify_pathway(first_group: str, ever_lessons: bool) -> str:
    if first_group != "Family Swim (Drop-In)" and ever_lessons:  return "Entered via Lessons"
    if first_group == "Family Swim (Drop-In)" and ever_lessons:  return "Converted from Family Swim"
    if first_group == "Family Swim (Drop-In)" and not ever_lessons: return "Stayed Family Swim Only"
    return "Lessons Only (never drop-in)"

# -----------------------------------------------------------------------
# Label utilities
# -----------------------------------------------------------------------
def shorten_labels(
    labels:         Iterable[str],
    mapping:        Optional[Dict[str, str]] = None,
    truncate_after: Optional[int]            = None,
    wrap_width:     Optional[int]            = None,
) -> List[str]:
    """Apply optional mapping, truncation, and word-wrap to a list of labels."""
    def _wrap(s: str, width: int) -> str:
        if not width or width <= 0: return s
        words = s.split()
        lines, line, curr = [], [], 0
        for w in words:
            add = (1 if line else 0) + len(w)
            if curr + add > width:
                lines.append(" ".join(line)); line = [w]; curr = len(w)
            else:
                line.append(w); curr += add
        if line: lines.append(" ".join(line))
        return "\n".join(lines)

    out = []
    for lbl in labels:
        s = str(lbl)
        if mapping and s in mapping:
            s = mapping[s]
        if truncate_after and len(s) > truncate_after:
            s = s[:truncate_after - 1] + "…"
        s = _wrap(s, wrap_width) if wrap_width else s
        out.append(s)
    return out

def _auto_ylim(max_height: float, pad: float) -> float:
    return max_height * (pad if pad > 1.0 else 1.0 + pad)

# -----------------------------------------------------------------------
# Data preparation
# -----------------------------------------------------------------------
def prepare_datasets(csv_path: Union[str, Path]):
    """
    Load and clean the raw registration CSV.

    Returns
    -------
    df          : enrollment-level DataFrame (one row per registration)
    df_people   : person-level DataFrame (approx. deduplicated participants)
    people_conv : person-level + LessonFlag column
    pathway     : per-person pathway type (Drop-In → Lessons conversion etc.)
    """
    df = standardize_dataframe(_read_csv_robust(csv_path))

    if "House income" in df.columns:
        df = df.rename(columns={"House income": "HouseIncomeRaw"})

    df["Age"]       = pd.to_numeric(df.get("Age"),       errors="coerce")
    df["Household"] = pd.to_numeric(df.get("Household"), errors="coerce")
    df["GenderClean"] = df.get("Gender", pd.Series([np.nan]*len(df))).apply(clean_gender)

    df["HouseIncome"] = df.get("HouseIncomeRaw", pd.Series([np.nan]*len(df))).apply(clean_income_raw)
    income_order_detail = [
        "$0-10,000","$10,001-20,000","$20,001-30,000","$30,001-40,000",
        "$40,001-50,000","$50,001-60,000","$60,001-70,000","$70,001-80,000",
        "$80,001-90,000","$90,001+",
    ]
    df["HouseIncome"]   = pd.Categorical(df["HouseIncome"], categories=income_order_detail, ordered=True)
    df["IncomeBucket"]  = df["HouseIncome"].apply(income_bucket)
    df["ProgramCategory"] = df.get("Program", pd.Series([""]*len(df))).apply(map_program_category)
    df["ProgramGroup"]  = np.where(df["ProgramCategory"] == "Family Swim (Drop-In)",
                                   "Family Swim (Drop-In)", "Swim Lessons (All)")
    df["AgeBand"]       = pd.cut(df["Age"], bins=AGE_BINS, labels=AGE_LABELS, right=True)
    df["YouthAdult"]    = pd.NA
    df.loc[df["Age"] <= 17, "YouthAdult"] = "Youth (0–17)"
    df.loc[df["Age"] >= 18, "YouthAdult"] = "Adults (18+)"

    # Race: split comma-separated selections, clean each, collapse to one model label
    race_long = df[["Race"]].copy()
    race_long["Race"] = race_long["Race"].fillna("").astype(str).str.split(",")
    race_long = race_long.explode("Race")
    race_long["Race"] = race_long["Race"].str.replace(r"\s+", " ", regex=True).str.strip()
    race_long = race_long[race_long["Race"] != ""]
    race_long["RaceClean"] = race_long["Race"].apply(map_race_clean)
    df["RaceModel"] = (race_long.groupby(race_long.index)["RaceClean"]
                                .apply(collapse_race_for_model)
                                .reindex(df.index))

    # Person deduplication
    person_cols   = ["Age", "GenderClean", "RaceModel", "Household"]
    df["PersonKey"] = df[person_cols].astype(str).agg("|".join, axis=1)
    dup_counts    = df["PersonKey"].value_counts()
    df_people     = df.drop_duplicates(subset="PersonKey").copy()
    df_people["EngagementBin"] = df_people["PersonKey"].map(
        lambda k: engagement_bin(dup_counts.get(k, 1))
    )

    # Convenience indicator columns
    df_people["POC"]       = df_people["RaceModel"].ne("White").astype(int)
    df_people["LowIncome"] = df_people["IncomeBucket"].eq("Under $40,000").astype(int)
    df_people["IsYouth"]   = df_people["YouthAdult"].eq("Youth (0–17)").astype(int)
    df_people["Female"]    = df_people["GenderClean"].eq("Female").astype(int)
    df_people["HighEng"]   = df_people["EngagementBin"].isin(
        {"4–6 visits","7–10 visits","10+ visits"}).astype(int)

    # Lesson conversion flag
    conv_lookup = df.groupby("PersonKey")["ProgramGroup"].apply(
        lambda g: "Lesson Participant" if (g == "Swim Lessons (All)").any() else "Family Swim Only"
    )
    people_conv = df_people.copy()
    people_conv["LessonFlag"]        = people_conv["PersonKey"].map(conv_lookup)
    people_conv["LessonParticipant"] = people_conv["LessonFlag"].eq("Lesson Participant").astype(int)

    # Pathway classification
    df_sorted   = df.sort_index()
    first_touch = df_sorted.groupby("PersonKey")["ProgramGroup"].first()
    ever_lessons= df_sorted.groupby("PersonKey")["ProgramGroup"].apply(
        lambda g: (g == "Swim Lessons (All)").any()
    )
    pathway = pd.DataFrame({"FirstGroup": first_touch, "EverLessons": ever_lessons})
    pathway["PathwayType"] = pathway.apply(
        lambda r: classify_pathway(r["FirstGroup"], r["EverLessons"]), axis=1
    )

    return df, df_people, people_conv, pathway

# -----------------------------------------------------------------------
# Save helper — PDF + PNG (300 DPI)
# preview=True  → skip disk writes, return PNG bytes instead (for Streamlit)
# preview=False → save to outputs/ as usual and return None
# -----------------------------------------------------------------------
def _save_fig(fig, fname_base: str, layout: Layout, preview: bool = False):
    import io as _io
    if not layout.use_constrained_layout:
        if all(v is not None for v in [layout.margin_left, layout.margin_right,
                                        layout.margin_bottom, layout.margin_top]):
            fig.subplots_adjust(
                left   = layout.margin_left,
                right  = 1 - layout.margin_right,
                bottom = layout.margin_bottom,
                top    = layout.margin_top,
            )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            plt.tight_layout()

    bbox = "tight" if layout.bbox_tight else None

    if preview:
        buf = _io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches=bbox)
        plt.close(fig)
        buf.seek(0)
        return buf.read()
    else:
        fig.savefig(OUT_PDF / f"{fname_base}.pdf", dpi=layout.dpi, bbox_inches=bbox)
        fig.savefig(OUT_PNG / f"{fname_base}.png", dpi=layout.dpi, bbox_inches=bbox)
        plt.close(fig)
        return None

# -----------------------------------------------------------------------
# Footer & title helpers
# -----------------------------------------------------------------------
def _footer(fig, org_name: str, level: str, x: float, y: float, style: PlotStyle) -> None:
    line1 = f"Source: {org_name} pool programs (2025)."
    line2  = ("Approx. unique participants (person-level)."
               if level == "people" else "Enrollment-level (all sign-ups).")
    fig.text(x, y, f"{line1}\n{line2}",
             ha="right", va="bottom",
             fontsize=style.footer_font, color=style.footer_color)

def _title(ax, line1: str, line2: str, level_label: str,
           org_name: str, color: str, size: int, pad: float) -> None:
    ax.set_title(
        f"{line1}\n{line2}\n{org_name} Pool Programs, 2025 — {level_label}",
        fontsize=size, fontweight="bold", color=color, pad=pad
    )

# -----------------------------------------------------------------------
# Figure factory (reserves footer slot in GridSpec)
# -----------------------------------------------------------------------
def _make_fig_axes(layout: Layout):
    fig_w = layout.figsize[0] * layout.fig_scale
    fig_h = layout.figsize[1] * layout.fig_scale

    if layout.use_constrained_layout and layout.use_footer_slot and layout.footer_reserved > 0:
        fig = plt.figure(figsize=(fig_w, fig_h), constrained_layout=True)
        footer_weight = max(0.01, min(0.3, layout.footer_reserved))
        gs  = fig.add_gridspec(nrows=2, ncols=1, height_ratios=[1.0, footer_weight])
        ax  = fig.add_subplot(gs[0, 0])
        ax_footer = fig.add_subplot(gs[1, 0])
        ax_footer.axis("off")
        return fig, ax
    else:
        fig, ax = plt.subplots(figsize=(fig_w, fig_h),
                               constrained_layout=layout.use_constrained_layout)
        return fig, ax

# -----------------------------------------------------------------------
# Bar chart
# -----------------------------------------------------------------------
def make_bar_chart(
    series:          Union[pd.Series, pd.Index, List, Dict],
    fname_base:      str,
    line1:           str,
    line2:           str,
    level_label:     str,
    org_name:        str   = "Aquatics Program",
    *,
    use_value_counts:bool  = True,
    value_is_percent: bool = False,
    style:           PlotStyle = PlotStyle(),
    layout:          Layout    = Layout(),
    ylabel:          str   = "Number of People",
    show_percent:    bool  = True,
    show_values:     bool  = True,
    annot_offset:    float = 6.0,
    label_map:       Optional[Dict[str, str]] = None,
    preview:         bool  = False,
):
    # Build counts/heights
    if isinstance(series, dict):
        s = pd.Series(series); use_value_counts = False
    elif isinstance(series, (list, pd.Index)):
        s = pd.Series(series)
    else:
        s = series

    if use_value_counts:
        counts  = s.value_counts(dropna=False)
        labels  = counts.index.astype(str).tolist()
        heights = counts.values.astype(float)
        perc    = (counts / counts.sum() * 100).round(1)
    else:
        s       = pd.Series(s).dropna()
        labels  = s.index.astype(str).tolist()
        heights = s.values.astype(float)
        total   = heights.sum() or 1.0
        perc    = pd.Series(
            heights if value_is_percent else heights / total * 100,
            index=labels
        ).round(1)

    labels = shorten_labels(labels, mapping=label_map,
                             truncate_after=layout.truncate_after,
                             wrap_width=layout.wrap_width)

    fig, ax = _make_fig_axes(layout)
    x       = np.arange(len(labels))
    bars    = ax.bar(x, heights, color=style.bar_color, edgecolor=style.edge_color)

    ymax = max(heights) if len(heights) else 1.0
    ax.set_ylim(*(layout.ylim or (0, _auto_ylim(ymax, layout.ylim_pad))))

    if show_values:
        for i, b in enumerate(bars):
            txt = (f"{heights[i]:.1f}%" if value_is_percent
                   else f"{int(heights[i])}" + (f"\n({perc.iloc[i]:.1f}%)" if show_percent else ""))
            ax.annotate(txt,
                        (b.get_x() + b.get_width() / 2.0, b.get_height()),
                        ha="center", va="bottom", fontsize=style.font_annot,
                        xytext=(0, annot_offset), textcoords="offset points")

    ax.set_ylabel(ylabel, fontsize=style.font_axis)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=style.font_tick,
                       rotation=(layout.rotate_x or 0),
                       ha=("right" if layout.rotate_x and layout.tick_align_right_when_rotated else "center"))
    ax.grid(axis="y", linestyle="--", alpha=style.grid_alpha)

    _title(ax, line1, line2, level_label, org_name, style.title_color, style.font_title, layout.title_pad)
    if layout.show_footer:
        level = "people" if ("People" in ylabel or "Person" in ylabel) else "enrollment"
        _footer(fig, org_name, level, layout.footer_x, layout.footer_y, style)

    return _save_fig(fig, fname_base, layout, preview=preview)

# -----------------------------------------------------------------------
# Stacked percent chart
# -----------------------------------------------------------------------
def make_stacked_percent_chart(
    table:       pd.DataFrame,
    fname_base:  str,
    line1:       str,
    line2:       str,
    level_label: str,
    org_name:    str        = "Aquatics Program",
    *,
    style:       PlotStyle  = PlotStyle(),
    layout:      Layout     = Layout(),
    ylabel:      str        = "Percent of People within Group",
    legend_title:str        = "",
    preview:         bool  = False,
):
    if table.empty:
        print(f"[WARN] {fname_base}: empty table — skipping.")
        return

    base_rgb = np.array(mcolors.to_rgb(style.bar_color))
    whites   = np.ones(3)
    alphas   = np.linspace(0.0, 0.6, table.shape[1])
    colors   = [mcolors.to_hex((1 - a) * base_rgb + a * whites) for a in alphas]

    fig, ax = _make_fig_axes(layout)
    x       = np.arange(len(table.index))
    bottom  = np.zeros(len(table.index))

    for col, color in zip(table.columns, colors):
        vals = table[col].values
        bars = ax.bar(x, vals, bottom=bottom, color=color, edgecolor=style.edge_color, label=col)
        for j, (bar, v) in enumerate(zip(bars, vals)):
            if v >= 7:
                ax.text(bar.get_x() + bar.get_width() / 2, bottom[j] + v / 2,
                        f"{v:.0f}%", ha="center", va="center", fontsize=style.font_annot)
        bottom += vals

    ax.set_ylim(0, 100)
    labels = shorten_labels(table.index.astype(str),
                             truncate_after=layout.truncate_after,
                             wrap_width=layout.wrap_width)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=style.font_tick,
                       rotation=(layout.rotate_x or 0),
                       ha=("right" if layout.rotate_x and layout.tick_align_right_when_rotated else "center"))
    ax.set_ylabel(ylabel, fontsize=style.font_axis)
    ax.grid(axis="y", linestyle="--", alpha=style.grid_alpha)

    if layout.legend_outside:
        ax.legend(title=legend_title, bbox_to_anchor=layout.legend_bbox_to_anchor,
                  loc=layout.legend_loc, borderaxespad=0.0,
                  fontsize=style.legend_font, title_fontsize=style.legend_title_font)
    else:
        ax.legend(title=legend_title,
                  fontsize=style.legend_font, title_fontsize=style.legend_title_font)

    _title(ax, line1, line2, level_label, org_name, style.title_color, style.font_title, layout.title_pad)
    if layout.show_footer:
        _footer(fig, org_name, "people", layout.footer_x, layout.footer_y, style)

    _save_fig(fig, fname_base, layout)
