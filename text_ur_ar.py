"""Plockar ut löptext (förvaltningsberättelse m.m.) ur utvalda årsredovisningar.

Användning: python text_ur_ar.py <bulkfil.zip> <orgnr_bokslut.txt> <utkatalog>
orgnr_bokslut.txt: en rad per årsredovisning, "orgnr_bokslutsdatum" (samma namn som filen i zip-arkivet).
Skriver <utkatalog>/<orgnr>_<bokslut>.txt med text, utan siffertabeller och utan underskriftsdelen.
"""
import html
import io
import os
import re
import sys
import zipfile

MAX = 9000


def till_text(xhtml):
    x = re.sub(r'(?is)<(script|style|head)\b.*?</\1>', ' ', xhtml)
    x = re.sub(r'(?is)<table\b.*?</table>', '\n[tabell]\n', x)
    x = re.sub(r'(?i)<br\s*/?>|</(p|div|h\d|li|tr)>', '\n', x)
    x = re.sub(r'<[^>]+>', ' ', x)
    x = html.unescape(x)
    x = re.sub(r'[ \t\xa0]+', ' ', x)
    x = re.sub(r'\n\s*\n+', '\n', x)
    return x.strip()


def klipp(t):
    low = t.lower()
    start = low.find('förvaltningsberättelse')
    t = t[start:] if start >= 0 else t
    # underskriftsdelen innehåller personnamn: skär bort allt från den
    m = re.search(r'(?i)\n[^\n]{0,60}(underskrifter|har undertecknats|undertecknas|elektroniskt underteckn)', t)
    if m:
        t = t[:m.start()]
    t = re.sub(r'(\[tabell\]\s*){2,}', '[tabell]\n', t)
    return t[:MAX]


def main(src, lista, ut):
    vill = {l.strip() for l in open(lista) if l.strip()}
    os.makedirs(ut, exist_ok=True)
    n = 0
    with zipfile.ZipFile(src) as yttre:
        for namn in yttre.namelist():
            bas = namn.rsplit('/', 1)[-1][:-4]
            if bas not in vill:
                continue
            try:
                with zipfile.ZipFile(io.BytesIO(yttre.read(namn))) as inre:
                    xf = [x for x in inre.namelist() if x.lower().endswith(('.xhtml', '.html', '.htm'))]
                    if not xf:
                        continue
                    txt = klipp(till_text(inre.read(xf[0]).decode('utf-8', 'ignore')))
            except Exception:
                continue
            open(os.path.join(ut, bas + '.txt'), 'w', encoding='utf-8').write(txt)
            n += 1
    print(f'{src}: {n} texter')


if __name__ == '__main__':
    main(*sys.argv[1:4])
