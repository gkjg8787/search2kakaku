import json
import sys
import argparse
import os
from collections import deque

from common import read_config


def set_argparse():
    parser = argparse.ArgumentParser(description="対象のファイルのログを表示")
    parser.add_argument(
        "-f",
        "--filename",
        type=str,
        help="対象のファイル名：例. application.log",
    )
    search_type_group = parser.add_mutually_exclusive_group(required=False)
    search_type_group.add_argument(
        "--key",
        nargs="*",
        help="対象のkeyが含まれているもののみを表示対象にする。'key1' 'key2'。複数指定の場合はOR条件とみなす。",
    )
    search_type_group.add_argument(
        "--search",
        nargs="*",
        help="対象のkeyのvalueを表示対象にする。keyとvalueのペアを 'key1:value1' 'key2:value2' の形式で指定。複数指定の場合はAND条件とみなす。",
    )
    read_type_group = parser.add_mutually_exclusive_group(required=False)
    read_type_group.add_argument(
        "--head", type=int, help="先頭から指定行まで読み込む。"
    )
    read_type_group.add_argument(
        "--tail", type=int, help="末尾から指定行の数だけ読み込む。"
    )
    return parser.parse_args()


class LineLog:
    timestamp: str
    event: str
    run_id: str
    logger: str
    level: str
    process_type: str
    other_dict: dict

    def __init__(
        self,
        event: str,
        timestamp: str = "",
        logger: str = "",
        level: str = "",
        run_id: str = "",
        process_type: str = "",
        **kwargs,
    ):
        self.timestamp = timestamp
        self.event = event
        self.logger = logger
        self.level = level
        self.run_id = run_id
        self.process_type = process_type
        self.other_dict = kwargs

    def __repr__(self) -> str:
        key_value = {
            "process_type": self.process_type,
            "run_id": self.run_id,
            "logger": self.logger,
        }
        if self.other_dict:
            key_value |= self.other_dict
        key_value_text = ", ".join([f"{k}={v}" for k, v in key_value.items()])
        return f"{self.timestamp} : [{self.level}] {self.event} | {key_value_text}"


def is_match_dict(target_dict: dict, search_pair: dict, key_list: list[str]) -> bool:
    if not search_pair and not key_list:
        return True

    if key_list:
        for k in key_list:
            if k in target_dict.keys():
                return True
        return False

    for search_key, search_val in search_pair.items():
        value = target_dict.get(search_key)
        if not value:
            return False
        if search_val != value:
            return False
    return True


def convert_dict_to_line(
    dict_list: list[dict], search_pair: dict, key_list: list[str]
) -> list[LineLog]:
    results = []
    for d in dict_list:
        if is_match_dict(target_dict=d, search_pair=search_pair, key_list=key_list):
            results.append(LineLog(**d))
    return results


def read_file(
    file_path: str, head_n: int | None = None, tail_n: int | None = None
) -> list[dict[str, str]]:
    if not head_n and not tail_n:
        with open(file_path, "r") as fs:
            text = [json.loads(f) for f in fs]
        return text
    if head_n:
        text = []
        with open(file_path, "r") as fs:
            for i, f in enumerate(fs, start=1):
                if i > head_n:
                    break
                text.append(json.loads(f))
        return text
    if tail_n:
        with open(file_path, "r") as fs:
            last_n_lines = deque(fs, maxlen=tail_n)
        return [json.loads(l) for l in last_n_lines]
    return []


def main():
    argp = set_argparse()
    if not argp.filename:
        filename = "application.log"
    else:
        filename = argp.filename

    search_pair = {}
    if argp.search:
        for kv in argp.search:
            kvs = str(kv).split(":")
            if len(kvs) != 2:
                print(f"length error, len={len(kvs)}, val={kv}")
                continue
            if not kvs[0] or not kvs[1]:
                print(f"key or value is None, key:{kvs[0]}, val:{kvs[1]}")
                continue
            search_pair[kvs[0]] = kvs[1]

    logoptions = read_config.get_log_options()
    file_path = os.path.join(logoptions.directory_path, filename)
    text = read_file(file_path=file_path, head_n=argp.head, tail_n=argp.tail)
    if isinstance(text, list):
        results = convert_dict_to_line(
            dict_list=text, search_pair=search_pair, key_list=argp.key
        )
    elif isinstance(text, dict):
        results = convert_dict_to_line(
            dict_list=[text], search_pair=search_pair, key_list=argp.key
        )

    print("\n".join([str(r) for r in results]))


if __name__ == "__main__":
    main()
