# DayLifePlanner MVP

Lokalna aplikacja demonstracyjna z webowym GUI przygotowana do pokazania prowadzącemu.

## Co potrafi to MVP
- dodawanie wydarzeń (uczelnia, praca, aktywność, odpoczynek, spotkanie),
- ustawianie priorytetów,
- generowanie planu dnia,
- wykrywanie konfliktów czasowych,
- uwzględnianie czasu dojazdu i minimalnej przerwy,
- podstawowe rekomendacje,
- prezentacja trzech planów subskrypcji: `base`, `premium`, `enterprise`,
- reset danych demonstracyjnych jednym kliknięciem.

## Uruchomienie
```bash
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# albo na Windows:
# .venv\Scripts\activate

pip install -r requirements.txt
python app.py
```

Aplikacja będzie dostępna pod adresem:
```text
http://127.0.0.1:5000
```

## Prezntacja
To jest **MVP demonstracyjne**, a nie pełna wersja produktu. Pokazuje główną logikę biznesową:
1. użytkownik wprowadza wydarzenia,
2. system sprawdza konflikty,
3. system uwzględnia bufor/dojazd,
4. generuje prosty plan dnia i rekomendacje.

## Naturalne kolejne kroki
- logowanie i konta użytkowników,
- baza danych SQL,
- integracja z Google Calendar / Outlook,
- mapy i realne czasy dojazdów,
- powiadomienia push,
- moduł tygodniowy,
- wersja enterprise z planowaniem spotkań międzyfirmowych.
