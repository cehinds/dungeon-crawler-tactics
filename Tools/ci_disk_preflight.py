"""Fail before large CI copies when a disposable runner lacks space."""
import argparse
import json
from pathlib import Path
import shutil

GIB = 1024 ** 3


def check(directory, required_bytes):
    free = shutil.disk_usage(directory).free
    result = {'free_bytes': free, 'required_free_bytes': required_bytes,
              'passed': free >= required_bytes}
    if not result['passed']:
        raise ValueError(json.dumps(result) + ': insufficient disk space; no validation was skipped')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=Path('.'))
    parser.add_argument('--required-free-gib', type=int, default=45)
    parser.add_argument('--publish-assets', type=Path,
                        help='Budget two additional art copies (build and publish), plus 4 GiB overhead')
    args = parser.parse_args()
    required = args.required_free_gib * GIB
    if args.publish_assets:
        size = sum(p.stat().st_size for p in args.publish_assets.rglob('*') if p.is_file())
        required = 2 * size + 4 * GIB
    print(json.dumps(check(args.directory, required), sort_keys=True))


if __name__ == '__main__':
    main()
