# Aquatics Program Analytics

A browser-based tool that turns raw pool registration data into
grant-ready charts — no coding required.

Built as part of a Math for Social Justice course in collaboration
with YWCA Central Maine (Nov 2025).

---

## Using the app

The app runs in your browser — nothing to install.

**[Click here to open the app](#)**
*(replace this link with your Streamlit Cloud URL after deploying)*

---

## What it does

1. **Upload your CSV** (or use the included sample to see it in action)
2. **Review 10 standard report charts** — tweak titles, colors, label
   rotation, font sizes, and spacing right in the browser
3. **Approve each chart** when it looks right
4. **Download everything as a zip** — PDF and PNG versions of all charts
5. **Build custom charts** from any column in your data

---

## Running locally (optional)

If you'd prefer to run it on your own machine:

### Requirements
Python 3.9–3.12 (Streamlit does not yet support Python 3.13+)

### Setup
```bash
pip install -r requirements.txt
streamlit run src/app.py
```

---

## Folder structure

```
├── README.md
├── requirements.txt
├── .streamlit/
│   └── config.toml          ← app theme and settings
├── data/
│   └── PoolDemographics_2025_SAMPLE.csv
├── src/
│   ├── app.py               ← the app
│   └── backend/
│       └── pool_backend.py  ← data cleaning and chart logic
└── outputs/
    ├── pdf/                 ← approved charts saved here
    └── png/
```

---

## Using your own data

Your CSV needs these six columns (names must match exactly):

| Column          | Example                          |
|-----------------|----------------------------------|
| `Program`       | `Family Swim 4/12/2025 5:00pm`   |
| `Age `          | `7`  *(trailing space)*          |
| `Gender`        | `male` / `female` / `non-binary` |
| `Race`          | Long-form survey string          |
| `Household`     | `3`                              |
| `House income ` | `$30,001-40,000` *(trailing space)* |

---

## Visual tweaks (sidebar)

| Setting | What it does |
|---|---|
| Title / subtitle | Edit the chart heading |
| Bar color | Pick any color |
| X-label rotation | 0 = flat, 45 = steep — fixes overlapping labels |
| Word-wrap labels | Wraps long labels at N characters |
| Title font size | Make the heading bigger or smaller |
| Tick font size | Size of labels along the x-axis |
| Annotation size | Size of numbers on top of bars |
| Top headroom | Space above the tallest bar |
