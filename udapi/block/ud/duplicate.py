"""ud.Duplicate block template."""

import sys
from collections import Counter
from udapi.core.block import Block
from copy import deepcopy

class Duplicate(Block):
    """Duplicates sentences with more than one Mark=Mark.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cop = {'is', 'are', 'was', 'were'}

    def process_document(self, document):
        for bundle in document.bundles:
            for tree in bundle:
                if self._should_process_tree(tree):
                    if len([n for n in tree.descendants if 'Mark' in n.misc]) > 1:
                        if not all(n.upos == 'VERB' and 'Mark' in n.misc and n.form not in self.cop for n in tree.descendants):
                            list_of_mark = [n for n in tree.descendants if 'Mark' in n.misc]
                            for i, marked_token in enumerate(list_of_mark[1:]):
                                new_tree = deepcopy(tree)
                                new_tree.sent_id = new_tree.sent_id + '-copy' + str(i + 1)
                                for new_token in new_tree.descendants:
                                    if 'Mark' in new_token.misc and new_token.ord != marked_token.ord:
                                        del new_token.misc['Mark']
                                new_bundle = document.create_bundle()
                                new_bundle.add_tree(new_tree)
                            for token in tree.descendants:
                                if 'Mark' in token.misc and token.ord != list_of_mark[0].ord:
                                    del token.misc['Mark']
