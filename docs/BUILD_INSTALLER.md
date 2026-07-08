# Budowanie instalatora Windows KOMPAS

Ten dokument opisuje przygotowanie instalatora Windows przy użyciu
PyInstaller oraz Inno Setup.

## Wymagania

- Windows x64.
- Python zainstalowany w `PATH`.
- Zależności projektu z `requirements.txt`.
- Inno Setup 6.
- Poprawny `config.ini` developerski potrzebny do walidacji builda.

## 1. Zbudowanie aplikacji EXE

Uruchom:

```text
build_exe.bat
```

Skrypt:

1. czyści `build/` i `dist/`;
2. uruchamia PyInstaller z `plan_pracy.spec`;
3. tworzy katalog:

```text
release/KOMPAS_0.9.0/
```

4. zapisuje:

```text
release/KOMPAS_0.9.0/VERSION.txt
```

Do wydania trafia `config.example.ini`, nie produkcyjny `config.ini`.

## 2. Instalacja Inno Setup

1. Pobierz Inno Setup 6 z oficjalnej strony projektu.
2. Zainstaluj narzędzie na maszynie buildowej.
3. Upewnij się, że dostępny jest kompilator:

```text
ISCC.exe
```

Skrypt `build_installer.bat` szuka go:

- w `PATH`;
- w `C:\Program Files (x86)\Inno Setup 6\ISCC.exe`;
- w `C:\Program Files\Inno Setup 6\ISCC.exe`.

## 3. Zbudowanie instalatora

Najprościej uruchomić:

```text
build_installer.bat
```

Skrypt:

1. uruchamia `build_exe.bat`;
2. sprawdza, czy istnieje:

```text
release/KOMPAS_0.9.0/KOMPAS.exe
```

3. sprawdza `VERSION.txt` i `config.example.ini`;
4. uruchamia:

```text
ISCC installer/KOMPAS.iss
```

5. zapisuje instalator w:

```text
release/installers/KOMPAS_Setup_0.9.0.exe
```

## 4. Ręczna kompilacja pliku ISS

Jeżeli chcesz uruchomić Inno Setup ręcznie:

```text
ISCC installer/KOMPAS.iss
```

Plik `installer/KOMPAS.iss` pakuje katalog:

```text
release/KOMPAS_0.9.0/
```

## 5. Sprawdzenie wersji instalatora

Wersja aplikacji jest zdefiniowana w:

```text
version.py
```

Dla wersji `0.9.0` instalator powinien mieć nazwę:

```text
KOMPAS_Setup_0.9.0.exe
```

W katalogu instalacji powinien znaleźć się plik:

```text
VERSION.txt
```

## 6. Zawartość instalatora

Instalator zawiera:

- `KOMPAS.exe`;
- pliki runtime wygenerowane przez PyInstaller;
- `config.example.ini`;
- `VERSION.txt`;
- `resources/`, w tym style QSS.

Instalator nie powinien zawierać:

- `config.ini` z hasłami;
- `kompas.db`;
- `.git/`;
- `.idea/`;
- plików tymczasowych;
- danych pacjentów;
- haseł produkcyjnych.

## 7. Test instalatora

1. Uruchom `release/installers/KOMPAS_Setup_0.9.0.exe`.
2. Zainstaluj do domyślnego katalogu:

```text
C:\Program Files\KOMPAS
```

3. Sprawdź, czy istnieją:

```text
C:\Program Files\KOMPAS\KOMPAS.exe
C:\Program Files\KOMPAS\config.ini
C:\Program Files\KOMPAS\config.example.ini
C:\Program Files\KOMPAS\VERSION.txt
```

4. Sprawdź skróty w menu Start i na pulpicie.
5. Uzupełnij hasła w `config.ini`.
6. Uruchom KOMPAS z menu Start.
