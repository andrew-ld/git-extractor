import sys
import dulwich.repo
import dulwich.walk
import dulwich.objects
import dulwich.diff_tree
import dulwich.index
import os
import os.path
import functools
import _patches


class Extractor:
    _repo: dulwich.repo.Repo

    __slots__ = [
        "_repo"
    ]

    def __init__(self, path: str):
        self._repo = dulwich.repo.Repo(path)

    def _extract_file(self, dest: str, sha: bytes):
        obj: dulwich.objects.Blob

        try:
            obj = self._repo.get_object(sha)
        except KeyError:
            return

        os.makedirs(os.path.dirname(dest), exist_ok=True)

        with open(dest, "wb") as file:
            file.write(obj.data)

    def _extract_tree(self, output: str, change: dulwich.diff_tree.TreeChange):
        if change.type != "delete":
            dest = output + change.new.path.decode("utf8")
            self._extract_file(dest, change.new.sha)

    def extract(self, output: str):
        index: dulwich.index.Index
        index = self._repo.open_index()

        for name, entry in index.items():
            entry: dulwich.index.IndexEntry

            dest = f"{output}/0-base/{name.decode('utf8')}"
            self._extract_file(dest, entry.sha)

        for uid, entry in enumerate(self._repo.get_walker(), 1):
            entry: dulwich.walk.WalkEntry

            current = f"{output}/{uid}-{entry.commit.id.decode('utf8')}/"
            os.makedirs(current, exist_ok=True)

            func = functools.partial(self._extract_tree, current)

            for changes in entry.changes():
                if isinstance(changes, list):
                    any(map(func, changes))

                else:
                    func(changes)


if __name__ == "__main__":
    _patches.patch_all()
    ex = Extractor(sys.argv[1])
    ex.extract(sys.argv[2])
