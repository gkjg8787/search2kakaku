import sys
import os
import json

import httpx

from sofmap.parser import CategoryParser


SOFMAP_URL = "https://www.sofmap.com/"
A_SOFMAP_URL = "https://a.sofmap.com/"

TEMP_FILENAME = "category_temp111.html"
OUTPUT_FILENAME = "category.json"


def dl_sofmap_top(url, filename):
    res = httpx.get(url)
    res.raise_for_status()
    with open(filename, "w") as f:
        f.write(res.text)


def main(
    argv,
    temp_filename=TEMP_FILENAME,
    is_delete_temp_file=True,
    output_filename=OUTPUT_FILENAME,
):
    sitename = SOFMAP_URL
    if len(argv) == 2:
        target = str(argv[1]).lower()
        if target == "a" or target == "akiba":
            sitename = A_SOFMAP_URL
    try:
        dl_sofmap_top(sitename, temp_filename)
    except Exception as e:
        print(f"ダウンロードに失敗 {e}")
        return
    if not os.path.exists(temp_filename):
        print(f"{temp_filename} が存在しません")
        return
    with open(temp_filename, "r") as f:
        html = f.read()

    cp = CategoryParser(html_str=html)
    cp.execute()
    with open(output_filename, "w") as f:
        f.write(json.dumps(cp.results.name_to_gid, ensure_ascii=False))

    if is_delete_temp_file:
        os.remove(temp_filename)


if __name__ == "__main__":
    main(sys.argv)
