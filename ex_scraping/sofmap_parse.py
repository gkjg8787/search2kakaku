import json
import sys
from sofmap.parser import SofmapParser

OUTPUT_PARSE_FNAME = "parse.json"
OUTPUT_FNAME = "output_file.html"
URL = "https://www.sofmap.com"


def main(argv):
    if len(argv) == 2:
        fname = argv[1]
    else:
        fname = OUTPUT_FNAME
        print(f"input default fname={OUTPUT_FNAME}")

    url = URL
    with open(fname, "r") as f:
        html = f.read()

    parser = SofmapParser(html)
    parser.execute(url=url)
    with open(OUTPUT_PARSE_FNAME, "w") as f:
        f.write(json.dumps(parser.get_results().model_dump_json(), ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv)
