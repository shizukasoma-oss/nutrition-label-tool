"""栄養素計算と表示テキスト生成"""

from __future__ import annotations


def _round_label(value: float, nutrient: str) -> str:
    """食品表示基準に基づく丸め処理"""
    if nutrient == "energy":
        # 熱量: 1kcal未満は0、10kcal未満は1kcal単位
        v = round(value)
        return str(v)
    elif nutrient == "sodium_equiv":
        # 食塩相当量: 0.1g単位
        return f"{value:.1f}"
    else:
        # たんぱく質・脂質・炭水化物・糖質・食物繊維: 0.1g単位
        return f"{value:.1f}"


def calculate_nutrition(ingredients: list[dict]) -> dict:
    """
    材料リストから栄養素合計を計算する。

    ingredients: [{"name": str, "amount": float, "energy": float, ...}, ...]
    各栄養値は 100g あたりの値。amount は実使用量(g)。

    Returns: {"energy": float, "protein": float, "fat": float,
              "carb": float, "fiber": float, "sugar": float, "salt": float}
    """
    totals = {"energy": 0.0, "protein": 0.0, "fat": 0.0,
              "carb": 0.0, "fiber": 0.0, "sodium": 0.0}

    for ing in ingredients:
        ratio = ing["amount"] / 100.0
        for key in totals:
            totals[key] += float(ing.get(key, 0.0)) * ratio

    sugar = max(totals["carb"] - totals["fiber"], 0.0)
    # 食塩相当量(g) = ナトリウム(mg) × 2.54 / 1000
    salt = totals["sodium"] * 2.54 / 1000.0

    return {
        "energy":  totals["energy"],
        "protein": totals["protein"],
        "fat":     totals["fat"],
        "carb":    totals["carb"],
        "fiber":   totals["fiber"],
        "sugar":   sugar,
        "salt":    salt,
    }


def format_label(ingredients: list[dict], bag_weight: float, num_bags: int = 1) -> str:
    """
    栄養成分表示テキストを生成する。

    num_bags: レシピで何袋できるか。1より大きい場合は合計栄養値を num_bags で割る。

    Returns: 例)
    栄養成分表示　1袋（60g）当たり　熱量90kcal、たんぱく質1.9g、脂質1.9g、
    炭水化物7.9g（糖質6.2g、食物繊維1.7g）、食塩相当量1.1g（推定値）
    """
    n_total = calculate_nutrition(ingredients)
    n = {k: v / num_bags for k, v in n_total.items()}
    weight = int(bag_weight) if bag_weight == int(bag_weight) else bag_weight

    parts = [
        f"栄養成分表示　1袋（{weight}g）当たり",
        f"熱量{_round_label(n['energy'], 'energy')}kcal",
        f"たんぱく質{_round_label(n['protein'], 'protein')}g",
        f"脂質{_round_label(n['fat'], 'fat')}g",
        f"炭水化物{_round_label(n['carb'], 'carb')}g（糖質{_round_label(n['sugar'], 'sugar')}g）",
        f"食塩相当量{_round_label(n['salt'], 'sodium_equiv')}g（推定値）",
    ]
    return "　".join(parts)
