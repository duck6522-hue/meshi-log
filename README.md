# めしログ

食事と体重を記録する、自分用のカロリー管理アプリです（スマホ向けPWA）。

- **きょう**: 朝食・昼食・夕食・間食ごとに記録。1日の合計カロリーと PFC（たんぱく質・脂質・炭水化物）を、目標に対する進捗バーつきで表示
- **食品の検索・追加**: 食品名（ひらがな・カタカナ・漢字）で検索し、g や「1個」「茶碗1杯」などの単位で量を調整して記録
- **マイ食品**: よく食べるものを手入力で登録（100gあたり／1食分あたりのどちらでも入力可）
- **体重**: 日ごとの体重を記録し、推移を折れ線グラフで表示
- **設定**: 目標カロリー、目標体重、PFC の目標比率、バックアップの書き出し・読み込み
- **端末内に保存**: データはその端末のブラウザ内（localStorage）だけに保存され、どこにも送信されません。オフラインでも動きます

## 使い方

ビルド不要の静的サイトです。GitHub Pages で `main` ブランチのルートを公開し、スマホのブラウザで開いて「ホーム画面に追加」してください。

手元で試すとき:

```sh
python3 -m http.server 8000   # http://localhost:8000/ を開く
```

## ファイル

| ファイル | 内容 |
|---|---|
| `index.html` | アプリ本体（HTML・CSS・JS） |
| `foods.json` | 同梱の食品データ（100gあたりのカロリーと PFC） |
| `sw.js` / `manifest.webmanifest` / `icon*` | PWA 用（オフライン対応・ホーム画面アイコン） |
| `tools/` | `foods.json` を作り直すためのスクリプトと通称リスト |

## 食品データ

文部科学省「日本食品標準成分表2020年版（八訂）」の全 2,478 品目について、可食部 100g あたりのエネルギー・たんぱく質・脂質・炭水化物（差引き法）を収録しています。JSON 化には [katoharu432/standards-tables-of-food-composition-in-japan](https://github.com/katoharu432/standards-tables-of-food-composition-in-japan)（CC BY 4.0）を利用しました。

よく使う 386 品目には `tools/common.txt` で通称（「ごはん（白米）」「鶏むね肉（皮なし）」など）と目安の単位（「1個＝50g」など）を付けています。通称や単位を足したいときは `common.txt` を編集して作り直します。

```sh
python3 tools/build_foods.py path/to/data.json --check   # 結びつきの確認だけ
python3 tools/build_foods.py path/to/data.json           # foods.json を書き出す
```

`foods.json` や `index.html` を更新したら、`sw.js` の `CACHE` の番号を上げる必要はありません（ネットワーク優先で取り直します）。
