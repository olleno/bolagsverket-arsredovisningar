"""Plockar ut bransch (SNI) och postnummer ur SCB:s företagsfil, bara för aktiebolag (JurForm 49).
Namn, adresser och c/o-uppgifter tas inte med. Status-fälten (FtgStat, JEStat) tas inte heller med:
de visar läget i dag och skulle avslöja facit i en modell som prövas bakåt i tiden.
Ut: orgnr;sni;sni2;postnr2 (gzip)"""
import csv, gzip, sys
src, ut = sys.argv[1], sys.argv[2]
n = 0
with open(src, encoding='latin-1', newline='') as fh, gzip.open(ut, 'wt', encoding='utf-8') as w:
    r = csv.reader(fh, delimiter='\t')
    head = [h.strip() for h in next(r)]
    i = {k: head.index(k) for k in ('PeOrgNr', 'Ng1', 'PostNr', 'JurForm')}
    w.write('orgnr;sni;sni2;postnr2\n')
    for rad in r:
        try:
            if rad[i['JurForm']].strip() != '49':
                continue
            org = rad[i['PeOrgNr']].strip()
            org = org[2:] if len(org) == 12 and org.startswith('16') else org
            sni = rad[i['Ng1']].strip()
            pn = rad[i['PostNr']].strip()
            w.write(f'{org};{sni};{sni[:2]};{pn[:2]}\n')
            n += 1
        except (IndexError, ValueError):
            continue
print('aktiebolag:', n)
