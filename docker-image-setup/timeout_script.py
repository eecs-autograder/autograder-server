#! /usr/bin/env python3

import sys
import subprocess
import argparse


def main():
    args = parse_args()
    # print(args.cmd_args)

    try:
        return_code = subprocess.call(args.cmd_args, timeout=args.time_limit)
        sys.exit(return_code)
    except subprocess.TimeoutExpired:
        print('Time limit exceeded')
        sys.exit(124)  # Return code currently expected by sandbox on timeout


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("time_limit", type=int)
    parser.add_argument("cmd_args", nargs=argparse.REMAINDER)

    return parser.parse_args()

if __name__ == '__main__':
    main()
