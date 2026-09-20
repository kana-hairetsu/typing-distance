#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""1打鍵ずつの移動を明細表示して検算できるようにする"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import math
from typing_distance import (kana_to_romaji, keystrokes_romaji, HAND_OF_KEY,
                             GEOMETRIES, ALPHA_LAYOUTS, U_MM)


def trace(text, geom, layout):
    romaji = kana_to_romaji(text)
    strokes = keystrokes_romaji(text, layout)
    keys = [k for k, _ in strokes]

    print(f"\n{'=' * 62}")
    print(f"お題文: {text}   →   {romaji}   ({len(keys)}打鍵)")
    print(f"ジオメトリ: {geom.name} / 配列: {layout['name']}")
    print("=" * 62)

    print("\n[キー座標] 単位 u")
    for k in dict.fromkeys(keys):
        x, y = geom.pos(k)
        print(f"  {k.upper()}  ({x:6.3f}, {y:5.3f})  {HAND_OF_KEY[k]}手")

    print(f"\n[打鍵順] {' → '.join(k.upper() for k in keys)}")
    print(f"[手の別] {' → '.join(HAND_OF_KEY[k] for k in keys)}")

    totals = {}
    for hand, label in (("L", "左手"), ("R", "右手")):
        seq = [k for k in keys if HAND_OF_KEY[k] == hand]
        print(f"\n[{label}] 打鍵列: {' → '.join(k.upper() for k in seq)}")
        d = 0.0
        for a, b in zip(seq, seq[1:]):
            (x1, y1), (x2, y2) = geom.pos(a), geom.pos(b)
            dx, dy = x2 - x1, y2 - y1
            seg = math.hypot(dx, dy)
            d += seg
            print(f"    {a.upper()} → {b.upper()}   dx={dx:+6.3f}  dy={dy:+6.3f}"
                  f"   √({dx**2:.4f}+{dy**2:.4f}) = {seg:.4f} u")
        print(f"    {label}合計 = {d:.4f} u  ({d * U_MM:.1f} mm)")
        totals[hand] = d

    tot = totals["L"] + totals["R"]
    print(f"\n[総計] {tot:.4f} u  ({tot * U_MM:.1f} mm)   左右比 = "
          f"{totals['L'] / tot * 100:.1f}% : {totals['R'] / tot * 100:.1f}%")
    return totals


if __name__ == "__main__":
    TEXT = "でじこみ"
    qwerty = ALPHA_LAYOUTS["qwerty"]

    summary = []
    for gkey in ("row_staggered", "ortholinear", "column_staggered"):
        geom = GEOMETRIES[gkey]
        t = trace(TEXT, geom, qwerty)
        summary.append((geom.name, t["L"], t["R"]))

    print(f"\n\n{'=' * 62}\n[まとめ] QWERTY・ローマ字入力\n{'=' * 62}")
    print(f"{'ジオメトリ':<24}{'左(u)':>9}{'右(u)':>9}{'合計(u)':>10}{'合計(mm)':>11}")
    for name, l, r in summary:
        print(f"{name:<24}{l:>9.3f}{r:>9.3f}{l + r:>10.3f}{(l + r) * U_MM:>11.1f}")
