# `git rebase-chain`

A tool to make gerrit-like PR chains easier to manage

## Usage

Let's say that we have 4 commits, `a`, `b`, `c`, and `d`. All of these correspond to different pull requests on GitHub that are under review.

Your colleague Alice lets you know that `b` has a typo in `supercalifragilisticexpialidocious.js`. Better update it! We switch to `b`, fix the typo, then run `git commit --amend`.

But wait! Now `c` and `d` are tracking the wrong commit. Worse, when we look at the PRs in GitHub they show weird and unexpected changes!

Fortunately, we can fix this easily with `git rebase-chain`. Just run

```shell
> git checkout d
> git rebase-chain b --push origin
Updating remote d to bd941f056dec5e7b0dd277c1786429f668611c28
Updating d to bd941f056dec5e7b0dd277c1786429f668611c28
Updating remote c to f6b59999b9dff86df0b6e7e0d9096946bd47c77a
Updating c to f6b59999b9dff86df0b6e7e0d9096946bd47c77a
```

Now all of our refs, both local and remote are up to date!

## Installation & Usage

To install

```bash
python3 -m pip install git-rebase-chain
```

To use

```bash
git rebase-chain [-@ <head>] [--dry] [--push <remote>] [-vvv] [--quiet] [--force] <target>
```

## Credits

Maintained by Zach Wade <zwad3>

Contributions always welcome!