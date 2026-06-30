# IQR over z-score: solar/wind are skewed and solar is zero-inflated, so mean/std
# fences get dragged around by the outliers we're trying to catch. Quartiles don't.
# Solar baseline uses daytime only (radiation > 0) so nighttime zeros don't flag noon.

from __future__ import annotations

import pandas as pd

IQR_K = 1.5  # Tukey fence


def flag_anomalies(df: pd.DataFrame, metric: str, k: float = IQR_K) -> pd.DataFrame:
    out = df.copy()
    series = pd.to_numeric(out[metric], errors="coerce")
    baseline = series[series > 0] if metric == "solar_radiation" else series.dropna()

    out["is_anomaly"] = False
    if len(baseline) < 4:
        return out

    q1, q3 = baseline.quantile(0.25), baseline.quantile(0.75)
    iqr = q3 - q1
    flags = (series < q1 - k * iqr) | (series > q3 + k * iqr)
    if metric == "solar_radiation":
        flags &= series > 0
    out["is_anomaly"] = flags.fillna(False)
    return out
