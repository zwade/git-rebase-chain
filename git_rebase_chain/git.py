from __future__ import annotations
from subprocess import PIPE, Popen
import sys
from typing import Literal, TypedDict, overload

from .pprint import verbosity, pprint, A


class NonzeroResponse(Exception):
    """
    An error to be thrown when a command returns a non-zero exit code.
    """
    def __init__(self, code: int, stdout: str, stderr: str, command: str):
        super().__init__(stderr)
        self.code = code
        self.stdout = stdout
        self.stderr = stderr
        self.command = command

class Ref(TypedDict):
    """
    A git ref
    """
    name: str
    path: str
    remote: str | None

class Commit(TypedDict):
    """
    A git commit
    """
    hash: str
    refs: list[Ref]
    title: str


@overload
def exc(cmd: str, *args: str, dry: Literal[False] = False) -> str: ...
@overload
def exc(cmd: str, *args: str, dry: bool) -> str | None: ...
def exc(cmd: str, *args: str, dry: bool = False) -> str | None:
    """
    Executes a git command and returns the result
    """
    command_str = f"git {cmd} {' '.join(args)}"
    side_len = max(3, (100 - 2 - len(command_str)) // 2)

    if dry or verbosity["value"] >= 2:
        color = A.gray if dry else A.yellow
        pprint(f"\n{'-' * side_len} {command_str} {'-' * side_len}", color = color)

    if dry:
        pprint("")
        return None

    proc = Popen(["git", cmd, *args], stdout = PIPE, stderr = PIPE)
    result = proc.wait()

    assert proc.stdout and proc.stderr

    stdout_str = proc.stdout.read().decode("utf-8")
    stderr_str = proc.stderr.read().decode("utf-8")

    if verbosity["value"] >= 3:
        pprint(f"-> result: {A.blue}{result}{A.clear}")

        if stdout_str != "":
            pprint("-> stdout:")
            pprint(stdout_str, color = A.blue)

        if stderr_str != "":
            pprint("-> stderr:")
            pprint(stderr_str, color = A.red)

        pprint("-" * (side_len * 2 + 2 + len(command_str)), color = A.yellow)

    if verbosity["value"] >= 2:
        pprint("")

    if result != 0:
        raise NonzeroResponse(result, stdout_str, stderr_str, command_str)

    return stdout_str.strip()

def parse_ref(ref: str, remotes: list[str]) -> Ref | None:
    """
    Parses a git ref from a variety of sources, and returns a Ref object
    """
    ref = ref.strip()
    if "->" in ref:
        ref = ref.split("->")[1].strip()

    if ref.startswith("refs/heads/"):
        ref = ref[11:]
    else:
        for remote in remotes:
            if ref.startswith(f"{remote}/"):
                return {
                    "name": ref[len(remote) + 1:],
                    "path": ref,
                    "remote": remote,
                }

    name = ref
    path = f"refs/heads/{ref}"

    if name == "HEAD":
        return None

    return {
        "name": name,
        "path": path,
        "remote": None,
    }

def get_current_head():
    """
    Finds and returns the current HEAD value
    """
    git_dir = exc("rev-parse", "--absolute-git-dir")
    with open(f"{git_dir}/HEAD", "r") as head_file:
        head = head_file.read()

    if head.startswith("ref: "):
        head = head[5:]
        ref = parse_ref(head, [])

        if ref:
            return ref["name"]

    return head


def parse_log_line(line: str, remotes: list[str]) -> Commit:
    """
    Parses a single line from the git log as formatted by
    `--format=format:%H|%d|%f`
    """
    hash, refs, title = line.strip().split("|")
    commit = Commit(hash = hash, refs = [], title = title)

    if refs != "":
        refs = refs.strip()
        if refs[0] != "(" or refs[-1] != ")":
            return commit

        individual_refs = [
            parse_ref(ref, remotes)
            for ref in refs[1:-1].split(", ")
        ]

        commit["refs"] = [
            ref
            for ref in individual_refs
            if ref is not None
        ]

    return commit

def get_log(head: str, base: str):
    """
    Gets the git log from base..head, and parses it
    """
    log = exc("log", f"{base}..{head}", "--format=format:%H|%d|%f")
    remotes = exc("remote", "show").split("\n")

    lines = [
        parse_log_line(line, remotes)
        for line in log.split("\n")
        if line.strip() != ""
    ]

    return lines

def get_target(head_name: str, target_name: str):
    """
    Computes the merge base of the head and the target,
    then attempts to identify the old version of the target
    in the original chain. Returns each of these three things as
    a tuple
    `(rebase_chain, rebase_ancestor, target_commit)`
    """

    head = exc("rev-parse", "--verify", head_name)
    target = exc("rev-parse", "--verify", target_name)
    merge_base = exc("merge-base", head, target)

    if merge_base == target:
        pprint("Head is already based on target. Nothing to be done!", color = A.blue)
        sys.exit(0)

    primary_chain = get_log(head, merge_base)

    try:
        target_commit = get_log(target, f"{target}~1")[0]
    except IndexError:
        pprint("Could not find the target commit in the log. Are you sure it's correct?", color = A.red)
        sys.exit(1)

    rebase_chain: list[Commit] = []
    rebase_ancestor: Commit | None = None
    for elt in primary_chain:
        if elt["title"] == target_commit["title"]:
            rebase_ancestor = elt
            break

        rebase_chain.append(elt)

    if rebase_ancestor is None:
        pprint(f"Unable to identify the predecessor of {target_name} in the current chain. Please specify it explicitly and try again", color = A.red)
        sys.exit(1)

    return (
        rebase_chain,
        rebase_ancestor,
        target_commit,
    )

def apply_rebase(
    rebase_chain: list[Commit],
    rebase_ancestor: Commit,
    target_commit: Commit,
):
    """
    Performs the rebase step
    """
    if len(rebase_chain) == 0:
        return

    try:
        exc("rebase", "--onto", target_commit["hash"], rebase_ancestor["hash"], rebase_chain[0]["hash"])
    except NonzeroResponse as NZR:
        if NZR.code == 1:
            pprint("Unable to complete rebase! Please manually complete the rebase.", color = A.yellow)
            pprint(exc("status"), color = A.red)
            pprint(f"When you're done, run {A.green}git rebase --continue{A.clear}, then type {A.green}[c/continue]{A.clear} to continue.")
            pprint(f"You can safely {A.yellow}background{A.clear} this process")

            while True:
                sys.stdout.write(f"[{A.green}c/continue{A.clear}] > ")
                if input().strip().lower() in ["c", "continue"]:
                    break

                pprint(f"Please type {A.green}[c/continue]{A.clear} to continue")


    return get_log("@", "@~1")[0]

def update_remote(
    remote: str,
    ref: Ref,
    target_commit: Commit,
    dry: bool = True
):
    """
    Updates a ref on the remote
    """
    pprint(f"Updating remote {A.red}{ref['name']}{A.clear} to {A.yellow}{target_commit['hash']}{A.clear}")
    exc(
        "push", "-f", remote, f"{target_commit['hash']}:{ref['name']}",
        dry = dry
    )

def update_local(
    ref: Ref,
    target_commit: Commit,
    dry: bool = True
):
    """
    Updates a ref locally
    """
    pprint(f"Updating {A.green}{ref['name']}{A.clear} to {A.yellow}{target_commit['hash']}{A.clear}")
    exc(
        "update-ref", ref["path"], target_commit["hash"],
        dry = dry
    )

def relabel(
    original_rebase_chain: list[Commit],
    target_commit: Commit,
    new_commit: Commit,
    push: str | None = None,
    dry: bool = True,
    force: bool = False,
):
    """
    Relabels all refs in the newly rebased chain, optionally pushing to origin
    if [push] is specified
    """
    new_rebase_chain = get_log(new_commit["hash"], target_commit["hash"])

    if len(new_rebase_chain) != len(original_rebase_chain):
        pprint("Something went wrong during rebase. Returning to the original state")
        exc("checkout", original_rebase_chain[0]["hash"])
        sys.exit(1)

    for original, new in zip(original_rebase_chain, new_rebase_chain):
        pushed_to_remote = False

        for ref in original["refs"]:
            if push is not None and push == ref["remote"]:
                update_remote(push, ref, new, dry)
                pushed_to_remote = True

        for ref in original["refs"]:
            if ref["remote"] is None:
                if push is not None and force and not pushed_to_remote:
                    update_remote(push, ref, new, dry)

                update_local(ref, new, dry)

