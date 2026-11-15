"""Maakt woorden/vervoegingen.json: de présent-vervoegingen van de werkwoorden
die in de woordenlijsten staan (woorden/*.txt en woorden/boek1/*.txt).

Gebruik:  pip install verbecc  &&  python3 tools/maak_vervoegingen.py
"""
import glob, json, logging, os, re

logging.disable(logging.CRITICAL)
from verbecc import CompleteConjugator

MAP = os.path.join(os.path.dirname(__file__), '..', 'woorden')
cg = CompleteConjugator(lang='fr')

# Grammaticale aanduidingen en aanvullingen die niet bij het werkwoord zelf horen
RUIS = re.compile(r'\((?:[^)]*)\)|\+\s*inf|\+\s*subj|\bqc\b|\bqn\b')
VOORZETSELS = {'de', 'à', 'sur', 'par', 'avec', 'pour', 'en'}
PERSONEN = ['je', 'tu', 'il', 'nous', 'vous', 'ils']
WEDERKEREND = {'je': ('me', "m'"), 'tu': ('te', "t'"), 'il': ('se', "s'"),
               'nous': ('nous', 'nous'), 'vous': ('vous', 'vous'), 'ils': ('se', "s'")}

cache = {}

def presens(infinitief):
    """Geeft {persoon: [vormen zonder onderwerp]} en of 'je' elideert, of None."""
    if infinitief in cache:
        return cache[infinitief]
    resultaat = None
    try:
        data = json.loads(cg.conjugate(infinitief).to_json())
        if not data['verb'].get('predicted'):
            vormen, elisie = {}, False
            for regel in data['moods']['indicatif']['présent']:
                p = regel['pr']
                if p in PERSONEN:
                    lijst = []
                    for c in regel['c']:
                        if p == 'je' and c.startswith("j'"):
                            elisie = True
                            lijst.append(c[2:])
                        else:
                            lijst.append(c.split(' ', 1)[1])
                    vormen[p] = lijst
            if all(p in vormen for p in PERSONEN):
                resultaat = (vormen, elisie)
    except Exception:
        pass
    cache[infinitief] = resultaat
    return resultaat


def werkwoord_uit(frans):
    """Haalt het (eventueel wederkerende) infinitief uit een regel, of None."""
    if '/' in frans or '?' in frans or '.' in frans:
        return None
    woorden = RUIS.sub(' ', frans).split()
    while woorden and woorden[-1] in VOORZETSELS:
        woorden.pop()
    wederkerend = False
    if woorden and woorden[0] == 'se':
        wederkerend, woorden = True, woorden[1:]
    elif woorden and woorden[0].startswith("s'"):
        wederkerend, woorden = True, [woorden[0][2:]] + woorden[1:]
    if len(woorden) != 1 or not re.fullmatch(r"[a-zàâçéèêëîïôûùüÿœ]+(er|ir|re|oir)", woorden[0]):
        return None
    return woorden[0], wederkerend


def werkwoord_uit_inf(frans):
    """Voor regels als 'écoutez (inf écouter)': geeft (inf, wederkerend, vorm) of None.
    Voltooide deelwoorden (met '/') en vragen worden overgeslagen."""
    m = re.search(r'\(inf ([^)]+)\)', frans)
    if not m:
        return None
    vorm = frans[:m.start()].strip()
    if not vorm or '/' in vorm or '?' in vorm or '.' in vorm:
        return None
    ww = werkwoord_uit(m.group(1).strip())
    if not ww:
        return None
    inf, wederkerend = ww
    if re.search(r'-vous\b', vorm):      # entraînez-vous -> s'entraîner
        wederkerend = True
    return inf, wederkerend, vorm


def maak_item(inf, wederkerend, nl):
    res = presens(inf)
    if not res:
        return None
    vormen, elisie = res
    vormen = {p: list(v) for p, v in vormen.items()}
    if wederkerend:
        for p in PERSONEN:
            vol, kort = WEDERKEREND[p]
            vormen[p] = [kort + v if elisie and kort != vol else vol + ' ' + v for v in vormen[p]]
        elisie = False  # 'je me...' / 'je m'...' : onderwerp elideert niet
        weergave = ('se ' if inf[0] not in 'aeiouéèêh' else "s'") + inf
    else:
        weergave = inf
    return {'inf': weergave, 'nl': nl, 'je': "j'" if elisie else 'je', 'v': vormen}


uitvoer = {}
bestanden = sorted(glob.glob(os.path.join(MAP, '*.txt'))) + sorted(glob.glob(os.path.join(MAP, 'boek1', '*.txt')))
for pad in bestanden:
    regels = [[d.strip() for d in r.split(' - ', 1)]
              for r in open(pad, encoding='utf-8') if ' - ' in r]
    lijst, gezien = [], set()
    # Eerst de gewone infinitieven, daarna (alleen Boek 1) vervoegde vormen met "(inf ...)"
    for frans, nl in regels:
        ww = werkwoord_uit(frans)
        item = ww and maak_item(ww[0], ww[1], nl)
        if item and item['inf'] not in gezien:
            gezien.add(item['inf'])
            lijst.append(item)
    if os.sep + 'boek1' + os.sep in pad:
        for frans, nl in regels:
            ww = werkwoord_uit_inf(frans)
            item = ww and maak_item(ww[0], ww[1], f'{nl} ({ww[2]})')
            if item and item['inf'] not in gezien:
                gezien.add(item['inf'])
                lijst.append(item)
    uitvoer[os.path.relpath(pad, os.path.join(MAP, '..')).replace(os.sep, '/')] = lijst

with open(os.path.join(MAP, 'vervoegingen.json'), 'w', encoding='utf-8') as f:
    json.dump(uitvoer, f, ensure_ascii=False, separators=(',', ':'))
print(sum(len(v) for v in uitvoer.values()), 'werkwoorden')
