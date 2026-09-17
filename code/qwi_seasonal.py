"""
Shared seasonal-adjustment helper for QWI employment series.

QWI has no seasonally-adjusted product. Its API schema carries a
`seasonadj` field, but every query returns data only for `seasonadj=U`
(Unadjusted) -- confirmed against the API across industries/states/years,
and against the raw bulk release files (lehd.ces.census.gov/data/qwi/),
where `seasonadj` is uniformly "U" as well. Census's own QWI 101
documentation describes taking a multi-quarter average as the recommended
way to reduce seasonal variation -- there is no official SA series to
pull instead.

This computes an approximation ourselves: classical multiplicative
seasonal decomposition (statsmodels `seasonal_decompose`, period=4) on a
quarterly series. The seasonal component is a repeating 4-quarter pattern
fit from the whole series, so the deseasonalized level is defined for
every quarter (no edge NaNs, unlike the trend component).

See temp_national_seasonality.py for a chart of the seasonal pattern this
removes.
"""

import pandas as pd
from statsmodels.tsa.seasonal import seasonal_decompose


def seasonally_adjust(df: pd.DataFrame, value_col: str,
                       year_col: str = "year", quarter_col: str = "quarter") -> pd.DataFrame:
    """Add f'{value_col}_sa' (seasonally adjusted) and f'{value_col}_seasonal'
    (the seasonal factor divided out) columns to a copy of `df`.

    `df` must have one row per quarter, sorted or not, with no gaps, and at
    least 2 full years of data (8 quarters) for the decomposition to run.
    """
    d = df.sort_values([year_col, quarter_col]).reset_index(drop=True)
    periods = d[year_col].astype(int).astype(str) + "Q" + d[quarter_col].astype(int).astype(str)
    idx = pd.PeriodIndex(periods, freq="Q")
    s = pd.Series(d[value_col].astype(float).values, index=idx)

    result = seasonal_decompose(s, model="multiplicative", period=4)
    d[f"{value_col}_seasonal"] = result.seasonal.values
    d[f"{value_col}_sa"] = (s / result.seasonal).values
    return d
