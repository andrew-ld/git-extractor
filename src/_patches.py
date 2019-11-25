import dulwich.diff_tree
import dulwich.objects
import dulwich.walk
import dulwich.errors


# noinspection PyProtectedMember
def patch_all():

    walk_trees_real = dulwich.diff_tree.walk_trees

    class Getter:
        def __init__(self, inst):
            self.inst = inst

        def __getitem__(self, item):
            try:
                return self.inst[item]

            except KeyError:
                print("skipped", item)

    def walk_trees_patched(store, *args, **kwargs):
        generator = walk_trees_real(Getter(store), *args, **kwargs)

        while True:
            try:
                yield next(generator)

            except StopIteration:
                break

    dulwich.diff_tree.walk_trees = walk_trees_patched

    # noinspection PyProtectedMember
    class _CommitTimeQueuePatched(dulwich.walk._CommitTimeQueue):
        def _push(self, object_id):
            try:
                return super()._push(object_id)
            except dulwich.errors.MissingCommitError:
                return None

    _CommitTimeQueueReal = dulwich.walk._CommitTimeQueue
    dulwich.walk._CommitTimeQueue = _CommitTimeQueuePatched

    class WalkerPatched(dulwich.walk.Walker):
        def __init__(self, *args, queue_cls=None, **kwargs):
            if queue_cls in (_CommitTimeQueueReal, None):
                queue_cls = _CommitTimeQueuePatched

            super().__init__(*args, queue_cls=queue_cls, **kwargs)

    dulwich.walk.Walker = WalkerPatched

    class WalkEntryPatched(dulwich.walk.WalkEntry):
        def changes(self, path_prefix=None):
            try:
                return super().changes(path_prefix=path_prefix)
            except KeyError:
                pass

            self._changes[path_prefix] = list(
                dulwich.diff_tree.tree_changes(
                    self._store, None, self.commit.tree,
                    rename_detector=self._rename_detector
                )
            )

            return self._changes[path_prefix]

    dulwich.walk.WalkEntry = WalkEntryPatched
