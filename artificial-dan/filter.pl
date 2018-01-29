#!/usr/bin/env perl

use utf8;
use open ':utf8';
binmode(STDIN, ':utf8');
binmode(STDOUT, ':utf8');
binmode(STDERR, ':utf8');

my $infile = $ARGV[0]; # ../unidep/UD_English/en-ud-test.conllu

#my $keep_tree_if_node = get_ktin_kira();
my $keep_tree_if_node = get_ktin_dan();
# We will put the keep-tree filter in double quotation marks. If it contains any quotation marks, escape them.
$keep_tree_if_node =~ s/"/\\"/g;

my $udapy = 'udapy -s util.Filter keep_tree_if_node="'.$keep_tree_if_node.'" mark="Mark" | udapy write.TextModeTrees';
my $command = "cat $infile | $udapy";
print STDERR ("$command\n");
system($command);



#------------------------------------------------------------------------------
# Dan's experimental filter.
#------------------------------------------------------------------------------
sub get_ktin_dan
{
    # Necessary conditions for the node that is a candidate for deletion.
    my @conditions = ('not node.parent.is_root()');
    push(@conditions, "node.deprel == 'conj'");
    push(@conditions, "node.parent.upos == 'VERB'");
    push(@conditions, "node.upos == 'VERB'");
    # The parent of the candidate node must have at least three children (two arguments and the candidate).
    push(@conditions, 'len([c for c in node.parent.children]) >= 3');
    # Both the candidate and its parent must have a subject child (###!!! this is just an approximation; there are examples of gapping without a subject).
    push(@conditions, "any(c.deprel in {'nsubj'} for c in node.parent.children)");
    push(@conditions, "any(c.deprel in {'nsubj'} for c in node.children)");
    # The parent of the candidate node must not have children of the following types.
    push(@conditions, "all(c.deprel not in {'cop', 'ccomp', 'xcomp'} for c in node.parent.children)");
    # The candidate node must not have children of the following types.
    push(@conditions, "all(c.deprel not in {'acl', 'acl:relcl', 'xcomp', 'ccomp', 'advcl', 'expl'} for c in node.children)");
    return join(' and ', @conditions);
}



#------------------------------------------------------------------------------
# Kira's original filter for English.
#------------------------------------------------------------------------------
sub get_ktin_kira
{
    # Kira:
    # c. Some details on query conditions (Show sentence if the following is true):
    # ('universal')
    #  - a candidate node is not the head of the sentence (not node.parent.is_root());
    #  - the head of a candidate node must have at least two dependents and one of them must be 'nsubj' and none of them can be 'ccomp' or 'xcomp';
    #  - a candidate node must be 'conj' and must have 'nsubj' among its dependents;
    #  - a candidate node must not have any dependents with  these relations: 'acl', 'acl:relcl', 'xcomp', 'ccomp', 'advcl', 'expl';
    # ('language dependent')
    #  -  if a candidate node is an adjective it must depend on another adjective (An ability of a verb to have adjectives as dependents strongly depends on the verb, for instance "he became ill" vs *"he smells rude");
    #  - "it is ..." clauses are forbidden for the second clauses;
    #  - if a candidate node is a verb and it has a head that is not a verb, the second clause must have at least two children which relations are not in 'aux', 'nsubj', 'cc', 'punct', 'obj' and word forms are not in 'nt', 'not', "n't";
    #  - if a candidate node is an adjective it must not be a comparison or a verbal adjective;
    #  - no interrogative sentences: two last conditions exclude sentences with any combinations of '?' in the end of a sentence and sentences that start with 'why' and 'what'.
    my $keep_tree_if_node =
        "not node.parent.is_root() and ".
        "len([c for c in node.parent.children]) >= 2 and ".
        "any(c.deprel in {'nsubj'} for c in node.parent.children) and ".
        "all(c.deprel not in {'ccomp', 'xcomp'} for c in node.parent.children) and ".
        "node.deprel == 'conj' and ".
        "all(c.deprel not in {'acl', 'acl:relcl', 'xcomp', 'ccomp', 'advcl', 'expl'} for c in node.children) and ".
        "any(c.deprel in {'nsubj'} for c in node.children) and ".
        "not (node.upos == 'ADJ' and node.parent.upos != 'ADJ') and ".
        "all(not(c.form == 'it' and c.deprel == 'nsubj') for c in node.children) and ".
        "not (".
            "node.upos == 'VERB' and ".
            "node.parent.upos != 'VERB' and ".
            "len([c for c in node.children if c.deprel not in {'aux', 'nsubj', 'cc', 'punct', 'obj'} and ".
            qq{(c.form not in {'nt', 'not', "n't"})}.
            "]) < 2) and ".
        "not (node.upos == 'ADJ' and (node.form.endswith('er') or node.form.endswith('ed'))) and ".
        "'?' not in root.text.split()[-1] and ".
        "root.text.split()[0].lower() not in {'why', 'what'}";
    return $keep_tree_if_node;
}
