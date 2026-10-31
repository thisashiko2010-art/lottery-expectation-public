"""lottery_engine.py の自己検証"""
from fractions import Fraction
from math import comb
import lottery_engine as le

# ロトの総組合せ数・代表的な公式確率との照合
assert comb(31, 5) == 169_911
assert comb(43, 6) == 6_096_454
assert comb(37, 7) == 10_295_472

mini = le.mini_loto()
assert mini.tiers[0].probability == Fraction(1, 169_911)
assert mini.tiers[1].probability == Fraction(1, 33_982) or abs(float(mini.tiers[1].probability) - 1/33_982) < 1e-8

l6 = le.loto6()
assert l6.tiers[0].probability == Fraction(1, 6_096_454)
assert abs(float(l6.tiers[1].probability) - 1/1_016_076) < 1e-10

l7 = le.loto7()
assert l7.tiers[0].probability == Fraction(1, 10_295_472)
assert abs(float(l7.tiers[1].probability) - 1/735_391) < 1e-8

# Numbers: 全桁異なる/ペア/2ペア/トリプルの並べ替え数
assert le._permutation_count("123") == 6
assert le._permutation_count("112") == 3
assert le._permutation_count("1234") == 24
assert le._permutation_count("1123") == 12
assert le._permutation_count("1122") == 6
assert le._permutation_count("1112") == 4

# Numbers3/4 straight / box / set / mini の期待払戻額が理論上ほぼ90円
for game, picks in [("ナンバーズ3", ["123", "112"]), ("ナンバーズ4", ["1234", "1123", "1122", "1112"])]:
    for pick in picks:
        for bet in ("straight", "box", "set"):
            r = le.numbers_game(game, pick, bet)
            assert abs(float(r.expected_payout_yen) - 90) < 0.2, (game, pick, bet, r.expected_payout_yen)
assert le.numbers_game("ナンバーズ3", "123", "mini").tiers[0].probability == Fraction(1, 100)

# Bingo5: 5^8通りを漏れなく分類し、公式確率と一致
dist = le.bingo5_line_distribution()
assert sum(dist.values()) == 390_625
assert dist[8] == 1
assert dist[6] == 16
assert dist[5] == 48
assert dist[4] == 192
assert dist[3] == 1_248
assert dist[2] == 6_656
assert dist[1] == 56_832

print("OK: 全テスト通過")
print("BINGO5 distribution:", {k:v for k,v in dist.items() if v})
