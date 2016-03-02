#! /usr/bin/env python3

import sys
import subprocess
import argparse
import resource


def main():
    args = parse_args()
    # print(args.cmd_args)

    def set_subprocess_rlimits():
        try:
            resource.setrlimit(resource.RLIMIT_NPROC,
                               (args.max_num_processes, args.max_num_processes))
            resource.setrlimit(resource.RLIMIT_STACK,
                               (args.max_stack_size, args.max_stack_size))
            try:
                resource.setrlimit(
                    resource.RLIMIT_VMEM,
                    (args.max_virtual_memory, args.max_virtual_memory))
            except Exception:
                resource.setrlimit(
                    resource.RLIMIT_AS,
                    (args.max_virtual_memory, args.max_virtual_memory))

        except Exception:
            import traceback
            traceback.print_exc()

    try:
        return_code = subprocess.call(args.cmd_args, timeout=args.time_limit,
                                      preexec_fn=set_subprocess_rlimits)
        sys.exit(return_code)
    except subprocess.TimeoutExpired:
        print('Time limit exceeded')
        sys.exit(124)  # Return code currently expected by sandbox on timeout


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("time_limit", type=int)
    parser.add_argument("max_num_processes", type=int)
    parser.add_argument("max_stack_size", type=int)
    parser.add_argument("max_virtual_memory", type=int)
    parser.add_argument("cmd_args", nargs=argparse.REMAINDER)

    return parser.parse_args()


if __name__ == '__main__':
    main()
