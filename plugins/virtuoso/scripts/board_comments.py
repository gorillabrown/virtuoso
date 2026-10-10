"""Read and resolve the roadmap board's row comments (roadmap-review B.3).

    board_comments.py --root .                       list the open comments
    board_comments.py --root . --json                the same, as JSON
    board_comments.py --root . --actor roadmap-review --resolve ITEM --answer "..." [--apply]

Resolving marks every open note on the item answered; the page shows it greyed out.
It previews unless --apply is given, and only a writer of the `boardComments` role may
apply it.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.governance import registry as registry_mod, textio  # noqa: E402
from tools.governance.errors import GovernanceError, RoleNotRegistered  # noqa: E402
from tools.roadmap_visualizer import board, comments  # noqa: E402


def main(argv=None) -> int:
    textio.utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".")
    parser.add_argument("--json", dest="as_json", action="store_true")
    parser.add_argument("--resolve", default="", metavar="ITEM")
    parser.add_argument("--answer", default="")
    parser.add_argument("--actor", default="")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        reg = registry_mod.load(str(Path(args.root).resolve()))
        if board.COMMENTS_ROLE not in reg.roles:
            raise RoleNotRegistered("no `boardComments` role is registered: the board has "
                                    "no comments to read (generate_board --create adds it)")
        path = reg.resolve(board.COMMENTS_ROLE)
        found, problems = comments.read_comments(path)
        if not args.resolve:
            notes = comments.open_notes(found)
            if args.as_json:
                print(json.dumps({"open": notes, "problems": problems}, indent=2,
                                 ensure_ascii=False))
            else:
                for note in notes:
                    print("%s  %s  %s" % (note["item"], note["at"], note["text"]))
                print("%d open board comment(s)" % len(notes))
                for problem in problems:
                    print("warning: %s" % problem)
            return 0
        if not args.answer.strip():
            raise GovernanceError("--resolve needs --answer: what the review did about it")
        if not reg.writable(board.COMMENTS_ROLE, args.actor):
            raise GovernanceError("%r may not write the boardComments role (allowedWriters: %s)"
                                  % (args.actor, ", ".join(
                                      reg.roles[board.COMMENTS_ROLE].allowed_writers)))
        if problems:
            # The reader skipped damaged entries; writing back would delete what people wrote.
            raise GovernanceError("the comments file has damaged entries; fix them before "
                                  "resolving anything: %s" % "; ".join(problems))
        count = comments.resolve(found, args.resolve, args.answer.strip())
        if not args.apply:
            print("preview — would mark %d open note(s) on %s resolved (run again with --apply)"
                  % (count, args.resolve))
            return 0
        comments.write_comments(path, found)
        print("resolved %d note(s) on %s" % (count, args.resolve))
        return 0
    except GovernanceError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
