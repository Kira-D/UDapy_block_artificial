"""ud.ConvertOrphansFi block template."""

import sys
from collections import Counter
from udapi.core.block import Block

class ConvertOrphansFi(Block):
    """Converts full sentences into artificial.
        Usage: cat file-to-convert.conllu | udapy -s ud.ConvertOrphansFi
        Notes: 
        If a sentence is processed, this information is added to the misc column:
            'Processed=Yes'marker is added to the node that will be deleted
             new heads and labels are added to nodes that should be rehung ('newNode=new-head:relation')
             'newNode=deleteThis' marker is added to all nodes that will be deleted
        Check processed sentences: file-to-convert.conllu | udapy -s util.Filter keep_tree_if_node="node.misc['Processed'] == 'Yes'" mark="Mark" | udapy write.TextModeTrees

    Step 0: Change subject form if needed
    Step 1: Find new head using priority list
    Step 2: Identify relations which should be removed
    Step 3: Identify relations which should be moved to new head
    Step 4: Delete node

    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.subst = {'mä': 'sä', 'minä': 'sinä', 'sä': 'mä', 'sinä': 'minä', 'kaikki': 'osa', 'osa': 'kaikki', 'me': 'te', 'te': 'me'} # mä rakastan treenaamista ja mä rakastan lätkää --> mä rakastan treenaamista ja sä lätkää
        self.core_ellipsis = {'aux', 'cop', 'compound'}
        self.none_core_ellipsis = {'nsubj', 'iobj', 'obj', 'aux', 'compound', 'mark', 'cop'}
        self.cop_form = {'olla'}
        self.priority = ['nsubj', 'obj', 'obl'] # my priority list to find promoted head
           
    def process_node(self, node):
        if 'Mark' in node.misc:
            children_to_delete = []
            children_to_process = []

            # VERB depends on VERB, and not copula
            if node.upos == 'VERB' and node.parent.upos == 'VERB' and \
               node.parent.lemma not in self.cop_form and node.lemma not in self.cop_form:

                # Step 0: Change subject form if needed (if we fail here, should we just skip the sentence?)
                status=self.change_form(node)
                if status is False:
                    node.misc['Processed'] = 'deleteSentence' # failed to convert this sentence
                    return
                
                # Step 1: Find new head using priority list
                new_head=self.identify_new_head(node)

                # Step 2 and Step 3: Identify relations which should be removed and relations which should be moved to new head
                self.process_children(node, new_head)

                # Step 4: Delete node
                node.misc['newNode'] = 'deleteThis'
                node.misc['Processed'] = 'Yes'
                return
            else:
                node.misc['Processed'] = 'deleteSentence' # failed to convert this sentence
                return


    def identify_new_head(self, node):
        types=[c.deprel for c in node.children]
        for p in self.priority:
            if p not in types:
                continue
            for child in node.children: # ordered list so we can take the first one
                if child.deprel==p:
                    return child
        print(types)
        assert False, "Cannot promote!!!!!"

    def process_children(self, node, new_head):

        for child in node.children:
            if child.deprel=='conj': # recursively remove everything under conj
                self.delete_recursively(child)
                continue
            if child==new_head: # rehang to node.parent as conj
                child.misc['newNode'] = str(node.parent.ord) + ':' + str(node.deprel)
            elif child.deprel in {'aux', 'aux:pass'}: # TODO something else?
                child.misc['newNode'] = 'deleteThis'
            else: # rehang to new node
                if child.deprel in {'cc', 'punct', 'conj', 'mark'}:
                    t=child.deprel
                else:
                    t='orphan'
                child.misc['newNode'] = str(new_head.ord) + ':' + t

    def delete_recursively(self, node):
        node.misc['newNode'] = 'deleteThis'
        for child in node.children:
            self.delete_recursively(child)


    def change_form(self, node):
        # change second subject if it's same as the first one
        subjectforms_node = [c.form.lower() for c in node.children if c.deprel.split(':')[0] == 'nsubj']
        subjectforms_parent = [c.form.lower() for c in node.parent.children if c.deprel.split(':')[0] == 'nsubj']
        if len(subjectforms_node)!=1 or len(subjectforms_parent)!=1 or subjectforms_node[0]!=subjectforms_parent[0]:
            return True # no need for this replacement
        parent_s=subjectforms_parent[0] # parent subject wordform
        node_s=subjectforms_node[0] # node subject wordform
        if parent_s in self.subst: # self.subst is a replacement dictionary
            new_form = self.subst[parent_s]
            for child in node.children:
                if child.deprel.split(':')[0] == 'nsubj':
                    child.form = new_form
                    if child.lemma != '':
                        child.lemma = child.form
                        break
            return True
        else:
            return False

