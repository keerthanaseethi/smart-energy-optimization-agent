from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Tuple
import pandas as pd
import datetime

from integrations.weather_api import fetch_open_meteo
from data.provenance import make_provenance


@dataclass
class TimeSeries:
    df: pd.DataFrame
    provenance: str
    source_meta: Dict[str, Any]
    provenance_metadata: Dict[str, Any]


class WeatherDataSource:
    """Minimal WeatherDataSource adapter for Open-Meteo (read-only).

    Usage:
      src = WeatherDataSource()
      ts = src.fetch(start, end, variables)

    The returned TimeSeries contains `df`, `provenance`, and `source_meta`.
    Validation checks are included (hourly freq, duplicates, missing timestamps).
    """

    def __init__(self, provider_name: str = "Open-Meteo"):
        self.provider_name = provider_name

    def fetch(self, start_date: str, end_date: str, variables: List[str] | None = None, latitude: float = 40.0, longitude: float = -83.0, timezone: str = "UTC") -> TimeSeries:
        """Fetch hourly weather data between start_date and end_date.

        Parameters are forwarded to the existing `integrations.weather_api.fetch_open_meteo` function.
        """

        if variables is None:
            variables = ["temperature_2m", "relativehumidity_2m"]

        df, meta = fetch_open_meteo(
            latitude=latitude,
            longitude=longitude,
            start_date=start_date,
            end_date=end_date,
            hourly=variables,
            timezone=timezone,
        )

        # Attach provenance and provider
        provenance = f"REAL_EXTERNAL:{self.provider_name}"

        source_meta: Dict[str, Any] = {
            "provider": self.provider_name,
            "coordinates": {"latitude": latitude, "longitude": longitude},
            "requested_variables": variables,
            "timezone": meta.get("timezone", timezone),
            "fetch_time_utc": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "start_requested": start_date,
            "end_requested": end_date,
            "returned_rows": meta.get("rows"),
            "request_url": meta.get("request_url"),
            "provenance": provenance,
        }

        # Normalize Datetime column to tz-naive UTC (documented in source_meta)
        if "Datetime" in df.columns:
            df["Datetime"] = pd.to_datetime(df["Datetime"], errors="coerce")
            # Ensure sorted and unique index for time checks
            df = df.sort_values("Datetime").reset_index(drop=True)

        # Validate hourly frequency (best-effort)
        freq_seconds = None
        if len(df) >= 3:
            diffs = df["Datetime"].diff().dropna().map(lambda x: x.total_seconds()).values
            if len(diffs):
                from collections import Counter

                cnt = Counter(diffs)
                most_common = cnt.most_common(1)[0][0]
                freq_seconds = most_common

        source_meta["inferred_frequency_seconds"] = freq_seconds

        # Check duplicates and missing hourly timestamps
        duplicates = df["Datetime"].duplicated().any()
        source_meta["has_duplicates"] = bool(duplicates)

        # Detect missing hourly timestamps between min and max (do not impute)
        missing_timestamps = None
        if len(df) and pd.notnull(df["Datetime"]).all():
            expected = pd.date_range(start=df["Datetime"].min(), end=df["Datetime"].max(), freq="h")
            actual = pd.DatetimeIndex(df["Datetime"]).tz_localize(None)
            missing = expected.difference(actual)
            missing_timestamps = len(missing)
            source_meta["missing_timestamps"] = int(missing_timestamps)
        else:
            source_meta["missing_timestamps"] = None

        # Preserve units if provided in meta
        if "returned_fields" in meta:
            source_meta["returned_fields"] = meta.get("returned_fields")

        data_start = df["Datetime"].min().isoformat() if len(df) else None
        data_end = df["Datetime"].max().isoformat() if len(df) else None
        provenance_metadata = make_provenance(
            "REAL_EXTERNAL",
            self.provider_name,
            source_meta.get("request_url") or "open-meteo-hourly",
            data_timestamp_start=data_start,
            data_timestamp_end=data_end,
            units=meta.get("hourly_units", {}),
            geographic_scope=f"coordinates:{latitude},{longitude}",
            semantic_description="Read-only external weather values from Open-Meteo.",
            transformation="timestamp normalization and ordering only; no imputation",
            metadata={
                "coordinates": {"latitude": latitude, "longitude": longitude},
                "requested_range": {"start": start_date, "end": end_date},
                "requested_variables": list(variables),
                "timezone": source_meta["timezone"],
                "inferred_frequency_seconds": freq_seconds,
                "missing_timestamps": source_meta.get("missing_timestamps"),
                "has_duplicates": source_meta.get("has_duplicates"),
                "read_only": True,
            },
        )
        source_meta["provenance_metadata"] = provenance_metadata

        # Return TimeSeries; do not impute or modify data beyond normalization and sorting
        ts = TimeSeries(
            df=df,
            provenance=provenance,
            source_meta=source_meta,
            provenance_metadata=provenance_metadata,
        )

        return ts
