import streamlit as st
import lottery_engine as le

st.set_page_config(
    page_title="数字選択式宝くじ・理論確率分析",
    page_icon="🎯",
    layout="wide",
)

st.title("数字選択式宝くじ・理論確率分析")
st.caption("理論確率エンジン Ver.0.1 — 過去データを使わない基礎計算")

st.info(
    "これは計算エンジンの動作確認用プロトタイプです。"
    "賞金は仮置きの理論値を含み、実際の当せん金・キャリーオーバー・"
    "発売額に連動した賞金配分はまだ反映していません。購入判断には使用しないでください。"
)

def yen(value):
    return f"¥{value:,.2f}"

def prob_text(p):
    if not p:
        return "0"
    return f"1 / {float(1 / p):,.3f}"

def result_rows(result):
    rows = []
    for tier in result.tiers:
        rows.append({
            "等級・申込タイプ": tier.rank,
            "当せん条件": tier.condition,
            "理論確率": prob_text(tier.probability),
            "確率（%）": float(tier.probability * 100),
            "仮定賞金": f"¥{tier.theoretical_prize_yen:,}",
            "期待払戻寄与": float(tier.probability * tier.theoretical_prize_yen),
        })
    return rows

tab_compare, tab_numbers, tab_bingo, tab_notes = st.tabs(
    ["6種類の比較", "ナンバーズ詳細", "ビンゴ5詳細", "計算上の注意"]
)

with tab_compare:
    st.subheader("6種類の基準値比較")
    results = le.all_game_baselines()
    data = []
    for r in results:
        data.append({
            "ゲーム": r.game,
            "1口価格": f"¥{r.ticket_price_yen:,}",
            "期待払戻額": yen(float(r.expected_payout_yen)),
            "期待収支": yen(float(r.expected_net_yen)),
            "理論回収率": f"{float(r.theoretical_return_rate * 100):.2f}%",
        })
    st.dataframe(data, use_container_width=True, hide_index=True)

    st.caption(
        "ナンバーズは比較用にナンバーズ3「123」ストレート、"
        "ナンバーズ4「1234」ストレートを表示しています。"
        "数字の構成や申込タイプによって等級別の賞金が変わる場合があります。"
    )

    st.subheader("各ゲームの等級別確率")
    selected_game = st.selectbox(
        "表示するゲーム",
        ["ミニロト", "ロト6", "ロト7", "ナンバーズ3（123ストレート）",
         "ナンバーズ4（1234ストレート）", "ビンゴ5"],
    )
    lookup = {
        "ミニロト": le.mini_loto(),
        "ロト6": le.loto6(),
        "ロト7": le.loto7(),
        "ナンバーズ3（123ストレート）": le.numbers_game("ナンバーズ3", "123", "straight"),
        "ナンバーズ4（1234ストレート）": le.numbers_game("ナンバーズ4", "1234", "straight"),
        "ビンゴ5": le.bingo5(),
    }
    r = lookup[selected_game]
    st.dataframe(result_rows(r), use_container_width=True, hide_index=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("1口の期待払戻額", yen(float(r.expected_payout_yen)))
    c2.metric("1口の期待収支", yen(float(r.expected_net_yen)))
    c3.metric("理論回収率", f"{float(r.theoretical_return_rate * 100):.2f}%")

with tab_numbers:
    st.subheader("ナンバーズ3・4 申込タイプ別計算")
    game = st.selectbox("ゲーム", ["ナンバーズ3", "ナンバーズ4"])
    digit_count = 3 if game == "ナンバーズ3" else 4
    default_pick = "123" if digit_count == 3 else "1234"
    pick = st.text_input("買い目（数字を桁数分入力。先頭の0も有効）", value=default_pick, max_chars=digit_count)
    types = ["straight", "box", "set"] + (["mini"] if digit_count == 3 else [])
    type_labels = {
        "straight": "ストレート",
        "box": "ボックス",
        "set": "セット",
        "mini": "ミニ",
    }
    selected_type = st.selectbox(
        "申込タイプ",
        types,
        format_func=lambda x: type_labels[x],
    )
    if st.button("この条件で計算", type="primary"):
        try:
            r = le.numbers_game(game, pick, selected_type)
            st.dataframe(result_rows(r), use_container_width=True, hide_index=True)
            c1, c2, c3 = st.columns(3)
            c1.metric("購入金額", f"¥{r.ticket_price_yen:,}")
            c2.metric("期待払戻額", yen(float(r.expected_payout_yen)))
            c3.metric("期待収支", yen(float(r.expected_net_yen)))
            st.caption(
                "数字の出現確率自体はすべて同じです。ボックス・セットの賞金構造は"
                "数字の重複パターンによって変わります。"
            )
        except Exception as exc:
            st.error(str(exc))

with tab_bingo:
    st.subheader("ビンゴ5 成立ライン数の厳密集計")
    dist = le.bingo5_line_distribution()
    total = 5 ** 8
    rows = []
    for lines in range(8, -1, -1):
        count = dist[lines]
        if count:
            rows.append({
                "成立ライン": f"{lines}ライン",
                "組合せ数": f"{count:,}",
                "理論確率": prob_text(le.Fraction(count, total)),
                "確率（%）": count / total * 100,
            })
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.metric("全組合せ数", f"{total:,}通り")
    st.caption("8マスそれぞれ5択として、全256通りの一致・不一致マスクを重み付け集計しています。")

with tab_notes:
    st.subheader("この版で計算していること")
    st.markdown(
        """
        - ロト系：本数字・ボーナス数字の組合せから理論確率を計算
        - ナンバーズ：数字の重複数に応じた並べ替え数を計算
        - ビンゴ5：8マスの一致パターンを全列挙して成立ライン数を集計
        - 期待払戻額：各等級の理論確率 × 仮定賞金の合計
        - 期待収支：期待払戻額 − 購入金額

        ### まだ実装していないこと
        - 最新の公式賞金体系・賞金配分ルールとの完全照合
        - ロト6・ロト7のキャリーオーバー反映
        - 発売額・当せん口数に応じた実際の賞金推定
        - 他の購入者との数字重複・賞金分配リスク推定
        - 過去抽せんデータの取得・保存
        - 月間3,000円の予算管理・購入履歴
        """
    )
    st.warning(
        "理論確率は過去の当せん数字の頻度によって変化しません。"
        "本アプリは当せんを予測したり、利益を保証したりするものではありません。"
    )

st.divider()
st.caption("Lottery Expectation Analysis — prototype / v0.1")
