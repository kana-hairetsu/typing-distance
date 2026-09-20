#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""配列入力用の Excel ブックを生成する

シート構成:
  単打          … シフトなし。配列名などの設定もここ
  2キー同時     … シフトキー1つ + 文字キー   × 20レイヤー
  3キー同時     … シフトキー2つ + 文字キー   × 20レイヤー
  4キー同時     … シフトキー3つ + 文字キー   × 20レイヤー
  個別指定      … 正データ。上記から数式で自動反映される
  記入方法 / キーID一覧
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

from make_template import GROUPS
from typing_distance import PHYSICAL_ROWS, THUMB_KEYS, SHIFT_KEYS

FONT = "Arial"
HDR_FILL = PatternFill("solid", fgColor="1F3864")
GRP_FILL = PatternFill("solid", fgColor="D9E2F3")
INPUT_FILL = PatternFill("solid", fgColor="FFFFCC")
LOCK_FILL = PatternFill("solid", fgColor="F2F2F2")
LABEL_FILL = PatternFill("solid", fgColor="E7E6E6")
SHIFT_FILL = PatternFill("solid", fgColor="FCE4D6")
TITLE_FILL = PatternFill("solid", fgColor="DDEBF7")
THIN = Side(style="thin", color="BFBFBF")
MED = Side(style="medium", color="808080")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
KEYBOX = Border(left=MED, right=MED, top=MED, bottom=MED)

FINGER_KEYS = [k for row in PHYSICAL_ROWS.values() for k in row]
ALL_KEYS = FINGER_KEYS + sorted(THUMB_KEYS) + sorted(SHIFT_KEYS)

SUB = 4
ROW_OFFSET_U = {3: 1.00, 2: 1.50, 1: 1.75, 0: 2.25}
ROW_LABEL = {3: "数字段", 2: "上段", 1: "中段", 0: "下段"}
BASE_COL = 2
THUMB_ROW = [("muhenkan", 3.5, 1.0), ("space", 4.5, 4.5),
             ("henkan", 9.0, 1.0), ("kana", 10.0, 1.0)]

N_LAYERS = 30
SHEETS = [
    ("単打", 0, 1, "シフトを押さずに、そのキーだけを打ったときのかな"),
    ("2キー同時", 1, N_LAYERS, "シフトキー1つと文字キーの同時打鍵"),
    ("3キー同時", 2, N_LAYERS, "シフトキー2つと文字キーの同時打鍵"),
    ("4キー同時", 3, N_LAYERS, "シフトキー3つと文字キーの同時打鍵"),
]

wb = Workbook()
wb.remove(wb.active)

# 隠しシート: キーID一覧（プルダウン用）
ref = wb.create_sheet("_キー一覧")
for i, k in enumerate(ALL_KEYS, 1):
    ref.cell(i, 1, k).font = Font(name=FONT)
ref.sheet_state = "hidden"
KEYLIST_REF = f"=_キー一覧!$A$1:$A${len(ALL_KEYS)}"


def draw_keyboard(ws, top_row, title, n_shift):
    """キーボード図を1面描き、(次の行, シフトセル一覧, スロット一覧) を返す"""
    ws.merge_cells(start_row=top_row, start_column=1,
                   end_row=top_row, end_column=BASE_COL + 12 * SUB)
    tc = ws.cell(top_row, 1, title)
    tc.font = Font(name=FONT, size=12, bold=True, color="1F3864")
    tc.fill = TITLE_FILL

    r = top_row + 1
    shift_cells = []
    if n_shift:
        ws.cell(r, 1, "シフトキー").font = Font(name=FONT, bold=True, size=10)
        for i in range(n_shift):
            c0 = 2 + i * (SUB + 1)
            ws.merge_cells(start_row=r, start_column=c0, end_row=r, end_column=c0 + SUB - 1)
            c = ws.cell(r, c0)
            c.fill = SHIFT_FILL
            c.border = KEYBOX
            c.font = Font(name=FONT, bold=True)
            c.alignment = Alignment(horizontal="center")
            shift_cells.append((r, c0))
        note = ("← これらのキーすべてと同時に押したときの、かなを下に記入します"
                if n_shift > 1 else "← このキーと同時に押したときの、かなを下に記入します")
        ws.cell(r, 2 + n_shift * (SUB + 1), note).font = Font(name=FONT, size=9, color="666666")
        r += 1

    slots = []
    for kb_row in (3, 2, 1, 0):
        label_r, input_r = r, r + 1
        ws.cell(label_r, 1, ROW_LABEL[kb_row]).font = Font(name=FONT, size=9, color="666666")
        start = BASE_COL + int(ROW_OFFSET_U[kb_row] * SUB)
        for i, k in enumerate(PHYSICAL_ROWS[kb_row]):
            c0 = start + i * SUB
            c1 = c0 + SUB - 1
            ws.merge_cells(start_row=label_r, start_column=c0, end_row=label_r, end_column=c1)
            lc = ws.cell(label_r, c0, k.upper())
            lc.font = Font(name=FONT, size=8, color="808080")
            lc.fill = LABEL_FILL
            lc.alignment = Alignment(horizontal="center")
            ws.merge_cells(start_row=input_r, start_column=c0, end_row=input_r, end_column=c1)
            ic = ws.cell(input_r, c0)
            ic.fill = INPUT_FILL
            ic.border = KEYBOX
            ic.font = Font(name=FONT, size=12)
            ic.alignment = Alignment(horizontal="center", vertical="center")
            slots.append((k, input_r, c0))
        ws.row_dimensions[label_r].height = 12
        ws.row_dimensions[input_r].height = 22
        r += 2

    label_r, input_r = r, r + 1
    ws.cell(label_r, 1, "親指段").font = Font(name=FONT, size=9, color="666666")
    for k, left_u, width_u in THUMB_ROW:
        c0 = BASE_COL + int(left_u * SUB)
        c1 = c0 + int(width_u * SUB) - 1
        ws.merge_cells(start_row=label_r, start_column=c0, end_row=label_r, end_column=c1)
        lc = ws.cell(label_r, c0, k)
        lc.font = Font(name=FONT, size=8, color="808080")
        lc.fill = LABEL_FILL
        lc.alignment = Alignment(horizontal="center")
        ws.merge_cells(start_row=input_r, start_column=c0, end_row=input_r, end_column=c1)
        ic = ws.cell(input_r, c0)
        ic.fill = INPUT_FILL
        ic.border = KEYBOX
        ic.font = Font(name=FONT, size=12)
        ic.alignment = Alignment(horizontal="center", vertical="center")
        slots.append((k, input_r, c0))
    ws.row_dimensions[label_r].height = 12
    ws.row_dimensions[input_r].height = 22
    r += 2

    return r + 1, shift_cells, slots


# ============================================================
# レイヤー用シートを作る
# ============================================================
layers = []   # (シート名, レイヤー名, n_shift, shift_cells, slots)

for sheet_name, n_shift, n_layers, subtitle in SHEETS:
    ws = wb.create_sheet(sheet_name)
    ws.cell(1, 1, sheet_name + "レイヤー").font = Font(name=FONT, size=16, bold=True)
    ws.cell(2, 1, subtitle).font = Font(name=FONT, size=10, color="666666")
    ws.cell(3, 1, "使わないレイヤーは、シフトキー欄を空欄のままにしてください。"
                  "そのレイヤーは無視されます。").font = Font(name=FONT, size=9, color="666666")

    start_row = 5
    if sheet_name == "単打":
        ws.cell(5, 1, "配列名").font = Font(name=FONT, bold=True)
        ws.cell(6, 1, "作者").font = Font(name=FONT, bold=True)
        ws.cell(5, 2, "（ここに配列名）")
        for rr in (5, 6):
            ws.merge_cells(start_row=rr, start_column=2, end_row=rr, end_column=2 + SUB * 3 - 1)
            ws.cell(rr, 2).fill = INPUT_FILL
            ws.cell(rr, 2).border = BORDER
            ws.cell(rr, 2).font = Font(name=FONT)
        start_row = 9

    cur = start_row
    dv = DataValidation(type="list", formula1=KEYLIST_REF, allow_blank=True)
    dv.error = "一覧にないキーIDです。"
    dv.errorTitle = "キーIDが不正です"
    ws.add_data_validation(dv)

    for i in range(1, n_layers + 1):
        lname = sheet_name if n_shift == 0 else f"{sheet_name}-{i:02d}"
        title = ("■ 単打レイヤー" if n_shift == 0
                 else f"■ {sheet_name}レイヤー {i:02d}")
        cur, scells, slots = draw_keyboard(ws, cur, title, n_shift)
        for (sr, sc) in scells:
            dv.add(f"{get_column_letter(sc)}{sr}")
        layers.append((sheet_name, lname, n_shift, scells, slots))

    ws.column_dimensions["A"].width = 11
    for c in range(2, BASE_COL + 13 * SUB + 2):
        ws.column_dimensions[get_column_letter(c)].width = 3.0
    ws.freeze_panes = f"B{start_row}"


# ============================================================
# 個別指定シート
# ============================================================
ws2 = wb.create_sheet("個別指定")
ws2["A1"] = "個別指定（正データ）"
ws2["A1"].font = Font(name=FONT, size=14, bold=True)
ws2["A2"] = ("キー1〜4・打鍵タイプは、各レイヤーシートから自動で反映されます（青字）。"
             "手で直接入力すると、その行は手入力が優先されます。")
ws2["A2"].font = Font(name=FONT, size=10, color="666666")
ws2["A3"] = ("文字キー同士の同時打鍵（でぃ = t + l など）や連続打鍵は、"
             "ここに直接記入してください。")
ws2["A3"].font = Font(name=FONT, size=10, color="666666")

HEADERS = ["かな", "グループ", "キー1", "キー2", "キー3", "キー4", "打鍵タイプ", "備考"]
HROW = 5
for c, h in enumerate(HEADERS, 1):
    cell = ws2.cell(HROW, c, h)
    cell.font = Font(name=FONT, bold=True, color="FFFFFF")
    cell.fill = HDR_FILL
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = BORDER

EX = HROW + 1
for c, v in enumerate(["【例】でぃ", "外来音", "t", "l", "", "", "同時",
                       "文字キー同士の同時打鍵（手入力）"], 1):
    cell = ws2.cell(EX, c, v)
    cell.font = Font(name=FONT, italic=True, color="808080")
    cell.border = BORDER

row = EX + 1
data_start = row
for group, kanas in GROUPS.items():
    for k in kanas:
        ws2.cell(row, 1, k).font = Font(name=FONT, size=11)
        ws2.cell(row, 1).fill = LOCK_FILL
        ws2.cell(row, 1).alignment = Alignment(horizontal="center")
        ws2.cell(row, 2, group).font = Font(name=FONT, size=9, color="666666")
        ws2.cell(row, 2).fill = GRP_FILL
        for c in range(3, 9):
            ws2.cell(row, c).fill = INPUT_FILL
            ws2.cell(row, c).font = Font(name=FONT)
        for c in range(1, 9):
            ws2.cell(row, c).border = BORDER
        row += 1
data_end = row - 1

dv_type = DataValidation(type="list", formula1='"同時,連続"', allow_blank=True)
ws2.add_data_validation(dv_type)
dv_type.add(f"G{data_start}:G{data_end}")

for col, w in {"A": 10, "B": 14, "C": 11, "D": 11, "E": 11,
               "F": 11, "G": 12, "H": 30}.items():
    ws2.column_dimensions[col].width = w
ws2.freeze_panes = f"A{data_start}"


# ============================================================
# 隠しシート: 対応表（レイヤー → 個別指定 の橋渡し）
# ============================================================
lk = wb.create_sheet("_対応表")
lk.append(["シート", "レイヤー", "キーID", "シフト1", "シフト2", "シフト3",
           "かな", "キー1", "キー2", "キー3", "キー4", "打鍵タイプ",
           "個別指定に行があるか", "重複"])
for c in range(1, 15):
    lk.cell(1, c).font = Font(name=FONT, bold=True)

lrow = 2
for sheet_name, lname, n_shift, scells, slots in layers:
    q = f"'{sheet_name}'"
    srefs = [f"{q}!${get_column_letter(c)}${r}" for (r, c) in scells]
    # シフトキーが1つでも空欄ならこのレイヤーは無効
    guard = ""
    if srefs:
        conds = ",".join(f'{s}=""' for s in srefs)
        guard = f"OR({conds})" if len(srefs) > 1 else f'{srefs[0]}=""'

    for k, ir, c0 in slots:
        ref = f"{q}!{get_column_letter(c0)}{ir}"
        lk.cell(lrow, 1, sheet_name)
        lk.cell(lrow, 2, lname)
        lk.cell(lrow, 3, k)
        for i in range(3):
            lk.cell(lrow, 4 + i,
                    f'=IF({srefs[i]}="","",{srefs[i]})' if i < len(srefs) else '=""')
        clean_expr = f'SUBSTITUTE(SUBSTITUTE({ref}," ",""),"　","")'
        if guard:
            lk.cell(lrow, 7, f'=IF({guard},"",IF({ref}="","",{clean_expr}))')
        else:
            lk.cell(lrow, 7, f'=IF({ref}="","",{clean_expr})')
        # キー1〜4: シフトキーを先、文字キーを最後に置く
        for i in range(4):
            col = 8 + i
            if i < n_shift:
                lk.cell(lrow, col, f'=IF($G{lrow}="","",{srefs[i]})')
            elif i == n_shift:
                lk.cell(lrow, col, f'=IF($G{lrow}="","","{k}")')
            else:
                lk.cell(lrow, col, '=""')
        lk.cell(lrow, 12,
                f'=IF($G{lrow}="","","同時")' if n_shift else '=""')
        lk.cell(lrow, 13,
                f'=IF($G{lrow}="","",IF(ISNA(MATCH($G{lrow},個別指定!$A:$A,0)),"行なし",""))')
        lrow += 1
LK_LAST = lrow - 1

for r in range(2, LK_LAST + 1):
    lk.cell(r, 14, f'=IF($G{r}="","",IF(COUNTIF($G$2:$G${LK_LAST},$G{r})>1,"重複",""))')
for c, w in zip(range(1, 15), (12, 14, 10, 10, 10, 10, 10, 10, 10, 10, 10, 12, 20, 8)):
    lk.column_dimensions[get_column_letter(c)].width = w
lk.sheet_state = "hidden"

# 個別指定シートに自動反映の数式
for r in range(data_start, data_end + 1):
    m = f'MATCH($A{r},_対応表!$G$2:$G${LK_LAST},0)'
    for i, col in enumerate((3, 4, 5, 6)):
        ws2.cell(r, col, f'=IFERROR(INDEX(_対応表!${get_column_letter(8+i)}$2:'
                         f'${get_column_letter(8+i)}${LK_LAST},{m}),"")')
    ws2.cell(r, 7, f'=IFERROR(INDEX(_対応表!$L$2:$L${LK_LAST},{m}),"")')
    for col in (3, 4, 5, 6, 7):
        ws2.cell(r, col).font = Font(name=FONT, color="0070C0")
        ws2.cell(r, col).alignment = Alignment(horizontal="center")

# 単打シートに集計を表示
ws_top = wb["単打"]
summ = [("反映済みのかな数", f'=SUMPRODUCT((_対応表!$G$2:$G${LK_LAST}<>"")*1)'),
        ("重複しているかな", f'=COUNTIF(_対応表!$N$2:$N${LK_LAST},"重複")'),
        ("個別指定に行がないかな", f'=COUNTIF(_対応表!$M$2:$M${LK_LAST},"行なし")'),
        ("使用中のレイヤー数",
         f'=SUMPRODUCT((_対応表!$B$2:$B${LK_LAST}<>"")*(_対応表!$G$2:$G${LK_LAST}<>""))')]
for i, (label, formula) in enumerate(summ):
    ws_top.cell(5 + i, 2 + SUB * 4, label).font = Font(name=FONT, bold=True, size=10)
    ws_top.cell(5 + i, 2 + SUB * 6, formula).font = Font(name=FONT, bold=True)


# ============================================================
# 記入方法 / キーID一覧
# ============================================================
ws3 = wb.create_sheet("記入方法")
guide = [
    ("記入方法", None),
    ("", None),
    ("1. レイヤーシート", None),
    ("単打", "シフトなしで打ったときのかなを、キーの位置に記入します。"),
    ("2キー同時", "シフトキーを1つ指定し、それと同時に押したときのかなを記入。20面あります。"),
    ("3キー同時", "シフトキーを2つ指定。その2つ + 文字キーの3キー同時打鍵。20面。"),
    ("4キー同時", "シフトキーを3つ指定。その3つ + 文字キーの4キー同時打鍵。20面。"),
    ("使わないレイヤー", "シフトキー欄を空欄のままにしてください。無視されます。"),
    ("", None),
    ("2. 個別指定シート（正データ）", None),
    ("自動反映", "レイヤーシートの内容が青字で自動的に入ります。数式です。"),
    ("手入力の優先", "青字のセルに直接入力すると、その行は手入力が優先されます。"),
    ("ここにしか書けないもの",
     "文字キー同士の同時打鍵（でぃ = t + l）と、連続打鍵（が = か → 濁点キー）。"),
    ("連続打鍵の書き方", "キー1・キー2… に順に打つキーを入れ、打鍵タイプを「連続」にします。"),
    ("", None),
    ("3. 拗音・外来音について", None),
    ("分解して打つ配列", "「ゃ」にキーを割り当てれば「しゃ」は自動で2打鍵になります。記入不要です。"),
    ("1打で打つ配列", "該当レイヤーの位置か、個別指定シートに記入してください。"),
    ("", None),
    ("4. 確認用の集計（単打シート右上）", None),
    ("反映済みのかな数", "レイヤーに記入され、個別指定へ反映された数。"),
    ("重複しているかな", "同じかなが複数のキーに割り当てられている数。0 が理想です。"),
    ("個別指定に行がないかな", "一覧にないかなを記入した場合。個別指定シートに行を追加してください。"),
    ("", None),
    ("5. 親指キー", None),
    ("space / muhenkan / henkan / kana", "スペース / 無変換 / 変換 / かな"),
    ("lshift / rshift", "左右のシフトキー。記号入力などで使う場合に指定します。"),
    ("lthumb / rthumb", "自作キーボードの左右親指キー"),
    ("space を押す親指", "既定は「打鍵する手と逆の親指」。親指の移動距離は指と別に集計します。"),
]
for i, (a, b) in enumerate(guide, 1):
    ws3.cell(i, 1, a)
    if b:
        ws3.cell(i, 2, b)
    ws3.cell(i, 1).font = Font(name=FONT, bold=(b is None and a != ""),
                               size=12 if i == 1 else 11)
    ws3.cell(i, 2).font = Font(name=FONT)
    ws3.cell(i, 2).alignment = Alignment(wrap_text=True, vertical="top")
ws3.column_dimensions["A"].width = 32
ws3.column_dimensions["B"].width = 78

ws4 = wb.create_sheet("キーID一覧")
ws4["A1"] = "使用できるキーID（QWERTY 刻印での位置）"
ws4["A1"].font = Font(name=FONT, size=13, bold=True)
r = 3
for kb_row in (3, 2, 1, 0):
    ws4.cell(r, 1, ROW_LABEL[kb_row]).font = Font(name=FONT, bold=True)
    for c, k in enumerate(PHYSICAL_ROWS[kb_row], 2):
        cell = ws4.cell(r, c, k)
        cell.font = Font(name=FONT)
        cell.alignment = Alignment(horizontal="center")
        cell.border = BORDER
    r += 1
r += 1
ws4.cell(r, 1, "親指キー").font = Font(name=FONT, bold=True)
for c, k in enumerate(sorted(THUMB_KEYS), 2):
    ws4.cell(r, c, k).font = Font(name=FONT)
    ws4.cell(r, c).border = BORDER
r += 1
ws4.cell(r, 1, "シフトキー").font = Font(name=FONT, bold=True)
for c, k in enumerate(sorted(SHIFT_KEYS), 2):
    ws4.cell(r, c, k).font = Font(name=FONT)
    ws4.cell(r, c).border = BORDER
ws4.column_dimensions["A"].width = 18
for c in range(2, 15):
    ws4.column_dimensions[get_column_letter(c)].width = 11

# 読み取り用メタ情報
mt = wb.create_sheet("_meta")
mt.append(["sheet", "layer", "n_shift", "shift_cells", "key", "input_row", "col"])
for sheet_name, lname, n_shift, scells, slots in layers:
    sc = ";".join(f"{r}:{c}" for (r, c) in scells)
    for k, ir, c0 in slots:
        mt.append([sheet_name, lname, n_shift, sc, k, ir, c0])
mt.sheet_state = "hidden"

wb.save("layout_input.xlsx")
print("layout_input.xlsx を生成しました")
print(f"  レイヤー総数: {len(layers)} 面 "
      f"(単打1 / 2キー同時{N_LAYERS} / 3キー同時{N_LAYERS} / 4キー同時{N_LAYERS})")
print(f"  対応表: {LK_LAST - 1} 行")
print(f"  個別指定: {data_end - data_start + 1} 行")
