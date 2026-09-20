# 算出結果

`python run.py` が出力する CSV です。ファイル名はお題文の名前になります。

## 列

| 列 | 内容 |
|---|---|
| `layout` / `input_mode` | 配列名、入力方式 |
| `geometry_id` / `geometry` | キーボード形状 |
| `text` / `text_chars` | お題文と文字数 |
| `keys` / `actions` / `keys_per_action` | 打鍵数、アクション数、同時率 |
| `left_fingers_u` / `left_thumb_u` / `left_total_u` | 左手の内訳（4指・親指・合計） |
| `right_fingers_u` / `right_thumb_u` / `right_total_u` | 右手の内訳 |
| `total_u` / `total_mm` | 総移動距離 |
| `per_key_u` / `per_action_u` | 1打鍵あたり、1アクションあたりの平均距離 |
| `balance_L_pct` | 総距離に占める左手の割合 |

距離の単位 u は 19.05mm です。

