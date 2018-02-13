"""ud.ConvertOrphans block template."""

import sys
from collections import Counter
from udapi.core.block import Block

class ConvertOrphans(Block):
    """Converts full sentences into artificial.
        Usage: cat file-to-convert.conllu | udapy -s ud.ConvertOrphans
        Notes:
        If a sentence is processed, this information is added to the misc column:
            'Processed=Yes'marker is added to the node that will be deleted
             new heads and labels are added to nodes that should be rehung ('newNode=new-head:relation')
             'newNode=deleteThis' marker is added to all nodes that will be deleted
        Check processed sentences: file-to-convert.conllu | udapy -s util.Filter keep_tree_if_node="node.misc['Processed'] == 'Yes'" mark="Mark" | udapy write.TextModeTrees
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.subst = {'he': 'she', 'she': 'he', 'i':'you', 'you': 'they', 'they': 'you', 'we': 'you'}
        self.core_ellipsis = {'aux', 'cop', 'compound'}
        self.none_core_ellipsis = {'nsubj', 'iobj', 'obj', 'aux', 'compound', 'mark', 'cop'}
        self.cop_form = {'was', 'were', 'is', 'are', "'m", 'am'}

    def process_node(self, node):
        if 'Mark' in node.misc:
            children_to_delete = []
            children_to_process = []

            # VERB depends on VERB
            if node.upos == 'VERB' and node.parent.upos == 'VERB' and \
               node.parent.form not in self.cop_form and node.form not in self.cop_form:

                #filter out non-matching subtrees
                matching_rels = [{'obj'}, {'iobj'}, {'obl', 'advmod'}]
                matches = []
                parent_rels_map = [c.deprel.split(':')[0] for c in node.parent.children]
                node_rels_map = [c.deprel.split(':')[0] for c in node.children]
                for rel_set in matching_rels:
                    if any(r in rel_set for r in parent_rels_map) and any(r in rel_set for r in node_rels_map):
                        break
                else:
                    node.misc['Processed'] = 'deleteSentence'
                    return

                # nsubj forms are the same
                if [c.form.lower() for c in node.children if c.deprel.split(':')[0] == 'nsubj'] == \
                   [c.form.lower() for c in node.parent.children if c.deprel.split(':')[0] == 'nsubj']:
                    for child in node.children:
                        if child.deprel.split(':')[0] in self.none_core_ellipsis or \
                            child.form in {'nt', "n't"} or (child.form == 'not' and child.prev_node.upos == 'AUX'):
                            children_to_delete.append(child)
                        else:
                            children_to_process.append(child)

                    # check conj
                    if any(ch.deprel == 'conj' for ch in children_to_process):
                        conj_nodes = [ch for ch in children_to_process if ch.deprel == 'conj']
                        for conj_node in conj_nodes:
                            if not any(chld.deprel == 'nsubj' for chld in conj_node.children):
                                conj_node.misc['newNode'] = 'deleteThis'
                                children_to_process.remove(conj_node)

                    if len([elem for elem in children_to_process if elem.deprel not in {'punct', 'cc', 'mark'}]) >= 2:
                        self.rehang(node, children_to_process)
                        for child in children_to_delete:
                            child.misc['newNode'] = 'deleteThis'
                    else:
                        # change the word form if needed
                        self.change_form(node)
                        for child in node.children:
                            if child.deprel.split(':')[0] in self.core_ellipsis or \
                               child.form in {'nt', "n't"} or (child.form == 'not' and child.prev_node.upos == 'AUX'):
                                children_to_delete.append(child)
                            else:
                                children_to_process.append(child)
                        self.rehang_alternative(node, children_to_process, children_to_delete, deleteNode=True)

                else:
                    for child in node.children:
                        if child.deprel.split(':')[0] in self.core_ellipsis or \
                           child.form in {'nt', "n't"} or (child.form == 'not' and child.prev_node.upos == 'AUX') or \
                           (child.upos == 'PART' and child.deprel == 'mark'):
                            children_to_delete.append(child)
                        else:
                            children_to_process.append(child)
                    self.rehang_alternative(node, children_to_process, children_to_delete, deleteNode=True)

            elif node.parent.upos == 'VERB' and node.parent.form not in self.cop_form:

                if node.upos in {'PROPN', 'NOUN', 'NUM', 'SYM', 'ADJ', 'ADV', 'PRON'}:
                    # 'real' ellipsis
                    if all(c.deprel not in {'cop', 'aux'} for c in node.children):
                        self.rehang_detected_orphan(node, node.children)

                    else:
                        node.misc['Processed'] = 'deleteSentence'

                    #else:
                    #    node.misc['Processed'] = 'deleteSentence'

            # VERB depends on a clause with 'cop'
            elif ((node.parent.upos == 'VERB' and node.parent.form in self.cop_form) or \
                 any(c.deprel in {'cop'} for c in node.parent.children)) and \
                 ((node.upos == 'VERB' and node.form in self.cop_form) or \
                 any(c.deprel in {'cop'} for c in node.children)):

                for child in node.children:
                    if child.deprel.split(':')[0] in self.none_core_ellipsis or \
                       child.form in {'nt', "n't"} or (child.form == 'not' and child.prev_node.upos == 'AUX'):
                        children_to_delete.append(child)
                    else:
                        children_to_process.append(child)

                if len([elem for elem in children_to_process if elem.deprel not in {'det', 'aux', 'cop', 'punct', 'cc', 'conj', 'mark', 'parataxis', 'discourse'}]) >= 2:
                    self.rehang(node, children_to_process)
                    for c in children_to_delete:
                        c.misc['newNode'] = 'deleteThis'
                else:
                    node.misc['Processed'] = 'deleteSentence'

            else:
                node.misc['Processed'] = 'deleteSentence'

    def promote_node(self, node, c, children_to_process):
        c.misc['newNode'] = str(node.parent.ord) + ':' + str(node.deprel)
        for the_rest in children_to_process:
            if c.ord != the_rest.ord:
                if the_rest.deprel in {'punct', 'cc', 'conj'}:
                    the_rest.misc['newNode'] = str(c.ord) + ':' + str(the_rest.deprel)
                elif the_rest.deprel.split(':')[0] in {'obl', 'advmod', 'nmod'}:
                    the_rest.misc['newNode'] = str(c.ord) + ':orphan'
                elif the_rest.deprel.split(':')[0] in {'det', 'amod', 'case'}:
                    continue
                else:
                    the_rest.misc['newNode'] = str(c.ord) + ':ALARM1'

    def promote_if_core(self, node, c, children_to_process):
        c.misc['newNode'] = str(node.parent.ord) + ':' + str(node.deprel)
        for the_rest in children_to_process:
            if c.ord != the_rest.ord:
                if the_rest.deprel in {'punct', 'cc', 'conj', 'mark'}:
                    the_rest.misc['newNode'] = str(c.ord) + ':' + str(the_rest.deprel)
                elif the_rest.deprel.split(':')[0] in {'obj', 'obl', 'advmod'}:
                    the_rest.misc['newNode'] = str(c.ord) + ':orphan'
                elif the_rest.deprel.split(':')[0] in {'det', 'amod', 'case', 'nmod'}:
                    continue
                else:
                    the_rest.misc['newNode'] = str(c.ord) + ':ALARM2'
        node.misc['newNode'] = str(c.ord) + ':orphan'

    def rehang(self, node, children_to_process, c=None):
        if c is None:
            for c in children_to_process:
                if c.deprel.split(':')[0] == 'obl':
                    self.promote_node(node, c, children_to_process)
                    node.misc['Processed'] = 'Yes'
                    node.misc['newNode'] = 'deleteThis'
                    break
            else:
                for c in children_to_process:
                    if c.deprel.split(':')[0] == 'advmod':
                        self.promote_node(node, c, children_to_process)
                        node.misc['Processed'] = 'Yes'
                        node.misc['newNode'] = 'deleteThis'
                        break
                else:
                    node.misc['Processed'] = 'deleteSentence'
        else:
            self.promote_if_core(node, c, children_to_process)

    def rehang_alternative(self, node, children_to_process, children_to_delete, deleteNode):
        for child in children_to_delete:
            child.misc['newNode'] = 'deleteThis'
        to_promote = [c for c in children_to_process if c.deprel.split(':')[0] == 'nsubj']
        if len(to_promote) == 1:
            self.rehang(node, children_to_process, c=to_promote[0])
            node.misc['Processed'] = 'Yes'
            if deleteNode:
                node.misc['newNode'] = 'deleteThis'
            else:
                node.misc['newNode'] = str(to_promote[0].ord) + ':orphan'
        else:
            node.misc['Processed'] = 'No'
            node.misc['newNode'] = 'ALARM3'

    def rehang_detected_orphan(self, node, children_to_process):
        to_promote = [c for c in children_to_process if c.deprel.split(':')[0] == 'nsubj']
        if len(to_promote) == 1:
            self.promote_if_core(node, to_promote[0], children_to_process)
            node.misc['Processed'] = 'Yes'
        else:
            node.misc['Processed'] = 'No'
            node.misc['newNode'] = 'ALARM4'

    def change_form(self, node):
        wordform = [c.form.lower() for c in node.children if c.deprel.split(':')[0] == 'nsubj'][0]
        if wordform in self.subst:
            new_form = self.subst[[c.form for c in node.children if c.deprel.split(':')[0] == 'nsubj'][0].lower()]
            for child in node.children:
                if child.deprel.split(':')[0] == 'nsubj':
                    child.form = new_form
                    if child.lemma != '':
                        child.lemma = child.form
                        break

