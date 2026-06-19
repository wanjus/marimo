# /// script
# [tool.marimo.runtime]
# auto_instantiate = false
# ///

import marimo

__generated_with = "ai"
app = marimo.App(width="medium")

@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import numpy as np
    import altair as alt
    import matplotlib.pyplot as plt
    
    mo.md("""
    # Git-Commit-Visualizer (Marimo)
    
    Dieses Notebook lädt ein Beispiel-Git-Log (oder eine hochgeladene Datei) und bietet interaktive Filter sowie Visualisierungen zu Commits pro Autor und pro Tag.
    
    Anleitung:
    - Lade optional eine `git log`-Datei hoch (Format: `git log --date=iso --pretty=format:%H%x09%an%x09%ad%x09%s`)
    - Oder nutze die Demo-Daten
    - Filtere nach Autor, Datumsbereich und Suchbegriff im Commit-Text
    """)
    return

@app.cell
def _():
    # UI-Elemente
    use_demo_data = mo.ui.checkbox(label="Demo-Daten verwenden", value=True)
    file_upload = mo.ui.file(label="git log Datei hochladen", multiple=False, full_width=True)
    text_query = mo.ui.text(value="", label="Suche im Commit-Text")
    
    mo.vstack([
        mo.hstack([use_demo_data]),
        file_upload,
        text_query,
    ])
    return

@app.cell
def _():
    # Daten laden und parsen
    
    def parse_git_log(text: str) -> pd.DataFrame:
        # Erwartetes Format je Zeile: SHA<TAB>Author<TAB>Date(ISO)<TAB>Subject
        rows = []
        for line in text.splitlines():
            parts = line.strip().split("\t")
            if len(parts) != 4:
                continue
            sha, author, date_str, subject = parts
            rows.append((sha, author, date_str, subject))
        df = pd.DataFrame(rows, columns=["sha", "author", "date", "subject"])
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
            df = df.dropna(subset=["date"]).reset_index(drop=True)
            df["date_local"] = df["date"].dt.tz_convert(None)
            df["date_day"] = df["date_local"].dt.date
        return df
    
    # Demo-Daten (kleines synthetisches Log)
    demo_text = "\n".join([
        "a1\tAlice\t2024-05-01T10:15:00+00:00\tInit project",
        "b2\tBob\t2024-05-01T12:00:00+00:00\tAdd README",
        "c3\tAlice\t2024-05-02T09:30:00+00:00\tImplement feature X",
        "d4\tCarol\t2024-05-03T17:45:00+00:00\tFix bug in parser",
        "e5\tBob\t2024-05-03T18:10:00+00:00\tRefactor utils",
        "f6\tAlice\t2024-05-05T08:05:00+00:00\tAdd tests for X",
        "g7\tCarol\t2024-05-06T11:20:00+00:00\tImprove docs",
    ])
    
    loaded_text = (
        demo_text if use_demo_data.value or file_upload.value is None else file_upload.value.read().decode("utf-8", errors="ignore")
    )
    
    raw_df = parse_git_log(loaded_text)
    raw_df
    return

@app.cell
def _():
    # UI auf Basis geladener Daten
    authors = ["Alle"] + (sorted(raw_df["author"].unique().tolist()) if not raw_df.empty else [])
    author_selector = mo.ui.dropdown(options=authors, value=(authors[0] if authors else None), label="Autor")
    
    if raw_df.empty:
        date_min, date_max = None, None
    else:
        date_min = pd.to_datetime(raw_df["date_local"].min())
        date_max = pd.to_datetime(raw_df["date_local"].max())
    
    date_slider = mo.ui.range_slider(
        start=int(pd.Timestamp(date_min).timestamp()) if date_min is not None else 0,
        stop=int(pd.Timestamp(date_max).timestamp()) if date_max is not None else 0,
        value=(
            (
                int(pd.Timestamp(date_min).timestamp()),
                int(pd.Timestamp(date_max).timestamp()),
            ) if date_min is not None and date_max is not None else (0, 0)
        ),
        label="Datumsbereich (Epoch Sekunden)",
    )
    
    mo.hstack([author_selector, date_slider])
    return

@app.cell
def _():
    # Daten filtern
    
    def apply_filters(df: pd.DataFrame, author_value: str, epoch_range: tuple[int, int], query: str) -> pd.DataFrame:
        if df.empty:
            return df
        out = df.copy()
        if author_value and author_value != "Alle":
            out = out[out["author"] == author_value]
        start_ts, end_ts = epoch_range
        start = pd.to_datetime(start_ts, unit="s") if start_ts else None
        end = pd.to_datetime(end_ts, unit="s") if end_ts else None
        if start is not None:
            out = out[out["date_local"] >= start]
        if end is not None:
            out = out[out["date_local"] <= end]
        q = (query or "").strip().lower()
        if q:
            out = out[out["subject"].str.lower().str.contains(q, na=False)]
        return out.reset_index(drop=True)
    
    filtered_df = apply_filters(raw_df, author_selector.value, date_slider.value, text_query.value)
    filtered_df
    return

@app.cell
def _():
    # KPIs
    n_commits = int(len(filtered_df))
    n_authors = int(filtered_df["author"].nunique()) if not filtered_df.empty else 0
    first_commit = (filtered_df["date_local"].min() if not filtered_df.empty else None)
    last_commit = (filtered_df["date_local"].max() if not filtered_df.empty else None)
    
    kpi_md = mo.md(
        f"""
    - Commits: {n_commits}
    - Autoren: {n_authors}
    - Erster Commit: {first_commit if first_commit is not None else '-'}
    - Letzter Commit: {last_commit if last_commit is not None else '-'}
    """
    )
    
    kpi_md
    return

@app.cell
def _():
    # Commits pro Autor (Altair)
    if filtered_df.empty:
        mo.md("Keine Daten für Auswahl")
    else:
        bar_data = (
            filtered_df.groupby("author", as_index=False)["sha"].count().rename(columns={"sha": "commits"})
        )
        chart_author = (
            alt.Chart(bar_data)
            .mark_bar()
            .encode(
                x=alt.X("commits:Q", title="Commits"),
                y=alt.Y("author:N", sort="-x", title="Autor"),
                tooltip=["author", "commits"],
                color=alt.Color("author:N", legend=None),
            )
            .properties(width=500, height=200, title="Commits pro Autor")
        )
        chart_author
    return

@app.cell
def _():
    # Commits pro Tag (Altair)
    if filtered_df.empty:
        mo.md("Keine Daten für Auswahl")
    else:
        daily = (
            filtered_df.groupby("date_day", as_index=False)["sha"].count().rename(columns={"sha": "commits"})
        )
        chart_daily = (
            alt.Chart(daily)
            .mark_line(point=True)
            .encode(
                x=alt.X("date_day:T", title="Datum"),
                y=alt.Y("commits:Q", title="Commits"),
                tooltip=["date_day", "commits"],
            )
            .properties(width=600, height=250, title="Commits pro Tag")
        )
        chart_daily
    return

@app.cell
def _():
    # Tabelle mit Explorer
    if filtered_df.empty:
        mo.md("Keine Daten für Auswahl")
    else:
        mo.ui.data_explorer(filtered_df[["sha", "author", "date_local", "subject"]])
    return

@app.cell
def _():
    # Matplotlib-Beispiel: Commits je Wochentag
    if filtered_df.empty:
        mo.md("Keine Daten für Auswahl")
    else:
        tmp = filtered_df.copy()
        tmp["weekday"] = tmp["date_local"].dt.day_name()
        order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        counts = tmp.groupby("weekday")["sha"].count().reindex(order).fillna(0)
        plt.figure(figsize=(6,3))
        plt.bar(counts.index, counts.values, color="#4C78A8")
        plt.xticks(rotation=45, ha="right")
        plt.title("Commits je Wochentag")
        plt.xlabel("")
        plt.ylabel("Commits")
        plt.gca()
    return

@app.cell
def _():
    mo.md("""
    ## Hinweise
    
    - Für eigene Daten: Führe im Repository `git log --date=iso --pretty=format:%H%x09%an%x09%ad%x09%s > gitlog.tsv` aus und lade die Datei hier hoch.
    - Falls Zeitachsen leer sind, prüfe das Datumsformat (ISO-8601 erforderlich).
    - Alle UI-Elemente sind reaktiv: Filter ändern aktualisieren automatisch Visualisierungen und Tabellen.
    """)
    return

if __name__ == "__main__":
    app.run()
