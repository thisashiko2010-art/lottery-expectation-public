# 数字選択式宝くじ 理論確率エンジン v0.1

## ファイル
- `lottery_engine.py`: 理論確率・期待値計算本体
- `test_lottery_engine.py`: 確率・等級分類の自己検証

## 動作環境
- Python 3.10以上
- 外部ライブラリ不要（標準ライブラリのみ）

## 実行
```bash
python lottery_engine.py
```

## テスト
```bash
python test_lottery_engine.py
```

## Numbersの使い方
```python
import lottery_engine as le

# ナンバーズ3・123・ボックス
result = le.numbers_game("ナンバーズ3", "123", "box")

# ナンバーズ4・1123・セット
result = le.numbers_game("ナンバーズ4", "1123", "set")

# 各等級の確率・賞金
for tier in result.tiers:
    print(tier.rank, tier.probability, tier.theoretical_prize_yen)

print("期待払戻額", float(result.expected_payout_yen))
print("期待収支", float(result.expected_net_yen))
```

## 現段階の制約
- 賞金は公式掲載の理論値を基準値として設定。実際の当せん金額ではありません。
- ロト6・ロト7のキャリーオーバーはまだ期待値へ加算していません。
- ロト系の賞金配分、等級別の賞金総額移動、上限、端数処理を完全再現するものではありません。
- Numbersの理論賞金は公式表に基づくモデルです。実際の賞金は発売額・当せん口数等により変動します。
- 過去の出現頻度による当せん確率の補正は一切していません。
- ビンゴ5は8マスの各5択を独立とし、全256通りの一致/不一致状態を重み付きで厳密集計しています。

## 設計方針
確率と賞金を分離して管理します。今後、実際の賞金・キャリーオーバー・発売額データを追加しても、理論確率の部分は変更せずに使える構造です。
