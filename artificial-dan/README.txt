WARNING: If you have two installations of Udapi in your system, e.g.,
a standard one and then this extension for orphans: make sure that this
Udapi is invoked and not the standard one. The standard installation
will look for blocks at its own location, not here! Hence it will not find
the blocks we have added.

UDapy_block_artificial/bin must be in PATH (check your ~/.bashrc)
UDapy_block_artificial/ must be in PYTHONPATH (check your ~/.bashrc)
The bin folder of your standard Udapi installation should be temporarily
removed from the PATH, or alias udapi should be set to this one.

filter.pl ../../../unidep/UD_English/en-ud-dev.conllu | udapy -s ud.Duplicate | udapy -s ud.ConvertOrphans > en-orphans.conllu



Kira:

duplicate.py ... ud.Duplicate
convertorphans.py ... ud.ConvertOrphans

I uploaded a version of my code to my GitHub: https://github.com/Kira-D/UDapy_block_artificial.git
1. "step1.txt" contains a query for English
2. "duplicate.py" duplicates sentences with multiple candidate nodes (one candidate node per sentence)
3. "convertorphans.py" contains conversion/deletion rules
4. "finalizeorphans.py" performs deletion and rehanging and deletes every label that was added to misc column by convertorphans.py

The full command would be:
cat en-ud-dev.conllu | udapy -s util.Filter keep_tree_if_node="not node.parent.is_root() and len([c for c in node.parent.children]) >= 3 and any(c.deprel in {'nsubj'} for c in node.parent.children) and all(c.deprel not in {'ccomp', 'xcomp'} for c in node.parent.children) and node.deprel == 'conj' and all(c.deprel not in {'acl', 'acl:relcl', 'xcomp', 'ccomp', 'advcl', 'expl'} for c in node.children) and any(c.deprel in {'nsubj'} for c in node.children) and not (node.upos != 'VERB' and node.parent.upos != 'VERB') and all(not(c.form == 'it' and c.deprel == 'nsubj') for c in node.children) and not (node.upos == 'VERB' and node.parent.upos != 'VERB' and len([c for c in node.children if c.deprel not in {'aux', 'nsubj', 'cc', 'punct', 'obj'} and (c.form not in {'nt', 'not'})]) < 2) and not (node.upos == 'ADJ' and (node.form.endswith('er') or node.form.endswith('ed') or any(ch.form in {'the'} for ch in node.children))) and '?' not in root.text.split()[-1] and root.text.split()[0].lower() not in {'why', 'what'}" mark="Mark" | udapy -s ud.Duplicate | udapy -s ud.ConvertOrphans > your-file-name.conllu

Ale já mám ten dotaz pro první krok schovaný ve skriptu filter.pl, takže mně by stačilo pustit tohle:
filter.pl input.conllu | udapy -s ud.Duplicate | udapy -s ud.ConvertOrphansCz > output.conllu

Real example:
./filter.pl ../../../unidep/UD_Czech/cs-ud-dev.conllu | udapy -s ud.Duplicate | udapy -s ud.ConvertOrphansCz > cs-ud-dev-converted.conllu

