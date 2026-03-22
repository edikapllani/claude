# METAR Weather Reader

A Flask web application that fetches live METAR weather reports for any airport in the world and decodes them into plain, readable English — no aviation knowledge required.

**What is a METAR?**
METAR (Meteorological Aerodrome Report) is the global standard format for routine weather observations at airports. They look like this:

```
METAR KJFK 221456Z 27015KT 10SM FEW025 BKN060 18/10 A2992
```

This app turns that into: *"Few clouds at 2,500 ft, broken clouds at 6,000 ft. 64°F, winds from the West at 17 mph, visibility 10+ miles, pressure 29.92 inHg."*

---

## Features

- Look up any airport by its 4-letter ICAO code (e.g. `KJFK`, `EGLL`, `YSSY`)
- Displays sky conditions, temperature, dewpoint, wind, visibility, weather events, and pressure
- Shows both Imperial (°F, mph, inHg) and metric (°C, hPa) units
- Raw METAR string always shown for reference
- Graceful error messages for invalid codes or network issues

---

## Requirements

- Python 3.8 or higher
- Dependencies: Flask, requests, python-metar (all installed via `requirements.txt`)

---

## Installation

**Clone and run locally:**

```bash
git clone https://github.com/edikapllani/claude.git
cd claude
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

---

## Usage

1. Enter a 4-letter ICAO airport code in the search box
2. Press **Get Weather**
3. Read the plain-English weather report

**Example ICAO codes:**

| Code   | Airport                        |
|--------|--------------------------------|
| `KJFK` | New York JFK, USA              |
| `KLAX` | Los Angeles, USA               |
| `KHIO` | Hillsboro, Oregon, USA         |
| `EGLL` | London Heathrow, UK            |
| `EDDM` | Munich, Germany                |
| `YSSY` | Sydney, Australia              |

> **Note:** ICAO codes are 4 letters. US airports begin with `K` (e.g. `KJFK`). If you only know the 3-letter IATA code (e.g. `JFK`), prepend `K` for US airports.

---

## Data Source

Live weather data is fetched from the **FAA Aviation Weather Center** public API — no API key required:

```
https://aviationweather.gov/api/data/metar?ids={ICAO}&format=raw
```

Data is refreshed at the source every 20–60 minutes depending on the airport.

---

## Project Structure

```
├── app.py                  # Flask app: routes, METAR fetch, and decode logic
├── templates/
│   └── index.html          # UI: search form and weather report display
├── test_app.py             # Unit tests for app.py (44 tests)
├── requirements.txt        # Python dependencies
├── read_members.py         # Unrelated CSV utility (separate tool)
└── test_read_members.py    # Tests for the CSV utility
```

---

## Running Tests

The test suite uses Python's built-in `unittest` module — no extra dependencies required.

```bash
python -m unittest test_app -v
```

All 44 tests should pass in under a second:

```
----------------------------------------------------------------------
Ran 44 tests in 0.013s

OK
```

**What is tested:**

| Area | Tests | Description |
|---|---|---|
| `fetch_metar` | 4 | Valid fetch, ICAO uppercasing, empty response → error, network failure |
| `decode_sky` | 7 | Clear, few/scattered/broken/overcast layers, cumulonimbus, towering cumulus |
| `decode_wind` | 6 | Calm, not reported, variable direction (VRB), fixed direction, gusts, compass mapping |
| `decode_visibility` | 7 | All quality bands (excellent / good / reduced / very poor) and boundary values |
| `decode_phenomena` | 8 | Rain, snow, fog, thunderstorm, freezing rain, multiple simultaneous events |
| `decode_metar` | 6 | Full pipeline with real METAR strings — keys, values, and raw string preservation |
| Flask routes | 6 | GET, POST valid/invalid/empty code, network error, ICAO preserved on error |

Tests use mock METAR observations for unit tests (no network calls) and real METAR strings for integration tests.

---

## Deploying to Production

Replace the built-in Flask development server with a production WSGI server:

```bash
pip install gunicorn
gunicorn app:app
```

For cloud hosting, the app is compatible with:
- [Railway](https://railway.app) — `railway up`
- [Render](https://render.com) — connect your GitHub repo and set start command to `gunicorn app:app`
- [Fly.io](https://fly.io) — `fly launch`

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

---

## License

MIT License — see [LICENSE](LICENSE) for details.
