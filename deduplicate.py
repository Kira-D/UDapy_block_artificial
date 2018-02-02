import sys

def read_conllu(f):
    sent=[]
    comment=[]
    for line in f:
        line=line.strip()
        if not line: # new sentence
            if sent:
                yield comment,sent
            comment=[]
            sent=[]
        elif line.startswith("#"):
            comment.append(line)
        else: #normal line
            sent.append(line.split("\t"))
    else:
        if sent:
            yield comment, sent

ID,FORM,LEMMA,CPOS,POS,FEAT,HEAD,DEPREL,DEPS,MISC=range(10)

uniq=set()

keep=[]
for comm, sent in read_conllu(sys.stdin):
    text=" ".join(t[FORM] for t in sent)
    if text in uniq:
        continue
    keep.append((comm,sent))
    uniq.add(text)

for comm,sent in keep:
    for c in comm:
        print(c)
    for token in sent:
        print("\t".join(c for c in token))
    print("")
