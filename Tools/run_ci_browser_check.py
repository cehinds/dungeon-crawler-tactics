"""Run one browser check and expose a bounded failure through Actions annotations."""
import argparse
from collections import deque
import html
import os
from pathlib import Path
import shlex
import subprocess


def run(name, command):
    if not command:
        raise ValueError('A browser check command is required')
    tail = deque(maxlen=80)
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, errors='replace')
    with process.stdout as stream:
        for line in stream:
            print(line, end='', flush=True)
            tail.append(line)
    result = process.wait()
    if result:
        detail = (''.join(tail) or f'Command exited with code {result} without output.')[-6000:]
        escape = lambda value: value.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
        print(f'::error title={escape(name)}::{escape(detail)}', flush=True)
        summary = os.environ.get('GITHUB_STEP_SUMMARY')
        if summary:
            with Path(summary).open('a') as stream:
                stream.write(f'<h2>Browser check failed: {html.escape(name)}</h2>\n')
                stream.write(f'<p>{html.escape(shlex.join(command))}</p>\n<pre>{html.escape(detail)}</pre>\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('A browser check command is required after --')
    raise SystemExit(run(args.name, command))


if __name__ == '__main__':
    main()
