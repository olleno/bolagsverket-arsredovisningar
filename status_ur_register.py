"""Plockar ut en kompakt statusfil ur Bolagsverkets registerfil.
Ut: orgnr;orgform;regdatum;avregdatum;avregorsak;pagande  (gzip)"""
import csv, gzip, sys
csv.field_size_limit(10**8)
src, ut = sys.argv[1], sys.argv[2]
n = 0
with open(src, encoding='utf-8', errors='replace', newline='') as fh, gzip.open(ut, 'wt', encoding='utf-8') as w:
    r = csv.reader(fh, delimiter=';')
    head = r.__next__()
    i = {k: head.index(k) for k in ('organisationsidentitet', 'organisationsform', 'registreringsdatum',
                                    'avregistreringsdatum', 'avregistreringsorsak',
                                    'pagandeAvvecklingsEllerOmstruktureringsforfarande')}
    w.write('orgnr;orgform;regdatum;avregdatum;avregorsak;pagande\n')
    for rad in r:
        try:
            org = rad[i['organisationsidentitet']].split('$')[0]
            form = rad[i['organisationsform']].split('-')[0]
            if form != 'AB':
                continue
            w.write(';'.join([org, form, rad[i['registreringsdatum']][:10], rad[i['avregistreringsdatum']][:10],
                              rad[i['avregistreringsorsak']].split('-')[0],
                              rad[i['pagandeAvvecklingsEllerOmstruktureringsforfarande']].replace(';', ',')[:80]]) + '\n')
            n += 1
        except (IndexError, ValueError):
            continue
print('aktiebolag:', n)
