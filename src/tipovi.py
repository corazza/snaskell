from lekser import *
from vepar import *

import scopes
import snailast


elementarni = {T.INT, T.BOOL, T.STRINGT, T.UNITT}


class TipFunkcije(AST):
    tip: 'tip'  # return type
    parametri: 'tip*'


# TODO unificiraj sa funkcijama
class TipKonstruktora(AST):
    tip: 'tip'  # return type
    parametri: 'tip*'


class SloženiTip(AST):
    """Ovo je pojednostavljeni Data(AST)."""
    ime: 'VELIKOIME'
    argumenti: 'tip*'

    def typecheck(self, scope, unutar):
        for p in self.argumenti:
            p.typecheck(scope, unutar)
        return self


def apply_vartipa_mapping(mapiranje, tip):
    if isinstance(tip, Token):
        assert(tip ^ T.VARTIPA)
        return mapiranje[tip] if tip in mapiranje else None
    elif isinstance(tip, SloženiTip):
        argumenti = [apply_vartipa_mapping(
            mapiranje, a) for a in tip.argumenti]
        return SloženiTip(tip.ime, argumenti)
    elif tip ^ elementarni:
        return tip
    else:
        raise RuntimeError(f'neprepoznat tip {tip} za mapiranje ({mapiranje})')


def izrazunaj_vartipa_mapiranje(parametar, argument):
    if isinstance(parametar, Token) and parametar ^ T.VARTIPA:
        if (isinstance(argument, Token) and (argument ^ T.VARTIPA or argument ^ elementarni)) or argument == None:
            return {parametar: argument}
    elif isinstance(parametar, SloženiTip):
        if isinstance(argument, SloženiTip) and len(parametar.argumenti) == len(argument.argumenti):
            return izrazunaj_vartipa_mapiranje(parametar.argumenti, argument.argumenti)
        elif argument == None:
            return izrazunaj_vartipa_mapiranje(parametar.argumenti, [argument] * len(parametar.argumenti))
    elif isinstance(parametar, list) and isinstance(argument, list) and len(parametar) == len(argument):
        mapiranja = [izrazunaj_vartipa_mapiranje(
            p, a) for (p, a) in zip(parametar, argument)]
        složeno_mapiranje = {}
        for mapiranje in mapiranja:
            for (p, a) in mapiranje.items():
                # treba paziti na konzistentnost mapiranja
                if p not in složeno_mapiranje or složeno_mapiranje[p] == a or složeno_mapiranje[p] == None:
                    složeno_mapiranje[p] = a
                elif a != None:
                    raise RuntimeError(
                        f'{složeno_mapiranje} već ima ključ {p} koji se ne mapira na {None}, a vrijednost {a} nije {složeno_mapiranje[p]}')

        return složeno_mapiranje

    raise RuntimeError(
        f'ne mogu izracunati mapiranje za {parametar} i {argument}')


def tip_u_konstruktor(funkcija_tipa, konstruktor, scope, unutar):
    assert(scope[funkcija_tipa.ime] == scope[konstruktor.od])
    dtip = scope[funkcija_tipa.ime]
    ime = konstruktor.ime
    originalni_konstruktor = next(
        filter(lambda x, ime=ime: x.ime == ime, dtip.konstruktori))
    mapiranje = {p: a for (p, a) in zip(
        dtip.parametri, funkcija_tipa.argumenti)}
    parametri = [apply_vartipa_mapping(mapiranje, tip)
                 for tip in originalni_konstruktor.parametri]
    return snailast.Konstruktor(konstruktor.od, konstruktor.ime, parametri)


def kompozicija_mapiranja(iz, u):
    mapiranje = {}
    for (k, v) in iz.items():
        assert(v in u)
        mapiranje[k] = u[v]
    return mapiranje


def konstruktor_u_tip(konstruktor, argumenti, scope, unutar):
    """Vrati funkciju tipa za konstruktor kad se primijene dani argumenti."""
    tip = scope[konstruktor.od]
    funkcija_tipa = SloženiTip(tip.ime, tip.parametri)
    originalni_konstruktor = tip_u_konstruktor(
        funkcija_tipa, konstruktor, scope, unutar)
    originalni_u_dani = izrazunaj_vartipa_mapiranje(
        originalni_konstruktor.parametri, konstruktor.parametri)
    mapiranje = izrazunaj_vartipa_mapiranje(konstruktor.parametri, argumenti)
    kompozicija = kompozicija_mapiranja(originalni_u_dani, mapiranje)
    return apply_vartipa_mapping(kompozicija, funkcija_tipa)


def equiv_types(a, b, scope, unutar):
    """Checks types a and b for equality within a scope"""
    if a == None:
        return b ^ T.VARTIPA
    elif b == None:
        return a ^ T.VARTIPA
    elif a ^ elementarni or b ^ elementarni:
        return a == b
    elif a ^ T.VARTIPA and b ^ T.VARTIPA:
        return a.sadržaj == b.sadržaj
    elif isinstance(a, SloženiTip) and isinstance(b, SloženiTip):
        return all([equiv_types(aarg, barg, scope, unutar)
                    for (aarg, barg) in zip(a.argumenti, b.argumenti)])

    raise SemantičkaGreška(f'{a} i {b} nisu tipovi')