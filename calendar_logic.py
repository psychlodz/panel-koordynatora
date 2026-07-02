from datetime import date, timedelta

import pandas as pd


def time_to_minutes(t: str) -> int:
    h, m = map(int, str(t).split(":"))
    return h * 60 + m


def safe_int(value, default):
    try:
        return int(value)
    except Exception:
        return default


def easter_date(year: int) -> date:
    """Data Wielkanocy wg algorytmu Meeusa/Jonesa/Butchera."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def polish_holidays(year: int) -> set[date]:
    easter = easter_date(year)
    return {
        date(year, 1, 1),   # Nowy Rok
        date(year, 1, 6),   # Trzech Króli
        easter,             # Wielkanoc
        easter + timedelta(days=1),
        date(year, 5, 1),
        date(year, 5, 3),
        easter + timedelta(days=49),  # Zielone Świątki
        easter + timedelta(days=60),  # Boże Ciało
        date(year, 8, 15),
        date(year, 11, 1),
        date(year, 11, 11),
        date(year, 12, 25),
        date(year, 12, 26),
    }


def prepare_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    out["DATA_DNIA_DT"] = pd.to_datetime(out["DATA_DNIA"]).dt.date
    out["GODZ_OD_MIN"] = out["GODZ_OD"].apply(time_to_minutes)
    out["GODZ_DO_MIN"] = out["GODZ_DO"].apply(time_to_minutes)
    out["OPIS_PRACY"] = out["PRACOWNIK"].fillna("[bez pracownika]") + "  " + out["GODZ_OD"].astype(str) + "-" + out["GODZ_DO"].astype(str)
    return out


def minutes_to_time(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def make_slots():
    """Stałe przedziały widoku: 07-10, 10-13, 13-16, 16-19, 19-22."""
    return [
        (7 * 60, 10 * 60, "07:00-10:00"),
        (10 * 60, 13 * 60, "10:00-13:00"),
        (13 * 60, 16 * 60, "13:00-16:00"),
        (16 * 60, 19 * 60, "16:00-19:00"),
        (19 * 60, 22 * 60, "19:00-22:00"),
    ]


def rows_for_cell(df: pd.DataFrame, day_date: date, slot_start: int, slot_end: int) -> pd.DataFrame:
    """Osoby, których przedział pracy nakłada się na dany 2-godzinny slot."""
    if df.empty:
        return df
    return df[
        (df["DATA_DNIA_DT"] == day_date)
        & (df["GODZ_OD_MIN"] < slot_end)
        & (df["GODZ_DO_MIN"] > slot_start)
    ].copy()
