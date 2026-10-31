"""
数字選択式宝くじ・理論確率計算エンジン v0.1
対象: ナンバーズ3 / ナンバーズ4 / ミニロト / ロト6 / ロト7 / ビンゴ5

注意:
- 確率は抽せん機構の理論確率。過去結果で補正しない。
- 賞金は公式サイト掲載の理論値を初期値としている。実際の賞金は発売額・当せん口数等で変動する。
- ロト系の賞金期待値は「理論賞金を固定額と仮定した基準値」。キャリーオーバー・賞金配分・上限・不的中等級からの上乗せは未反映。
- ナンバーズのセット賞金は公式の理論値の構造を反映（100円未満切捨てを考慮）。
- ビンゴ5の確率は8マスの一致/不一致を全256パターン列挙し、各マス5択の重みを付けて厳密計算。
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import comb, factorial
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class Tier:
    rank: str
    condition: str
    probability: Fraction
    theoretical_prize_yen: int


@dataclass(frozen=True)
class GameResult:
    game: str
    ticket_price_yen: int
    tiers: Tuple[Tier, ...]

    @property
    def expected_payout_yen(self) -> Fraction:
        return sum(
            (t.probability * t.theoretical_prize_yen for t in self.tiers),
            Fraction(0, 1),
        )

    @property
    def expected_net_yen(self) -> Fraction:
        return self.expected_payout_yen - self.ticket_price_yen

    @property
    def theoretical_return_rate(self) -> Fraction:
        return self.expected_payout_yen / self.ticket_price_yen


def _tier(rank: str, condition: str, favorable: int, total: int, prize: int) -> Tier:
    return Tier(rank, condition, Fraction(favorable, total), prize)


def lotto_tiers(
    game: str,
    pool_size: int,
    main_count: int,
    bonus_count: int,
    ticket_price: int,
    prizes: Dict[str, int],
) -> GameResult:
    """
    ロト系の当せん確率を組合せで計算する。
    抽せん: 本数字 main_count 個、その後残りから bonus_count 個。
    """
    total = comb(pool_size, main_count) * comb(pool_size - main_count, bonus_count)
    tiers: List[Tier] = []
    n = main_count

    # 1等: 本数字が全て一致
    f1 = comb(n, n) * comb(pool_size - n, 0) * comb(pool_size - n, bonus_count)
    tiers.append(_tier("1等", f"本数字{n}個一致", f1, total, prizes["1等"]))

    # 2等: 本数字 n-1 個 + ボーナス1個（ボーナスから必要なチケット数字を選ぶ）
    if bonus_count >= 1:
        f2 = (
            comb(n, n - 1)
            * comb(pool_size - n, 1)
            * comb(n - (n - 1), 1)
            * comb(pool_size - n - 1, bonus_count - 1)
        )
        tiers.append(_tier("2等", f"本数字{n-1}個＋ボーナス1個", f2, total, prizes["2等"]))

    # 3等: 本数字 n-1 個、ボーナス数字は不一致
    if "3等" in prizes:
        f3 = (
            comb(n, n - 1)
            * comb(pool_size - n, 1)
            * comb(pool_size - n - 1, bonus_count)
        )
        tiers.append(_tier("3等", f"本数字{n-1}個（ボーナス不一致）", f3, total, prizes["3等"]))

    # 4等以下: 本数字一致数だけで判定する等級
    if game in ("ミニロト", "ロト6", "ロト7"):
        if game == "ミニロト":
            # 3等は本数字4個、4等は本数字3個。
            k_prizes = [(3, "4等"),]
        elif game == "ロト6":
            # 4等=4個、5等=3個
            k_prizes = [(4, "4等"), (3, "5等")]
        else:
            # ロト7: 4等=5個、5等=4個、6等=3個+ボーナス1個以上
            k_prizes = [(5, "4等"), (4, "5等")]
        for k, rank in k_prizes:
            # ここではボーナス一致を問わない。ボーナスの選び方すべてを含む。
            favorable = comb(n, k) * comb(pool_size - n, n - k) * comb(pool_size - n, bonus_count)
            tiers.append(_tier(rank, f"本数字{k}個一致", favorable, total, prizes[rank]))

    # ロト7 6等: 本数字3個 + ボーナス1個または2個
    if game == "ロト7":
        k = 3
        non_ticket_in_main = n - k
        remaining_ticket = n - k
        remaining_non_ticket = pool_size - n - non_ticket_in_main
        bonus_favorable = sum(
            comb(remaining_ticket, j) * comb(remaining_non_ticket, bonus_count - j)
            for j in range(1, min(bonus_count, remaining_ticket) + 1)
        )
        f6 = comb(n, k) * comb(pool_size - n, non_ticket_in_main) * bonus_favorable
        tiers.append(_tier("6等", "本数字3個＋ボーナス1個以上", f6, total, prizes["6等"]))

    # 等級順に表示
    order = {"1等": 1, "2等": 2, "3等": 3, "4等": 4, "5等": 5, "6等": 6}
    tiers.sort(key=lambda x: order[x.rank])
    return GameResult(game, ticket_price, tuple(tiers))


def mini_loto() -> GameResult:
    # 本数字5個、ボーナス1個。賞金は公式掲載の理論値。
    return lotto_tiers(
        "ミニロト", 31, 5, 1, 200,
        {"1等": 10_000_000, "2等": 150_000, "3等": 10_000, "4等": 1_000},
    )


def loto6() -> GameResult:
    return lotto_tiers(
        "ロト6", 43, 6, 1, 200,
        {"1等": 200_000_000, "2等": 10_000_000, "3等": 300_000, "4等": 6_800, "5等": 1_000},
    )


def loto7() -> GameResult:
    return lotto_tiers(
        "ロト7", 37, 7, 2, 300,
        {"1等": 700_000_000, "2等": 6_100_000, "3等": 500_000, "4等": 6_500, "5等": 1_400, "6等": 1_000},
    )


def _permutation_count(digits: str) -> int:
    """数字列の異なる並べ替え数。"""
    n = len(digits)
    denominator = 1
    for d in set(digits):
        denominator *= factorial(digits.count(d))
    return factorial(n) // denominator


def _floor_100(yen: Fraction) -> int:
    """賞金の100円未満切捨て。"""
    return (yen.numerator // (yen.denominator * 100)) * 100


def numbers_game(game: str, pick: str, bet_type: str) -> GameResult:
    """
    Numbers3/4の指定数字に対する理論期待値。
    bet_type: straight / box / set / mini（miniはNumbers3のみ）
    """
    n = 3 if game == "ナンバーズ3" else 4
    if len(pick) != n or not pick.isdigit():
        raise ValueError(f"{game}は{n}桁の数字を指定してください（先頭0も有効）。")
    if bet_type not in ({"straight", "box", "set", "mini"} if n == 3 else {"straight", "box", "set"}):
        raise ValueError("申込タイプが正しくありません。")
    if bet_type in ("box", "set") and len(set(pick)) == 1:
        raise ValueError("ボックス・セットでは全桁同一の数字は申し込めません。")

    total = 10 ** n
    straight_full = 90_000 if n == 3 else 900_000
    m = _permutation_count(pick)

    if bet_type == "straight":
        tiers = (_tier("ストレート", "数字と並び順が完全一致", 1, total, straight_full),)
    elif bet_type == "box":
        box_prize = straight_full // m
        tiers = (_tier("ボックス", "数字の構成が一致（順不同）", m, total, box_prize),)
    elif bet_type == "set":
        # セットはストレートとボックスを半分ずつ購入。
        # ボックス側の理論賞金は、全額ボックス賞金の半額（100円未満切捨て）。
        set_box_prize = _floor_100(Fraction(straight_full, 2 * m))
        set_straight_prize = straight_full // 2 + set_box_prize
        tiers = (
            _tier("セット（ストレート）", "数字と並び順が完全一致", 1, total, set_straight_prize),
            _tier("セット（ボックス）", "数字の構成が一致（ストレートを除く）", m - 1, total, set_box_prize),
        )
    else:  # Numbers3 mini
        tiers = (_tier("ミニ", "下2桁が並び順も含めて一致", 10, total, 9_000),)

    return GameResult(f"{game} {pick} {bet_type}", 200, tiers)


def bingo5_line_distribution() -> Dict[int, int]:
    """
    ビンゴ5の成立ライン数ごとの全組合せ数を厳密列挙。
    8マスそれぞれが独立に5択。各マスの一致は1通り、不一致は4通り。
    256個の一致/不一致マスクを4^(不一致マス数)で重み付けする。
    """
    # 8マスの順序: 左上, 上中央, 右上, 左中, 右中, 左下, 下中央, 右下
    # 中央FREEを含む8ライン（横3、縦3、斜め2）。FREEを除いた必要マスを定義。
    lines = (
        (0, 1, 2),  # 上段
        (3, 4),     # 中段（中央FREE）
        (5, 6, 7),  # 下段
        (0, 3, 5),  # 左列
        (1, 6),     # 中央列（中央FREE）
        (2, 4, 7),  # 右列
        (0, 7),     # 左上-右下
        (2, 5),     # 右上-左下
    )
    distribution = {i: 0 for i in range(9)}
    for mask in range(1 << 8):
        hits = tuple((mask >> i) & 1 for i in range(8))
        matched_cells = sum(hits)
        line_count = sum(all(hits[i] for i in line) for line in lines)
        distribution[line_count] += 4 ** (8 - matched_cells)
    assert sum(distribution.values()) == 5 ** 8
    return distribution


def bingo5() -> GameResult:
    counts = bingo5_line_distribution()
    total = 5 ** 8
    prizes = {
        8: 5_550_000,
        6: 300_000,
        5: 45_000,
        4: 18_200,
        3: 2_500,
        2: 700,
        1: 200,
    }
    rank_by_lines = {8: "1等", 6: "2等", 5: "3等", 4: "4等", 3: "5等", 2: "6等", 1: "7等"}
    tiers = tuple(
        _tier(rank_by_lines[lines], f"{lines}ライン成立", counts[lines], total, prize)
        for lines, prize in sorted(prizes.items(), reverse=True)
    )
    return GameResult("ビンゴ5", 200, tiers)


def all_game_baselines() -> Tuple[GameResult, ...]:
    """
    6ゲームの比較用基準値。
    ナンバーズは買い方/数字構成で値が変わるため、代表例（全桁異なる）を掲載。
    """
    return (
        numbers_game("ナンバーズ3", "123", "straight"),
        numbers_game("ナンバーズ4", "1234", "straight"),
        mini_loto(),
        loto6(),
        loto7(),
        bingo5(),
    )


def format_probability(p: Fraction) -> str:
    if p == 0:
        return "0"
    return f"1/{float(1 / p):,.3f}"


def print_report() -> None:
    print("数字選択式宝くじ 理論確率エンジン v0.1")
    print("-" * 76)
    for result in all_game_baselines():
        print(f"\n{result.game}（1口 {result.ticket_price_yen:,}円）")
        for tier in result.tiers:
            print(
                f"  {tier.rank:16s} 確率 {format_probability(tier.probability):>16s}"
                f"  賞金 {tier.theoretical_prize_yen:>12,}円"
            )
        print(f"  期待払戻額: {float(result.expected_payout_yen):,.2f}円")
        print(f"  期待収支  : {float(result.expected_net_yen):,.2f}円")
        print(f"  回収率    : {float(result.theoretical_return_rate * 100):,.2f}%")

    print("\nビンゴ5 成立ライン数の全組合せ数:")
    for lines, count in sorted(bingo5_line_distribution().items()):
        if count:
            print(f"  {lines}ライン: {count:,} / 390,625")


if __name__ == "__main__":
    print_report()
