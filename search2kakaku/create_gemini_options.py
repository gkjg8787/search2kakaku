import argparse
import json

from app.gemini import models as gemini_models


def _set_argparse():
    parser = argparse.ArgumentParser(
        description="GEMINI APIを使ったスクレイピングのオプションを設定します。",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="gemini_options.json",
        help="出力するJSONファイルのパスを指定します。デフォルトは 'gemini_options.json' です。",
    )
    parser.add_argument(
        "--view",
        action="store_true",
        help="作成したオプションを表示します。",
    )
    return parser.parse_args()


def _create_seleinum_options():
    wait_css_selector = input("CSS Selector (default ''): ").strip()
    page_load_timeout = input("Page Load Timeout (seconds, default 30): ").strip()
    tag_wait_timeout = input("Tag Wait Timeout (seconds, default 10): ").strip()
    page_wait_time = input("Page Wait Time (seconds, default 0): ").strip()
    return gemini_models.GeminiWaitOptions(
        wait_css_selector=wait_css_selector,
        page_load_timeout=(
            int(page_load_timeout) if page_load_timeout.isdigit() else None
        ),
        tag_wait_timeout=(
            int(tag_wait_timeout) if tag_wait_timeout.isdigit() else None
        ),
        page_wait_time=(
            float(page_wait_time)
            if page_wait_time.replace(".", "", 1).isdigit()
            else None
        ),
    )


def _create_nodriver_options():
    cookie = input("Use Cookie (y/n, default n): ").strip().lower() == "y"
    if cookie:
        cookie_list_str = input(
            'Cookie Dict List (JSON format, e.g. [{"name": "key", "value": "value"}]): '
        ).strip()
        try:
            cookie_dict_list = json.loads(cookie_list_str)
            if not isinstance(cookie_dict_list, list):
                raise ValueError("Not a list")
        except Exception as e:
            print(f"Invalid JSON format for Cookie Dict List: {e}")
            cookie_dict_list = None
        return_cookies = (
            input("Return Cookies (y/n, default n): ").strip().lower() == "y"
        )
        cookie_model = gemini_models.Cookie(
            cookie_dict_list=cookie_dict_list, return_cookies=return_cookies
        )
    wait_css_selector = (
        input("Use Wait CSS Selector (y/n, default n): ").strip().lower() == "y"
    )
    if wait_css_selector:
        selector = input("CSS Selector: ").strip()
        timeout = input("Timeout (seconds): ").strip()
        on_error_action_type = (
            input("On Error Action Type (raise/retry, default raise): ").strip().lower()
        )
        on_error_max_retries = input("On Error Max Retries : ").strip()
        on_error_wait_time = input("On Error Wait Time (seconds): ").strip()
        on_error_check_exist_tag = input(
            "On Error Check Exist Tag (CSS selector, default ''): "
        ).strip()
        on_error_model = gemini_models.OnError(
            action_type=(
                on_error_action_type
                if on_error_action_type in ["raise", "retry"]
                else "raise"
            ),
            max_retries=(
                int(on_error_max_retries) if on_error_max_retries.isdigit() else None
            ),
            wait_time=(
                float(on_error_wait_time)
                if on_error_wait_time.replace(".", "", 1).isdigit()
                else None
            ),
            check_exist_tag=on_error_check_exist_tag,
        )
        wait_css_selector_model = gemini_models.WaitCSSSelector(
            selector=selector,
            timeout=int(timeout) if timeout.isdigit() else 10,
            on_error=on_error_model,
            pre_wait_time=0.0,
        )
    page_wait_time = input("Page Wait Time (seconds): ").strip()
    return gemini_models.NodriverOptions(
        cookie=cookie_model if cookie else None,
        wait_css_selector=wait_css_selector_model if wait_css_selector else None,
        page_wait_time=(
            float(page_wait_time)
            if page_wait_time.replace(".", "", 1).isdigit()
            else None
        ),
    )


def _create_gemini_options():
    print("GEMINI API Options Creator")
    sitename = input("Sitename: ").strip()
    label = input("Label: ").strip()
    recreate_parser = input("Recreate Parser (y/n, default n): ").strip().lower() == "y"
    exclude_script = (
        not input("Exclude Script (y/n, default y): ").strip().lower() == "n"
    )
    compress_whitespace = (
        input("Compress Whitespace (y/n, default n): ").strip().lower() == "y"
    )
    download_type = (
        input("Download Type (httpx/selenium/nodriver, default httpx): ")
        .strip()
        .lower()
    )
    selenium = None
    nodriver = None
    if download_type == "selenium":
        selenium = _create_seleinum_options()
    elif download_type == "nodriver":
        nodriver = _create_nodriver_options()

    options_model = gemini_models.AskGeminiOptions(
        sitename=sitename,
        label=label,
        recreate_parser=recreate_parser,
        exclude_script=exclude_script,
        compress_whitespace=compress_whitespace,
        selenium=selenium,
        nodriver=nodriver,
    )
    return options_model.model_dump(mode="json", exclude_none=True)


def main():
    argp = _set_argparse()
    options = _create_gemini_options()
    if argp.view:
        print(json.dumps(options, ensure_ascii=False, indent=4))
    with open(argp.output, "w", encoding="utf-8") as f:
        json.dump(options, f, ensure_ascii=False, indent=4)
    print(f"Successfully created GEMINI options and saved to {argp.output}")


if __name__ == "__main__":
    main()
