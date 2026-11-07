# -*- coding: utf-8 -*-
"""ピアノ配列（ここつく）の定義ファイル layouts/piano.json を作る。

    python tools/build_piano.py

ピアノ配列はローマ字系だが、か行 c・な行 '・ん n・っ f・きくちつの単打・
拗音 q・拡張（です／ます／する など）を持つ独自のローマ字テーブルなので、
kana_direct 形式（かな → QWERTY のキー位置の打鍵列）で書き出す。

■ a省略
<子音>a の a は、次の打鍵が母音（a i u l e o）以外なら省略できる（任意）。
次の打鍵で省略してよいかが決まるため、1かなの定義だけでは表せない。
そこで、お題文に実際に出てくる「省略できるかなの連なり＋次のかな」を
まとめて1つの定義として追加する（例：「からは」→ c r h a）。
エンジンは打鍵数が最少になる切り分けを選ぶので、省略は使える所すべてで使われる。

■ 仕様の出典
https://pianolayout.hatenablog.com/entry/2026/09/24/150721 （英字配置）
https://pianolayout.hatenablog.com/entry/2026/09/24/153758 （ローマ字テーブル詳説）
"""
import json, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---- 英字配置：ピアノ配列の文字 → QWERTY のキー位置 ------------------------
#   上段  . x d m b | - l u o q
#   中段  ' r s t c | f n i e a    外側：左 y（caps）、右 ,（' の位置）
#   下段  w h z g p | j k v ; /
POS = {}
for row, qrow in ((".xdmb-luoq", "qwertyuiop"),
                  ("'rstcfniea", "asdfghjkl;"),
                  ("whzgpjkv;/", "zxcvbnm,./")):
    POS.update(zip(row, qrow))
POS["y"] = "caps"
POS[","] = "'"

VOW = set("aiuleo")

# ---- 基本のかな ------------------------------------------------------------
ROWS = {  # 子音キー: あ い う え お
    "c": "かきくけこ", "g": "がぎぐげご", "s": "さしすせそ", "z": "ざじずぜぞ",
    "t": "たちつてと", "d": "だぢづでど", "'": "なにぬねの", "h": "はひふへほ",
    "b": "ばびぶべぼ", "p": "ぱぴぷぺぽ", "m": "まみむめも", "r": "らりるれろ",
}
U = "l"  # u と l は同じ働き。作者が主に使う l で書く

units = {}   # かな -> ピアノ配列の打鍵（文字列）


def add(kana, keys):
    if kana not in units or len(keys) < len(units[kana]):
        units[kana] = keys


for v, k in zip("あいうえお", "aiUeo"):
    add(v, U if k == "U" else k)
for c, row in ROWS.items():
    for kana, v in zip(row, "ai" + U + "eo"):
        add(kana, c + v)
for kana, keys in {"や": "ya", "ゆ": "y" + U, "よ": "yo", "わ": "wa", "を": "wo",
                   "ん": "n", "っ": "f", "ー": "-", "、": ",", "。": ".",
                   # きくちつの単打
                   "き": "/", "く": "k", "ち": ";", "つ": "j",
                   # ふぁ行・ゔぁ行（ふ は h 行）
                   "ふぁ": "fa", "ふぃ": "fi", "ふぇ": "fe", "ふぉ": "fo",
                   "ゔぁ": "va", "ゔぃ": "vi", "ゔ": "v" + U, "ゔぇ": "ve", "ゔぉ": "vo",
                   # 外来音
                   "てぃ": "tqi", "でぃ": "dqi", "しぇ": "sqe", "じぇ": "zqe", "ちぇ": "tqe",
                   # x 拡張（記号など）
                   "こと": "xq", "：": "x;", "・": "x/", "…": "x.",
                   }.items():
    add(kana, keys)
# 拗音 <子音>q + a/u/o
for c, row in ROWS.items():
    for small, v in zip("ゃゅょ", "a" + U + "o"):
        add(row[1] + small, c + "q" + v)

# ---- です／ます拡張・特殊動詞拡張 -----------------------------------------
EXT = {
    "です": "dx" + U, "でした": "dxa", "でして": "dxe", "でしょう": "dxo",
    "ます": "mx" + U, "ました": "mxa", "まして": "mxe", "ません": "mxn", "ましょう": "mxo",
    "する": "x" + U, "し": "xi", "して": "xe", "した": "xa", "しな": "xn", "すれ": "xf", "しよう": "xo",
    "なる": "'x" + U, "なり": "'xi", "なって": "'xe", "ならな": "'xn", "なった": "'xa", "なれ": "'xf", "なろう": "'xo",
    "できる": "yx" + U, "でき": "yxi", "できて": "yxe", "できな": "yxn", "できた": "yxa", "できれ": "yxf",
    "いただく": "tx" + U, "いただき": "txi", "いただいて": "txe", "いただかな": "txn",
    "いただいた": "txa", "いただけ": "txf", "いただこう": "txo",
    "くださる": "cx" + U, "ください": "cxi", "くださり": "cxri", "くださって": "cxe",
    "くださらな": "cxn", "くださった": "cxa", "くだされ": "cxf",
}
for kana, keys in EXT.items():
    add(kana, keys)

# ---- 末尾の母音を省略できるかな --------------------------------------------
# short[かな] = (省略形, 次の打鍵として許さないキー)
X_SECOND = set("qbvs;/.")          # x のあとに続くと別の拡張になるキー（こと・■・私・鈴木・：・・・…）
VERB_TAIL = VOW | set("nfr")        # 'x yx tx cx のあとに続くと活用形になるキー
PREFIX_X = set("ctdm'y")            # 子音のあとに x が来ると拡張になる子音

short = {}
for kana, keys in units.items():
    # a省略：<子音>a と <子音>qa。ふぁ（fa）と あ は省略しない
    # 拡張（した xa、ました mxa など）の a は省略できない
    if len(keys) >= 2 and keys[-1] == "a" and keys[0] not in VOW and keys[0] != "f" \
            and "x" not in keys:
        forbid = VOW | {"q"} | ({"x"} if keys[0] in PREFIX_X else set())
        short[kana] = (keys[:-1], forbid)
# です・ます・し・なり・でき・いただき・ください：母音を続けないときは末尾を省ける
short["です"] = ("dx", VOW)
short["ます"] = ("mx", VOW)
short["し"] = ("x", VOW | set("nf") | X_SECOND)
for kana, keys in (("なり", "'x"), ("でき", "yx"), ("いただき", "tx"), ("ください", "cx")):
    short[kana] = (keys, VERB_TAIL)


def allowed(forbid, nxt):
    """省略形のあとに打鍵列 nxt が続いてよいか"""
    if not nxt:
        return True
    if nxt[0] in forbid:
        return False
    if nxt[0] == "f" and len(nxt) > 1 and nxt[1] in VOW:   # ふぁ行と読まれてしまう
        return False
    return True


def chains(text, maxunits=8):
    """お題文に出てくる「省略形の連なり＋次のかな」を集める"""
    maxlen = max(len(k) for k in units)
    n = len(text)
    found = {}

    def dfs(start, p, keys, forbid, depth):
        for ln in range(1, min(maxlen, n - p) + 1):
            seg = text[p:p + ln]
            if seg not in units:
                continue
            full = units[seg]
            if allowed(forbid, full):
                cand = keys + full
                k = text[start:p + ln]
                if k not in found or len(cand) < len(found[k]):
                    found[k] = cand
            if seg in short and depth < maxunits:
                s, f = short[seg]
                if allowed(forbid, s):
                    if p + ln == n:   # お題文の末尾
                        k = text[start:]
                        if k not in found or len(keys + s) < len(found[k]):
                            found[k] = keys + s
                    dfs(start, p + ln, keys + s, f, depth + 1)

    for i in range(n):
        for ln in range(1, min(maxlen, n - i) + 1):
            seg = text[i:i + ln]
            if seg in short:
                s, f = short[seg]
                dfs(i, i + ln, s, f, 1)
    return found


def to_entry(keys):
    st = []
    for ch in keys:
        st.append(POS[ch])
    return st[0] if len(st) == 1 else st


def main():
    texts = []
    for name in ("wagahai.txt", "wagahai_500.txt"):
        t = open(os.path.join(BASE, "texts", name), encoding="utf-8").read()
        texts.append(t.replace("\n", "").replace("　", "").replace("―", ""))
    m = {k: to_entry(v) for k, v in units.items()}
    m["？"] = "lshift+/"
    m["！"] = "rshift+1"
    m["「"] = "["
    m["」"] = "]"
    n_base = len(m)
    extra = {}
    for t in texts:
        for k, v in chains(t).items():
            if k not in units and (k not in extra or len(v) < len(extra[k])):
                extra[k] = v
    for k, v in sorted(extra.items()):
        m[k] = to_entry(v)

    out = {
        "name": "ピアノ配列",
        "author": "ここつく",
        "input_mode": "kana_direct",
        "_記法": "かな → QWERTY のキー位置の打鍵列。tools/build_piano.py で生成（手で直さない）",
        "_英字配置": {
            "上段": ". x d m b | - l u o q",
            "中段": "' r s t c | f n i e a（外側 左 y＝caps、右 ,＝' の位置）",
            "下段": "w h z g p | j k v ; /",
        },
        "_補足": [
            "u と l は同じ働き。ここでは作者が主に使う l で書いた",
            "き / く k ち ; つ j は単打。し は x（拡張）、ん は n、っ は f",
            f"先頭の {n_base} 件が基本の定義。残りの {len(extra)} 件は a省略などの省略形を、"
            "お題文に出てくる連なりごとに展開したもの",
            "「」は配列図に無いため QWERTY の [ ] のまま",
        ],
        "map": m,
    }
    path = os.path.join(BASE, "layouts", "piano.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"{path}: 基本 {n_base} 件 + 省略形 {len(extra)} 件")


if __name__ == "__main__":
    main()
