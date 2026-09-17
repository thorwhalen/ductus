"""``python -m ductus`` -- the CLI, built from the same functions the library exposes.

ductus gauge draft.md                      # a markdown diagnosis on stdout
ductus gauge draft.md --format html --out report.html
ductus gauge - --format json < draft.md    # from stdin, machine-readable
ductus tells --tier E                      # what the catalogue enforces
ductus install-skills --write              # link the skills into ~/.claude
"""

import cw

from ductus.tools import _dispatch_funcs


def main() -> int:
    return cw.dispatch(_dispatch_funcs)


if __name__ == "__main__":
    raise SystemExit(main())
