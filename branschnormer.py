"""Branschnormer: hur ser nyckeltalen ut för bolag i samma bransch? Underlag för Konrads jämförelser
("dina kundfordringar är högre än för 9 av 10 bolag i din bransch").

Bransch = SNI på två siffror ur SCB:s företagsfil (data/scb_ab.csv.gz). Obs: SCB-filen visar bolag som finns i dag,
så bolag som redan försvunnit saknar bransch. Normerna gäller därför levande bolag – bra för jämförelser,
inte för att mäta risk.

Bara grupper med minst 10 bolag visas (datasling-regeln). Inga organisationsnummer skrivs ut.
Användning: python branschnormer.py [datakatalog] [ut.json]
"""
import glob
import json
import os
import sys
from datetime import date

import pandas as pd

KAT = sys.argv[1] if len(sys.argv) > 1 else 'data'
UT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(KAT, 'facit', 'branschnormer.json')
MIN_BOLAG = 10
KVANTILER = [0.1, 0.25, 0.5, 0.75, 0.9]
KOL = ['orgnr', 'bokslut', 'Nettoomsattning', 'Rorelseresultat', 'Tillgangar', 'EgetKapital', 'KassaBank',
       'KortfristigaSkulder', 'Kundfordringar', 'Leverantorsskulder', 'Personalkostnader', 'Varulager',
       'InventarierVerktygInstallationerAnskaffningsvarden',
       'InventarierVerktygInstallationerForandringAvskrivningarAretsAvskrivningar']

MATT = {
    'soliditet': ('Eget kapital / tillgångar', lambda d: d.EgetKapital / d.Tillgangar),
    'rorelsemarginal': ('Rörelseresultat / omsättning', lambda d: d.Rorelseresultat / d.Nettoomsattning),
    'kundfordr_dagar': ('Kundfordringar i dagar av omsättningen', lambda d: 365 * d.Kundfordringar / d.Nettoomsattning),
    'levskuld_andel': ('Leverantörsskulder / omsättning', lambda d: d.Leverantorsskulder / d.Nettoomsattning),
    'kassalikviditet': ('Kassa och bank / kortfristiga skulder', lambda d: d.KassaBank / d.KortfristigaSkulder),
    'personal_andel': ('Personalkostnader / omsättning', lambda d: d.Personalkostnader / d.Nettoomsattning),
    'lager_dagar': ('Varulager i dagar av omsättningen', lambda d: 365 * d.Varulager / d.Nettoomsattning),
    # Version 3 (noterna): avskrivningstid för inventarier = anskaffningsvärde / årets avskrivning. Bara när datan finns.
    'avskrivningstid_inventarier': ('Avskrivningstid inventarier i år (anskaffningsvärde / årets avskrivning)',
        lambda d: (d['InventarierVerktygInstallationerAnskaffningsvarden']
                   / d['InventarierVerktygInstallationerForandringAvskrivningarAretsAvskrivningar'].abs())
        if 'InventarierVerktygInstallationerAnskaffningsvarden' in d else pd.Series(dtype=float)),
}


def main():
    filer = sorted(glob.glob(os.path.join(KAT, 'ar3', '*.csv.gz')))
    if len(filer) < 500:
        filer = sorted(glob.glob(os.path.join(KAT, 'ar2', '*.csv.gz')))
    d = pd.concat([pd.read_csv(f, usecols=lambda c: c in KOL, dtype={'orgnr': str}) for f in filer])
    d['bokslut'] = pd.to_datetime(d['bokslut'], errors='coerce')
    d = d.sort_values('bokslut').drop_duplicates('orgnr', keep='last')      # senaste årsredovisningen per bolag
    d = d[(d.bokslut >= '2023-01-01') & (d.Nettoomsattning > 100_000) & (d.Tillgangar > 0)]
    scb = pd.read_csv(os.path.join(KAT, 'scb_ab.csv.gz'), sep=';', dtype=str)[['orgnr', 'sni2']]
    d = d.merge(scb, on='orgnr', how='inner')
    ut = {'skapad': date.today().isoformat(), 'urval': 'senaste årsredovisning per bolag, bokslut 2023 eller senare, '
          'omsättning över 100 000 kr', 'min_bolag': MIN_BOLAG, 'matt': {k: v[0] for k, v in MATT.items()},
          'bransch': {}}
    for sni2, g in d.groupby('sni2'):
        rad = {'bolag': int(len(g))}
        for k, (_, f) in MATT.items():
            v = f(g).replace([float('inf'), -float('inf')], pd.NA).dropna()
            if len(v) >= MIN_BOLAG:
                rad[k] = {'n': int(len(v)), **{f'p{int(q * 100)}': round(float(v.quantile(q)), 3) for q in KVANTILER}}
        if len(g) >= MIN_BOLAG:
            ut['bransch'][sni2] = rad
    os.makedirs(os.path.dirname(UT), exist_ok=True)
    with open(UT, 'w', encoding='utf-8') as f:
        json.dump(ut, f, ensure_ascii=False, indent=1)
    print('bolag med bransch', len(d), 'branscher', len(ut['bransch']))
    for s in ('41', '43', '56', '62', '68'):
        b = ut['bransch'].get(s, {})
        print(s, b.get('bolag'), 'soliditet', b.get('soliditet', {}).get('p50'), 'kundfordr dagar',
              b.get('kundfordr_dagar', {}).get('p50'), b.get('kundfordr_dagar', {}).get('p90'))


if __name__ == '__main__':
    main()
