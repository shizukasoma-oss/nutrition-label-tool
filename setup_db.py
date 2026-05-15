"""
文部科学省「八訂 食品成分表」Excel を CSV に変換するセットアップスクリプト。

使い方:
  python setup_db.py <ダウンロードしたExcelファイルのパス>

対応ファイル: 20201225-mxt_kagsei-mext_01110_012.xlsx (第2章データ)
"""

import sys
from pathlib import Path

import pandas as pd

OUTPUT = Path(__file__).parent / "data" / "food_composition.csv"

# 八訂Excelの固定列インデックス (0始まり)
COL_NAME   = 3   # 食品名
COL_KCAL   = 6   # エネルギー(kcal)
COL_PROT   = 9   # たんぱく質
COL_FAT    = 12  # 脂質
COL_FIBER  = 18  # 食物繊維総量
COL_CARB   = 20  # 炭水化物（差引き法）
COL_NA     = 23  # ナトリウム(mg)

HEADER_ROWS = 12  # データ行開始前のヘッダー行数


def _clean(val: str) -> float:
    """「Tr」「-」「*」「(0)」などを数値に変換する"""
    v = str(val).strip()
    if v in ("Tr", "-", "*", "", "nan", "−"):
        return 0.0
    v = v.strip("()")  # (11.3) → 11.3
    try:
        return float(v)
    except ValueError:
        return 0.0


def convert(excel_path: str) -> None:
    path = Path(excel_path)
    if not path.exists():
        print(f"エラー: ファイルが見つかりません: {path}")
        sys.exit(1)

    print(f"読み込み中: {path.name}")
    xl = pd.ExcelFile(path)

    # 1枚目(表紙等)を除いた全シートを処理
    data_sheets = xl.sheet_names[1:]
    print(f"処理するシート: {len(data_sheets)} 群")

    all_rows = []
    for sheet in data_sheets:
        df = pd.read_excel(
            path,
            sheet_name=sheet,
            header=None,
            skiprows=HEADER_ROWS,
            dtype=str,
        )
        for _, row in df.iterrows():
            name = str(row.iloc[COL_NAME]).strip()
            # 食品番号が数字でない行（空行・注記行）をスキップ
            food_no = str(row.iloc[1]).strip() if len(row) > 1 else ""
            if not food_no.isdigit():
                continue
            if not name or name in ("nan", "食品名"):
                continue

            all_rows.append({
                "name":    name,
                "energy":  _clean(row.iloc[COL_KCAL]),
                "protein": _clean(row.iloc[COL_PROT]),
                "fat":     _clean(row.iloc[COL_FAT]),
                "carb":    _clean(row.iloc[COL_CARB]),
                "fiber":   _clean(row.iloc[COL_FIBER]),
                "sodium":  _clean(row.iloc[COL_NA]),
            })

    out = pd.DataFrame(all_rows)
    OUTPUT.parent.mkdir(exist_ok=True)
    out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(f"完了: {len(out)} 品目を {OUTPUT} に保存しました。")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    convert(sys.argv[1])
