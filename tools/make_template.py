#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""配列定義JSONの雛形生成と検証

  python make_template.py                          雛形を生成
  python make_template.py validate 配列.json        定義を検証
  python make_template.py validate 配列.json でじこみ  お題文つきで検証
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import json
import sys
from typing_distance import (PHYSICAL_ROWS, THUMB_KEYS, SHIFT_KEYS,
                             keystrokes_kana, parse_entry, GEOMETRIES, compute)

GROUPS = {
    "清音": list("あいうえおかきくけこさしすせそたちつてとなにぬねの"
                 "はひふへほまみむめもやゆよらりるれろわゐゑをん"),
    "濁音・半濁音": list("がぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽ"),
    "小書き": list("ぁぃぅぇぉっゃゅょゎ"),
    "拗音": [b + s for b in "きしちにひみりぎじぢびぴ" for s in "ゃゅょ"],
    "外来音": [
        "うぁ", "うぃ", "うぇ", "うぉ",
        "ゔ", "ゔぁ", "ゔぃ", "ゔぇ", "ゔぉ", "ゔゅ",
        "しぇ", "じぇ", "ちぇ", "つぁ", "つぃ", "つぇ", "つぉ",
        "てぃ", "てゅ", "でぃ", "でゅ", "とぅ", "どぅ",
        "ふぁ", "ふぃ", "ふぇ", "ふぉ", "ふゅ",
        "くぁ", "くぃ", "くぇ", "くぉ", "ぐぁ", "いぇ",
    ],
    "記号": ["ー", "、", "。", "・", "？", "！", "「", "」"],
}


def build_template(path="layout_template.json"):
    m = {}
    for keys in GROUPS.values():
        for k in keys:
            m[k] = ""
    doc = {
        "name": "（配列名をここに）",
        "author": "",
        "input_mode": "kana_direct",
        "_記法": {
            "単打": '"あ": "a"',
            "同時打鍵": '"で": "e+j"  … + でつなぐ。シフトでも文字キー同士でも同じ',
            "順次打鍵": '"にゃ": ["c", "k", "b"]  … 角括弧で囲んで、打つ順に並べる',
            "3キー同時": '"ぎゃ": "w+f+h"',
            "未使用": '空文字 "" のままにすると「その配列では入力しない」扱い',
        },
        "_使えるキーID": {
            "指キー": " ".join("".join(v) for v in PHYSICAL_ROWS.values()),
            "親指キー": " / ".join(sorted(THUMB_KEYS)),
            "シフトキー": " / ".join(sorted(SHIFT_KEYS)),
        },
        "_補足": [
            "拗音・外来音を分解して打つ配列なら、それらは空欄のままで構いません。",
            "「ゃ」にキーを割り当てておけば「しゃ」は自動で し→ゃ の2打鍵になります。",
            "カナ系新配列のように「でぃ」を1回の同時打鍵で打つ配列だけ、明示的に書いてください。",
            "ここに無いかな（外来音の細かい組み合わせ等）は自由に追加できます。",
        ],
        "map": m,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print(f"{path} を生成しました（全 {len(m)} 項目）")
    for g, v in GROUPS.items():
        print(f"    {g:<12} {len(v):>3} 項目")


def validate(path, sample_text=None):
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    m = doc.get("map", {})
    valid_keys = set(THUMB_KEYS) | set(SHIFT_KEYS)
    for row in PHYSICAL_ROWS.values():
        valid_keys |= set(row)

    filled = {k: v for k, v in m.items() if v}
    print(f"\n[{doc.get('name', path)}]  定義済み {len(filled)} / 全 {len(m)} 項目")

    errors = []
    multi = []
    for kana, entry in filled.items():
        try:
            strokes = parse_entry(entry)
        except ValueError as e:
            errors.append(f"{kana}: 記法エラー — {e}")
            continue
        for main, mods in strokes:
            for k in [main] + list(mods):
                if k not in valid_keys:
                    errors.append(f"{kana}: 未知のキーID {k!r}")
        if len(kana) > 1:
            multi.append(kana)

    for e in errors:
        print(f"  [エラー] {e}")
    if not errors:
        print("  記法・キーID: 問題なし")
    if multi:
        print(f"  複数文字の項目 {len(multi)} 件: {' '.join(multi)}")

    empty = [k for k, v in m.items() if not v]
    if empty:
        print(f"  [未割当] {len(empty)} 項目: {' '.join(empty[:20])}"
              + (" …" if len(empty) > 20 else ""))

    if sample_text:
        print(f"\n  お題文: {sample_text}")
        st = keystrokes_kana(sample_text, doc)
        r = compute(st, GEOMETRIES["row_staggered"], layout_name=doc.get("name", ""),
                    )
        print(f"  打鍵 {r.keys} / 動作 {r.actions} / 同時率 {r.keys_per_action:.2f}")
        print(f"  距離 左{r.dist_L:.3f} 右{r.dist_R:.3f} 合計{r.total:.3f} u")
    return not errors


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "validate":
        validate(sys.argv[2] if len(sys.argv) > 2 else "layout_template.json",
                 sys.argv[3] if len(sys.argv) > 3 else None)
    else:
        build_template()
