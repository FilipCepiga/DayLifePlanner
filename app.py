from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

from flask import Flask, render_template, request, redirect, url_for, flash

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / 'instance' / 'data.json'

app = Flask(__name__)
app.secret_key = 'daylifeplanner-demo-secret'


@dataclass
class Event:
    title: str
    category: str
    location: str
    start: str  # HH:MM
    end: str    # HH:MM
    priority: int
    notes: str = ''


DEFAULT_DATA = {
    'events': [
        {
            'title': 'Algorytmy - wykład',
            'category': 'Uczelnia',
            'location': 'AGH C1',
            'start': '08:00',
            'end': '09:30',
            'priority': 5,
            'notes': 'Obecność obowiązkowa'
        },
        {
            'title': 'Praca zdalna',
            'category': 'Praca',
            'location': 'Dom',
            'start': '10:30',
            'end': '14:00',
            'priority': 5,
            'notes': 'Daily + zadania projektowe'
        },
        {
            'title': 'Siłownia',
            'category': 'Aktywność',
            'location': 'MyFitness',
            'start': '18:00',
            'end': '19:15',
            'priority': 3,
            'notes': 'FBW'
        }
    ],
    'settings': {
        'default_commute_minutes': 20,
        'rest_buffer_minutes': 15,
        'work_start': '07:00',
        'work_end': '22:00',
        'subscription': 'premium'
    }
}


def ensure_data_file() -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        save_data(DEFAULT_DATA)



def load_data() -> Dict[str, Any]:
    ensure_data_file()
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)



def save_data(data: Dict[str, Any]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)



def parse_time(value: str) -> datetime:
    return datetime.strptime(value, '%H:%M')



def minutes_between(start: str, end: str) -> int:
    return int((parse_time(end) - parse_time(start)).total_seconds() // 60)



def sort_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(events, key=lambda e: (e['start'], -int(e['priority'])))



def analyze_schedule(events: List[Dict[str, Any]], settings: Dict[str, Any]) -> Dict[str, Any]:
    events_sorted = sort_events(events)
    commute = int(settings.get('default_commute_minutes', 20))
    rest_buffer = int(settings.get('rest_buffer_minutes', 15))

    conflicts = []
    recommendations = []
    enriched = []
    total_load_minutes = 0

    for i, event in enumerate(events_sorted):
        duration = minutes_between(event['start'], event['end'])
        total_load_minutes += max(duration, 0)
        current = dict(event)
        current['duration_minutes'] = duration
        current['travel_needed_before'] = 0
        current['status'] = 'OK'

        if i > 0:
            prev = events_sorted[i - 1]
            prev_end = parse_time(prev['end'])
            current_start = parse_time(event['start'])
            gap = int((current_start - prev_end).total_seconds() // 60)

            changed_location = prev['location'].strip().lower() != event['location'].strip().lower()
            needed_gap = commute if changed_location else rest_buffer
            current['travel_needed_before'] = needed_gap

            if gap < 0:
                current['status'] = 'Konflikt'
                conflicts.append({
                    'type': 'overlap',
                    'message': f"'{prev['title']}' nakłada się z '{event['title']}' o {-gap} min.",
                })
            elif gap < needed_gap:
                current['status'] = 'Za mało czasu'
                reason = 'dojazd' if changed_location else 'przerwa'
                conflicts.append({
                    'type': 'buffer',
                    'message': (
                        f"Pomiędzy '{prev['title']}' a '{event['title']}' jest tylko {gap} min, "
                        f"a potrzeba {needed_gap} min na {reason}."
                    ),
                })

        enriched.append(current)

    if total_load_minutes > 10 * 60:
        recommendations.append('Plan jest bardzo intensywny — warto ograniczyć liczbę zadań lub zwiększyć przerwy.')
    elif total_load_minutes < 4 * 60:
        recommendations.append('Plan jest lekki — można dodać krótkie zadanie rozwojowe lub aktywność dodatkową.')

    high_priority = [e for e in events_sorted if int(e['priority']) >= 4]
    if not high_priority:
        recommendations.append('Brakuje zadań o wysokim priorytecie — ustaw priorytety, aby planowanie było trafniejsze.')

    if conflicts:
        recommendations.append('Wykryto problemy w harmonogramie — przesuń wydarzenia albo zwiększ bufor na dojazd/przerwę.')
    else:
        recommendations.append('Plan wygląda logicznie i nie zawiera konfliktów czasowych.')

    if any(e['category'] == 'Praca' for e in events_sorted) and any(e['category'] == 'Uczelnia' for e in events_sorted):
        recommendations.append('Łączysz uczelnię i pracę — rozważ zablokowanie stałych okien na odpoczynek i posiłki.')

    free_slots = compute_free_slots(events_sorted, settings)

    return {
        'events': enriched,
        'conflicts': conflicts,
        'recommendations': recommendations,
        'free_slots': free_slots,
        'total_load_hours': round(total_load_minutes / 60, 2),
    }



def compute_free_slots(events: List[Dict[str, Any]], settings: Dict[str, Any]) -> List[str]:
    if not events:
        return [f"Cały dzień wolny w zakresie {settings.get('work_start', '07:00')}–{settings.get('work_end', '22:00')}"]

    slots = []
    start_day = parse_time(settings.get('work_start', '07:00'))
    end_day = parse_time(settings.get('work_end', '22:00'))

    first_start = parse_time(events[0]['start'])
    if first_start > start_day:
        slots.append(f"{start_day.strftime('%H:%M')}–{first_start.strftime('%H:%M')}")

    for i in range(len(events) - 1):
        end_current = parse_time(events[i]['end'])
        start_next = parse_time(events[i + 1]['start'])
        if start_next > end_current:
            slots.append(f"{end_current.strftime('%H:%M')}–{start_next.strftime('%H:%M')}")

    last_end = parse_time(events[-1]['end'])
    if last_end < end_day:
        slots.append(f"{last_end.strftime('%H:%M')}–{end_day.strftime('%H:%M')}")

    return slots[:5]


@app.route('/')
def index():
    data = load_data()
    analysis = analyze_schedule(data['events'], data['settings'])
    return render_template('index.html', data=data, analysis=analysis)


@app.route('/add-event', methods=['POST'])
def add_event():
    data = load_data()
    try:
        event = Event(
            title=request.form['title'].strip(),
            category=request.form['category'].strip(),
            location=request.form['location'].strip(),
            start=request.form['start'],
            end=request.form['end'],
            priority=int(request.form['priority']),
            notes=request.form.get('notes', '').strip(),
        )

        if parse_time(event.end) <= parse_time(event.start):
            flash('Godzina zakończenia musi być późniejsza niż rozpoczęcia.', 'error')
            return redirect(url_for('index'))

        data['events'].append(asdict(event))
        save_data(data)
        flash('Dodano wydarzenie.', 'success')
    except Exception as exc:
        flash(f'Nie udało się dodać wydarzenia: {exc}', 'error')
    return redirect(url_for('index'))


@app.route('/delete-event/<int:event_id>', methods=['POST'])
def delete_event(event_id: int):
    data = load_data()
    if 0 <= event_id < len(data['events']):
        removed = data['events'].pop(event_id)
        save_data(data)
        flash(f"Usunięto: {removed['title']}", 'success')
    else:
        flash('Nie znaleziono wydarzenia.', 'error')
    return redirect(url_for('index'))


@app.route('/settings', methods=['POST'])
def update_settings():
    data = load_data()
    try:
        data['settings']['default_commute_minutes'] = int(request.form['default_commute_minutes'])
        data['settings']['rest_buffer_minutes'] = int(request.form['rest_buffer_minutes'])
        data['settings']['work_start'] = request.form['work_start']
        data['settings']['work_end'] = request.form['work_end']
        data['settings']['subscription'] = request.form['subscription']
        save_data(data)
        flash('Zapisano ustawienia.', 'success')
    except Exception as exc:
        flash(f'Błąd zapisu ustawień: {exc}', 'error')
    return redirect(url_for('index'))


@app.route('/reset-demo', methods=['POST'])
def reset_demo():
    save_data(DEFAULT_DATA)
    flash('Przywrócono dane demonstracyjne.', 'success')
    return redirect(url_for('index'))


if __name__ == '__main__':
    ensure_data_file()
    app.run(debug=True, host='127.0.0.1', port=5000)
