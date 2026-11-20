#!/usr/bin/env python3
"""foods.json を作る。
使い方: python3 tools/build_foods.py <data.json> [--check]
data.json は日本食品標準成分表2020年版(八訂)を JSON 化したもの
(https://github.com/katoharu432/standards-tables-of-food-composition-in-japan, CC BY 4.0)。
tools/common.txt に書いた通称を成分表の品目に結びつけ、全品目と一緒に ../foods.json へ書き出す。
"""
import json, re, sys, pathlib

here = pathlib.Path(__file__).resolve().parent
src = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
check = "--check" in sys.argv

def num(v):
    # 元データには "14.0†" "(0.5)" "Tr" のような注記つきの値がある。数字の部分だけを使う
    if v is None:
        return 0
    if isinstance(v, str):
        m = re.search(r"\d+\.?\d*", v)
        v = m.group(0) if m else 0
    return round(float(v), 1)

def clean(name):
    return re.sub(r"\s+", " ", name).strip()

foods = [{"id": x["foodId"], "name": clean(x["foodName"]), "kcal": num(x["enercKcal"]),
          "p": num(x["prot"]), "f": num(x["fat"]), "c": num(x["chocdf"]),
          "fib": num(x["fib"]), "salt": num(x["naclEq"])} for x in src]

common, problems = [], []
for raw in (here / "common.txt").read_text(encoding="utf-8").splitlines():
    if not raw.strip() or raw.startswith("#"):
        continue
    parts = [s.strip() for s in raw.split(";")]
    label, kana, pat = parts[0], parts[1], parts[2]
    units = []
    if len(parts) > 3 and parts[3]:
        for u in parts[3].split(","):
            ul, ug = u.rsplit("=", 1)
            units.append([ul.strip(), float(ug)])
    exact = [pat[1:]] if pat.startswith("=") else []
    if exact:
        hits = [f for f in foods if f["name"] == exact[0].strip()]
    else:
        toks = pat.split()
        inc = [t for t in toks if not t.startswith("!")]
        exc = [t[1:] for t in toks if t.startswith("!")]
        hits = [f for f in foods if all(t in f["name"] for t in inc) and not any(t in f["name"] for t in exc)]
        if len(hits) > 1:  # 語の並びが最も短い（＝余計な修飾がない）品目を優先
            short = min(len(f["name"]) for f in hits)
            best = [f for f in hits if len(f["name"]) == short]
            if len(best) == 1 and check:
                problems.append(f"? {label}: {len(hits)}件から最短を採用 -> {best[0]['name']} | 他: " + " / ".join(f['name'] for f in hits if f is not best[0])[:200])
            hits = best
    if len(hits) != 1:
        problems.append(f"! {label}: {len(hits)}件 [{pat}] " + " / ".join(f["name"] for f in hits[:8]))
        continue
    common.append({"id": hits[0]["id"], "n": label, "k": kana, "u": units})
    if check:
        f = hits[0]
        print(f"{label}\t{f['name']}\t{f['kcal']}\t{f['p']}\t{f['f']}\t{f['c']}")

seen = {}
for cm in common:
    if cm["id"] in seen:
        problems.append(f"! {cm['n']}: {seen[cm['id']]} と同じ品目に結びついています")
    seen[cm["id"]] = cm["n"]
print("\n".join(problems), file=sys.stderr)
print(f"foods={len(foods)} common={len(common)} problems={sum(p.startswith('!') for p in problems)}", file=sys.stderr)
# ---- 成分表にない料理（材料から計算）と市販品の目安
by_label = {cm["n"]: next(f for f in foods if f["id"] == cm["id"]) for cm in common}
by_name = {f["name"]: f for f in foods}
extra = []
for raw in (here / "dishes.txt").read_text(encoding="utf-8").splitlines():
    if not raw.strip() or raw.startswith("#"):
        continue
    label, kana, unit, recipe = [s.strip() for s in raw.split(";")]
    tot = {"g": 0.0, "kcal": 0.0, "p": 0.0, "f": 0.0, "c": 0.0, "fib": 0.0, "salt": 0.0}
    bad = False
    for part in recipe.split(","):
        ing, g = part.rsplit("=", 1)
        ing, g = ing.strip(), float(g)
        f = {"kcal": 0, "p": 0, "f": 0, "c": 0, "fib": 0, "salt": 0} if ing == "水" else by_label.get(ing) or by_name.get(ing)
        if f is None:
            problems.append(f"! {label}: 材料「{ing}」が見つかりません")
            bad = True
            continue
        tot["g"] += g
        for k in ("kcal", "p", "f", "c", "fib", "salt"):
            tot[k] += f[k] * g / 100
    if bad:
        continue
    ulabel, _, split = unit.partition("/")
    n = int(split) if split else 1
    units = [[ulabel, round(tot["g"] / n, 1)]]
    if n > 1:
        units.append([f"1人前（{n}{ulabel[1:]}）", round(tot["g"], 1)])
    per = {k: round(tot[k] * 100 / tot["g"], 2 if k == "salt" else 1) for k in ("kcal", "p", "f", "c", "fib", "salt")}
    extra.append({"id": "d:" + label, "n": label, "k": kana, "u": units, **per, "t": "d"})
    if check:
        print(f"{label}\t{ulabel} {units[0][1]}g\t{round(tot['kcal'] / n)}kcal\tP{round(tot['p'] / n, 1)} F{round(tot['f'] / n, 1)} C{round(tot['c'] / n, 1)} 繊維{round(tot['fib'] / n, 1)} 塩{round(tot['salt'] / n, 1)}")
for raw in (here / "extra.txt").read_text(encoding="utf-8").splitlines():
    if not raw.strip() or raw.startswith("#"):
        continue
    label, kana, kcal, pp, ff, cc, fib, salt, us = [s.strip() for s in raw.split(";")]
    units = [[u.rsplit("=", 1)[0].strip(), float(u.rsplit("=", 1)[1])] for u in us.split(",") if u.strip()]
    extra.append({"id": "x:" + label, "n": label, "k": kana, "u": units, "kcal": float(kcal), "p": float(pp), "f": float(ff), "c": float(cc), "fib": float(fib), "salt": float(salt), "t": "x"})
# ---- チェーン店の公式値（1食あたり）。重さがないので、100g を「1食」とみなして持つ
for raw in (here / "chains.txt").read_text(encoding="utf-8").splitlines():
    if not raw.strip() or raw.startswith("#"):
        continue
    cols = [s.strip() for s in raw.split(";")]
    shop, menu, size, kcal, pp, ff, cc, salt, kana = cols[:9]
    note = cols[9] if len(cols) > 9 else ""
    fib = float(cols[10]) if len(cols) > 10 and cols[10] not in ("", "-") else None  # 食物繊維（公表している店だけ）
    name = f"{shop} {menu}" + (f"（{size}）" if size != "-" else "")
    unit = size if size != "-" else "1食"
    nopfc = pp == "-"  # PFC が公表されていない店（n: で始まる id にして、アプリで「公表なし」と表示する）
    extra.append({"id": f"{'n' if nopfc else 's'}:{shop}:{menu}:{size}", "n": name, "k": f"{shop} {kana}", "u": [[unit, 100]],
                  "kcal": float(kcal), "p": 0.0 if nopfc else float(pp), "f": 0.0 if nopfc else float(ff), "c": 0.0 if nopfc else float(cc), "fib": fib, "salt": None if salt == "-" else float(salt), "t": "s", "shop": shop, **({"note": note} if note else {})})
# ---- 市販のお菓子（メーカー公式の栄養成分表示。基準量あたりの値を100gあたりに換算）
for raw in (here / "snacks.txt").read_text(encoding="utf-8").splitlines():
    if not raw.strip() or raw.startswith("#"):
        continue
    maker, name, kana, g, kcal, pp, ff, cc, fib, salt, us, url = [s.strip() for s in raw.split(" ; ")]
    g = float(g)
    k100 = lambda v: round(float(v) * 100 / g, 2)
    units = [[u.rsplit("=", 1)[0], float(u.rsplit("=", 1)[1])] for u in us.split(",") if u.strip()]
    basis = next((u for u, x in units if abs(x - g) < 0.01), None)
    if name in {cm["n"] for cm in common} | {e["n"] for e in extra}:
        name = f"{name}（{maker}）"  # 成分表の通称や他の品目と同じ名前なら、メーカー名を添える
    extra.append({"id": f"b:{maker}:{name}", "n": name, "k": f"{maker} {kana}", "u": units,
                  "kcal": k100(kcal), "p": k100(pp), "f": k100(ff), "c": k100(cc), "fib": None if fib == "-" else k100(fib), "salt": round(float(salt) * 100 / g, 3),
                  "t": "b", "shop": maker, "basis": f"{basis}（{g:g}g）" if basis else f"{g:g}g"})
names = [e["n"] for e in extra] + [cm["n"] for cm in common]
for n in sorted(set(x for x in names if names.count(x) > 1)):
    problems.append(f"! {n}: 名前が重複しています")
print("\n".join(p for p in problems if "材料" in p or "重複" in p), file=sys.stderr)
print(f"extra={len(extra)} problems={sum(p.startswith('!') for p in problems)}", file=sys.stderr)

if not check:
    out = {
        "source": "日本食品標準成分表2020年版（八訂）",
        "per": "可食部100gあたり。並びは id, 名前, kcal, たんぱく質, 脂質, 炭水化物(差引き法), 食物繊維総量, 食塩相当量",
        "foods": [[f["id"], f["name"], f["kcal"], f["p"], f["f"], f["c"], f["fib"], f["salt"]] for f in foods],
        "common": common,
        "extra": extra,
    }
    (here.parent / "foods.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
