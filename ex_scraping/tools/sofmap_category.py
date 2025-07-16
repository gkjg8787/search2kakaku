import sys
import os


from app.sofmap.category import dl_sofmap_top, SOFMAP_TOP_URL, A_SOFMAP_TOP_URL
from sofmap.parser import CategoryParser
from sofmap.repository import (
    FileCategoryRepository,
    FileAkibaCategoryRepository,
)


TEMP_FILENAME = "category_temp111.html"


def main(
    argv,
    temp_filename=TEMP_FILENAME,
    is_delete_temp_file=True,
):
    sitename = SOFMAP_TOP_URL
    if len(argv) == 2:
        target = str(argv[1]).lower()
        if target == "a" or target == "akiba":
            sitename = A_SOFMAP_TOP_URL
    try:
        text = dl_sofmap_top(sitename)
        with open(temp_filename, "w") as f:
            f.write(text.text)
    except Exception as e:
        print(f"ダウンロードに失敗 {e}")
        return
    if not os.path.exists(temp_filename):
        print(f"{temp_filename} が存在しません")
        return
    with open(temp_filename, "r") as f:
        html = f.read()

    cp = CategoryParser(html_str=html)
    if sitename == A_SOFMAP_TOP_URL:
        repository = FileAkibaCategoryRepository()
    else:
        repository = FileCategoryRepository()
    cp.execute()
    repository.save(cate=cp.get_results())

    if is_delete_temp_file:
        os.remove(temp_filename)


if __name__ == "__main__":
    main(sys.argv)
