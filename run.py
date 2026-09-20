#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""layouts/ の全配列について距離を算出し、results/ に CSV を書き出す

  python run.py                      全配列 × 全ジオメトリ
  python run.py --text texts/xxx.txt お題文を指定
  python run.py --layout naginata    特定の配列だけ
"""

import argparse
import csv
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from typing_distance import (GEOMETRIES, QWERTY, DVORAK, analyze, U_MM, report)

BASE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TEXT = os.path.join(BASE, "texts", "wagahai.txt")

COLUMNS = [
    "layout", "input_mode", "geometry_id", "geometry",
    "text", "text_chars",
    "keys", "actions", "keys_per_action",
    "left_fingers_u", "left_thumb_u", "left_total_u",
    "right_fingers_u", "right_thumb_u", "right_total_u",
    "total_u", "total_mm", "per_key_u", "per_action_u", "balance_L_pct",
]


def load_text(path):
    with open(path, encoding="utf-8-sig") as f:
        return "".join(c for c in f.read() if c.strip())


def load_layouts(only=None):
    """組み込みのローマ字配列と、layouts/*.json を読み込む

    only: 配列名またはファイル名の部分一致で絞り込む（大文字小文字は区別しない）
    """
    out = [dict(QWERTY, _file="qwerty"), dict(DVORAK, _file="dvorak")]
    for path in sorted(glob.glob(os.path.join(BASE, "layouts", "*.json"))):
        stem = os.path.splitext(os.path.basename(path))[0]
        if stem.startswith("_"):
            continue
        with open(path, encoding="utf-8") as f:
            lay = json.load(f)
        lay["_file"] = stem
        out.append(lay)

    if only:
        q = only.lower()
        hit = [l for l in out
               if q in l.get("name", "").lower() or q in l["_file"].lower()]
        if not hit:
            print(f"「{only}」に一致する配列がありません。")
            print("  利用できる配列:")
            for l in out:
                print(f"    {l['_file']:<16} ({l.get('name', '?')})")
        return hit
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default=DEFAULT_TEXT)
    ap.add_argument("--layout", default=None, help="配列名の部分一致で絞り込む")
    ap.add_argument("--out", default=None)
    ap.add_argument("--segment-policy", default="min_distance",
                    choices=["min_distance", "min_actions", "longest"])
    ap.add_argument("--allow-unmapped", action="store_true",
                    help="未定義文字を読み飛ばして続行する（未完成の配列を試算する用）。"
                         "結果は過小評価になるので比較には使わないこと")
    args = ap.parse_args()

    text = load_text(args.text)
    text_name = os.path.splitext(os.path.basename(args.text))[0]
    layouts = load_layouts(args.layout)
    if not layouts:
        raise SystemExit("該当する配列がありません")

    print(f"お題文: {args.text} ({len(text)} 文字)")
    print(f"配列: {', '.join(l.get('name', '?') for l in layouts)}")

    rows, results = [], []
    failed = []
    for geom_id, geom in GEOMETRIES.items():
        for lay in layouts:
            is_romaji = lay.get("input_mode") == "romaji"
            try:
                r = analyze(text, lay, geom,
                            segment_policy=None if is_romaji else args.segment_policy,
                            allow_unmapped=args.allow_unmapped)
            except ValueError as e:
                if lay["_file"] not in [f for f, _ in failed]:
                    failed.append((lay["_file"], str(e)))
                continue
            results.append(r)
            rows.append({
                "layout": r.layout,
                "input_mode": "romaji" if is_romaji else "kana_direct",
                "geometry_id": geom_id, "geometry": geom.name,
                "text": text_name, "text_chars": len(text),
                "keys": r.keys, "actions": r.actions,
                "keys_per_action": round(r.keys_per_action, 3),
                "left_fingers_u": round(r.dist_L, 2),
                "left_thumb_u": round(r.thumb_L, 2),
                "left_total_u": round(r.left_total, 2),
                "right_fingers_u": round(r.dist_R, 2),
                "right_thumb_u": round(r.thumb_R, 2),
                "right_total_u": round(r.right_total, 2),
                "total_u": round(r.total, 2),
                "total_mm": round(r.total * U_MM, 0),
                "per_key_u": round(r.per_key, 4),
                "per_action_u": round(r.per_action, 4),
                "balance_L_pct": round(r.left_total / r.total * 100, 1) if r.total else 0,
            })

    if args.out:
        out = args.out
    elif args.layout:
        # 絞り込み時は既定の比較表を壊さないよう、別名で書き出す
        out = os.path.join(BASE, "results", f"{text_name}_{args.layout}.csv")
    else:
        out = os.path.join(BASE, "results", f"{text_name}.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)

    if failed:
        print("\n" + "=" * 60)
        print("次の配列はお題文を最後まで打てないため、計算から除外しました。")
        for fid, msg in failed:
            print(f"\n  [{fid}] " + msg.replace("\n", "\n  "))
        print("=" * 60)

    if not rows:
        raise SystemExit("\n計算できた配列がありません。定義を確認してください。")

    report(results, f"{text_name}（{len(text)}字）")
    print(f"\n{out} に {len(rows)} 行を書き出しました")
    if failed:
        print(f"  ※ {len(failed)} 配列を除外しています")


if __name__ == "__main__":
    main()
