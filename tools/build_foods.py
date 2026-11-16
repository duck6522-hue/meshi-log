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
    return 0 if v is None else round(float(v), 1)

def clean(name):
    return re.sub(r"\s+", " ", name).strip()

foods = [{"id": x["foodId"], "name": clean(x["foodName"]), "kcal": num(x["enercKcal"]),
          "p": num(x["prot"]), "f": num(x["fat"]), "c": num(x["chocdf"])} for x in src]

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
if not check:
    out = {
        "source": "日本食品標準成分表2020年版（八訂）",
        "per": "可食部100gあたり。c は差引き法による炭水化物",
        "foods": [[f["id"], f["name"], f["kcal"], f["p"], f["f"], f["c"]] for f in foods],
        "common": common,
    }
    (here.parent / "foods.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
