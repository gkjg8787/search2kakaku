# 外付け HTML パーサー

## 概要

- コマンドによる価格情報取得、検索＆登録、アップデート。selenium 使用。

## 対応サイト

- sofmap
  - 検索結果`https://www.sofmap.com/search_result.aspx`に対応。個別ページ`https://www.sofmap.com/product_detail.aspx`には非対応。akiba sofmap`https://a.sofmap.com/`も同様。

## 前提

- docker 導入済み

## 起動

- `docker compose up --build -d`

## 使い方

- 基本は`ex_scraping`コンテナに入ってコマンドで操作する。<br>`docker compose exec -it ex_scraping bash`

- 検索と価格情報の登録
  - `python search.py sofmap "keyword"` で情報取得、URL、価格ログのデータベース登録
  - この時点ではアップデート対象にはならない。
- アップデート対象情報の確認
  - `python register_for_updates.py view` で URL のアップデート対象かどうかを確認可。is_active=True でアップデート対象
- アップデート対象の登録
  - アップデート対象に新規登録<br>`python register_for_updates.py add --new`
  - 検索を挟まず直接 URL をアップデート対象に登録
    - 登録したい URL 一覧を一行一 URL のファイルを用意する。例 urls.txt
    - ファイルに書かれた URL を登録<br>`python register_for_updates.py add -f urls.txt`
  - アップデート対象から URL を外す
    - 外したい URL 一覧を一行一 URL のファイルを用意する。 例 urls.txt
    - アップデート対象から除外<br>`python register_for_updates.py remove -f urls.txt`
    - 全て外す<br>`python register_for_updates.py remove --all`
- アップデート対象の URL から価格情報を取得してデータベース登録<br>`python update_urls.py`
  - 細かい設定は[kakakuscraping-fastapi への通知](https://github.com/gkjg8787/external_scraping#kakakuscraping-fastapi への通知)を参照
- 設定した kakakuscraping の API へログデータを送信<br>`python send_to_api.py send_log`
- ※詳細オプションは `--help` を参照

### celery beat による自動アップデート

- celery beat を使用すると定期的にアップデートすることができる。対象のファイルは tasks.py
- サンプルとして compose_sample に celery beat を動かす compose.yaml を置いた。このディレクトリ配下を README.md があるフォルダにコピーして使用する。
- tasks.py の` "schedule": crontab(hour="14"),`を変更することで動作時間を変更可能。

### kakakuscraping-fastapi への通知

- 使用するには以下の設定が必要。
  - ex_scraping/settings.py の送信先の API の URL 設定を書き換える。
  - [kakakuscraping-fastapi](https://github.com/gkjg8787/kakakuscraping-fastapi)側の API も有効にする。
  - kakakuscraping-fastapi のアイテムにアップデート対象の URL を登録する必要がある。
    - 対象の API 側の docs から直接操作して登録する方法とコマンドを使用する方法がある。ここではコマンドのみ説明。
    - 以下を使用して kakakuscraping-fastapi に新規アイテムを追加する。<br>`python send_to_api.py create_item --name "item name" --url "url1" "url2"`
    - 既存アイテムに URL を追加する<br>`python send_to_api.py add_url --item_id [number] --url "url1"`
- celery beat で通知を定期実行するにはタスクを変更する必要がある。
  - tasks.py のコメントアウトされている`"update-and-notify-every-day"`を有効にし、重複する`"update-every-day"`をコメントアウトする。

### その他

- コマンドログを表示。<br>`python view_log.py`
