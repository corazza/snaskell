from inspect import Parameter
from signal import default_int_handler
from vepar import *

from lekser import *
from util import *

from snailast import *


class P(Parser):
    def start(p) -> 'Program':
        p.imef = None
        p.parametrif = None
        p.tipf = None
        p.funkcije = Memorija(redefinicija=False)
        return Program(p.naredbe(KRAJ))

    def naredbe(p, until, pojedi=False) -> 'naredba+':
        naredbe = [p.naredba()]
        while not p > until:
            naredbe.append(p.naredba())
        if pojedi:
            p >> until
        return Naredbe(naredbe)

    # TODO naredbe u dvije kategorije, one koje završavaju na end_, i one koje imaju delimiter (?)
    def naredba(p, read_delim=True) -> 'pridruživanje|printanje|grananje':
        if ime := p >= T.IME:
            poziv = p.poziv_ili_pridruživanje(ime)
            if read_delim:  # TODO izluci ovo van
                p >> T.TOČKAZ
            return poziv
        elif p >= T.PRINT:
            printanje = p.printanje()
            if read_delim:
                p >> T.TOČKAZ
            return printanje
        elif p >= T.INPUT:
            input = p.input()
            if read_delim:
                p >> T.TOČKAZ
            return input
        elif p >= T.TOINT:
            toint = p.to_int()
            if read_delim:
                p >> T.TOČKAZ
            return toint
        elif p >= T.CONCAT:
            concat = p.concat()
            if read_delim:
                p >> T.TOČKAZ
            return concat
        elif p >= T.IF:
            return p.grananje()
        elif p >= T.DEF:
            return p.funkcija()
        elif p >= T.OPERATOR:
            return p.operator()
        elif p >= T.LET:
            let = p.definiranje()
            if read_delim:
                p >> T.TOČKAZ
            return let
        elif p >= T.IMPORT:
            imp = p.imp()
            if read_delim:
                p >> T.TOČKAZ
            return imp
        elif p >= T.DATA:
            return p.definiranje_tipa()
        elif p >= T.MATCH:
            return p.match()
        elif p >> T.RETURN:
            vraćanje = p.vraćanje()
            if read_delim:
                p >> T.TOČKAZ
            return vraćanje

    def match(p) -> 'Match':
        izraz = p.izraz()
        p >> T.AS
        varijante = [p.varijanta()]
        while p >= T.ZAREZ:
            varijante.append(p.varijanta())
        p >> T.ENDMATCH
        return Match(izraz, varijante)

    def imp(p) -> 'Import':
        path = p >> T.STRING
        return Import(path)

    def varijanta(p) -> 'Varijanta':
        izraz = p.pattern()
        p >> T.SLIJEDI
        naredba = p.naredba(read_delim=False)
        return Varijanta(izraz, naredba)

    def pattern(p) -> 'Pattern':
        ime = p >> T.VELIKOIME
        if p >= T.OTV:
            imena = [p >> T.IME]
            while p >= T.ZAREZ:
                imena.append(p >> T.IME)
            p >> T.ZATV
        else:
            imena = []
        konstruktor = p.funkcije[ime]
        return Pattern(konstruktor, imena)

    def poziv_ili_pridruživanje(p, ime) -> 'Poziv|Pridruživanje':
        if p >= T.PRIDRUŽI:
            izraz = p.izraz()
            return Pridruživanje(ime, izraz)
        else:
            if ime in p.funkcije:
                funkcija = p.funkcije[ime]
                parametri = funkcija.parametri
            elif ime == p.imef:
                funkcija = nenavedeno
                parametri = p.parametrif
            else:
                raise SintaksnaGreška(f'nepoznata funkcija {ime}')
            argumenti = p.argumenti(parametri)
            return Poziv(funkcija, argumenti)

    def grananje(p) -> 'Grananje':
        provjera = p.izraz()
        p >> T.THEN
        ako = p.naredbe({T.ELSE, T.ENDIF})
        if p >= T.ENDIF:
            return Grananje(provjera, ako, nenavedeno)
        elif p >= T.ELSE:
            inače = p.naredbe(T.ENDIF, pojedi=True)
            return Grananje(provjera, ako, inače)
        else:
            exit("Sintaktička greška")

    def printanje(p) -> 'Ispis':
        if newline := p >= T.NEWLINE:
            return Ispis(newline)
        else:
            izraz = p.izraz()
            return Ispis(izraz)

    def definiranje(p) -> 'Definiranje':
        tipizirano = p.tipizirano()
        p >> T.PRIDRUŽI
        izraz = p.izraz()
        return Definiranje(tipizirano.ime, tipizirano.tip, izraz)

    def input(p) -> 'Unos':
        ime = p >> T.IME
        return Unos(ime)

    def to_int(p) -> 'ToInt':
        iz = p >> T.IME
        u = p >> T.IME
        return ToInt(iz, u)

    def concat(p) -> 'Concat':
        prvi = p >> T.IME
        drugi = p >> T.IME
        treci = p >> T.IME
        return Concat(prvi, drugi, treci)

    def definiranje_tipa(p) -> 'Data':
        ime = p >> T.VELIKOIME
        if p >> T.MANJE:
            parametri = p.parametri_tipa()
            p >> T.VECE
        else:
            parametri = []
        p >> T.AS
        konstruktori = p.konstruktori(ime)
        p >> T.ENDDATA
        return Data(ime, parametri, konstruktori)

    def parametri_tipa(p) -> '(VARTIPA#)+':
        parametri = [p >> T.VARTIPA]
        while p >= T.ZAREZ:
            parametri.append(p >= T.VARTIPA)
        return parametri

    def konstruktori(p, ime) -> 'Konstruktor+':
        konstruktori_tipa = [p.konstruktor(ime)]
        while p >= T.ZAREZ:
            konstruktori_tipa.append(p.konstruktor(ime))
        return konstruktori_tipa

    def konstruktor(p, od) -> 'Konstruktor':
        ime = p >> T.VELIKOIME
        if p >= T.OTV:
            članovi = p.članovi_konstruktora()
            p >> T.ZATV
        else:
            članovi = []
        konstruktor = Konstruktor(od, ime, članovi)
        p.funkcije[ime] = konstruktor
        return konstruktor

    def članovi_konstruktora(p) -> 'tip+':
        tipovi = [p.tip()]
        while p >= T.ZAREZ:  # TODO koristi ili_samo
            tipovi.append(p.tip())
        return tipovi

    def tip(p) -> 'tip|VARTIPA#|SloženiTip':
        if elementarni := p >= {T.INT, T.BOOLT, T.STRINGT, T.UNITT}:
            return elementarni
        elif vartipa := p >= T.VARTIPA:
            return vartipa
        else:
            # TODO apstrahiraj pattern (npr. i u parametri_tipa)
            ime = p >> T.VELIKOIME
            if p >= T.MANJE:
                parametri = [p.tip()]
                while p >= T.ZAREZ:
                    parametri.append(p.tip())
                p >> T.VECE
            else:
                parametri = []
            return tipovi.SloženiTip(ime, parametri)

    def funkcija(p) -> 'Funkcija':
        staro_imef = p.imef
        stari_parametrif = p.parametrif
        stari_tipf = p.tipf
        memo_flag = 0
        # TODO istražiti: memorija u parseru je loša ideja, može li se ovo preseliti drugdje?

        if p >= T.MEMO:
            memo_flag = 1

        ime = p >> T.IME
        p.imef = ime

        parametri = p.parametri()
        p.parametrif = parametri
        p >> T.FTYPE
        tip = p.tip()
        p.tipf = tip
        p >> T.AS
        tijelo = p.naredbe(T.ENDDEF, pojedi=True)
        fja = Funkcija(ime, tip, parametri, tijelo, memo_flag)
        p.funkcije[ime] = fja

        p.imef = staro_imef
        p.parametrif = stari_parametrif
        p.tipf = stari_tipf

        return fja

    def operator(p) -> 'Funkcija':
        staro_imef = p.imef
        stari_parametrif = p.parametrif
        stari_tipf = p.tipf

        ime = p >> lekser.korisnicki_operatori
        p.imef = ime

        if ime ^ lekser.unarni_korisnicki_operatori:
            parametri = p.parametri_tocno(1)
        elif ime ^ lekser.binarni_korisnicki_operatori:
            parametri = p.parametri_tocno(2)
        elif ime ^ lekser.ternarni_korisnicki_operatori:
            parametri = p.parametri_tocno(3)
        else:
            raise SintaksnaGreška('mora biti jedan ili dva parametra')

        p.parametrif = parametri
        p >> T.FTYPE
        tip = p.tip()
        p.tipf = tip
        p >> T.AS
        tijelo = p.naredbe(T.ENDOPERATOR, pojedi=True)
        fja = Funkcija(ime, tip, parametri, tijelo, False)
        p.funkcije[ime] = fja

        p.imef = staro_imef
        p.parametrif = stari_parametrif
        p.tipf = stari_tipf

        return fja

    def vraćanje(p):
        return Vraćanje(p.izraz())

    def tipizirano(p) -> 'Tipizirano':
        ime = p >> T.IME
        p >> T.OFTYPE
        tip = p.tip()
        return Tipizirano(ime, tip)

    def izraz(p):
        stablo = p.član()
        while op := p >= {T.PLUS, T.MINUS, T.MANJE, T.VECE, T.JMANJE,
                          T.JVECE, T.JEDNAKO, T.NEJEDNAKO, T.LOGI,
                          T.LOGILI, T.NEGACIJA, T.DUPLIPLUS, T.PERCENTAGE}\
                .union(unarni_korisnicki_operatori):
            desni = p.član()
            stablo = Infix(op, stablo, desni)
        return stablo

    def član(p) -> 'faktor|Infix':
        stablo = p.faktor()
        while op := p >= {T.PUTA, T.DIV, T.LOGI}.union(ternarni_korisnicki_operatori):
            if not op ^ ternarni_korisnicki_operatori:
                desni = p.faktor()
                stablo = Infix(op, stablo, desni)
            else:
                lijevi = p.faktor()
                p >> T.TERNARNI_SEP
                desni = p.faktor()
                return Ternarni(op, stablo, lijevi, desni)
        return stablo

    def faktor(p):
        if p >= T.OTV:
            if p >= T.ZATV:
                # TODO FIXME
                return UnitValue()
            else:
                izraz = p.izraz()
                p >> T.ZATV
                return izraz
        elif minus := p >= T.MINUS:
            return Infix(minus, nenavedeno, p.faktor())
        elif konjeksp := p >= T.DOLAR:
            return Infix(konjeksp, nenavedeno, p.faktor())
        elif negacija := p >= T.NEGACIJA:
            return Infix(negacija, nenavedeno, p.faktor())
        elif p >= T.TRUE:
            return BoolovskaVrijednost(True)
        elif p >= T.FALSE:
            return BoolovskaVrijednost(False)
        elif broj := p >= T.BROJ:
            return broj
        elif string := p >= T.STRING:
            return string
        elif unit := p >= T.UNIT:
            return unit
        else:
            ime = p >> {T.IME, T.VELIKOIME}
            return p.možda_poziv(ime)

    def možda_poziv(p, ime) -> 'Poziv|IME|VELIKOIME':
        # (T.VELIKOIME treba posebnu shemu)
        if ime in p.funkcije and ime ^ T.IME:
            funkcija = p.funkcije[ime]
            return Poziv(funkcija, p.argumenti(funkcija.parametri))
        elif ime in p.funkcije and ime ^ T.VELIKOIME:
            konstruktor = p.funkcije[ime]
            if len(konstruktor.parametri) > 0:
                return Poziv(konstruktor, p.argumenti(konstruktor.parametri))
            else:
                return Poziv(konstruktor, [])
        elif ime == p.imef:
            return Poziv(nenavedeno, p.argumenti(p.parametrif))
        else:
            return ime

    def parametri(p) -> 'tipizirano*':
        p >> T.OTV
        if p >= T.ZATV:
            return []
        parametri = [p.tipizirano()]
        while p >= T.ZAREZ:
            parametri.append(p.tipizirano())
        p >> T.ZATV
        return parametri

    def parametri_tocno(p, n) -> 'tipizirano*':
        p >> T.OTV
        parametri = []
        for i in range(n-1):
            parametri.append(p.tipizirano())
            p >> T.ZAREZ
        parametri.append(p.tipizirano())
        p >> T.ZATV
        return parametri

    def argumenti(p, parametri):
        broj_parametara = len(parametri)
        izrazi = []
        p >> T.OTV
        for i in range(broj_parametara):
            izrazi.append(p.izraz())
            if i < broj_parametara - 1:
                p >> T.ZAREZ
        p >> T.ZATV
        return izrazi
