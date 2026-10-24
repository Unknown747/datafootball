"""Entry point CLI lengkap untuk datafootball."""
import argparse
import sys
from pathlib import Path

from src import __version__
from src.logger import get_logger

logger = get_logger("datafootball.cli")

def cmd_status(args) -> int:
    """Tampilkan status proyek dan file data."""
    logger.info("datafootball v%s", __version__)
    base = Path("/root/datafootball")

    files = {
        "matches.csv": base / "data/processed/matches.csv",
        "features.csv": base / "data/features/features.csv",
        "poisson_predictions.csv": base / "data/predictions/poisson_predictions.csv",
        "elo_predictions.csv": base / "data/predictions/elo_predictions.csv",
        "baseline_predictions.csv": base / "data/predictions/baseline_predictions.csv",
        "backtest_results.csv": base / "data/evaluations/backtest_results.csv",
    }
    for name, path in files.items():
        if path.exists():
            lines = sum(1 for _ in open(path, encoding="utf-8"))
            logger.info("  %-30s %d baris", name, lines - 1)
        else:
            logger.info("  %-30s (belum ada)", name)
    return 0

def cmd_import_data(args) -> int:
    from src.football_data_loader import run_ingestion
    logger.info("Menjalankan impor data dari mirror lokal...")
    run_ingestion()
    return 0

def cmd_features(args) -> int:
    from src.feature_engineer import run_feature_engineering
    logger.info("Menghitung fitur statistik...")
    run_feature_engineering()
    return 0

def cmd_predict(args) -> int:
    from src.poisson_model import run_predictions
    from src.elo_model import run_elo
    from src.baseline_model import run_baseline
    logger.info("Menjalankan prediksi Poisson...")
    run_predictions()
    logger.info("Menjalankan prediksi Elo...")
    run_elo()
    logger.info("Menjalankan baseline...")
    run_baseline()
    return 0

def cmd_backtest(args) -> int:
    from src.odds_value import main as compute_value
    from src.backtester import run_backtest
    logger.info("Menghitung value...")
    compute_value()
    logger.info("Menjalankan backtest...")
    run_backtest()
    return 0

def cmd_report(args) -> int:
    """Tampilkan laporan pertandingan tertentu dalam format tabel."""
    import csv
    pred_path = Path("/root/datafootball/data/predictions/value_poisson.csv")
    if not pred_path.exists():
        logger.error("File prediksi belum ada. Jalankan 'predict' dulu.")
        return 1
    with open(pred_path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["match_id"] == args.match_id:
                print(f"\n=== Laporan Pertandingan ===")
                print(f"Match ID   : {row['match_id']}")
                print(f"Musim      : {row['season']}")
                print(f"Tanggal    : {row['date']}")
                print(f"Tim        : {row['home_team']} vs {row['away_team']}")
                print()
                print(f"{'Market':<10} | {'Prob':>6} | {'Fair':>6} | {'Aktual':>6} | {'Value':>8}")
                print("-" * 50)
                markets = [
                    ("Home", row["prob_home_win"], row["fair_odds_home"], row["actual_odds_home"], row["value_home_pct"]),
                    ("Draw", row["prob_draw"], row["fair_odds_draw"], row["actual_odds_draw"], row["value_draw_pct"]),
                    ("Away", row["prob_away_win"], row["fair_odds_away"], row["actual_odds_away"], row["value_away_pct"]),
                ]
                for name, prob, fair, actual, val in markets:
                    p = f"{float(prob)*100:.1f}%" if prob else "N/A"
                    f_ = fair if fair else "N/A"
                    a = actual if actual else "N/A"
                    v = f"{val}%" if val else "N/A"
                    print(f"{name:<10} | {p:>6} | {f_:>6} | {a:>6} | {v:>8}")
                print()
                return 0
    logger.error("Match ID %s tidak ditemukan di file prediksi.", args.match_id)
    return 1

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="datafootball",
        description="Football Stats & Prediction Engine",
    )
    parser.add_argument("--version", action="version", version=f"datafootball {__version__}")
    parser.add_argument("--verbose", "-v", action="store_true", help="Aktifkan log debug")

    sub = parser.add_subparsers(dest="command", help="Perintah yang tersedia")

    sub.add_parser("status", help="Tampilkan status proyek")
    sub.add_parser("import-data", help="Impor CSV mentah ke matches.csv")
    sub.add_parser("features", help="Hitung fitur statistik")
    sub.add_parser("predict", help="Jalankan prediksi Poisson, Elo, Baseline")
    sub.add_parser("backtest", help="Hitung value dan evaluasi model")
    
    p_report = sub.add_parser("report", help="Tampilkan laporan pertandingan")
    p_report.add_argument("--match-id", required=True, help="ID pertandingan")

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel("DEBUG")

    if args.command == "status":
        return cmd_status(args)
    if args.command == "import-data":
        return cmd_import_data(args)
    if args.command == "features":
        return cmd_features(args)
    if args.command == "predict":
        return cmd_predict(args)
    if args.command == "backtest":
        return cmd_backtest(args)
    if args.command == "report":
        return cmd_report(args)

    parser.print_help()
    return 1

if __name__ == "__main__":
    sys.exit(main())
