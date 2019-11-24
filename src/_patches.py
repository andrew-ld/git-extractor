import stat
import dulwich.diff_tree
import dulwich.objects
import dulwich.walk
import dulwich.errors


# noinspection PyProtectedMember
def patch_all():

    # noinspection PyProtectedMember
    def walk_trees_patched(store, tree1_id, tree2_id, prune_identical=False):
        mode1 = tree1_id and stat.S_IFDIR or None
        mode2 = tree2_id and stat.S_IFDIR or None

        todo = [
            (dulwich.objects.TreeEntry(b'', mode1, tree1_id),
             dulwich.objects.TreeEntry(b'', mode2, tree2_id))
        ]

        while todo:
            entry1, entry2 = todo.pop()
            is_tree1 = dulwich.diff_tree._is_tree(entry1)
            is_tree2 = dulwich.diff_tree._is_tree(entry2)
            if prune_identical and is_tree1 and is_tree2 and entry1 == entry2:
                continue

            try:
                tree1 = is_tree1 and store[entry1.sha] or None
                tree2 = is_tree2 and store[entry2.sha] or None
            except KeyError as error:
                print("skipped tree", error.args[0])
                tree1 = None
                tree2 = None

            path = entry1.path or entry2.path
            todo.extend(reversed(dulwich.diff_tree._merge_entries(path, tree1, tree2)))
            yield entry1, entry2

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
