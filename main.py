"""Menu interaktif datafootball."""
import sys
from pathlib import Path

sys.path.insert(0, "/root/datafootball")

from src.logger import get_logger
from src.cli import cmd_import_data, cmd_features, cmd_predict, cmd_backtest

logger = get_logger("datafootball.main")

def menu_update():
    print("\n--- Update Database (musim aktif 2526 + 2627) ---")
    from src.football_data_updater import update_active_season
    update_active_season()
    print("Selesai update.")

def menu_predict():
    print("\n--- Prediksi Pertandingan Mendatang ---")
    from src.upcoming_predictor import run_upcoming
    run_upcoming()
    path = Path("/root/datafootball/data/predictions/upcoming_predictions.csv")
    if path.exists():
        import csv
        print(f"\n{'Kickoff (WIB)':<17} {'Home':<16} {'Away':<16} {'P(H)':>6} {'P(D)':>6} {'P(A)':>6} {'O/U2.5':>7} {'BTTS':>6} {'Rekomendasi':<12} {'Prob':>6} {'Fair':>6}")
        print("-" * 135)
        with open(path, "r", encoding="utf-8") as f:
            for i, row in enumerate(csv.DictReader(f)):
                if i >= 20:
                    print(f"... dan {i} pertandingan lainnya.")
                    break
                print(f"{row['kickoff_wib']:<17} {row['home_team']:<16} {row['away_team']:<16} "
                      f"{row['prob_home_win']:>6} {row['prob_draw']:>6} {row['prob_away_win']:>6} "
                      f"{row['prob_over_2_5']:>7} {row['prob_btts_yes']:>6} "
                      f"{row['recommended_bet']:<12} {row['bet_prob']:>6} {row['bet_fair_odds']:>6}")

def menu_backtest():
    print("\n--- Backtest ---")
    cmd_backtest(type("Args", (), {})())
    path = Path("/root/datafootball/data/evaluations/backtest_results.csv")
    if path.exists():
        import csv
        print(f"\n{'Model':<10} {'n':>6} {'LogLoss':>10} {'Brier':>10} {'Accuracy':>10}")
        print("-" * 50)
        with open(path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                print(f"{row['model']:<10} {row['n_matches']:>6} {row['log_loss']:>10} {row['brier_score']:>10} {row['accuracy']:>10}")

def menu_status():
    print("\n--- Status Database ---")
    files = {
        "matches.csv": Path("/root/datafootball/data/processed/matches.csv"),
        "features.csv": Path("/root/datafootball/data/features/features.csv"),
        "poisson_predictions.csv": Path("/root/datafootball/data/predictions/poisson_predictions.csv"),
        "upcoming_predictions.csv": Path("/root/datafootball/data/predictions/upcoming_predictions.csv"),
        "backtest_results.csv": Path("/root/datafootball/data/evaluations/backtest_results.csv"),
    }
    for name, path in files.items():
        if path.exists():
            n = sum(1 for _ in open(path, encoding="utf-8")) - 1
            print(f"  {name:<30} {n} baris")
        else:
            print(f"  {name:<30} (belum ada)")

def menu():
    print("=" * 60)
    print("  datafootball — Football Stats & Prediction Engine")
    print("=" * 60)
    while True:
        print("\nMenu:")
        print("  1. Update Database (unduh data terbaru)")
        print("  2. Prediksi Pertandingan Mendatang")
        print("  3. Backtest")
        print("  4. Status Database")
        print("  5. Keluar")
        choice = input("\nPilih [1-5]: ").strip()

        if choice == "1":
            menu_update()
        elif choice == "2":
            menu_predict()
        elif choice == "3":
            menu_backtest()
        elif choice == "4":
            menu_status()
        elif choice == "5":
            print("Keluar.")
            break
        else:
            print("Pilihan tidak valid.")

if __name__ == "__main__":
    menu()
