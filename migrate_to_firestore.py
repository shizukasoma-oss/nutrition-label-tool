"""
既存のローカルJSONデータをFirestoreに移行する（一回だけ実行）

使い方:
  python migrate_to_firestore.py shizuka.soma@gmail.com
"""

import json
import sys
from pathlib import Path

from firebase_utils import db

BASE_DIR = Path(__file__).parent


def migrate(user_email: str) -> None:
    # ── レシピ移行 ──────────────────────────────────────────────────────────
    recipes_file = BASE_DIR / "recipes.json"
    if recipes_file.exists():
        recipes = json.loads(recipes_file.read_text(encoding="utf-8"))
        col = db.collection("nutrition_recipes").document(user_email).collection("recipes")
        for r in recipes:
            col.document(r["name"]).set(r)
            print(f"  レシピ移行: {r['name']}")
        print(f"レシピ {len(recipes)} 件を移行しました。")
    else:
        print("recipes.json が見つかりません。スキップします。")

    # ── カスタム食品移行 ────────────────────────────────────────────────────
    custom_file = BASE_DIR / "custom_foods.json"
    if custom_file.exists():
        foods = json.loads(custom_file.read_text(encoding="utf-8"))
        col = db.collection("nutrition_customFoods").document(user_email).collection("foods")
        for f in foods:
            col.document(f["name"]).set(f)
            print(f"  カスタム食品移行: {f['name']}")
        print(f"カスタム食品 {len(foods)} 件を移行しました。")
    else:
        print("custom_foods.json が見つかりません。スキップします。")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使い方: python migrate_to_firestore.py <メールアドレス>")
        sys.exit(1)
    migrate(sys.argv[1])
    print("移行完了！")
