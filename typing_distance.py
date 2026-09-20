#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打鍵単純移動距離 算出エンジン
------------------------------
お題文（ひらがな）→ 打鍵列 → 左右の手ごとに連続キー間のユークリッド距離を合計する。

3つの独立した軸を差し替えて比較できる:
  1. ジオメトリ (geometry) : ロウスタッガード / オーソリニア / カラムスタッガード
  2. 配列 (layout)         : QWERTY / Dvorak / 任意の新配列（JSONで定義）
  3. 入力方式 (input mode) : ローマ字入力 / かな直接入力

距離の単位は u（1u = キーピッチ = 19.05mm）。mm 換算値も併記する。

同じ手の複数キー同時押しは、キー間を順次移動したとはみなさず、
そのキー中心の重心を当該アクションの代表位置として扱う。
"""

import math
import json
from dataclasses import dataclass, field

U_MM = 19.05  # 1u のミリメートル換算


# ============================================================
# 1. ジオメトリ定義
# ============================================================
# 物理キーを「行番号 row（下から 0,1,2,3）」「列番号 col（左から 0 始まり）」で持ち、
# ジオメトリごとに実座標 (x, y) へ変換する。

# 物理キー配置（ANSI 相当の 4 段）。左から順にキーIDを並べる。
PHYSICAL_ROWS = {
    3: list("1234567890-="),      # 数字段
    2: list("qwertyuiop[]"),      # 上段
    1: list("asdfghjkl;'"),       # 中段（ホーム）
    0: list("zxcvbnm,./"),        # 下段
}

ALL_PHYSICAL_KEYS = {k for _row in PHYSICAL_ROWS.values() for k in _row}

# 手の割り当て（標準的なタッチタイプ）
HAND_OF_KEY = {}
for _r, _keys in PHYSICAL_ROWS.items():
    for _i, _k in enumerate(_keys):
        # 数字段は 1-5 が左、上段は q-t が左…という一般的な区切り
        left_count = {3: 5, 2: 5, 1: 5, 0: 5}[_r]
        HAND_OF_KEY[_k] = "L" if _i < left_count else "R"

# 指の割り当て（0=左小,1=左薬,2=左中,3=左人,4=右人,5=右中,6=右薬,7=右小）
FINGER_OF_KEY = {}
for _r, _keys in PHYSICAL_ROWS.items():
    for _i, _k in enumerate(_keys):
        if _i <= 0:
            f = 0
        elif _i == 1:
            f = 1
        elif _i == 2:
            f = 2
        elif _i in (3, 4):
            f = 3
        elif _i in (5, 6):
            f = 4
        elif _i == 7:
            f = 5
        elif _i == 8:
            f = 6
        else:
            f = 7
        FINGER_OF_KEY[_k] = f


# --- シフトキー ---
# 幅が不揃いなので実座標で持つ。指は左右とも小指。
SHIFT_KEYS = {"lshift", "rshift"}
HAND_OF_KEY.update({"lshift": "L", "rshift": "R"})
FINGER_OF_KEY.update({"lshift": 0, "rshift": 7})
ALL_PHYSICAL_KEYS |= SHIFT_KEYS

# --- 親指キー ---
# 幅が不揃いなので、指キーのような col 計算ではなく実座標を直接持たせる。
THUMB_KEYS = {"space", "muhenkan", "henkan", "kana", "lthumb", "rthumb"}
for _k in THUMB_KEYS:
    FINGER_OF_KEY[_k] = 8  # 8 = 親指
HAND_OF_KEY.update({
    "muhenkan": "L", "lthumb": "L",
    "henkan": "R", "kana": "R", "rthumb": "R",
    "space": None,   # None = 打鍵時に決定（既定は逆手の親指）
})


@dataclass
class Geometry:
    name: str
    # 各行の x オフセット（u）。キー中心 x = offset + col + 0.5
    row_x_offset: dict
    # 各列の y オフセット（u）。カラムスタッガード用。指番号 -> 上方向オフセット
    finger_y_offset: dict = field(default_factory=dict)
    row_pitch: float = 1.0  # 段間の縦ピッチ（u）
    # 親指キーの実座標（u）。キーID -> (x, y)
    thumb_positions: dict = field(default_factory=dict)

    def pos(self, key: str):
        if key in self.thumb_positions:
            return self.thumb_positions[key]
        for r, keys in PHYSICAL_ROWS.items():
            if key in keys:
                col = keys.index(key)
                x = self.row_x_offset[r] + col + 0.5
                y = r * self.row_pitch + self.finger_y_offset.get(FINGER_OF_KEY[key], 0.0)
                return (x, y)
        raise KeyError(f"未定義の物理キー: {key!r}")


# --- ロウスタッガード（ANSI 標準寸法） ---
# 数字段は ` が 1u、上段は Tab 1.5u、中段は Caps 1.75u、下段は Shift 2.25u ぶん右にずれる
# 親指段は JIS 配列を想定: 無変換(中心4.0) / スペース(中心6.75) / 変換(中心9.5) / かな(中心10.5)
ROW_STAGGERED = Geometry(
    name="ロウスタッガード(ANSI)",
    row_x_offset={3: 1.0, 2: 1.5, 1: 1.75, 0: 2.25},
    thumb_positions={
        "muhenkan": (4.0, -1.0), "space": (6.75, -1.0),
        "henkan": (9.5, -1.0), "kana": (10.5, -1.0),
        "lthumb": (4.0, -1.0), "rthumb": (9.5, -1.0),
        # 下段: LShift 2.25u / 10キー / RShift 2.75u
        "lshift": (1.125, 0.0), "rshift": (13.625, 0.0),
    },
)

# --- オーソリニア（完全格子） ---
ORTHOLINEAR = Geometry(
    name="オーソリニア",
    row_x_offset={3: 0.0, 2: 0.0, 1: 0.0, 0: 0.0},
    thumb_positions={
        "muhenkan": (3.5, -1.0), "space": (5.5, -1.0),
        "henkan": (7.5, -1.0), "kana": (8.5, -1.0),
        "lthumb": (3.5, -1.0), "rthumb": (7.5, -1.0),
        "lshift": (-0.5, 0.0), "rshift": (10.5, 0.0),
    },
)

# --- カラムスタッガード（Corne 系の一例。数値は調整可能） ---
COLUMN_STAGGERED = Geometry(
    name="カラムスタッガード(例)",
    row_x_offset={3: 0.0, 2: 0.0, 1: 0.0, 0: 0.0},
    finger_y_offset={0: 0.0, 1: 0.25, 2: 0.5, 3: 0.25,
                     4: 0.25, 5: 0.5, 6: 0.25, 7: 0.0},
    # 分割型は親指キーが内側に寄る
    thumb_positions={
        "muhenkan": (3.0, -0.75), "space": (4.0, -1.0),
        "henkan": (7.0, -1.0), "kana": (8.0, -0.75),
        "lthumb": (4.0, -1.0), "rthumb": (7.0, -1.0),
        "lshift": (-0.5, 0.0), "rshift": (10.5, 0.0),
    },
)

GEOMETRIES = {
    "row_staggered": ROW_STAGGERED,
    "ortholinear": ORTHOLINEAR,
    "column_staggered": COLUMN_STAGGERED,
}


# ============================================================
# 2. 配列定義（英字配列 = ローマ字入力用）
# ============================================================
# 3段30キーの並びを文字列で与える。物理キー q..p / a..; / z../ に対応。

ALPHA_SLOTS = list("qwertyuiop") + list("asdfghjkl;") + list("zxcvbnm,./")


def alpha_layout(name, top, home, bottom, extra=None):
    """論理文字 -> 物理キー の辞書を作る

    英字30キーだけでは日本語ローマ字入力に足りない。長音「ー」は '-' へ
    展開されるため、その物理キーを extra で明示する必要がある。
    """
    chars = list(top) + list(home) + list(bottom)
    assert len(chars) == 30, f"{name}: 30文字必要（現在{len(chars)}）"
    m = {c: k for c, k in zip(chars, ALPHA_SLOTS)}
    if extra:
        for c, spec in extra.items():
            # "rshift+1" のようなシフト付き指定も受け付ける
            for k in str(spec).split("+"):
                if k not in ALL_PHYSICAL_KEYS:
                    raise ValueError(f"{name}: 未知の物理キー {k!r}（{c!r} の指定）")
            m[c] = spec
    return {"name": name, "map": m, "input_mode": "romaji"}


# 英字30キー以外の文字は、配列ごとに物理キーが異なるので個別に指定する。
#   ー … 長音。QWERTY は数字段 '-'、Dvorak は中段右端（QWERTY の ' 位置）
#   「」 … IME 上で [ ] を出すキー。Dvorak では数字段 '-' '=' に移る
#   ！ … Shift + 1（数字段は Dvorak でも同配置）
#   ？ … Shift + '/' が出るキー。Dvorak では物理 '[' に移る
# シフトは打鍵する手と逆の手で押す前提（1 は左手なので rshift、/ は右手なので lshift）
QWERTY = alpha_layout("QWERTY", "qwertyuiop", "asdfghjkl;", "zxcvbnm,./",
                      extra={"-": "-", "「": "[", "」": "]",
                             "！": "rshift+1", "？": "lshift+/"})
DVORAK = alpha_layout("Dvorak", "',.pyfgcrl", "aoeuidhtns", ";qjkxbmwvz",
                      extra={"-": "'", "「": "-", "」": "=",
                             "/": "[", "！": "rshift+1", "？": "lshift+["})

ALPHA_LAYOUTS = {"qwerty": QWERTY, "dvorak": DVORAK}


# ============================================================
# 3. かな -> ローマ字 変換
# ============================================================
KANA_ROMAJI = {
    "あ": "a", "い": "i", "う": "u", "え": "e", "お": "o",
    "か": "ka", "き": "ki", "く": "ku", "け": "ke", "こ": "ko",
    "さ": "sa", "し": "si", "す": "su", "せ": "se", "そ": "so",
    "た": "ta", "ち": "ti", "つ": "tu", "て": "te", "と": "to",
    "な": "na", "に": "ni", "ぬ": "nu", "ね": "ne", "の": "no",
    "は": "ha", "ひ": "hi", "ふ": "hu", "へ": "he", "ほ": "ho",
    "ま": "ma", "み": "mi", "む": "mu", "め": "me", "も": "mo",
    "や": "ya", "ゆ": "yu", "よ": "yo",
    "ら": "ra", "り": "ri", "る": "ru", "れ": "re", "ろ": "ro",
    "わ": "wa", "ゐ": "wi", "ゑ": "we", "を": "wo", "ん": "N",  # N = 文脈で n / nn に解決するプレースホルダ
    "が": "ga", "ぎ": "gi", "ぐ": "gu", "げ": "ge", "ご": "go",
    "ざ": "za", "じ": "zi", "ず": "zu", "ぜ": "ze", "ぞ": "zo",
    "だ": "da", "ぢ": "di", "づ": "du", "で": "de", "ど": "do",
    "ば": "ba", "び": "bi", "ぶ": "bu", "べ": "be", "ぼ": "bo",
    "ぱ": "pa", "ぴ": "pi", "ぷ": "pu", "ぺ": "pe", "ぽ": "po",
    "ぁ": "xa", "ぃ": "xi", "ぅ": "xu", "ぇ": "xe", "ぉ": "xo",
    "ゃ": "xya", "ゅ": "xyu", "ょ": "xyo", "ゎ": "xwa",
    "ー": "-", "、": ",", "。": ".", "・": "/",
    "ゔ": "vu", "ゔぁ": "va", "ゔぃ": "vi", "ゔぇ": "ve", "ゔぉ": "vo",
    "ゔゅ": "vyu",
}
# 拗音（2文字まとめ打ち）
for base, cons in [("き", "k"), ("し", "s"), ("ち", "t"), ("に", "n"), ("ひ", "h"),
                   ("み", "m"), ("り", "r"), ("ぎ", "g"), ("じ", "z"), ("ぢ", "d"),
                   ("び", "b"), ("ぴ", "p")]:
    for small, v in [("ゃ", "ya"), ("ゅ", "yu"), ("ょ", "yo")]:
        KANA_ROMAJI[base + small] = cons + v
for base, cons in [("ふ", "f"), ("う", "w"), ("て", "th"), ("で", "dh"), ("と", "tw"), ("ど", "dw")]:
    for small, v in [("ぁ", "a"), ("ぃ", "i"), ("ぅ", "u"), ("ぇ", "e"), ("ぉ", "o")]:
        KANA_ROMAJI.setdefault(base + small, cons + v)


# 「ん」の直後がこれらの音で始まる場合は n 一打では確定できないため nn が必要
_N_NEEDS_DOUBLE = set("aiueony")


def kana_to_romaji(text: str, n_policy: str = "shortest") -> str:
    """ひらがな列をローマ字打鍵文字列に変換（最長一致・促音は子音重ね）

    n_policy:
      "shortest" … 母音・な行・や行・語末以外は n 一打（実際の打鍵に近い）
      "always_nn" … 常に nn
    """
    out = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] == "っ":
            # 次のかなの頭子音を重ねる
            j = i + 1
            nxt = ""
            for ln in (2, 1):
                if j + ln <= n and text[j:j + ln] in KANA_ROMAJI:
                    nxt = KANA_ROMAJI[text[j:j + ln]]
                    break
            if nxt and nxt[0].isalpha() and nxt[0] not in "aiueo":
                out.append(nxt[0])
            else:
                out.append("xtu")
            i += 1
            continue
        matched = False
        for ln in (2, 1):
            seg = text[i:i + ln]
            if seg in KANA_ROMAJI:
                out.append(KANA_ROMAJI[seg])
                i += ln
                matched = True
                break
        if not matched:
            if text[i].strip():
                out.append(text[i])
            i += 1

    # プレースホルダ N を n / nn に解決する
    resolved = []
    for idx, seg in enumerate(out):
        if seg != "N":
            resolved.append(seg)
            continue
        if n_policy == "always_nn":
            resolved.append("nn")
            continue
        nxt = out[idx + 1] if idx + 1 < len(out) else ""
        if not nxt or nxt[0] in _N_NEEDS_DOUBLE:
            resolved.append("nn")   # 語末・母音前・な行前・や行前
        else:
            resolved.append("n")    # それ以外は一打で確定
    return "".join(resolved)


# ============================================================
# 4. 打鍵列の生成
# ============================================================
# 打鍵 = (物理キー, シフトキー or None)

def _raise_unmapped(layout, chars, kind="かな"):
    """未定義文字があれば ValueError にする

    配列に存在しない文字を黙って捨てると、その文字ぶんの打鍵数・
    アクション数・距離がすべて 0 になり、その配列だけが不当に
    有利になる。比較を目的とする以上、黙って続行してはいけない。
    """
    uniq = "".join(dict.fromkeys(chars))
    detail = "、".join(f"{c!r}×{chars.count(c)}" for c in uniq)
    raise ValueError(
        f"{layout.get('name', '配列')}: 配列に未定義の{kind}があります: {detail}\n"
        f"  この配列でお題文を最後まで打てません。定義を追加してください。\n"
        f"  未完成のまま試算したい場合は allow_unmapped=True を指定してください"
        f"（その文字は読み飛ばされ、結果は過小評価になります）。")


def keystrokes_romaji(text: str, layout) -> list:
    """ひらがな文をローマ字入力の物理打鍵列へ変換する。

    配列に存在しない文字を黙って捨てると比較結果が過小評価されるため、
    未定義文字が1つでもあれば ValueError にする。
    """
    romaji = kana_to_romaji(text)
    strokes = []
    unmapped = []
    for ch in romaji:
        spec = layout["map"].get(ch)
        if spec is None:
            unmapped.append(ch)
            continue
        # "rshift+1" のようなシフト付き指定も受け付ける
        strokes.append(parse_stroke(spec))
    if unmapped:
        uniq = "".join(dict.fromkeys(unmapped))
        raise ValueError(
            f"{layout.get('name', '配列')}: 配列に未定義のローマ字打鍵があります: {uniq!r} "
            f"(展開結果: {romaji!r})"
        )
    return strokes


def parse_stroke(spec):
    """1打鍵の記法を (主キー, シフトキー列) に分解する

      "a"        -> ("a", [])          単打
      "space+u"  -> ("u", ["space"])   同時押し
      "space+shift+u" -> ("u", ["space","shift"])  3キー同時押し
    """
    if not isinstance(spec, str):
        raise ValueError(f"打鍵の指定は文字列で書いてください: {spec!r}")
    parts = [p.strip() for p in spec.split("+") if p.strip()]
    if not parts:
        raise ValueError("空の打鍵指定です")
    return parts[-1], parts[:-1]


def parse_entry(entry):
    """map の値を打鍵列 [(主キー, シフト列), ...] に展開する

      "a"                -> 1打鍵
      "space+u"          -> 1打鍵（同時押し）
      ["i", "y"]         -> 2打鍵（連続）
      ["space+i", "y"]   -> 2打鍵（1打目が同時押し）
    """
    if isinstance(entry, str):
        return [parse_stroke(entry)]
    if isinstance(entry, list):
        return [parse_stroke(s) for s in entry]
    raise ValueError(f"未知の記法です: {entry!r}")


def keystrokes_kana(text: str, kana_layout, segment_policy=None,
                    allow_unmapped=False) -> list:
    """かな直接入力系（新配列）。kana_layout['map'] は かな -> 打鍵指定

    segment_policy:
      "longest"     … 最長一致（先頭から最も長いかな列を優先）
      "min_actions" … アクション数が最小になる切り分けを選ぶ（既定）

    「ちょ」を1アクションで打てる配列なら、どちらの方針でも
    「ち」+「ょ」には分解されない。両者が食い違うのは、同じかな列に
    複数の打ち方が定義されていて、長い方が却って打鍵数を増やす場合。
    """
    policy = segment_policy or kana_layout.get("segment_policy") or "min_actions"
    m = {k: v for k, v in kana_layout["map"].items() if v}
    maxlen = max((len(k) for k in m), default=1)
    n = len(text)
    unmapped = []

    if policy == "longest":
        strokes, i = [], 0
        while i < n:
            matched = False
            for ln in range(min(maxlen, n - i), 0, -1):
                seg = text[i:i + ln]
                if seg in m:
                    strokes.extend(parse_entry(m[seg]))
                    i += ln
                    matched = True
                    break
            if not matched:
                if text[i].strip():
                    unmapped.append(text[i])
                i += 1
        if unmapped and not allow_unmapped:
            _raise_unmapped(kana_layout, unmapped)
        if unmapped:
            print(f"  [警告] 配列に未定義のかな（読み飛ばし）: "
                  f"{''.join(dict.fromkeys(unmapped))}")
        return strokes

    # --- min_actions: 動的計画法で総アクション数を最小化する ---
    INF = float("inf")
    best = [INF] * (n + 1)
    back = [None] * (n + 1)   # (直前の位置, 打鍵列)
    best[0] = 0
    for i in range(n):
        if best[i] == INF:
            continue
        for ln in range(1, min(maxlen, n - i) + 1):
            seg = text[i:i + ln]
            if seg not in m:
                continue
            st = parse_entry(m[seg])
            cost = best[i] + len(st)
            if cost < best[i + ln]:
                best[i + ln] = cost
                back[i + ln] = (i, st)
        # どの定義にも当たらない1文字は読み飛ばす（コストは加算しない）
        if best[i] + 0 < best[i + 1] and back[i + 1] is None:
            best[i + 1] = best[i]
            back[i + 1] = (i, None)

    if best[n] == INF:
        return keystrokes_kana(text, kana_layout, segment_policy="longest")

    strokes, pos = [], n
    while pos > 0:
        prev, st = back[pos]
        if st is None:
            ch = text[prev]
            if ch.strip():
                unmapped.append(ch)
        else:
            strokes = st + strokes
        pos = prev
    unmapped.reverse()
    if unmapped and not allow_unmapped:
        _raise_unmapped(kana_layout, unmapped)
    if unmapped:
        print(f"  [警告] 配列に未定義のかな（読み飛ばし）: "
              f"{''.join(dict.fromkeys(unmapped))}")
    return strokes


# ============================================================
# 5. 距離計算
# ============================================================
@dataclass
class Result:
    geometry: str
    layout: str
    keys: int        # 打鍵数（押されたキーの延べ数。同時押しはキーの数だけ数える）
    actions: int     # アクション数（打鍵動作の回数。同時押しは何キーでも1）
    dist_L: float
    dist_R: float
    n_L: int
    n_R: int
    thumb_L: float = 0.0
    thumb_R: float = 0.0

    @property
    def left_total(self):
        """左手合計（4指 + 親指）"""
        return self.dist_L + self.thumb_L

    @property
    def right_total(self):
        """右手合計（4指 + 親指）"""
        return self.dist_R + self.thumb_R

    @property
    def total_non_thumb(self):
        """親指を除いた旧来の合計値。"""
        return self.dist_L + self.dist_R

    @property
    def total(self):
        """左右とも親指を含む総移動距離。"""
        return self.left_total + self.right_total

    @property
    def total_with_thumb(self):
        # 旧APIとの互換用。現在の total は最初から親指込み。
        return self.total

    @property
    def per_key(self):
        return self.total / self.keys if self.keys else 0.0

    @property
    def per_action(self):
        return self.total / self.actions if self.actions else 0.0

    @property
    def keys_per_action(self):
        return self.keys / self.actions if self.actions else 0.0


def resolve_hand(key, main_key=None, space_hand="opposite"):
    """キーを打つ手を決める。スペースは既定で『打鍵と逆の手の親指』"""
    h = HAND_OF_KEY.get(key)
    if h is not None:
        return h
    # space の場合
    if space_hand == "left":
        return "L"
    if space_hand == "right":
        return "R"
    if main_key is None:
        return "L"
    return "R" if HAND_OF_KEY.get(main_key) == "L" else "L"


PATHS = (("L", False), ("R", False), ("L", True), ("R", True))


def _bucket(strokes, space_hand, thumb_separate, include_chord_keys=True):
    """打鍵列を (手, 親指か) ごとの「同時打鍵の塊」の列に変換する。

    include_chord_keys=False の場合は主キーだけを距離計算対象にする。
    旧 count_shift という名前は、実際には Shift だけでなく Space や文字キーを
    含む同時押しキー全般を指していたため廃止した。
    """
    groups = []
    for key, mods in strokes:
        mods = [] if not mods else ([mods] if isinstance(mods, str) else list(mods))
        allk = (mods if include_chord_keys else []) + [key]
        buckets = {}
        for k in allk:
            h = resolve_hand(k, key, space_hand)
            is_thumb = thumb_separate and FINGER_OF_KEY.get(k) == 8
            buckets.setdefault((h, is_thumb), []).append(k)
        for pk, ks in buckets.items():
            groups.append((pk, ks))
    return groups


def _group_position(keys, geom):
    """同じ手・同じ指群で同時押しするキー集合の代表位置を返す。

    単打はそのキー中心。同じ手の複数キー同時押しはキー中心の重心とする。
    これにより、J+L を J→L のような順次移動として数えない。
    """
    pts = [geom.pos(k) for k in keys]
    return (sum(x for x, _ in pts) / len(pts),
            sum(y for _, y in pts) / len(pts))


def _advance(state, strokes, geom, simul_policy="centroid", space_hand="opposite",
             thumb_separate=True, include_chord_keys=True):
    """現在位置 state から打鍵列を実行し、(経路別距離, 新state) を返す。

    state は {("L",False): (x,y), ...}。None は「まだ触れていない」。

    同じ手の同時押しは、各キーを順番に移動したとはみなさず、キー中心の重心を
    そのアクションにおける手の代表位置とする。旧 simul_policy="min_path" は
    後方互換のため受理するが、計算は centroid と同じ扱いにする。
    """
    if simul_policy not in ("centroid", "min_path"):
        raise ValueError(f"未知の simul_policy: {simul_policy!r}")

    st = dict(state)
    cost = {p: 0.0 for p in PATHS}
    for pk, ks in _bucket(strokes, space_hand, thumb_separate, include_chord_keys):
        prev_pos = st.get(pk)
        cur_pos = _group_position(ks, geom)
        if prev_pos is not None:
            cost[pk] += math.dist(prev_pos, cur_pos)
        st[pk] = cur_pos
    return cost, st


def compute(strokes, geom: Geometry, include_chord_keys=True,
            start_from_home=False, geometry_name=None, layout_name="",
            space_hand="opposite", thumb_separate=True,
            simul_policy="centroid", count_shift=None):
    """左右それぞれについて、連続アクション間の単純移動距離を合計する。

    include_chord_keys:
      True  … 同時押しされた全キーを距離計算に含める（既定）
      False … 主キーだけを距離計算に含める

    count_shift は旧引数名との互換用。指定された場合は include_chord_keys を上書きする。
    """
    if count_shift is not None:
        include_chord_keys = count_shift

    HOME = {"L": "f", "R": "j"}
    init = {p: None for p in PATHS}
    if start_from_home:
        init[("L", False)] = geom.pos(HOME["L"])
        init[("R", False)] = geom.pos(HOME["R"])

    cost, _ = _advance(init, strokes, geom, simul_policy, space_hand,
                       thumb_separate, include_chord_keys)

    groups = _bucket(strokes, space_hand, thumb_separate, include_chord_keys)
    n = {"L": 0, "R": 0}
    for (h, _t), ks in groups:
        n[h] += len(ks)

    return Result(
        geometry=geometry_name or geom.name,
        layout=layout_name,
        keys=sum(1 + (0 if not sh else (1 if isinstance(sh, str) else len(sh)))
                 for _, sh in strokes),
        actions=len(strokes),
        dist_L=cost[("L", False)], dist_R=cost[("R", False)],
        n_L=n["L"], n_R=n["R"],
        thumb_L=cost[("L", True)], thumb_R=cost[("R", True)],
    )


# ============================================================
# 6. レポート出力
# ============================================================
def strokes_min_distance(text, kana_layout, geom, beam=3000,
                         simul_policy="centroid", space_hand="opposite",
                         thumb_separate=True, include_chord_keys=True,
                         start_from_home=False, count_shift=None,
                         allow_unmapped=False):
    """移動距離が最小になる打鍵経路を動的計画法で求める

    同じかな列に複数の打ち方が定義されている配列で、
    「そのとき指がどこにあるか」まで考慮して打ち方を選ぶ。

    beam: 各位置で保持する状態数の上限（安全弁）。
    """
    if count_shift is not None:
        include_chord_keys = count_shift

    m = {k: v for k, v in kana_layout["map"].items() if v}
    if not m:
        return [], 0.0
    maxlen = max(len(k) for k in m)
    n = len(text)
    HOME = {"L": "f", "R": "j"}

    init = {p: None for p in PATHS}
    if start_from_home:
        init[("L", False)] = geom.pos(HOME["L"])
        init[("R", False)] = geom.pos(HOME["R"])
    init_key = tuple(init[p] for p in PATHS)

    dp = [dict() for _ in range(n + 1)]
    dp[0][init_key] = (0.0, None)
    unmapped = []

    for i in range(n):
        if not dp[i]:
            continue
        if len(dp[i]) > beam:
            dp[i] = dict(sorted(dp[i].items(), key=lambda kv: kv[1][0])[:beam])

        matched_any = False
        for ln in range(1, min(maxlen, n - i) + 1):
            seg = text[i:i + ln]
            if seg not in m:
                continue
            matched_any = True
            st_list = parse_entry(m[seg])
            for skey, (cost, _) in dp[i].items():
                state = dict(zip(PATHS, skey))
                add, new_state = _advance(state, st_list, geom, simul_policy,
                                          space_hand, thumb_separate, include_chord_keys)
                nc = cost + sum(add.values())
                nkey = tuple(new_state[p] for p in PATHS)
                cur = dp[i + ln].get(nkey)
                if cur is None or nc < cur[0] - 1e-12:
                    dp[i + ln][nkey] = (nc, (i, skey, st_list))

        if not matched_any:
            if text[i].strip():
                unmapped.append(text[i])
            for skey, (cost, _) in dp[i].items():
                cur = dp[i + 1].get(skey)
                if cur is None or cost < cur[0] - 1e-12:
                    dp[i + 1][skey] = (cost, (i, skey, None))

    if not dp[n]:
        return keystrokes_kana(text, kana_layout, segment_policy="min_actions"), None

    best_key = min(dp[n], key=lambda k: dp[n][k][0])
    total = dp[n][best_key][0]

    strokes, pos, skey = [], n, best_key
    while pos > 0:
        _, back = dp[pos][skey]
        prev_i, prev_key, st_list = back
        if st_list:
            strokes = st_list + strokes
        pos, skey = prev_i, prev_key

    if unmapped and not allow_unmapped:
        _raise_unmapped(kana_layout, unmapped)
    if unmapped:
        print(f"  [警告] 配列に未定義のかな（読み飛ばし）: "
              f"{''.join(dict.fromkeys(unmapped))}")
    return strokes, total


def strokes_for(text, layout, geom, segment_policy=None,
                allow_unmapped=False, **opts):
    """お題文・配列・ジオメトリから打鍵列を返す

    analyze() が内部で使うのと同じ経路を取り出せる。
    ヒートマップ用のキー別集計などに使う。
    """
    policy = segment_policy or layout.get("segment_policy") or "min_actions"
    if layout.get("input_mode") == "romaji":
        return keystrokes_romaji(text, layout)
    if policy == "min_distance":
        strokes, _ = strokes_min_distance(text, layout, geom,
                                          allow_unmapped=allow_unmapped, **opts)
        return strokes
    return keystrokes_kana(text, layout, segment_policy=policy,
                           allow_unmapped=allow_unmapped)


def key_counts(strokes, space_hand="opposite", thumb_separate=True,
               include_chord_keys=True):
    """打鍵列をキー別の打鍵回数に集計する

    戻り値: (counts, summary)
      counts  … {キーID: 回数}。同時打鍵は構成キーそれぞれを1回と数える
      summary … 左右・親指の打鍵回数と比率
    """
    counts = {}
    by_path = {p: 0 for p in PATHS}
    for pk, ks in _bucket(strokes, space_hand, thumb_separate, include_chord_keys):
        for k in ks:
            counts[k] = counts.get(k, 0) + 1
            by_path[pk] += 1
    total = sum(counts.values())

    def pct(n):
        return round(n / total * 100, 2) if total else 0.0

    lf, rf = by_path[("L", False)], by_path[("R", False)]
    lt, rt = by_path[("L", True)], by_path[("R", True)]
    summary = {
        "total": total,
        "left_fingers": lf, "left_thumb": lt, "left_total": lf + lt,
        "right_fingers": rf, "right_thumb": rt, "right_total": rf + rt,
        "left_pct": pct(lf + lt), "right_pct": pct(rf + rt),
        "thumb_pct": pct(lt + rt),
    }
    return counts, summary


def analyze(text, layout, geom, segment_policy=None,
            allow_unmapped=False, **opts):
    """お題文・配列・ジオメトリから Result を返す（打ち方の選択も含む）

    segment_policy:
      "min_distance" … 移動距離が最小になる打ち方（ジオメトリに依存）
      "min_actions"  … アクション数が最小になる打ち方
      "longest"      … 最長一致
    """
    strokes = strokes_for(text, layout, geom, segment_policy,
                          allow_unmapped=allow_unmapped, **opts)
    return compute(strokes, geom, layout_name=layout.get("name", ""),
                   geometry_name=geom.name, **opts)


def report(results, title=""):
    if title:
        print(f"\n■ {title}")
    print(f"{'ジオメトリ':<22}{'配列':<14}{'打鍵':>6}{'動作':>6}{'同時率':>8}"
          f"{'左4指':>8}{'左親':>8}{'左計':>8}"
          f"{'右4指':>8}{'右親':>8}{'右計':>8}"
          f"{'合計(u)':>10}{'mm':>9}{'/打鍵':>8}{'/動作':>8}")
    print("-" * 142)
    for r in results:
        print(f"{r.geometry:<22}{r.layout:<14}{r.keys:>6}{r.actions:>6}"
              f"{r.keys_per_action:>8.2f}"
              f"{r.dist_L:>8.2f}{r.thumb_L:>8.2f}{r.left_total:>8.2f}"
              f"{r.dist_R:>8.2f}{r.thumb_R:>8.2f}{r.right_total:>8.2f}"
              f"{r.total:>10.2f}{r.total * U_MM:>9.0f}"
              f"{r.per_key:>8.3f}{r.per_action:>8.3f}")


def distance_between(k1, k2, geom=ROW_STAGGERED):
    (x1, y1), (x2, y2) = geom.pos(k1), geom.pos(k2)
    return math.hypot(x2 - x1, y2 - y1)


# ============================================================
# 7. 実行例
# ============================================================
if __name__ == "__main__":
    print("=== 検算: ご提示の例（ロウスタッガード） ===")
    for a, b in [("q", "w"), ("q", "e"), ("q", "s"), ("s", "e")]:
        print(f"  {a.upper()} → {b.upper()} : {distance_between(a, b):.4f} u "
              f"({distance_between(a, b) * U_MM:.1f} mm)")

    print("\n=== 同じ組み合わせをオーソリニアで ===")
    for a, b in [("q", "w"), ("q", "e"), ("q", "s"), ("s", "e")]:
        print(f"  {a.upper()} → {b.upper()} : {distance_between(a, b, ORTHOLINEAR):.4f} u")

    # お題文（ひらがな）
    ODAI = "きょうはよいてんきなのでこうえんまでさんぽにいきました"

    print(f"\n=== お題文 ===\n  {ODAI}")
    print(f"  ローマ字展開: {kana_to_romaji(ODAI)}")

    results = []
    for gkey, geom in GEOMETRIES.items():
        for lkey, lay in ALPHA_LAYOUTS.items():
            st = keystrokes_romaji(ODAI, lay)
            results.append(compute(st, geom, layout_name=lay["name"],
                                   geometry_name=geom.name))
    report(results, "ローマ字入力・配列 × ジオメトリ比較")
