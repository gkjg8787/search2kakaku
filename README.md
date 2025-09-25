# Search API to kakakuscraping API

## 目次

- [概要](#概要)
- [対応サイト](#対応サイト)
- [前提](#前提)
- [起動](#起動)
- [使い方](#使い方)
  - [`search.py` - 商品の検索と価格情報の初期登録](#search.py---商品の検索と価格情報の初期登録)
  - [`register_for_updates.py` - 自動更新対象の管理](#register_for_updates.py---自動更新対象の管理)
  - [`update_urls.py` - 価格情報の更新](#update_urls.py---価格情報の更新)
  - [`send_to_api.py` - `kakakuscraping-fastapi`との連携](#send_to_api.py---kakakuscraping-fastapiとの連携)
  - [`view_log.py` - コマンドログの表示](#view_log.py---コマンドログの表示)
- [celery beat による自動アップデート](#celery-beat-による自動アップデート)
- [kakakuscraping-fastapi への通知](#kakakuscraping-fastapi-への通知)
- [その他](#その他)
- [Gemini API の使用例](#gemini-api-の使用例)

## 概要

- コマンドによる価格情報取得、検索＆登録、アップデート。kakakuscraping-fastapi への情報の送信（任意）。[external_search](https://github.com/gkjg8787/external_search)が必要。[kakakuscraping-fastapi](https://github.com/gkjg8787/kakakuscraping-fastapi)を使用（※必要なら）。

## 対応サイト

- external_search で対応できるサイトのリスト
  - sofmap
  - geo
  - iosys
  - その他(gemini によるパーサ作成)

## 前提

- docker 導入済み
- [external_search](https://github.com/gkjg8787/external_search)の稼働。
- [kakakuscraping-fastapi](https://github.com/gkjg8787/kakakuscraping-fastapi)の稼働(※必要なら)。
- celery & redis (※自動アップデートを使用するなら)。

## 起動

- search2kakaku/settings.py の API_OPTIONS を設定する。
  - `get_data->url` を external_search の URL に書き換える。
  - [kakakuscraping-fastapi](https://github.com/gkjg8787/kakakuscraping-fastapi)への接続が必要なら`post_data->url`も書き換える。
- `docker compose up --build -d`

## 使い方

- 基本は`search2kakaku`コンテナに入ってコマンドで操作する。<br>`docker compose exec -it search2kakaku bash`
- 実行するディレクトリパスはコンテナ内の`/app/search2kakaku`を想定。
- 各コマンドの詳細なオプションは `--help` を参照。

---

### `search.py` - 商品の検索と価格情報の初期登録

各サイトをキーワードで検索し、取得した商品情報（URL、価格など）をデータベースに登録します。この時点では、自動更新の対象にはなりません。

**書式:**
`python search.py [サイト名] "キーワード" [オプション]`

**対応サイトと主なオプション:**

- **`sofmap`**
  - `-a, --akiba`: 秋葉原の店舗(`a.sofmap.com`)を検索対象にします。
  - `-ca, --category`: カテゴリを指定します (例: 'PC パーツ')。
  - `--categorylist`: 指定可能なカテゴリの一覧を表示します。
  - `-co, --condition`: 商品状態を指定します (`NEW`, `USED`など)。
- **`geo`**
  - オプションは少なく、キーワード検索が主です。
- **`iosys`**
  - `--condition`: 商品状態を指定します (`new`, `used`, `a`)。
  - `--sort`: 表示順を指定します (`l`: 価格が安い順, `h`: 高い順など)。
  - `--min_price`, `--max_price`: 価格範囲を指定します。

**共通オプション:**

- `-v, --verbose`: 結果をコンソールに表示します。
- `--without_registration`: データベースに登録せず、検索結果の表示のみ行います。

---

### `register_for_updates.py` - 自動更新対象の管理

`search.py`で登録した商品や、直接指定した URL を自動更新の対象として管理します。

**コマンド一覧:**

- **`view` - 更新対象の確認**

  - `python register_for_updates.py view`
  - `--target [all|active|inactive]`: 表示する対象を絞り込みます（デフォルト: `all`）。
  - `--url_option`: Gemini API 用のオプションも表示します。

- **`add` - 更新対象への追加**

  - `python register_for_updates.py add --new`: `search.py`で検索後、まだ更新対象になっていない URL をすべて追加します。
  - `python register_for_updates.py add --all`: データベース内のすべての URL を更新対象にします。
  - `python register_for_updates.py add --url <URL>`: 指定した URL を更新対象に追加します。
  - `python register_for_updates.py add --url_id <ID>`: 指定した URL ID を更新対象に追加します。
  - `python register_for_updates.py add -f <ファイル名>`: ファイルに記載された URL リストをまとめて追加します。

- **`remove` - 更新対象からの除外**

  - `python register_for_updates.py remove --all`: すべての URL を更新対象から外します。
  - `python register_for_updates.py remove --url <URL>`: 指定した URL を更新対象から外します。
  - `python register_for_updates.py remove --url_id <ID>`: 指定した URL ID を更新対象から外します。
  - `python register_for_updates.py remove -f <ファイル名>`: ファイルに記載された URL リストをまとめて除外します。

- **`gemini` - Gemini API 用オプションの設定**
  - `python register_for_updates.py gemini --url_id <ID> --options '{"key": "value"}'`: 指定した URL ID に対して、スクレイピング時に使用する Gemini API のオプションを JSON 形式で設定します。
  - `--options_from <ファイル名>`でファイルからオプションを読み込むことも可能です。
  - **Note:** `--options`や`--options_from`で指定する JSON ファイルは、`create_gemini_options.py`スクリプトを使って対話的に作成できます。<br>`python create_gemini_options.py -o my_options.json --view`<br>このスクリプトは、external_search の gemini api オプションの設定を対話形式で案内し、ファイルに保存します。

---

### `update_urls.py` - 価格情報の更新

`register_for_updates.py`で更新対象に設定されている URL の価格情報を取得し、データベースに保存します。

- `python update_urls.py`: 更新対象になっているすべての URL の価格情報を更新します。
- `python update_urls.py --url_id <ID>`: 指定した URL ID の価格情報のみを更新します。

---

### `send_to_api.py` - `kakakuscraping-fastapi`との連携

`kakakuscraping-fastapi`へ価格ログを送信したり、アイテム情報を操作したりします。

**コマンド一覧:**

- **`send_log` - 価格ログの送信**

  - `python send_to_api.py send_log`
  - `-sjd`, `-sud`などでログの開始日時を指定可能です。

- **`create_item` - 新規アイテムの作成**

  - `python send_to_api.py create_item --name "アイテム名" --url "URL1" "URL2"`

- **`add_url` - 既存アイテムへの URL 追加**

  - `python send_to_api.py add_url --item_id <アイテムID> --url "URL"`

- **`get_item` - アイテム情報の取得**
  - `python send_to_api.py get_item --url "URL"`: 指定 URL が登録されているアイテムの情報を取得します。

---

### `view_log.py` - コマンドログの表示

`application.log`に記録された JSON 形式のログを見やすく表示します。

- `python view_log.py`: ログを表示します。
- `-f <ファイル名>`: 表示するログファイルを指定します。
- `--head <行数>`, `--tail <行数>`: 先頭または末尾から指定行数のみ表示します。
- `--key <キー>`: 指定したキーを含むログのみ表示します (複数指定は OR 条件)。
- `--search <キー:値>`: 指定したキーと値のペアに一致するログのみ表示します (複数指定は AND 条件)。

### celery beat による自動アップデート

- celery beat を使用すると定期的にアップデートすることができる。対象のファイルは tasks.py
- サンプルとして compose_sample ディレクトリ に celery beat を動かす compose.yaml を置いた。このディレクトリ配下を README.md があるフォルダにコピーして使用する。
- settings.py の設定
  - `AUTO_UPDATE_OPTIONS`の`"schedule"`を変更することで動作時間を変更可能。または直接 tasks.py の` "schedule": crontab(hour="14"),`を変更することで動作時間を変更可能。
- compose_sample 配下の compose.yaml を使用する際は一度 search2kakaku だけを起動してコンテナに入り DB を作る必要がある。<br>コンテナに入った後、<br>`cp tool/db_create.py .` <br>`python db_create.py`<br>DB 作成後、他のコンテナを起動する。

### kakakuscraping-fastapi への通知

- 使用するには以下の設定が必要。
  - settings.py の設定
    - `API_OPTIONS`の`post_data`、送信先の API の URL 設定を書き換える。
    - `AUTO_UPDATE_OPTIONS`の`enable`を True にする。`notify_to_api`を True にする。
  - [kakakuscraping-fastapi](https://github.com/gkjg8787/kakakuscraping-fastapi)側の API も有効にする。
  - kakakuscraping-fastapi のアイテムにアップデート対象の URL を登録する必要がある。
    - 対象の API 側の docs から直接操作して登録する方法とコマンドを使用する方法がある。ここではコマンドのみ説明。
    - 以下を使用して kakakuscraping-fastapi に新規アイテムを追加する。<br>`python send_to_api.py create_item --name "item name" --url "url1" "url2"`
    - 既存アイテムに URL を追加する<br>`python send_to_api.py add_url --item_id [number] --url "url1"`
- celery beat で通知を定期実行するにはタスクを変更する必要がある。
  - tasks.py のコメントアウトされている`"update-and-notify-every-day"`を有効にし、重複する`"update-every-day"`をコメントアウトする。

### その他

- 取得した URL のログを見るには sqlite3 を使う。データベースのパスと名前は settings.py で設定したものを使用する。<br>`sqlite3 ../db/database.db "select * from pricelog"`
- DB について
  - settings.py に非同期(a_sync)と同期(sync)の設定があるが同期は DB 作成の時に使用。それ以外のアクセスは基本的に非同期のみを使用している。

### Gemini API の使用例

- kakakuscraping-fastapi にアイテムと URL を追加<br>`python send_to_api.py create_item --name "マリオカートワールド" --url "https://www.biccamera.com/bc/category/001/210/?q=%83}%83%8A%83I%83J%81[%83g%83%8F%81[%83%8B%83h%20%83\%83t%83g"`
- gemini 用オプションの作成<br>

```
python create_gemini_options.py -o biccamera_options.json

GEMINI API Options Creator
Sitename: biccamera
Label: biccamera_search
Recreate Parser (y/n, default n):
Exclude Script (y/n, default y):
Compress Whitespace (y/n, default n):
Download Type (httpx/selenium/nodriver, default httpx): nodriver
Use Cookie (y/n, default n):
Use Wait CSS Selector (y/n, default n): y
CSS Selector: .bcs_listItem
Timeout (seconds): 15
On Error Action Type (raise/retry, default raise): retry
On Error Max Retries : 3
On Error Wait Time (seconds): 5
On Error Check Exist Tag (CSS selector, default ''):
Page Wait Time (seconds):
Successfully created GEMINI options and saved to biccamera_options.json
```

- update 対象に URL を追加<br>`python register_for_updates.py add --url "https://www.biccamera.com/bc/category/001/210/?q=%83}%83%8A%83I%83J%81[%83g%83%8F%81[%83%8B%83h%20%83\%83t%83g" --sitename gemini --options_from biccamera_options.json`

- 価格情報を取得<br>`python update_urls.py`<br>※gemini による新規のパーサを作成する場合は時間がかかります。またパーサの作成に失敗する場合もあります。その場合は何度かやり直す必要があります。
- 価格情報を kakakuscraping-fastapi に送信<br>`python send_to_api.py send_log`

### Geo の登録例

- 検索してログを取得<br>`python search.py geo "マリオカートワールド"`
- update 対象に登録<br>`python register_for_updates.py add --new`
- 登録された URL を確認<br>`python register_for_updates.py view`
  - こんな感じの情報が出てくる

```
 [{'id': 3, 'url': 'https://ec.geo-online.co.jp/shop/goods/search.aspx?search=x&keyword=%83%7D%83%8A%83I%83J%81%5B%83g%83%8F%81%5B%83%8B%83h&submit1=%91%97%90M'}]
```

- kakakuscraping-fastapi に URL を追加<br>`python send_to_api.py add_url --item_id 1 --url " https://ec.geo-online.co.jp/shop
/goods/search.aspx?search=x&keyword=%83%7D%83%8A%83I%83J%81%5B%83g%83%8F%81%5B%83%8B%83h&submit1=%91%97%90M"`

- 価格情報を kakakuscraping-fastapi に送信<br>`python send_to_api.py send_log`
