import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "starter"))


def section(title: str):
    print("\n" + "=" * 80)
    print(f"SECTION: {title}")
    print("=" * 80)


def dump_file(rel_path: str, max_lines: int = 120):
    p = ROOT / rel_path
    print(f"\n--- FILE: {rel_path} (exists={p.exists()}) ---")
    if not p.exists():
        return
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines[:max_lines]:
        print(line)
    if len(lines) > max_lines:
        print(f"... [TRUNCATED: {len(lines) - max_lines} more lines] ...")


def main():
    # 1. Struktur file di /data
    section("1. DATA DIRECTORY TREE")
    data_dir = ROOT / "data"
    if data_dir.exists():
        for p in sorted(data_dir.rglob("*")):
            if p.is_file():
                size_mb = p.stat().st_size / (1024 * 1024)
                print(f"  {p.relative_to(ROOT)} ({size_mb:.2f} MB)")
    else:
        print("  [WARNING] Folder /data tidak ditemukan di root.")

    # 2. Isi helper scripts & evaluation CLI
    section("2. REPO HELPER & EVALUATION SCRIPTS")
    for script in [
        "games.py",
        "starter/load_atd.py",
        "starter/load_smart_tagging.py",
        "evaluation/validate_submission.py",
        "evaluation/run_evaluation.py",
    ]:
        dump_file(script, max_lines=120)

    # 3. Inspeksi ATD Tracking Data
    section("3. ATD TRACKING DATA SCHEMA")
    try:
        import load_atd
        print("load_atd attributes:", [a for a in dir(load_atd) if not a.startswith("_")])

        # Coba panggil fungsi loader umum yang biasa ada di starter
        dataset = None
        for fn_name in ["load_atd", "load_tracking", "get_atd", "load_data"]:
            if hasattr(load_atd, fn_name) and callable(getattr(load_atd, fn_name)):
                try:
                    dataset = getattr(load_atd, fn_name)()
                    print(f"Loaded via load_atd.{fn_name}() -> type: {type(dataset)}")
                    break
                except TypeError:
                    pass

        if dataset is not None:
            if hasattr(dataset, "metadata"):
                print("\n--- Metadata Teams & Players ---")
                for t in dataset.metadata.teams:
                    player_ids = [p.player_id for p in t.players]
                    print(f"  Team: name={t.name!r}, ground={t.ground}, n_players={len(player_ids)}")
                    print(f"    sample player_ids: {player_ids[:6]}")
                df_atd = dataset.to_df()
            elif isinstance(dataset, pd.DataFrame):
                df_atd = dataset
            else:
                df_atd = None

            if df_atd is not None:
                print(f"\ndf_atd.shape: {df_atd.shape}")
                print(f"df_atd.index: name={df_atd.index.name!r}, dtype={df_atd.index.dtype}, head={df_atd.index[:5].tolist()}")
                non_player_cols = [c for c in df_atd.columns if not any(c.endswith(s) for s in ("_x", "_y", "_s", "_d", "_vx", "_vy")) or c.startswith("ball_")]
                player_cols = [c for c in df_atd.columns if c not in non_player_cols]
                print(f"Non-player columns ({len(non_player_cols)}): {non_player_cols}")
                print(f"Player columns count: {len(player_cols)} | Sample first 12: {player_cols[:12]}")
                print("\nDtypes of non-player columns:")
                print(df_atd[non_player_cols].dtypes.to_string())
                if "ball_x" in df_atd.columns:
                    print(f"\nball_x NaN ratio (all frames): {df_atd['ball_x'].isna().mean():.4f}")
                sample_cols = non_player_cols[:6] + player_cols[:4]
                print("\nSample 3 rows (non-null ball if available):")
                valid_sample = df_atd.dropna(subset=["ball_x"]).head(3) if "ball_x" in df_atd.columns else df_atd.head(3)
                print(valid_sample[sample_cols].to_string())
    except Exception as e:
        print(f"[ERROR inspecting ATD]: {type(e).__name__}: {e}")

    # 4. Inspeksi Smart Tagging Data
    section("4. SMART TAGGING DATA SCHEMA")
    try:
        import load_smart_tagging
        print("load_smart_tagging attributes:", [a for a in dir(load_smart_tagging) if not a.startswith("_")])

        st_obj = None
        for fn_name in ["load_smart_tagging", "load_events", "get_smart_tagging", "load_data"]:
            if hasattr(load_smart_tagging, fn_name) and callable(getattr(load_smart_tagging, fn_name)):
                try:
                    st_obj = getattr(load_smart_tagging, fn_name)()
                    print(f"Loaded via load_smart_tagging.{fn_name}() -> type: {type(st_obj)}")
                    break
                except TypeError:
                    pass

        if st_obj is not None:
            df_st = st_obj.to_df() if hasattr(st_obj, "to_df") else st_obj
            if isinstance(df_st, pd.DataFrame):
                print(f"\ndf_st.shape: {df_st.shape}")
                print(f"df_st.columns: {df_st.columns.tolist()}")
                print("\nDtypes:")
                print(df_st.dtypes.to_string())
                for col in ["code", "Team", "Type"]:
                    if col in df_st.columns:
                        print(f"\nValue counts for '{col}':")
                        print(df_st[col].value_counts(dropna=False).to_string())
                print("\nSample 5 rows:")
                print(df_st.head(5).to_string())
    except Exception as e:
        print(f"[ERROR inspecting Smart Tagging]: {type(e).__name__}: {e}")

    # 5. Inspeksi Public GT & Baseline Submission
    section("5. PUBLIC GT & BASELINE SUBMISSION FORMAT")
    for csv_rel in [
        "evaluation/gt/BAR-ATH_possession_gt_public.csv",
        "evaluation/results/baseline_raw.csv",
    ]:
        p = ROOT / csv_rel
        print(f"\n--- CSV: {csv_rel} (exists={p.exists()}) ---")
        if p.exists():
            df_c = pd.read_csv(p)
            print(f"shape={df_c.shape}, columns={df_c.columns.tolist()}")
            if "frame" in df_c.columns:
                print(f"frame min={df_c['frame'].min()}, max={df_c['frame'].max()}")
            if "label" in df_c.columns:
                print(f"label counts={df_c['label'].value_counts(dropna=False).to_dict()}")
            print(df_c.head(5).to_string(index=False))


if __name__ == "__main__":
    main()