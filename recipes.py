"""レシピの保存・読み込みロジック（Firestore版）"""

from datetime import datetime

from firebase_utils import db


def _col(user_email: str):
    return db.collection("nutrition_recipes").document(user_email).collection("recipes")


def load_recipes(user_email: str) -> list[dict]:
    docs = _col(user_email).stream()
    recipes = [doc.to_dict() for doc in docs]
    recipes.sort(key=lambda r: r.get("saved_at", ""))
    return recipes


def save_recipe(user_email: str, name: str, bag_weight: float, num_bags: int, ingredients: list[dict]) -> None:
    _col(user_email).document(name).set({
        "name": name,
        "bag_weight": bag_weight,
        "num_bags": num_bags,
        "ingredients": ingredients,
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })


def delete_recipe(user_email: str, name: str) -> None:
    _col(user_email).document(name).delete()


def duplicate_recipe(user_email: str, name: str) -> str:
    """レシピを複製して「名前 のコピー」で保存。新しい名前を返す。"""
    recipes = load_recipes(user_email)
    original = next((r for r in recipes if r["name"] == name), None)
    if not original:
        return ""
    new_name = f"{name} のコピー"
    count = 2
    existing = {r["name"] for r in recipes}
    while new_name in existing:
        new_name = f"{name} のコピー{count}"
        count += 1
    save_recipe(user_email, new_name, original["bag_weight"], original["num_bags"], original["ingredients"])
    return new_name
