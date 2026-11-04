"""Facit för Konrads bedömningar: prövar varje bedömningsregel mot vad som faktiskt hände med bolagen.

Utfall: konkurs inom två år efter bokslutsdagen (ur Bolagsverkets registerfil).
Regeln prövas på två skilda perioder: bokslut 2020–2021 (lära) och 2022–2023 (pröva).
En regel "håller" bara om den slår ut minst 2 gånger basfrekvensen i BÅDA perioderna och har minst 100 träffar i varje.
Så undviker vi regler som bara råkade stämma en gång.

Användning: python facit_bedomningar.py [datakatalog] [ut.json]
Ut: data/facit/bedomningar.json – läses av Konrad (olleno/bokforing-plattform) som belägg i bokslutsflaggorna.
Inga organisationsnummer skrivs ut, bara antal och andelar.
"""
import glob
import json
import os
import sys
from datetime import date

import pandas as pd

KAT = sys.argv[1] if len(sys.argv) > 1 else 'data'
UT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(KAT, 'facit', 'bedomningar.json')
DAGAR = 730
MIN_TRAFFAR = 100
MIN_GANGER = 2.0

KOL = ['orgnr', 'bokslut', 'Nettoomsattning', 'AretsResultat', 'AretsResultat_f', 'Tillgangar', 'EgetKapital',
       'EgetKapital_f', 'KassaBank', 'KortfristigaSkulder', 'Kundfordringar', 'Aktiekapital', 'Agartillskott',
       'revisor', 'kontrollbalans', 'fortsatt_drift', 'txt_rekonstruktion', 'txt_personligt_ansvar',
       # version 3 (noterna) – används när data/ar3 finns
       'osakerhet_drift', 'revisor_modifierad', 'NedskrivningarAret', 'Uppskrivningsfond',
       'InventarierVerktygInstallationerAnskaffningsvarden',
       'InventarierVerktygInstallationerForandringAvskrivningarAretsAvskrivningar']


def las_ar(kat):
    # Version 3 när den är hämtad (minst 500 delar), annars version 2.
    filer = sorted(glob.glob(os.path.join(kat, 'ar3', '*.csv.gz')))
    if len(filer) < 500:
        filer = sorted(glob.glob(os.path.join(kat, 'ar2', '*.csv.gz')))
    df = pd.concat([pd.read_csv(f, usecols=lambda c: c in KOL, dtype={'orgnr': str}) for f in filer])
    df = df.drop_duplicates(['orgnr', 'bokslut'])
    df['bokslut'] = pd.to_datetime(df['bokslut'], errors='coerce')
    return df


def las_konkurser(kat):
    st = pd.read_csv(os.path.join(kat, 'status_ab.csv.gz'), sep=';', dtype=str)
    pag = st['pagande'].fillna('')
    avslutad = st['avregorsak'] == 'KKAV'
    pagaende = pag.str.extract(r'\|KK[^$|]*\$(\d{4}-\d{2}-\d{2})')[0]
    st['kkdat'] = pd.to_datetime(st['avregdatum'].where(avslutad, pagaende), errors='coerce')
    return st.loc[st['kkdat'].notna(), ['orgnr', 'kkdat']].drop_duplicates('orgnr')


def regler(d):
    """Varje regel: (id, beskrivning på vanlig svenska, lagrum eller grund, mask)."""
    ek, ak = d['EgetKapital'], d['Aktiekapital']
    upplyst = (d['kontrollbalans'] == 1)
    oms = d['Nettoomsattning'].where(d['Nettoomsattning'] > 100_000)
    ut = [
        ('negativt_ek_utan_upplysning', 'Negativt eget kapital, men kapitalbristen nämns inte i årsredovisningen',
         'ABL 25 kap. 13 §; ÅRL 6 kap. 1 §', (ek < 0) & ~upplyst),
        ('negativt_ek_med_upplysning', 'Negativt eget kapital, och kontrollbalansräkning nämns',
         'ABL 25 kap. 13 §', (ek < 0) & upplyst),
        ('ek_under_halva_ak', 'Eget kapital över noll men under halva aktiekapitalet',
         'ABL 25 kap. 13 § (ungefärlig: justerat eget kapital saknas i datan)', (ek >= 0) & (ek < 0.5 * ak)),
        ('forlust_tva_ar', 'Förlust två år i rad', 'Bedömning av fortsatt drift (ÅRL 2 kap. 4 §)',
         (d['AretsResultat'] < 0) & (d['AretsResultat_f'] < 0)),
        ('ek_sjunkit_halften', 'Eget kapital har mer än halverats på ett år', 'Bedömning av fortsatt drift',
         (d['EgetKapital_f'] > 0) & (ek < 0.5 * d['EgetKapital_f'])),
        ('kassa_under_5pct_kortfr', 'Kassa och bank under 5 % av de kortfristiga skulderna',
         'Bedömning av fortsatt drift', (d['KortfristigaSkulder'] > 0) & (d['KassaBank'] < 0.05 * d['KortfristigaSkulder'])),
        ('kundfordr_over_halva_oms', 'Kundfordringar över halva årets omsättning (osäkra fordringar?)',
         'K2 (BFNAR 2016:10) värdering av fordringar', d['Kundfordringar'] > 0.5 * oms),
        ('agartillskott', 'Ägartillskott under året', 'Tecken på kapitalbehov', d['Agartillskott'] > 0),
        ('rekonstruktion_i_text', 'Rekonstruktion eller ackord nämns i texten', 'Lag (2022:964) om företagsrekonstruktion',
         d['txt_rekonstruktion'] > 0),
    ]
    if 'osakerhet_drift' in d:
        anskaffn = d['InventarierVerktygInstallationerAnskaffningsvarden']
        avskr = d['InventarierVerktygInstallationerForandringAvskrivningarAretsAvskrivningar'].abs()
        ut += [
            ('osakerhet_drift', 'Väsentlig osäkerhet om fortsatt drift upplyst', 'ÅRL 2 kap. 4 §; ISA 570',
             d['osakerhet_drift'] == 1),
            ('revisor_modifierad', 'Revisorn har reservation, avstyrkande eller avstår från uttalande',
             'Revisionslagen (1999:1079) 9 kap.', d['revisor_modifierad'] == 1),
            ('nedskrivning_i_aret', 'Nedskrivningar gjorda under året', 'ÅRL 4 kap. 5 §', d['NedskrivningarAret'] > 0),
            ('uppskrivningsfond', 'Bolaget har en uppskrivningsfond', 'ÅRL 4 kap. 6 §', d['Uppskrivningsfond'] > 0),
            ('lang_avskrivningstid_inventarier', 'Inventarier skrivs av på mer än 10 år (anskaffning / årets avskrivning)',
             'K2 (BFNAR 2016:10) avskrivning enligt plan', (avskr > 0) & (anskaffn / avskr > 10)),
        ]
    return ut


def provperiod(d, fran, till):
    p = d[(d['bokslut'] >= fran) & (d['bokslut'] <= till)]
    bas = p['utfall'].mean()
    rad = {'arsredovisningar': int(len(p)), 'basfrekvens': round(float(bas), 5), 'regler': {}}
    for rid, _, _, m in regler(p):
        m = m.fillna(False)
        n = int(m.sum())
        f = float(p.loc[m, 'utfall'].mean()) if n else None
        rad['regler'][rid] = {'traffar': n, 'konkurs_inom_2_ar': round(f, 5) if f is not None else None,
                              'ganger_basfrekvensen': round(f / bas, 2) if f is not None and bas else None}
    return rad


def main():
    d = las_ar(KAT).merge(las_konkurser(KAT), on='orgnr', how='left')
    d['utfall'] = (d['kkdat'] > d['bokslut']) & (d['kkdat'] <= d['bokslut'] + pd.Timedelta(days=DAGAR))
    lara = provperiod(d, '2020-01-01', '2021-12-31')
    prova = provperiod(d, '2022-01-01', '2023-12-31')
    ut = {'skapad': date.today().isoformat(), 'utfall': f'konkurs inom {DAGAR} dagar efter bokslutsdagen',
          'krav_for_att_halla': f'minst {MIN_GANGER} gånger basfrekvensen och minst {MIN_TRAFFAR} träffar i båda perioderna',
          'perioder': {'lara_2020_2021': lara, 'prova_2022_2023': prova}, 'regler': []}
    for rid, text, grund, _ in regler(d.head(1)):
        a, b = lara['regler'][rid], prova['regler'][rid]
        haller = all(x['traffar'] >= MIN_TRAFFAR and (x['ganger_basfrekvensen'] or 0) >= MIN_GANGER for x in (a, b))
        ut['regler'].append({'id': rid, 'text': text, 'grund': grund, 'haller': haller,
                             'ganger_lara': a['ganger_basfrekvensen'], 'ganger_prova': b['ganger_basfrekvensen'],
                             'traffar_prova': b['traffar'], 'konkurs_prova': b['konkurs_inom_2_ar']})
    os.makedirs(os.path.dirname(UT), exist_ok=True)
    with open(UT, 'w', encoding='utf-8') as f:
        json.dump(ut, f, ensure_ascii=False, indent=1)
    for r in ut['regler']:
        print(f"{'HÅLLER' if r['haller'] else 'nej   '} {r['ganger_lara']!s:>6} {r['ganger_prova']!s:>6} "
              f"{r['traffar_prova']:>7}  {r['text']}")
    print('basfrekvens', lara['basfrekvens'], prova['basfrekvens'])


if __name__ == '__main__':
    main()
