#!/usr/bin/env python3

from __future__ import annotations

import sys
import argparse

from .pprint import pprint, verbosity
from .git import NonzeroResponse, apply_rebase, exc, get_current_head, get_target, relabel

def parse_args():
    """
    CLI Args
    """
    parser = argparse.ArgumentParser(description = "A tool to help you rebase a chain of branches in sequence")
    parser.add_argument(
        "target",
        type = str,
        help = "The target commit to rebase onto"
    )
    parser.add_argument(
        "-@",
        "--head",
        type = str,
        default = "@",
        help = "The top commit to rebase from"
    )
    parser.add_argument(
        "-d",
        "--dry",
        action = "store_true",
        default = False,
        help = "Don't change any refs, local or remote"
    )
    parser.add_argument(
        "-p",
        "--push",
        type = str,
        default = None,
        help = "Update <origin> refs on the remote"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action = "count",
        default = 1,
        help = "Print more"
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action = "store_true",
        default = False,
        help = "Print less",
    )
    parser.add_argument(
        "-f",
        "--force",
        action = "store_true",
        default = False,
        help = "Use with [--push <origin>] to update all local refs on the remote, even those that don't exist in the current chain."
    )

    return parser.parse_args()

def main():
    args = parse_args()

    if args.verbose > 1 and args.quiet:
        pprint("Cannot be both quiet and verbose")
        sys.exit(1)

    verbosity["value"] = 0 if args.quiet else args.verbose

    current_head = get_current_head()

    try:
        rebase_chain, rebase_ancestor, target_commit = get_target(args.head, args.target)
        new_commit = apply_rebase(rebase_chain, rebase_ancestor, target_commit)
        if new_commit is None:
            return

        relabel(
            rebase_chain,
            target_commit,
            new_commit,
            push = args.push,
            dry = args.dry,
            force = args.force,
        )
    except NonzeroResponse as e:
        sys.stderr.write(f"Error executing command: {e.command} ({e.code})\n")
        sys.stderr.write(e.stderr)

    exc("checkout", current_head)

if __name__ == "__main__":
    main()