# 外付け HTML パーサー

## 概要

- コマンドによる価格情報取得、検索＆登録、アップデート。selenium 使用。

## 対応サイト

- sofmap の検索結果（個別詳細ページには未対応）

## 使い方

- python sofmap_search.py "keyword" で情報取得 + URL、ログデータベース登録
- python register_for_updates.py --add --new でアップデート対象に登録
  - 検索を挟まず直接 URL をアップデート対象に登録
    - 登録したい URL 一覧を一行一 URL のファイルを用意する。例 urls.txt
    - python register_for_updates.py --add -f urls.txt で URL、アップデート対象として登録
  - アップデート対象から URL を外す
    - 外したい URL 一覧を一行一 URL のファイルを用意する。 例 urls.txt
    - python register_for_updates.py --remove -f urls.txt でアップデート対象から除外
    - 全て外すなら python register_for_updates.py --remove --all
- python update_urls.py でアップデート対象の URL から情報を取得 → データベース登録
- python notifi_to_api.py で 設定した kakakuscraping の API へログデータを送信
- ※細かいオプションは --help を参照

### celery beat による自動アップデート

- celery beat を使用すると定期的にアップデートすることができる。対象のファイルは tasks.py
- サンプルとして compose_sample に celery beat を動かす compose.yaml を置いた。このディレクトリ配下を README.md があるフォルダにコピーして使用する。
- tasks.py の` "schedule": crontab(hour="14"),`を変更することで動作時間を変更可能。

### kakakuscraping-fastapi への通知

- 使用するには以下の設定が必要。
  - ex_scraping/settings.py の送信先の API の URL 設定を書き換える。
  - kakakuscraping-fastapi 側の API も有効にする。
  - 事前に API を使用して kakakuscraping-fastapi のアイテムにアップデート対象の URL を登録する必要がある。
- celery beat を使用するにはタスクを変更する必要がある。
  - tasks.py のコメントアウトされている`"update-and-notify-every-day"`を有効にし、重複する`"update-every-day"`をコメントアウトする。
