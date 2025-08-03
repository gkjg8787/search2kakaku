# 外付け HTML パーサー

## 概要

- コマンドによる価格情報取得、検索＆登録、アップデート。selenium 使用。

## 対応サイト

- sofmap
  - 検索結果(https://www.sofmap.com/search_result.aspx)に対応。個別ページ(https://www.sofmap.com/product_detail.aspx)には非対応。akiba sofmap(https://a.sofmap.com/)も同様。

## 使い方

- `python sofmap_search.py "keyword"` で情報取得 + URL、ログデータベース登録
- `python register_for_updates.py add --new` でアップデート対象に登録
  - 検索を挟まず直接 URL をアップデート対象に登録
    - 登録したい URL 一覧を一行一 URL のファイルを用意する。例 urls.txt
    - `python register_for_updates.py add -f urls.txt` で URL、アップデート対象として登録
  - アップデート対象から URL を外す
    - 外したい URL 一覧を一行一 URL のファイルを用意する。 例 urls.txt
    - `python register_for_updates.py remove -f urls.txt` でアップデート対象から除外
    - 全て外すなら `python register_for_updates.py remove --all`
  - アップデート対象情報の確認
    - `python register_for_updates.py view` で URL のアップデート対象かどうかを確認可能
      - is_active=True でアップデート対象
- `python update_urls.py` でアップデート対象の URL から情報を取得 → データベース登録
- `python notifi_to_api.py` で 設定した kakakuscraping の API へログデータを送信
- ※細かいオプションは `--help` を参照

### celery beat による自動アップデート

- celery beat を使用すると定期的にアップデートすることができる。対象のファイルは tasks.py
- サンプルとして compose_sample に celery beat を動かす compose.yaml を置いた。このディレクトリ配下を README.md があるフォルダにコピーして使用する。
- tasks.py の` "schedule": crontab(hour="14"),`を変更することで動作時間を変更可能。

### kakakuscraping-fastapi への通知

- 使用するには以下の設定が必要。
  - ex_scraping/settings.py の送信先の API の URL 設定を書き換える。
  - kakakuscraping-fastapi 側の API も有効にする。
  - kakakuscraping-fastapi のアイテムにアップデート対象の URL を登録する必要がある。
    - 対象の API 側の docs から直接操作して登録する方法とコマンドを使用する方法がある。ここではコマンドのみ説明。
    - `python create_item_url_via_api.py` を使用して kakakuscraping-fastapi に新規アイテムを追加 または既存のアイテムに URL を追加する。
      - オプション `--new_item "item name" --url "url1" "url2"` で新規アイテムとそのアイテムに URL 追加。
      - オプション `--item_id [number] --url "url1" "url2"` で登録済みアイテムに URL を追加。
- celery beat を使用するにはタスクを変更する必要がある。
  - tasks.py のコメントアウトされている`"update-and-notify-every-day"`を有効にし、重複する`"update-every-day"`をコメントアウトする。

### その他

- `python view_log.py`でコマンドのログを表示。
