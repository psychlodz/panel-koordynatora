PlanPracy - aplikacja Windows

Architektura KOMPAS:
- Oracle / Eskulap = System of Record.
  Przechowuje dane pacjenta i dane medyczne.
- KOMPAS = System of Coordination.
  Zarzadza programami, sciezkami, epizodami i zadaniami.
- KOMPAS nie utrzymuje lokalnej kopii danych osobowych pacjenta.
  Aktualne dane sa pobierane z Oracle przez Eskulap Gateway.

1. Edytuj config.ini:
   - user
   - password
   - dsn
   - default_jo_id

2. Zbuduj program:
   build_exe.bat

   Alternatywnie:
   powershell -ExecutionPolicy Bypass -File build_exe.ps1

3. Gotowy program:
   dist\PlanPracy\PlanPracy.exe

Plan Pracy v1.0.1 - zmiany:
- zachowane przedzialy godzin: 07:00-10:00, 10:00-13:00, 13:00-16:00, 16:00-19:00, 19:00-22:00;
- w komorkach widac tylko nazwiska, godziny pozostaja w popupie szczegolow po kliknieciu komorki;
- legenda / szybki filtr zostala przeniesiona do lewego panelu;
- lista pracownikow ma wyszukiwarke i przewijanie, wiec nie poszerza okna aplikacji;
- brak zaznaczenia pracownikow oznacza widok wszystkich osob;
- zaznaczenie jednej lub wielu osob filtruje harmonogram;
- kolory pracownikow sa stabilne na podstawie nazwiska;
- weekendy, swieta i dzisiejszy dzien sa oznaczone delikatnym tlem;
- eksport do Excela pozostaje bez zmian.

Wazne:
Widok ESK_RAPORTY.V_PLAN_PRACY_KALENDARZ musi zawierac co najmniej pola:
jo_id, jo_symbol, jo_nazwa, data_dnia, pracownik, godz_od, godz_do.

Logi aplikacji:
logs\plan_pracy.log
