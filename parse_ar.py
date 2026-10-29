"""Läser en av Bolagsverkets månadsfiler med årsredovisningar (zip i zip, iXBRL)
och skriver en rad per årsredovisning med nyckeltal för innevarande och föregående år.

Användning: python parse_ar.py <fil.zip> <inlamningsmanad YYYY-MM> <ut.csv>
"""
import csv
import io
import re
import sys
import zipfile

# Nyckeltal ur den svenska taxonomin (se-gen-base). Namnet efter kolonet räcker.
FALT = [
    'Nettoomsattning', 'Rorelseresultat', 'ResultatEfterFinansiellaPoster', 'AretsResultat',
    'Tillgangar', 'EgetKapital', 'Omsattningstillgangar', 'KassaBank', 'KassaBankExklRedovisningsmedel',
    'KortfristigaSkulder', 'LangfristigaSkulder', 'ObeskattadeReserver', 'Avsattningar',
    'MedelantaletAnstallda', 'Personalkostnader', 'Aktiekapital', 'BalanseratResultat',
    'Kundfordringar', 'Leverantorsskulder', 'SkulderKreditinstitutKortfristiga',
    'SkulderKreditinstitutLangfristiga', 'Varulager', 'ForslagUtdelning',
]
FALTSET = set(FALT)

RE_CTX = re.compile(r'<xbrli:context\b[^>]*\bid="([^"]+)"[^>]*>(.*?)</xbrli:context>', re.S)
RE_DATE = re.compile(r'<xbrli:(?:instant|endDate)>\s*([^<\s]+)\s*<')
RE_DIM = re.compile(r'xbrldi:explicitMember', re.S)
RE_NF = re.compile(r'<ix:nonFraction\b([^>]*)>(.*?)</ix:nonFraction>', re.S)
RE_NN = re.compile(r'<ix:nonNumeric\b([^>]*)>(.*?)</ix:nonNumeric>', re.S)


def attr(a, s):
    m = re.search(r'\b%s="([^"]*)"' % a, s)
    return m.group(1) if m else None


def tal(txt, scale, sign):
    t = re.sub(r'<[^>]+>', '', txt)
    t = t.replace('\xa0', '').replace(' ', '').replace('−', '-')
    t = t.replace('.', '').replace(',', '.')
    if not re.match(r'^-?\d+(\.\d+)?$', t or ''):
        return None
    v = float(t)
    if scale:
        try:
            v *= 10 ** int(scale)
        except ValueError:
            pass
    if sign == '-':
        v = -v
    return v


def las(xhtml):
    ctx = {}
    for m in RE_CTX.finditer(xhtml):
        if RE_DIM.search(m.group(2)):
            continue  # dimensioner (t.ex. per aktieslag) hoppas över
        d = RE_DATE.search(m.group(2))
        if d:
            ctx[m.group(1)] = d.group(1)[:10]
    ut = {}
    for m in RE_NF.finditer(xhtml):
        at = m.group(1)
        namn = (attr('name', at) or '').split(':')[-1]
        if namn not in FALTSET:
            continue
        d = ctx.get(attr('contextRef', at) or '')
        if not d:
            continue
        v = tal(m.group(2), attr('scale', at), attr('sign', at))
        if v is not None and (namn, d) not in ut:
            ut[(namn, d)] = v
    # Enkla icke-numeriska flaggor
    flaggor = {'revisor': 0, 'fortsatt_drift': 0, 'kontrollbalans': 0}
    for m in RE_NN.finditer(xhtml):
        namn = (attr('name', m.group(1)) or '').split(':')[-1].lower()
        if 'revisor' in namn:
            flaggor['revisor'] = 1
        if 'fortsattdrift' in namn or 'fortlevnad' in namn:
            flaggor['fortsatt_drift'] = 1
        if 'kontrollbalans' in namn:
            flaggor['kontrollbalans'] = 1
    low = xhtml.lower()
    if 'kontrollbalansräkning' in low or 'kontrollbalansr&auml;kning' in low:
        flaggor['kontrollbalans'] = 1
    if 'fortsatt drift' in low or 'väsentlig osäkerhet' in low:
        flaggor['fortsatt_drift'] = 1
    return ut, flaggor


def main(src, manad, utfil):
    rader = []
    trasiga = 0
    with zipfile.ZipFile(src) as yttre:
        for n in yttre.namelist():
            if not n.lower().endswith('.zip'):
                continue
            bas = n.rsplit('/', 1)[-1][:-4]
            try:
                orgnr, bokslut = bas.split('_', 1)
            except ValueError:
                continue
            try:
                with zipfile.ZipFile(io.BytesIO(yttre.read(n))) as inre:
                    xf = [x for x in inre.namelist() if x.lower().endswith(('.xhtml', '.html', '.htm'))]
                    if not xf:
                        continue
                    xhtml = inre.read(xf[0]).decode('utf-8', 'ignore')
            except Exception:
                trasiga += 1
                continue
            v, fl = las(xhtml)
            datum = sorted({d for (_, d) in v}, reverse=True)
            if not datum:
                continue
            nu = datum[0]
            forra = datum[1] if len(datum) > 1 else ''
            # Spärr: bara juridiska personer. Ett nummer vars tredje och fjärde siffra är under 20
            # ser ut som ett personnummer och tas aldrig med (repot är publikt).
            if not (len(orgnr) == 10 and orgnr.isdigit() and int(orgnr[2:4]) >= 20):
                continue
            rad = {'orgnr': orgnr, 'bokslut': bokslut, 'inlamnad': manad, 'ar_nu': nu, 'ar_forra': forra}
            for f in FALT:
                rad[f] = v.get((f, nu), '')
                rad[f + '_f'] = v.get((f, forra), '') if forra else ''
            rad.update(fl)
            rader.append(rad)
    if not rader:
        print('inga rader', src, 'trasiga', trasiga)
        return
    with open(utfil, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rader[0].keys()))
        w.writeheader()
        w.writerows(rader)
    print(f'{src}: {len(rader)} årsredovisningar, {trasiga} trasiga')


if __name__ == '__main__':
    main(*sys.argv[1:4])
