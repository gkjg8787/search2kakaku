import json
import sys
from pprint import pprint

OUTPUT_PARSE_FNAME = "parse.json"


def main(argv):
    if len(argv) == 2:
        fname = argv[1]
    else:
        fname = OUTPUT_PARSE_FNAME
        print(f"input default fname = {OUTPUT_PARSE_FNAME}")
    with open(fname, "r") as f:
        parse_file = f.read()
    j = json.loads(parse_file)
    pprint(j)


if __name__ == "__main__":
    main(sys.argv)
