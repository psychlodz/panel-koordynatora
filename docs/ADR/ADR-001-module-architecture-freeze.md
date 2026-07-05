# ADR-001: Zamrożenie architektury modułów KOMPAS

- Status: **Accepted**
- Data decyzji: 2026-07-05
- Zakres: KOMPAS 1.0

## Kontekst

KOMPAS rozwija się iteracyjnie, a kolejne funkcje obejmują pracę
koordynatora, konfigurację procesów, integrację z Eskulapem oraz
administrację. Bez stabilnych granic każda nowa funkcja mogłaby prowadzić
do powstawania kolejnego kafelka, osobnego okna konfiguracyjnego lub
bezpośredniego połączenia UI ze źródłem danych.

Potrzebna jest jedna zatwierdzona struktura, która:

- ogranicza rozproszenie interfejsu;
- wskazuje właściciela każdej odpowiedzialności;
- utrzymuje Oracle jako źródło danych pacjenta i danych medycznych;
- skupia konfigurację w jednym obszarze administracyjnym;
- stanowi podstawę planowania kolejnych sprintów.

## Decyzja

**Zamrożono strukturę modułów KOMPAS 1.0.**

Zatwierdzona struktura:

```text
KOMPAS
├── Dashboard
├── Pacjenci / Epizody
├── Harmonogram
├── Programy
├── Ścieżki
├── Administracja
│   └── Ustawienia systemu
├── Gateway Eskulap
└── Pomoc
```

Przyjęto następujące reguły:

1. Nowy moduł może powstać tylko wtedy, gdy nie mieści się logicznie
   w żadnym z zatwierdzonych modułów.
2. Wszystkie funkcje konfiguracyjne i administracyjne trafiają do
   „Administracja → Ustawienia systemu”.
3. Oracle/Eskulap pozostaje źródłem danych pacjenta i danych medycznych.
4. PostgreSQL przechowuje wyłącznie dane procesowe oraz konfigurację
   KOMPAS.
5. UI nie odwołuje się bezpośrednio do Oracle. Dane Eskulapa są dostępne
   przez `EskulapGateway`.
6. Odstępstwo od zamrożonej struktury wymaga nowego ADR.

## Konsekwencje

### Pozytywne

- launcher i nawigacja pozostają przewidywalne;
- ustawienia nie rozpraszają się pomiędzy niezależnymi oknami;
- integracja Oracle ma jedno kontrolowane wejście;
- odpowiedzialności modułów są czytelne dla kolejnych sprintów;
- łatwiej ocenić, gdzie umieścić nową funkcję.

### Ograniczenia

- nie każda większa funkcja otrzyma osobny moduł lub kafelek;
- istniejące funkcje mogą wymagać przeniesienia do właściwego kontenera;
- rozszerzenie listy modułów wymaga świadomej decyzji architektonicznej
  zapisanej w ADR.

## Odrzucone alternatywy

### Osobny moduł dla każdego obszaru konfiguracji

Odrzucono z powodu rozproszenia Administracji i rosnącej liczby okien
głównych.

### Bezpośrednie używanie repozytoriów Oracle przez UI

Odrzucono, ponieważ ujawnia szczegóły Eskulapa w warstwie prezentacji
i utrudnia kontrolę zasady tylko do odczytu.

### Przechowywanie danych pacjenta w PostgreSQL

Odrzucono. Oracle/Eskulap pozostaje systemem źródłowym, a KOMPAS
przechowuje wyłącznie techniczny identyfikator pacjenta oraz dane procesu.

## Dokument referencyjny

Szczegółowe granice modułów opisuje
`docs/ARCHITECTURE/KOMPAS_MODULE_ARCHITECTURE.md`.

