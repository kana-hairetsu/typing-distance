# 配列定義

## ファイル

- `_template_input.xlsx` … 記入用の空ブック。コピーして使ってください
- `_template_layout.json` … JSON を直接書く場合の雛形
- `<配列名>.xlsx` … 記入済みブック（編集用の原本）
- `<配列名>.json` … 計算に使う定義（xlsx から生成）

`_` で始まるファイルは計算対象から除外されます。

## 追加の手順

1. `_template_input.xlsx` をコピーし、配列名を付ける
2. 各レイヤーシートに記入する
3. `python tools/xlsx_to_json.py layouts/配列名.xlsx layouts/配列名.json`
4. `python run.py`

xlsx と json の両方をコミットしてください。xlsx は人が編集するための原本、
json は計算とレビューのためのテキスト形式です。json は差分が読めるので、
定義の変更履歴を追えます。

