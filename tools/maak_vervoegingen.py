"""Maakt woorden/vervoegingen.json: de présent-vervoegingen van de werkwoorden
die in de woordenlijsten staan.

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


uitvoer = {}
for pad in sorted(glob.glob(os.path.join(MAP, '*.txt'))):
    lijst, gezien = [], set()
    for regel in open(pad, encoding='utf-8'):
        if ' - ' not in regel:
            continue
        frans, nl = [d.strip() for d in regel.split(' - ', 1)]
        ww = werkwoord_uit(frans)
        if not ww:
            continue
        inf, wederkerend = ww
        res = presens(inf)
        if not res:
            continue
        vormen, elisie = res
        vormen = {p: list(v) for p, v in vormen.items()}
        if wederkerend:
            for p in PERSONEN:
                vol, kort = WEDERKEREND[p]
                vormen[p] = [(kort if elisie and kort != vol else vol + ' ') + v
                             if not (elisie and kort != vol) else kort + v for v in vormen[p]]
            elisie = False  # 'je me...' / 'je m'...' : onderwerp elideert niet
            weergave = ('se ' if not inf[0] in 'aeiouéèêh' else "s'") + inf
        else:
            weergave = inf
        if weergave in gezien:
            continue
        gezien.add(weergave)
        lijst.append({'inf': weergave, 'nl': nl, 'je': "j'" if elisie else 'je', 'v': vormen})
    uitvoer['woorden/' + os.path.basename(pad)] = lijst

with open(os.path.join(MAP, 'vervoegingen.json'), 'w', encoding='utf-8') as f:
    json.dump(uitvoer, f, ensure_ascii=False, separators=(',', ':'))
print(sum(len(v) for v in uitvoer.values()), 'werkwoorden')
