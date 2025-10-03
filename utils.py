import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- Fungsi ambil data dari Google Sheets ---
def load_google_sheet(sheet_url, sheet_name):
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(sheet_url).worksheet(sheet_name)
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    # Jika ada kolom 'line', pastikan bertipe string
    if 'line' in df.columns:
        df['line'] = df['line'].astype(str)
    return df

# --- Hitung OEE & KPI ---
def calculate_oee(df_oee, df_downtime):
    # Standardisasi nama kolom
    df_oee.columns = df_oee.columns.str.strip().str.lower()
    df_downtime.columns = df_downtime.columns.str.strip().str.lower()

    # Pastikan kolom 'line' dan 'shift' bertipe string di semua data
    if 'line' in df_oee.columns:
        df_oee['line'] = df_oee['line'].astype(str)
    if 'line' in df_downtime.columns:
        df_downtime['line'] = df_downtime['line'].astype(str)
    if 'shift' in df_oee.columns:
        df_oee['shift'] = df_oee['shift'].astype(str)
    if 'shift' in df_downtime.columns:
        df_downtime['shift'] = df_downtime['shift'].astype(str)


    # Konversi Start & Finish ke datetime + hitung duration (support lintas hari)
    if "start" in df_downtime and "finish" in df_downtime:
        df_downtime["start"] = pd.to_datetime(df_downtime["start"], format="%H:%M", errors="coerce")
        df_downtime["finish"] = pd.to_datetime(df_downtime["finish"], format="%H:%M", errors="coerce")
        # Jika finish < start, tambahkan 1 hari ke finish (lintas hari)
        finish_adj = df_downtime["finish"]
        mask = (df_downtime["finish"].dt.hour < df_downtime["start"].dt.hour) | \
               ((df_downtime["finish"].dt.hour == df_downtime["start"].dt.hour) & (df_downtime["finish"].dt.minute < df_downtime["start"].dt.minute))
        finish_adj = finish_adj.where(~mask, finish_adj + pd.Timedelta(days=1))
        df_downtime["duration"] = (finish_adj - df_downtime["start"]).dt.total_seconds() / 60
        df_downtime["duration"] = df_downtime["duration"].abs()

    # Pastikan kolom numerik bertipe float
    num_cols = ["good product output", "hold & all defect", "loading time", "output maksimal"]
    for col in num_cols:
        if col in df_oee.columns:
            df_oee[col] = pd.to_numeric(df_oee[col], errors="coerce")

    # Copy data OEE
    df = df_oee.copy()


    # Hitung total downtime per line dan tanggal
    if "line" in df.columns and "tanggal" in df.columns and "line" in df_downtime.columns and "tanggal" in df_downtime.columns:
        # Pastikan tanggal di kedua df sudah datetime
        df["tanggal"] = pd.to_datetime(df["tanggal"], errors="coerce")
        df_downtime["tanggal"] = pd.to_datetime(df_downtime["tanggal"], errors="coerce")
        downtime_per_row = df.merge(
            df_downtime.groupby(["line", "tanggal"])['duration'].sum().reset_index(),
            on=["line", "tanggal"],
            how="left"
        )['duration'].fillna(0)
        with pd.option_context('mode.use_inf_as_na', True):
            # Proteksi jika loading time <= 0
            avail = (df["loading time"] - downtime_per_row)
            avail = avail.where(df["loading time"] > 0, pd.NA)
            df["availability"] = (avail / df["loading time"]).replace([float('inf'), -float('inf')], pd.NA) * 100
    else:
        # fallback: tetap pakai total downtime (kurang akurat)
        with pd.option_context('mode.use_inf_as_na', True):
            df["availability"] = (((df["loading time"] - df_downtime["duration"].sum())) / df["loading time"]).replace([float('inf'), -float('inf')], pd.NA) * 100

    # Proteksi pembagian dengan nol untuk performance dan quality
    with pd.option_context('mode.use_inf_as_na', True):
        # Rumus performance baru: (good product output + hold & all defect) / output maksimal
        denom_perf = df["output maksimal"].replace(0, pd.NA)
        numer_perf = df["good product output"] + df["hold & all defect"]
        perf = (numer_perf / denom_perf).replace([float('inf'), -float('inf')], pd.NA)
        df["performance"] = perf * 100

        # Quality tetap sesuai rumus sebelumnya
        numer_qual = df["good product output"] - df["hold & all defect"]
        denom_qual = df["good product output"]
        denom_qual = denom_qual.replace(0, pd.NA)
        qual = (numer_qual / denom_qual).replace([float('inf'), -float('inf')], pd.NA)
        df["quality"] = qual * 100

        df["oee"] = (df["availability"] * df["performance"] * df["quality"]) / 10000


    # Tambah kolom bulan
    if "tanggal" in df:
        df["tanggal"] = pd.to_datetime(df["tanggal"], errors="coerce")
        df["bulan"] = df["tanggal"].dt.to_period("M")

        # OEE harian berbasis total agregat PER LINE
        agg_cols = ["good product output", "hold & all defect", "loading time", "output maksimal"]
        # Gabungkan OEE per shift dengan downtime per shift (merge by tanggal, line, shift)
        # Agregasi OEE harian per line tanpa downtime dulu
        df_harian = df.groupby(["tanggal", "line"])[agg_cols].sum().reset_index()
        df_harian['line'] = df_harian['line'].astype(str)
        # Agregasi downtime harian per line langsung dari df_downtime
        downtime_harian = df_downtime.groupby(["tanggal", "line"])["duration"].sum().reset_index()
        downtime_harian['line'] = downtime_harian['line'].astype(str)
        # Merge downtime harian ke df_harian
        df_harian = df_harian.merge(downtime_harian, on=["tanggal", "line"], how="left")
        df_harian['duration'] = df_harian['duration'].fillna(0)
        # Hitung OEE harian dari total harian per line
        with pd.option_context('mode.use_inf_as_na', True):
            denom_perf = df_harian["output maksimal"].replace(0, pd.NA)
            numer_perf = df_harian["good product output"] + df_harian["hold & all defect"]
            perf = (numer_perf / denom_perf).replace([float('inf'), -float('inf')], pd.NA)
            df_harian["performance"] = perf * 100

            numer_qual = df_harian["good product output"] - df_harian["hold & all defect"]
            denom_qual = df_harian["good product output"]
            denom_qual = denom_qual.replace(0, pd.NA)
            qual = (numer_qual / denom_qual).replace([float('inf'), -float('inf')], pd.NA)
            df_harian["quality"] = qual * 100

            # Availability harian: total loading time - total downtime harian PER LINE
            avail = (df_harian["loading time"] - df_harian["duration"])
            avail = avail.where(df_harian["loading time"] > 0, pd.NA)
            df_harian["availability"] = (avail / df_harian["loading time"]).replace([float('inf'), -float('inf')], pd.NA) * 100

            df_harian["oee"] = (df_harian["availability"] * df_harian["performance"] * df_harian["quality"]) / 10000

        # OEE bulanan berbasis total agregat
        df["bulan"] = df["tanggal"].dt.to_period("M")
        df_bulanan = df.groupby("bulan")[agg_cols].sum().reset_index()
        with pd.option_context('mode.use_inf_as_na', True):
            denom_perf = df_bulanan["output maksimal"].replace(0, pd.NA)
            numer_perf = df_bulanan["good product output"] + df_bulanan["hold & all defect"]
            perf = (numer_perf / denom_perf).replace([float('inf'), -float('inf')], pd.NA)
            df_bulanan["performance"] = perf * 100

            numer_qual = df_bulanan["good product output"] - df_bulanan["hold & all defect"]
            denom_qual = df_bulanan["good product output"]
            denom_qual = denom_qual.replace(0, pd.NA)
            qual = (numer_qual / denom_qual).replace([float('inf'), -float('inf')], pd.NA)
            df_bulanan["quality"] = qual * 100

            # Availability bulanan: total loading time - total downtime bulanan
            if "bulan" in df_downtime:
                df_downtime["bulan"] = pd.to_datetime(df_downtime["tanggal"], errors="coerce").dt.to_period("M")
                downtime_bulanan = df_downtime.groupby("bulan")["duration"].sum().reset_index()
                df_bulanan = df_bulanan.merge(downtime_bulanan, on="bulan", how="left")
                df_bulanan["duration"] = df_bulanan["duration"].fillna(0)
                avail = ((df_bulanan["loading time"] - df_bulanan["duration"]) / df_bulanan["loading time"]).replace([float('inf'), -float('inf')], pd.NA) * 100
                df_bulanan["availability"] = avail
            else:
                df_bulanan["availability"] = pd.NA

            df_bulanan["oee"] = (df_bulanan["availability"] * df_bulanan["performance"] * df_bulanan["quality"]) / 10000

    else:
        df_harian = pd.DataFrame()
        df_bulanan = pd.DataFrame()


    # Pareto downtime per line + kategori + bulan
    if "line" in df_downtime and "kategori" in df_downtime and "tanggal" in df_downtime:
        df_downtime["bulan"] = pd.to_datetime(df_downtime["tanggal"], errors="coerce").dt.to_period("M")
        downtime_summary = (
            df_downtime.groupby(["bulan", "line", "kategori"])["duration"].sum().reset_index()
        )
        downtime_summary["line"] = downtime_summary["line"].astype(str)
        downtime_summary = downtime_summary.sort_values(["bulan", "line", "duration"], ascending=[True, True, False])
    else:
        downtime_summary = pd.DataFrame()

    # ✅ return HARUS di dalam fungsi (indent ke dalam)
    return df, df_harian, df_bulanan, downtime_summary
