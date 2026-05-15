"""食品成分DBの読み込み・検索ロジック

データソース優先順位:
1. 文部科学省 食品成分表CSV (data/food_composition.csv) - setup_db.py で作成
2. 組み込みデータ (一般的なお菓子材料 約60品目、八訂準拠の近似値)
3. カスタム食品 (custom_foods.json)
"""

import unicodedata
from pathlib import Path

import pandas as pd

from firebase_utils import db

BASE_DIR = Path(__file__).parent
MEXT_CSV = BASE_DIR / "data" / "food_composition.csv"


def _custom_col(user_email: str):
    return db.collection("nutrition_customFoods").document(user_email).collection("foods")

# 組み込みデータ (100gあたり) - 文部科学省 八訂食品成分表 準拠の近似値
# [食品名, エネルギー(kcal), たんぱく質(g), 脂質(g), 炭水化物(g), 食物繊維(g), ナトリウム(mg)]
_BUILTIN = [
    # --- 穀類 ---
    ("薄力粉",           368, 8.3,  1.5,  75.8, 2.5,    1),
    ("強力粉",           365, 11.8, 1.5,  71.7, 2.7,    1),
    ("全粒薄力粉",        328, 12.8, 2.5,  68.2, 9.9,    1),
    ("米粉",             356, 6.0,  0.7,  81.3, 0.6,    3),
    ("片栗粉",           338, 0.1,  0.1,  86.4, 0.0,    1),
    ("コーンスターチ",    354, 0.1,  0.7,  86.3, 0.0,    4),
    ("ベーキングパウダー", 127, 0.0,  0.0,  29.0, 0.0, 10200),
    ("重曹",               0, 0.0,  0.0,   0.0, 0.0, 27360),
    # --- 砂糖・甘味料 ---
    ("上白糖",           384, 0.0,  0.0,  99.3, 0.0,    1),
    ("グラニュー糖",      387, 0.0,  0.0, 100.0, 0.0,    0),
    ("粉糖",             384, 0.0,  0.0,  99.5, 0.0,    1),
    ("三温糖",           383, 0.1,  0.0,  99.0, 0.0,    7),
    ("黒糖",             352, 1.7,  0.0,  89.9, 0.0,   27),
    ("きび砂糖",          383, 0.1,  0.0,  98.9, 0.0,    5),
    ("和三盆糖",          382, 0.0,  0.0,  99.6, 0.0,    1),
    ("蜂蜜",             329, 0.2,  0.0,  81.9, 0.0,    6),
    ("メープルシロップ",   266, 0.0,  0.1,  66.3, 0.0,    5),
    ("水飴",             349, 0.0,  0.0,  91.8, 0.0,   13),
    # --- 油脂 ---
    ("バター（有塩）",    745, 0.6, 81.0,   0.2, 0.0,  750),
    ("バター（無塩）",    763, 0.6, 83.0,   0.2, 0.0,   11),
    ("マーガリン",        769, 0.4, 83.1,   0.5, 0.0,  490),
    ("サラダ油",          921, 0.0,100.0,   0.0, 0.0,    0),
    ("ショートニング",     921, 0.0,100.0,   0.0, 0.0,    0),
    ("ラード",            941, 0.0,100.0,   0.0, 0.0,    0),
    ("ごま油",            921, 0.0,100.0,   0.0, 0.0,    0),
    # --- 乳製品 ---
    ("牛乳",              67, 3.3,  3.8,   4.8, 0.0,   41),
    ("生クリーム（乳脂肪）", 433, 2.0, 45.0,  3.1, 0.0,   38),
    ("ヨーグルト（無糖）",  62, 3.6,  3.0,   4.9, 0.0,   48),
    ("クリームチーズ",    346, 8.2, 33.0,   2.3, 0.0,  260),
    ("マスカルポーネ",    411, 5.0, 40.0,   3.5, 0.0,   55),
    ("コンデンスミルク",  333, 7.7,  8.5,  56.0, 0.0,  120),
    ("スキムミルク",      359,35.8,  1.0,  53.3, 0.0,  490),
    # --- 卵 ---
    ("全卵（生）",        151,12.3, 10.3,   0.3, 0.0,  140),
    ("卵黄（生）",        387,16.5, 33.5,   0.1, 0.0,   52),
    ("卵白（生）",         47,10.1,  0.0,   0.5, 0.0,  160),
    # --- ナッツ・種実 ---
    ("アーモンド（乾）",   608,19.6, 51.8,  20.7,10.1,    4),
    ("アーモンドプードル", 608,19.6, 51.8,  20.7,10.1,    4),
    ("くるみ（乾）",       713,14.6, 68.8,  11.7, 7.5,    4),
    ("ヘーゼルナッツ（乾）",684,13.6, 69.3, 13.9, 7.4,    1),
    ("ピスタチオ（乾）",   615,17.4, 56.1,  20.9, 9.2,  270),
    ("カシューナッツ（フライ）",576,19.8,47.6,26.7, 6.7,    5),
    ("マカダミアナッツ（乾）",751, 8.3, 76.7,  12.2, 6.2,    2),
    ("ごま（乾）",         605,20.3, 53.8,  18.5,10.8,    2),
    ("ピーナッツ（乾）",   585,25.4, 49.4,  18.8, 7.4,    2),
    ("ピーナッツバター",   640,25.4, 50.7,  18.4, 6.1,  390),
    # --- チョコレート・カカオ ---
    ("スイートチョコレート", 588, 5.7, 34.1, 55.8, 3.9,    6),
    ("ミルクチョコレート",  558, 6.9, 34.1,  51.7, 2.7,   55),
    ("ホワイトチョコレート", 588, 7.2, 38.9, 47.3, 0.0,   60),
    ("ピュアカカオ（クーベルチュール）", 588, 5.7, 34.1, 55.8, 3.9, 6),
    ("ピュアココア",       274,18.5, 21.6,  42.4,23.9,    6),
    # --- 和菓子・粉類 ---
    ("白玉粉",            362, 6.3,  1.0,  82.5, 0.5,    2),
    ("上新粉",            362, 6.2,  0.9,  82.0, 0.6,    3),
    ("道明寺粉",          356, 6.2,  0.9,  81.0, 0.5,    2),
    ("きな粉（全粒・黄）", 437,36.7, 25.7,  30.7,16.9,    1),
    ("抹茶",             324,29.6,  5.3,  39.5,38.5,    6),
    # --- ドライフルーツ ---
    ("レーズン",          324, 2.7,  0.2,  80.3, 4.1,   12),
    ("クランベリー（乾）", 336, 0.1,  0.6,  84.8, 5.9,    3),
    ("アプリコット（乾）", 246, 3.4,  0.4,  60.6, 9.8,   11),
    ("いちじく（乾）",    291, 3.0,  1.1,  68.6,10.7,   22),
    # --- ゼラチン・凝固剤 ---
    ("ゼラチン",          344,87.6,  0.3,   0.0, 0.0,  160),
    ("粉寒天",            154, 2.4,  0.2,  74.1,74.1,   28),
    ("アガー",            190, 0.0,  0.0,  47.5,47.5,  510),
    # --- 調味料 ---
    ("食塩",                0, 0.0,  0.0,   0.0, 0.0,39000),
    ("バニラエッセンス",    330, 0.0,  0.0,  69.0, 0.0,    0),
    ("ラム酒",             237, 0.0,  0.0,   0.1, 0.0,    1),
    ("コアントロー（オレンジリキュール）",318,0.0,0.0,28.0,0.0,2),
]

_COLUMNS = ["name", "energy", "protein", "fat", "carb", "fiber", "sodium"]


def _normalize(text: str) -> str:
    """全角→半角、大文字→小文字に正規化して検索しやすくする"""
    return unicodedata.normalize("NFKC", text).lower()


def _builtin_df() -> pd.DataFrame:
    df = pd.DataFrame(_BUILTIN, columns=_COLUMNS)
    df["source"] = "組み込み"
    return df


def load_mext_csv() -> pd.DataFrame | None:
    """文部科学省CSVを読み込む（setup_db.py で作成済みの場合）"""
    if not MEXT_CSV.exists():
        return None
    df = pd.read_csv(MEXT_CSV, dtype=str)
    for col in ["energy", "protein", "fat", "carb", "fiber", "sodium"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df["source"] = "文部科学省DB"
    return df[_COLUMNS + ["source"]]


def load_custom_foods(user_email: str) -> pd.DataFrame:
    """Firestoreからカスタム食品を読み込む"""
    docs = _custom_col(user_email).stream()
    data = [doc.to_dict() for doc in docs]
    if not data:
        return pd.DataFrame(columns=_COLUMNS + ["source"])
    df = pd.DataFrame(data)
    df["source"] = "カスタム"
    return df[_COLUMNS + ["source"]]


def save_custom_food(user_email: str, food: dict) -> None:
    """カスタム食品をFirestoreに保存する"""
    _custom_col(user_email).document(food["name"]).set({k: food[k] for k in _COLUMNS})


def delete_custom_food(user_email: str, name: str) -> None:
    """カスタム食品をFirestoreから削除する"""
    _custom_col(user_email).document(name).delete()


def get_full_db(user_email: str) -> pd.DataFrame:
    """全ソースを統合したDataFrameを返す（カスタム＞文部科学省＞組み込みの優先順）"""
    frames = [load_custom_foods(user_email)]
    mext = load_mext_csv()
    if mext is not None:
        frames.append(mext)
    frames.append(_builtin_df())
    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates(subset="name", keep="first")
    return df


def search_food(query: str, user_email: str, limit: int = 20) -> list[dict]:
    """食品名でインクリメンタル検索し、dictのリストを返す"""
    if not query.strip():
        return []
    q = _normalize(query)
    df = get_full_db(user_email)
    df["_norm"] = df["name"].apply(_normalize)
    prefix = df[df["_norm"].str.startswith(q)]
    contains = df[df["_norm"].str.contains(q, regex=False) & ~df["_norm"].str.startswith(q)]
    result = pd.concat([prefix, contains]).head(limit)
    return result.drop(columns="_norm").to_dict("records")
