"""ud.FinalizeOrphans block template."""

import sys
from collections import Counter
from udapi.core.block import Block

class FinalizeOrphans(Block):
    """Converts full sentences into artificial: final conllu
       Usage: cat file-to-convert.conllu | udapy -s ud.FinalizeOrphans
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def process_tree(self, tree):
        for node in tree.descendants:
            if 'Mark' in node.misc:
                if all(token.misc['Processed'] != 'deleteSentence' for token in node.root.descendants):
                    shit_happens = False
                    for token in node.root.descendants:
                        if 'newNode' in token.misc and token.misc['newNode'] != 'deleteThis':
                            try:
                                position, relation = token.misc['newNode'].split(':')
                                token.deprel = relation
                                token.parent = node.root.descendants[int(position)-1]
                            except ValueError:
                                shit_happens = True

                    if shit_happens:
                        for token in node.root.descendants:
                            if 'newNode' in token.misc and token.misc['newNode'] != 'deleteThis':
                                position, relation = token.misc['newNode'].split(':')
                                token.deprel = relation
                                token.parent = node.root.descendants[int(position)-1]
                else:
                    tree.remove()

        for node in tree.descendants:
            if 'newNode' in node.misc and node.misc['newNode'] == 'deleteThis':
                node.remove()
        for node in tree.descendants:
            if 'newNode' in node.misc:
                del node.misc['newNode']
            if 'Processed' in node.misc:
                del node.misc['Processed']
