import json
import sys
import argparse
import os

from common import read_config


def set_argparse(argv):
    parser = argparse.ArgumentParser(description="対象のファイルのログを表示")
    parser.add_argument(
        "-f",
        "--filename",
        type=str,
        help="対象のファイル名：例. application.log",
    )
    parser.add_argument(
        "--search",
        nargs="*",
        help="対象のkeyのvalueを探す。keyとvalueのペアを 'key1:value1' 'key2:value2' の形式で指定",
    )
    return parser.parse_args(argv)


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


def is_match_dict(target_dict: dict, search_pair: dict) -> bool:
    if not search_pair:
        return True
    for search_key, search_val in search_pair.items():
        value = target_dict.get(search_key)
        if not value:
            return False
        if search_val != value:
            return False
    return True


def convert_dict_to_line(dict_list: list[dict], search_pair: dict) -> list[LineLog]:
    results = []
    for d in dict_list:
        if is_match_dict(target_dict=d, search_pair=search_pair):
            results.append(LineLog(**d))
    return results


def main(argv):
    argp = set_argparse(argv[1:])
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
    with open(file_path, "r") as fs:
        text = [json.loads(f) for f in fs]
    if isinstance(text, list):
        results = convert_dict_to_line(dict_list=text, search_pair=search_pair)
    elif isinstance(text, dict):
        results = convert_dict_to_line(dict_list=[text], search_pair=search_pair)

    print("\n".join([str(r) for r in results]))


if __name__ == "__main__":
    main(sys.argv)
