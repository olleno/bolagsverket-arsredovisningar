"""Räknar vilka uppgiftsnamn (ix:nonFraction / ix:nonNumeric) och taxonomier som förekommer i en bulkfil.
Användning: python namn_i_ar.py <fil.zip> <ut.txt>. Inga organisationsnummer eller belopp skrivs ut."""
import io, re, sys, zipfile, collections
src, ut = sys.argv[1], sys.argv[2]
nf, nn, tax = collections.Counter(), collections.Counter(), collections.Counter()
n = 0
with zipfile.ZipFile(src) as y:
    for namn in y.namelist():
        if not namn.lower().endswith('.zip'):
            continue
        try:
            with zipfile.ZipFile(io.BytesIO(y.read(namn))) as i:
                xf = [x for x in i.namelist() if x.lower().endswith(('.xhtml', '.html', '.htm'))]
                x = i.read(xf[0]).decode('utf-8', 'ignore')
        except Exception:
            continue
        n += 1
        for m in set(re.findall(r'<ix:nonFraction\b[^>]*\bname="([^"]+)"', x)):
            nf[m] += 1
        for m in set(re.findall(r'<ix:nonNumeric\b[^>]*\bname="([^"]+)"', x)):
            nn[m] += 1
        for m in set(re.findall(r'schemaRef[^>]*href="([^"]+)"', x)):
            tax[m] += 1
with open(ut, 'w') as f:
    f.write(f'arsredovisningar {n}\n\n## taxonomier\n')
    for k, v in tax.most_common(): f.write(f'{v}\t{k}\n')
    f.write('\n## numeriska\n')
    for k, v in nf.most_common(): f.write(f'{v}\t{k}\n')
    f.write('\n## text\n')
    for k, v in nn.most_common(): f.write(f'{v}\t{k}\n')
print(n)
