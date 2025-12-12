# Search API to kakakuscraping API

## 目次

- [概要](#概要)

## 概要

- 価格情報取得のための自動アップデートとURLの登録API。kakakuscraping-fastapi への情報の送信（任意）。[external_search](https://github.com/gkjg8787/external_search)が必要。[kakakuscraping-fastapi](https://github.com/gkjg8787/kakakuscraping-fastapi)を使用（※必要なら）。

- [旧 README.md (pythonコマンドの説明)](old/README.md)
  - チェックはしてないが動くはず

- HTMLでURLの追加、kakakuscrapingへの登録の操作が可能
  - `docker compose up -d` で起動後、`http://localhost:8120/url/` にアクセス
  - kakakuscrapingとの連携は[settings.py](search2kakaku/settings.py)で以下の`"to_link": False`を`True`に変更する。必要に応じて`base_url`の項目も変更が必要。

```
HTML_OPTIONS = {
    "kakaku": {
        "to_link": False,
        "base_url": "post_data",  # Base of the link URL, post_data or any URL
    }
}
```

