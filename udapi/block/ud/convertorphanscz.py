"""ud.ConvertOrphansCz block template."""

import sys
from collections import Counter
from udapi.core.block import Block

class ConvertOrphansCz(Block):
    """Converts full sentences into artificial.
        Usage: cat file-to-convert.conllu | udapy -s ud.ConvertOrphansCz
        Notes:
        If a sentence is processed, this information is added to the misc column:
            'Processed=Yes'marker is added to the node that will be deleted
             new heads and labels are added to nodes that should be rehung ('newNode=new-head:relation')
             'newNode=deleteThis' marker is added to all nodes that will be deleted
        Check processed sentences: file-to-convert.conllu | udapy -s util.Filter keep_tree_if_node="node.misc['Processed'] == 'Yes'" mark="Mark" | udapy write.TextModeTrees
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Substitution of pronouns is probably useless because Czech is a pro-drop language.
        self.subst = {'on': 'ona', 'ona': 'on', 'já':'ty', 'vy': 'oni', 'oni': 'vy', 'my': 'vy'}
        # Auxiliary children to remove if parent is elided. (DZ: I don't know why it is called core_ellipsis.)
        self.core_ellipsis = {'aux', 'cop', 'expl', 'compound'}
        # DZ: I don't know why this is called non_core_ellipsis but these are children to be deleted too!
        self.none_core_ellipsis = {'nsubj', 'obj', 'iobj', 'aux', 'cop', 'expl', 'compound', 'mark'}
        self.cop_form = {'byl', 'byla', 'bylo', 'byli', 'byly', 'jsem', 'jsi', 'je', 'jsme', 'jste', 'jsou', 'budu', 'budeš', 'bude', 'budeme', 'budete', 'budou', 'nebyl', 'nebyla', 'nebylo', 'nebyli', 'nebyly', 'nejsem', 'nejsi', 'není', 'nejsme', 'nejste', 'nejsou', 'nebudu', 'nebudeš', 'nebude', 'nebudeme', 'nebudete', 'nebudou'}

    def process_node(self, node):
        if 'Mark' in node.misc:
            children_to_delete = []
            children_to_process = []

            # VERB depends on VERB
            if node.upos == 'VERB' and node.parent.upos == 'VERB' and \
               node.parent.form not in self.cop_form and node.form not in self.cop_form:
                ###!!! Late filtering. It would be better to rule such sentences out in the filtering step.
                ###!!! But filtering of the web parsebank takes four hours and I do not want to re-run it.
                if not self.is_good_candidate(node):
                    node.misc['Processed'] = 'No'
                    return
                # nsubj forms are the same
                # THINK: here it is also possible to copy a sentence and make two kinds of ellipsis using one sentence
                if [c.form.lower() for c in node.children if c.deprel.split(':')[0] == 'nsubj'] == \
                   [c.form.lower() for c in node.parent.children if c.deprel.split(':')[0] == 'nsubj']:
                    # Remove core children (nsubj, obj, iobj) and auxiliaries. Keep oblique arguments and adjuncts.
                    for child in node.children:
                        if child.deprel.split(':')[0] in self.none_core_ellipsis:
                            children_to_delete.append(child)
                        else:
                            children_to_process.append(child)
                    # We need two oblique children. One will be promoted. The other will be attached as orphan.
                    if len([elem for elem in children_to_process if elem.deprel not in {'punct', 'cc', 'mark'}]) >= 2:
                        self.rehang(node, children_to_process)
                        for child in children_to_delete:
                            child.misc['newNode'] = 'deleteThis'
                    else:
                        # change the word form if needed
                        self.change_form(node)
                        for child in node.children:
                            # Remove auxiliaries and other uninteresting children.
                            if child.deprel.split(':')[0] in self.core_ellipsis:
                                children_to_delete.append(child)
                            else:
                                children_to_process.append(child)
                        self.rehang_alternative(node, children_to_process, children_to_delete, deleteNode=True)

                else: # subject forms differ
                    for child in node.children:
                        if child.deprel.split(':')[0] in self.core_ellipsis:
                            children_to_delete.append(child)
                        else:
                            children_to_process.append(child)
                    self.rehang_alternative(node, children_to_process, children_to_delete, deleteNode=True)

            # Node is not verb. Its parent is verb.
            elif node.parent.upos == 'VERB' and node.parent.form not in self.cop_form:

                if node.upos in {'PROPN', 'NOUN', 'NUM', 'SYM', 'ADJ', 'ADV'}:
                    # 'real' ellipsis
                    if all(c.deprel not in {'cop', 'aux'} for c in node.children):
                        self.rehang_detected_orphan(node, node.children)

                    else:
                        # change the word form if needed
                        self.change_form(node)

                        for child in node.children:
                            if child.deprel.split(':')[0] in self.none_core_ellipsis:
                                children_to_delete.append(child)
                            else:
                                children_to_process.append(child)

                        if node.upos in {'ADJ', 'ADV'} and \
                           len([elem for elem in children_to_process if elem.deprel.split(':')[0] not in \
                           {'punct', 'cc', 'conj', 'det', 'amod', 'case', 'nmod'}]) >= 2:
                                self.rehang(node, children_to_process)
                                for child in children_to_delete:
                                    child.misc['newNode'] = 'deleteThis'
                        else:
                            # pass relation and the head to the subject
                            self.rehang_to_subj(node)

            # VERB depends on a clause with 'cop'
            elif (node.parent.upos == 'VERB' and node.parent.form in self.cop_form) or \
                 any(c.deprel in {'cop'} for c in node.parent.children):
                for child in node.children:
                    if child.deprel.split(':')[0] in self.none_core_ellipsis:
                        children_to_delete.append(child)
                    else:
                        children_to_process.append(child)

                if len([elem for elem in children_to_process if elem.deprel not in {'punct', 'cc', 'conj', 'mark', 'parataxis'}]) >= 2:
                    self.rehang(node, children_to_process)
                    for c in children_to_delete:
                        c.misc['newNode'] = 'deleteThis'
                else:
                    self.change_form(node)
                    self.rehang_to_subj(node)
                    node.misc['newNode'] = 'deleteThis'

            else:
                node.misc['Processed'] = 'No'

    def is_good_candidate(self, node):
        """
        We pre-filtered the corpus in the first step, before applying this block. However,
        there are some further conditions (often language-specific) that should be tested
        and if they are not met, the candidate should be discarded.
        """
        ###!!! It would be better to rule such sentences out in the filtering step.
        ###!!! But filtering of the web parsebank takes four hours and I do not want to re-run it.
        # Avoid gapping if the subject of the second clause is "což" (relation of consequence).
        if [c.form.lower() for c in node.children if c.deprel.split(':')[0] == 'nsubj'][0] == 'což':
            return False
        aadeprels = {'nsubj', 'obj', 'iobj', 'obl', 'obl:arg', 'obl:agent'}
        cdeps = {self.get_dependent_type(c) for c in node.children if c.deprel in aadeprels}
        pdeps = {self.get_dependent_type(c) for c in node.parent.children if c.deprel in aadeprels}
        # There must be at least two children of the same type under both verbs.
        # That is, the intersection of pdeps and cdeps must have at least two members.
        if len(pdeps & cdeps) < 2:
            return False
        return True

    def get_dependent_type(self, node):
        """
        Returns a string that identifies the type of dependent.
        Dependency relation label (deprel) is accompanied by morphological case and adposition, if applicable.
        Therefore a dative object is different from a genitive object.
        """
        type = str(node.deprel)
        adpositions = [adp.lemma for adp in node.children if adp.deprel == 'case']
        if len(adpositions) >= 1:
            type = type + ':' + str(adpositions[0])
        case = node.feats['Case']
        if case != '':
            type = type + ':' + str(case).lower()
        return type

    def promote_node(self, node, c, children_to_process):
        """
        node ... The node that will be deleted.
        c ...... The child that will be promoted to the position of the deleted node.
        children_to_process ... All children of the to-be-deleted node.
        """
        c.misc['newNode'] = str(node.parent.ord) + ':' + str(node.deprel)
        for the_rest in children_to_process:
            if c.ord != the_rest.ord:
                if the_rest.deprel in {'punct', 'cc', 'conj'}:
                    the_rest.misc['newNode'] = str(c.ord) + ':' + str(the_rest.deprel)
                elif the_rest.deprel.split(':')[0] in {'obl', 'advmod'}:
                    the_rest.misc['newNode'] = str(c.ord) + ':orphan'
                elif the_rest.deprel.split(':')[0] in {'det', 'amod', 'case', 'nmod'}:
                    continue ###??? DZ: Why?
                else:
                    the_rest.misc['newNode'] = str(c.ord) + ':ALARM1'

    def promote_if_core(self, node, c, children_to_process):
        """
        node ... The node that will be deleted.
        c ...... The child that will be promoted to the position of the deleted node.
        children_to_process ... All children of the to-be-deleted node.
        """
        c.misc['newNode'] = str(node.parent.ord) + ':' + str(node.deprel)
        for the_rest in children_to_process:
            if c.ord != the_rest.ord:
                if the_rest.deprel in {'punct', 'cc', 'conj', 'mark'}:
                    the_rest.misc['newNode'] = str(c.ord) + ':' + str(the_rest.deprel)
                elif the_rest.deprel.split(':')[0] in {'obj', 'iobj', 'obl', 'advmod'}:
                    the_rest.misc['newNode'] = str(c.ord) + ':orphan'
                elif the_rest.deprel.split(':')[0] in {'det', 'amod', 'case', 'nmod'}:
                    continue ###??? DZ: Why?
                else:
                    the_rest.misc['newNode'] = str(c.ord) + ':ALARM2'
        node.misc['newNode'] = str(c.ord) + ':orphan'

    def rehang(self, node, children_to_process, c=None):
        """
        node ... The node that will be deleted.
        children_to_process ... Children of the to-be-deleted node.
        c ...... Child that should be promoted (if we already have a candidate; otherwise it will be selected now).
        """
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
            # The candidate verb has two or more subjects.
            # That should not happen in manually annotated data but it cannot be excluded in automatically parsed data.
            node.misc['Processed'] = 'deleteSentence'

    def rehang_detected_orphan(self, node, children_to_process):
        to_promote = [c for c in children_to_process if c.deprel.split(':')[0] == 'nsubj']
        if len(to_promote) == 1:
            self.promote_if_core(node, to_promote[0], children_to_process)
            node.misc['Processed'] = 'Yes'
        else:
            node.misc['Processed'] = 'No'
            node.misc['newNode'] = 'ALARM4'

    def change_form(self, node):
        """
        If two conjoined verbs have identical subjects, we can try to remove the second verb and
        replace its subject by something else (as in "He will prepare the dinner and !she! [will] [go] home.")
        """
        wordform = [c.form.lower() for c in node.children if c.deprel.split(':')[0] == 'nsubj'][0]
        if wordform in self.subst:
            new_form = self.subst[[c.form for c in node.children if c.deprel.split(':')[0] == 'nsubj'][0].lower()]
            for child in node.children:
                if child.deprel.split(':')[0] == 'nsubj':
                    child.form = new_form
                    if child.lemma != '':
                        child.lemma = child.form
                        break

    def rehang_to_subj(self, node):
        for child in node.children:
            if child.deprel.split(':')[0] == 'nsubj':
                child.misc['newNode'] = str(node.parent.ord) + ':' + str(node.deprel)
                child.misc['Processed'] = 'Yes'
                if any(c.form.lower() == 'ale' for c in node.children):
                    change_form = [c for c in node.children if c.form.lower() == 'ale']
                    change_form[0].form = 'a'
                    change_form[0].lemma = 'a'
                    change_form[0].parent = child
                elif any(c.form.lower() == 'a' for c in node.children):
                    change_form = [c for c in node.children if c.form.lower() == 'a']
                    change_form[0].parent = child
                else:
                    shift_here = min(child.children + [child], key=lambda x: x.ord)
                    child.create_child(form='a', lemma='a', upos='CCONJ', deprel='cc').shift_before_node(shift_here)
                shift_here = max(child.children + [child], key=lambda x: x.ord)
                start = child.create_child(form='také', lemma='také', upos='ADV', deprel='orphan')
                start.shift_after_node(shift_here)
                if node.root.descendants[-1].deprel == 'punct':
                    start.misc['SpaceAfter']='No'
                if node.root.descendants[-1].deprel == 'punct':
                    end = -1
                else:
                    end = None
                for token in node.root.descendants[start.ord:end]:
                    token.misc['newNode'] = 'deleteThis'
                    if any(c.deprel.split(':')[0] in {'advmod', 'obl'} for c in node.children):
                        for c in node.children:
                            if c.deprel.split(':')[0] in {'advmod', 'obl'}:
                                c.parent = child
                break

