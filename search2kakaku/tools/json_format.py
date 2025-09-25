import json
import argparse
import sys

def format_json(data, pretty=False, compact=False):
    if pretty:
        return json.dumps(data, indent=4, ensure_ascii=False)
    if compact:
        return json.dumps(data, separators=(',', ':'), ensure_ascii=False)
    return json.dumps(data, ensure_ascii=False)

def main():
    parser = argparse.ArgumentParser(description='Format a JSON file.')
    parser.add_argument('-i', '--input', required=True, help='Input file name.')
    parser.add_argument('-o', '--output', help='Output file name (overwrite).')
    parser.add_argument('-v', '--view', action='store_true', help='View the formatted JSON.')
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-p', '--pretty', action='store_true', help='Pretty print the JSON.')
    group.add_argument('-c', '--compact', action='store_true', help='Compact the JSON to one line.')

    args = parser.parse_args()

    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in file: {args.input}", file=sys.stderr)
        sys.exit(1)

    formatted_json = format_json(data, pretty=args.pretty, compact=args.compact)

    if args.view:
        print(formatted_json)

    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(formatted_json)
            print(f"Successfully formatted and saved to {args.output}")
        except IOError as e:
            print(f"Error writing to output file {args.output}: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == '__main__':
    main()