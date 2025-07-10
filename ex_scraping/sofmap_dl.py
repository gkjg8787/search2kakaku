import sys
from urllib.parse import urlparse


from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


OUTPUT_FNAME = "output_file.html"
SOFMAP_DOMAIN = "www.sofmap.com"
tag_timeout = 15


def check_domain(url, target_domain) -> bool:
    parsed_url = urlparse(url)
    # ネットロケーション（netloc）がドメイン名に相当する
    if target_domain in parsed_url.netloc:
        return True
    return False


def main(argv):
    if len(argv) == 2:
        url = argv[1]
    else:
        raise ValueError("not url")

    if not check_domain(url, SOFMAP_DOMAIN):
        raise ValueError(f"url is not sofmap url={url}")
    driver = webdriver.Remote(
        command_executor="http://selenium:4444/wd/hub",
        options=webdriver.ChromeOptions(),
    )
    driver.get(url)
    css_selector = ".product_list.flexcartbtn.ftbtn"
    try:
        target_element = WebDriverWait(driver, tag_timeout).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, css_selector))
        )
        print(f"指定された要素が見つかりました！テキスト: '{target_element.text}'")
        print(
            f"要素のタグ名: {target_element.tag_name}, クラス: {target_element.get_attribute('class')}"
        )

        html = driver.page_source
    except TimeoutException:
        print(
            "指定された要素が時間内に表示されませんでした (Explicit Waitによるタイムアウト)。"
        )
        return
    except Exception as e:
        print(f"その他のエラーが発生しました: {e}")
        return
    finally:
        driver.quit()

    with open(OUTPUT_FNAME, "w") as f:
        f.write(html)


if __name__ == "__main__":
    main(sys.argv)
