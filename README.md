# 宝くじ6種類 基礎データ収集キット v0.4

対象: ロト6 / ロト7 / ミニロト / ナンバーズ3 / ナンバーズ4 / ビンゴ5

## この版の確認
- 取得元として登録した6つのJSON配信URLは、公開データハブのREADMEに掲載されているURLと一致します。
- 配信元の更新プログラムでは、各データ行は `round` / `date` / `numbers` / `bonus` 形式で生成されています。
- `data` または `draws` などの配列ラッパーと、配列そのものの両方を読み込めます。
- ナンバーズの先頭ゼロを文字列で保持し、ビンゴ5は8列の順序と列ごとの範囲を検査します。
- テストは合成データで行い、実際の6URLからの一括取得はネットワーク制約のため未確認です。

## ローカル実行
```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
python collect.py
```

## GitHub Actions
`.github/workflows/collect.yml` を含めてリポジトリへ配置し、GitHubのActionsから `Collect lottery history` を手動実行します。収集結果はActions Artifactとして30日間保存し、リポジトリへデータを自動コミットしません。

## 出力
- `data/raw/*.json`: 取得した元JSON
- `data/normalized/*.csv`: 分析用CSV
- `reports/collection_report.json`: 出典、取得日時、SHA256、回号範囲、欠番、重複、形式エラー

## 注意
取得元は第三者の公開データです。公開されていることと、再配布が許可されていることは別です。まず個人研究用に取得し、公式発表と照合してから分析に採用してください。
