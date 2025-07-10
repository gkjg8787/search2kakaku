from selenium import webdriver
from selenium.webdriver.common.by import By

import sys

output_fname = "output_file.html"


def main(argv):
    if len(argv) == 2:
        url = argv[1]
    else:
        raise ValueError("not url")

    browser = webdriver.Remote(
        command_executor="http://selenium:4444/wd/hub",
        options=webdriver.ChromeOptions(),
    )
    browser.get(url)
    try:
        html = browser.page_source
    finally:
        browser.quit()

    with open(output_fname, "w") as f:
        f.write(html)


if __name__ == "__main__":
    main(sys.argv)
