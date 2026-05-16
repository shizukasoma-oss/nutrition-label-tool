"""栄養成分表示ラベル自動生成ツール - Streamlit メインアプリ"""

import json

import streamlit as st
import streamlit.components.v1 as components

from calculator import calculate_nutrition, format_label
from firebase_utils import is_allowed_user, sign_in
from food_db import (
    delete_custom_food,
    load_custom_foods,
    save_custom_food,
    search_food,
)
from recipes import delete_recipe, duplicate_recipe, load_recipes, save_recipe

st.set_page_config(page_title="栄養成分表示ラベル作成", page_icon="🏷️", layout="wide")

# Streamlitのデフォルトメニュー・フッター・ツールバーを非表示
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
[data-testid="stToolbar"] {visibility: hidden;}
[data-testid="stDecoration"] {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ── ログイン画面 ───────────────────────────────────────────────────────────
if "user" not in st.session_state:
    st.title("🏷️ 栄養成分表示ラベル作成ツール")
    st.subheader("ログイン")
    email = st.text_input("メールアドレス")
    password = st.text_input("パスワード", type="password")
    if st.button("ログイン", type="primary"):
        with st.spinner("確認中..."):
            result = sign_in(email, password)
        if result and is_allowed_user(result["email"]):
            st.session_state.user = {"email": result["email"]}
            st.rerun()
        else:
            st.session_state.pop("_login_error", None)
            st.error("ログインできません。メールアドレスとパスワードを確認してください。")
    st.stop()

user_email = st.session_state.user["email"]

# ── セッション状態の初期化 ──────────────────────────────────────────────────
if "ingredients" not in st.session_state:
    st.session_state.ingredients = []
if "search_results" not in st.session_state:
    st.session_state.search_results = []
if "selected_index" not in st.session_state:
    st.session_state.selected_index = 0
if "product_name" not in st.session_state:
    st.session_state.product_name = ""
if "bag_weight_val" not in st.session_state:
    st.session_state.bag_weight_val = None
if "num_bags_val" not in st.session_state:
    st.session_state.num_bags_val = None
if "loaded_recipe_name" not in st.session_state:
    st.session_state.loaded_recipe_name = None
if "load_id" not in st.session_state:
    st.session_state.load_id = 0


# ── ヘッダー ───────────────────────────────────────────────────────────────
title_col, logout_col = st.columns([8, 1])
title_col.title("🏷️ 栄養成分表示ラベル作成ツール")
title_col.caption("材料と分量を入力すると、食品表示用のテキストを自動生成します。")
if logout_col.button("ログアウト"):
    del st.session_state["user"]
    st.rerun()

# ── 保存済みレシピを読み込む ───────────────────────────────────────────────
saved_recipes = load_recipes(user_email)
if saved_recipes:
    with st.expander(f"📂 保存済みレシピ（{len(saved_recipes)}件）"):
        for recipe in saved_recipes:
            _kcal_per_bag = calculate_nutrition(recipe["ingredients"])["energy"] / recipe["num_bags"]
            st.write(f"**{recipe['name']}**　{recipe['bag_weight']}g × {recipe['num_bags']}個　{round(_kcal_per_bag)}kcal/袋")
            rc1, rc2, rc3 = st.columns(3)
            if rc1.button("📂 読み込む", key=f"load_{recipe['name']}", use_container_width=True):
                st.session_state.load_id += 1
                for k in list(st.session_state.keys()):
                    if k.startswith("amount_"):
                        del st.session_state[k]
                st.session_state.ingredients = [dict(ing) for ing in recipe["ingredients"]]
                st.session_state.bag_weight_val = recipe["bag_weight"]
                st.session_state.num_bags_val = recipe["num_bags"]
                st.session_state.product_name = recipe["name"]
                st.session_state.loaded_recipe_name = recipe["name"]
                st.rerun()
            if rc2.button("📋 複製", key=f"dup_{recipe['name']}", use_container_width=True):
                new_name = duplicate_recipe(user_email, recipe["name"])
                st.session_state.load_id += 1
                for k in list(st.session_state.keys()):
                    if k.startswith("amount_"):
                        del st.session_state[k]
                st.session_state.ingredients = [dict(ing) for ing in recipe["ingredients"]]
                st.session_state.bag_weight_val = recipe["bag_weight"]
                st.session_state.num_bags_val = recipe["num_bags"]
                st.session_state.product_name = new_name
                st.session_state.loaded_recipe_name = new_name
                st.toast(f"「{new_name}」を作成しました。商品名と重量を変更して保存してください。", icon="📋")
                st.rerun()
            if rc3.button("🗑️ 削除", key=f"del_recipe_{recipe['name']}", use_container_width=True):
                delete_recipe(user_email, recipe["name"])
                st.rerun()
            st.divider()

# ── 商品名 ＆ 1袋の重量 ＆ 個数 ──────────────────────────────────────────
p_col, w_col, n_col, save_col = st.columns([3, 2, 2, 1], vertical_alignment="bottom")
product_name = p_col.text_input(
    "商品名",
    key="product_name",
    placeholder="例: 塩クッキー",
)
bag_weight = w_col.number_input(
    "1袋の重量（g）",
    min_value=1.0,
    max_value=10000.0,
    value=st.session_state.bag_weight_val,
    step=1.0,
    placeholder="例: 30",
    help="ラベルに「1袋（○○g）当たり」と表示される重量です。",
)
st.session_state.bag_weight_val = bag_weight

num_bags_input = n_col.number_input(
    "何個できますか？",
    min_value=1,
    max_value=10000,
    value=st.session_state.num_bags_val,
    step=1,
    placeholder="例: 6",
    help="このレシピの材料で何袋（個）できるかを入力してください。栄養値をその数で割って1袋あたりに換算します。",
)
st.session_state.num_bags_val = num_bags_input
num_bags = int(num_bags_input) if num_bags_input else 1

if save_col.button("💾 保存", disabled=(not product_name.strip() or not st.session_state.ingredients)):
    new_name = product_name.strip()
    if st.session_state.loaded_recipe_name and st.session_state.loaded_recipe_name != new_name:
        delete_recipe(user_email, st.session_state.loaded_recipe_name)
    save_recipe(
        user_email=user_email,
        name=new_name,
        bag_weight=bag_weight or 0,
        num_bags=num_bags,
        ingredients=st.session_state.ingredients,
    )
    st.session_state.loaded_recipe_name = new_name
    st.toast(f"「{new_name}」を保存しました！", icon="✅")
    st.rerun()

st.divider()

# ── 材料追加エリア ─────────────────────────────────────────────────────────
st.subheader("材料を追加")

col_search, col_amount, col_add = st.columns([4, 2, 1], vertical_alignment="bottom")

with col_search:
    query = st.text_input("食品名を入力して検索", placeholder="例: 薄力粉、バター、砂糖")

results = search_food(query, user_email) if query else []

selected_food: dict | None = None
if results:
    with col_search:
        options = [f"{r['name']}（{r['source']}）" for r in results]
        sel_idx = st.selectbox(
            "検索結果",
            range(len(options)),
            format_func=lambda i: options[i],
            label_visibility="collapsed",
        )
        selected_food = results[sel_idx]
elif query:
    st.info(f"「{query}」はDBに見つかりません。下の「カスタム食品を登録」から手動で追加できます。")

with col_amount:
    amount = st.number_input("分量（g）", min_value=0.1, max_value=10000.0, value=None, step=0.5, placeholder="例: 100")

with col_add:
    if st.button("追加", type="primary", disabled=(selected_food is None or amount is None)):
        entry = {**selected_food, "amount": amount}
        st.session_state.ingredients.append(entry)
        st.rerun()

# ── カスタム食品登録 ───────────────────────────────────────────────────────
with st.expander("➕ DBにない食品をカスタム登録"):
    cc0, _ = st.columns([3, 5])
    c_name = cc0.text_input("食品名", key="c_name")

    ref_col, _ = st.columns([3, 5])
    c_ref = ref_col.number_input(
        "ラベルの基準量（g）",
        min_value=0.1, max_value=1000.0, value=None, step=0.5,
        placeholder="例: 100",
        key="c_ref",
        help="ラベルに「14g当たり」と書いてあれば14を入力。100gあたりなら100のまま。",
    )
    c_ref_val = float(c_ref) if c_ref else 100.0

    cc1, cc2, cc3 = st.columns(3)
    ref_label = f"{c_ref_val:g}g"
    c_energy  = cc1.number_input(f"熱量（kcal / {ref_label}）",     min_value=0.0, value=None, step=1.0, placeholder="0", key="c_energy")
    c_protein = cc2.number_input(f"たんぱく質（g / {ref_label}）",  min_value=0.0, value=None, step=0.1, placeholder="0", key="c_protein")
    c_fat     = cc3.number_input(f"脂質（g / {ref_label}）",        min_value=0.0, value=None, step=0.1, placeholder="0", key="c_fat")
    c_carb    = cc1.number_input(f"炭水化物（g / {ref_label}）",    min_value=0.0, value=None, step=0.1, placeholder="0", key="c_carb")
    c_sodium  = cc2.number_input(f"ナトリウム（mg / {ref_label}）", min_value=0.0, value=None, step=1.0, placeholder="0", key="c_sodium")

    c_energy  = float(c_energy  or 0)
    c_protein = float(c_protein or 0)
    c_fat     = float(c_fat     or 0)
    c_carb    = float(c_carb    or 0)
    c_sodium  = float(c_sodium  or 0)

    scale = 100.0 / c_ref_val
    if c_ref_val != 100.0:
        st.caption(
            f"100gあたりに換算 → 熱量 **{c_energy * scale:.1f}** kcal　"
            f"たんぱく質 **{c_protein * scale:.1f}** g　"
            f"脂質 **{c_fat * scale:.1f}** g　"
            f"炭水化物 **{c_carb * scale:.1f}** g　"
            f"ナトリウム **{c_sodium * scale:.1f}** mg"
        )

    save_col2, _, _ = st.columns([2, 3, 3])
    if save_col2.button("登録する", disabled=(not c_name.strip())):
        save_custom_food(user_email, {
            "name":    c_name.strip(),
            "energy":  round(c_energy  * scale, 2),
            "protein": round(c_protein * scale, 2),
            "fat":     round(c_fat     * scale, 2),
            "carb":    round(c_carb    * scale, 2),
            "fiber":   0.0,
            "sodium":  round(c_sodium  * scale, 2),
        })
        st.success(f"「{c_name.strip()}」を登録しました。検索から使用できます。")
        st.rerun()

# ── カスタム食品管理 ───────────────────────────────────────────────────────
custom_df = load_custom_foods(user_email)
if not custom_df.empty:
    with st.expander(f"📋 登録済みカスタム食品（{len(custom_df)}件）"):
        for _, row in custom_df.iterrows():
            dc1, dc2 = st.columns([6, 1])
            dc1.write(
                f"**{row['name']}** — 熱量{row['energy']:.0f}kcal / たんぱく質{row['protein']:.1f}g"
                f" / 脂質{row['fat']:.1f}g / 炭水化物{row['carb']:.1f}g"
                f" / Na{row['sodium']:.0f}mg"
            )
            if dc2.button("削除", key=f"del_custom_{row['name']}"):
                delete_custom_food(user_email, row["name"])
                st.rerun()

st.divider()

# ── 材料リスト ─────────────────────────────────────────────────────────────
st.subheader("材料リスト")

if not st.session_state.ingredients:
    st.info("まだ材料が追加されていません。上のフォームから材料を追加してください。")
else:
    to_delete = None
    for i, ing in enumerate(st.session_state.ingredients):
        row_cols = st.columns([3, 2, 0.8])
        row_cols[0].write(f"**{ing['name']}**")
        new_amount = row_cols[1].number_input(
            "分量(g)",
            min_value=0.1,
            max_value=10000.0,
            value=float(ing["amount"]),
            step=0.5,
            key=f"amount_{st.session_state.load_id}_{i}",
            label_visibility="collapsed",
        )
        if new_amount != ing["amount"]:
            st.session_state.ingredients[i]["amount"] = new_amount
            st.rerun()
        ratio = new_amount / 100.0
        if row_cols[2].button("✕", key=f"del_{i}"):
            to_delete = i
        st.caption(
            f"熱量: {ing['energy'] * ratio:.1f}kcal　"
            f"たんぱく質: {ing['protein'] * ratio:.1f}g　"
            f"脂質: {ing['fat'] * ratio:.1f}g　"
            f"炭水化物: {ing['carb'] * ratio:.1f}g"
        )

    if to_delete is not None:
        st.session_state.ingredients.pop(to_delete)
        st.rerun()

    n_total = calculate_nutrition(st.session_state.ingredients)
    label_total = "合計" if num_bags == 1 else f"合計（{num_bags}個分）"
    st.markdown(
        f"**{label_total}** ─ 熱量: **{n_total['energy']:.1f}kcal**　"
        f"たんぱく質: **{n_total['protein']:.1f}g**　"
        f"脂質: **{n_total['fat']:.1f}g**　"
        f"炭水化物: **{n_total['carb']:.1f}g**"
    )
    if num_bags > 1:
        st.markdown(
            f"**↳ 1袋あたり** ─ 熱量: **{n_total['energy'] / num_bags:.1f}kcal**　"
            f"たんぱく質: **{n_total['protein'] / num_bags:.1f}g**　"
            f"脂質: **{n_total['fat'] / num_bags:.1f}g**　"
            f"炭水化物: **{n_total['carb'] / num_bags:.1f}g**"
        )

    if st.button("材料をすべてクリア"):
        st.session_state.ingredients = []
        st.session_state.product_name = ""
        st.session_state.bag_weight_val = None
        st.session_state.num_bags_val = None
        st.session_state.loaded_recipe_name = None
        st.rerun()

st.divider()

# ── ラベル生成・出力 ───────────────────────────────────────────────────────
st.subheader("栄養成分表示テキスト")

if st.session_state.ingredients:
    if not bag_weight:
        st.warning("「1袋の重量」を入力するとラベルテキストが生成されます。")
    else:
        label = format_label(st.session_state.ingredients, bag_weight, num_bags)
        label_js = json.dumps(label)
        components.html(f"""
<div style="background:#f0f2f6;border-radius:6px;padding:14px 120px 14px 14px;
            position:relative;font-family:monospace;font-size:14px;line-height:1.6;
            word-break:break-all;">
  <span id="label-text">{label}</span>
  <textarea id="copy-area" style="position:absolute;left:-9999px;">{label}</textarea>
  <button id="copy-btn" onclick="
    var ta=document.getElementById('copy-area');
    ta.select();
    ta.setSelectionRange(0,99999);
    document.execCommand('copy');
    var b=document.getElementById('copy-btn');
    b.innerText='✅ コピーしました';
    b.style.background='#21c55d';
    setTimeout(function(){{b.innerText='📋 コピー';b.style.background='#ff4b4b';}},2000);
  " style="position:absolute;top:10px;right:10px;background:#ff4b4b;color:white;
           border:none;border-radius:4px;padding:6px 12px;cursor:pointer;
           font-size:13px;font-family:sans-serif;">📋 コピー</button>
</div>
""", height=80)

    n_total = calculate_nutrition(st.session_state.ingredients)
    n = {k: v / num_bags for k, v in n_total.items()}
    with st.expander("📊 栄養成分の内訳（1袋あたり）"):
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("熱量", f"{n['energy']:.0f} kcal")
        c2.metric("たんぱく質", f"{n['protein']:.1f} g")
        c3.metric("脂質", f"{n['fat']:.1f} g")
        c4.metric("炭水化物", f"{n['carb']:.1f} g")
        c5.metric("食塩相当量", f"{n['salt']:.1f} g")

        sugar = max(n["carb"] - n["fiber"], 0)
        st.caption(
            f"糖質 = 炭水化物 − 食物繊維 = {n['carb']:.1f} − {n['fiber']:.1f} = {sugar:.1f} g　"
            f"｜　食塩相当量 = ナトリウム × 2.54 / 1000"
        )
else:
    st.info("材料を追加すると、ここに栄養成分表示テキストが生成されます。")

# ── フッター ───────────────────────────────────────────────────────────────
st.divider()
st.caption("※ 栄養計算は自動で「推定値」として表示されます。")
