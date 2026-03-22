"""
METAR Weather Reader — Flask Web Application
=============================================
Fetches live METAR reports from the FAA Aviation Weather Center and
decodes them into plain-English weather summaries for a given airport.

Data source:
    https://aviationweather.gov/api/data/metar

Dependencies:
    Flask, requests, metar (python-metar)

Usage:
    python app.py
    Then open http://127.0.0.1:5000 in your browser.
"""

import requests
from flask import Flask, render_template, request
from metar.Metar import Metar, ParserError

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Lookup tables
#
# These map the abbreviated METAR codes to human-readable English strings.
# Defined as module-level constants so they are built once at import time.
# ---------------------------------------------------------------------------

# METAR sky-coverage codes (WMO and FAA standard)
SKY_COVERAGE = {
    "CLR": "Clear skies",          # No clouds below 12,000 ft (automated)
    "SKC": "Clear skies",          # No clouds (manual observation)
    "NSC": "No significant clouds",
    "NCD": "No clouds detected",
    "FEW": "Few clouds",           # 1–2 oktas coverage
    "SCT": "Scattered clouds",     # 3–4 oktas coverage
    "BKN": "Broken clouds",        # 5–7 oktas coverage
    "OVC": "Overcast",             # 8 oktas — full cloud cover
    "VV":  "Vertical visibility",  # Sky obscured; value is max altitude visible
}

# Present-weather intensity prefixes
WEATHER_INTENSITY = {
    "-":  "Light",
    "+":  "Heavy",
    "VC": "In vicinity",  # Within 5–10 miles of the airport
    "":   "",             # No prefix = moderate intensity
}

# Present-weather descriptor codes
WEATHER_DESCRIPTOR = {
    "MI": "shallow",
    "BC": "patchy",
    "PR": "partial",
    "DR": "low drifting",
    "BL": "blowing",
    "SH": "shower",
    "TS": "thunderstorm",
    "FZ": "freezing",
}

# Precipitation type codes
WEATHER_PRECIP = {
    "DZ": "drizzle",
    "RA": "rain",
    "SN": "snow",
    "SG": "snow grains",
    "IC": "ice crystals",
    "PL": "ice pellets",
    "GR": "hail",
    "GS": "small hail",
    "UP": "unknown precipitation",
}

# Obscuration type codes (reduce visibility but are not precipitation)
WEATHER_OBSCURATION = {
    "BR": "mist",
    "FG": "fog",
    "FU": "smoke",
    "VA": "volcanic ash",
    "DU": "dust",
    "SA": "sand",
    "HZ": "haze",
    "PY": "spray",
}

# Other significant weather codes
WEATHER_OTHER = {
    "PO": "dust whirls",
    "SQ": "squalls",
    "FC": "tornado/waterspout",
    "SS": "sandstorm",
    "DS": "dust storm",
}

# Cardinal direction names ordered clockwise from North, spaced 45° apart.
# Used to convert a wind bearing (0–360°) to a readable compass point.
WIND_DIRECTIONS = [
    "North", "Northeast", "East", "Southeast",
    "South", "Southwest", "West", "Northwest",
]


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def degrees_to_cardinal(degrees):
    """Convert a wind bearing in degrees to a compass direction string.

    Args:
        degrees (float): Wind direction in degrees (0–360).

    Returns:
        str: Compass direction, e.g. "Northeast".
    """
    return WIND_DIRECTIONS[round(degrees / 45) % 8]


def c_to_f(celsius):
    """Convert Celsius to Fahrenheit, rounded to the nearest whole degree.

    Args:
        celsius (float): Temperature in degrees Celsius.

    Returns:
        int: Temperature in degrees Fahrenheit.
    """
    return round(celsius * 9 / 5 + 32)


# ---------------------------------------------------------------------------
# METAR fetch and decode
# ---------------------------------------------------------------------------

def fetch_metar(icao):
    """Fetch the latest raw METAR string for a given airport from the FAA.

    Calls the Aviation Weather Center public API and returns the raw METAR
    text exactly as published. Returns an empty response as a ValueError so
    callers can present a friendly "airport not found" message.

    Args:
        icao (str): The 4-letter ICAO airport code, e.g. "KHIO".

    Returns:
        str: The raw METAR string, e.g. "METAR KHIO 220853Z AUTO ...".

    Raises:
        ValueError: If the API returns no data for the given code.
        requests.RequestException: If the network request fails.
    """
    url = (
        "https://aviationweather.gov/api/data/metar"
        f"?ids={icao.upper()}&format=raw"
    )
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    raw = resp.text.strip()
    if not raw:
        raise ValueError(
            f"No METAR data found for '{icao.upper()}'. "
            "Check the airport code."
        )
    return raw


def decode_sky(obs):
    """Decode sky-condition layers from a parsed METAR observation.

    Each layer in obs.sky is a 3-tuple:
        (coverage_code, altitude_quantity_or_None, cloud_type_or_None)

    Args:
        obs (Metar): A parsed python-metar observation object.

    Returns:
        list[str]: Human-readable description of each cloud layer.
    """
    if not obs.sky:
        return ["Sky condition not reported"]

    layers = []
    for coverage, height, cloud_type in obs.sky:
        desc = SKY_COVERAGE.get(coverage, coverage)

        if height is not None:
            alt_ft = int(height.value("FT"))
            desc += f" at {alt_ft:,} ft"

        # Cumulonimbus (CB) and towering cumulus (TCU) signal convective activity
        if cloud_type == "CB":
            desc += " (cumulonimbus — thunderstorm potential)"
        elif cloud_type == "TCU":
            desc += " (towering cumulus)"

        layers.append(desc)

    return layers


def decode_wind(obs):
    """Decode wind speed and direction from a parsed METAR observation.

    Handles calm winds (00000KT), variable direction (VRB), and gusts.
    Speed is reported in both mph and knots for broad readability.

    Args:
        obs (Metar): A parsed python-metar observation object.

    Returns:
        str: Plain-English wind description.
    """
    if obs.wind_speed is None:
        return "Not reported"

    speed_kt = obs.wind_speed.value("KT")
    speed_mph = round(obs.wind_speed.value("MPH"))

    if speed_kt == 0:
        return "Calm"

    # obs.wind_dir is None when the METAR reports variable direction (VRB)
    if obs.wind_dir is None:
        result = f"Variable at {speed_mph} mph ({round(speed_kt)} kt)"
    else:
        deg = obs.wind_dir.value()
        cardinal = degrees_to_cardinal(deg)
        result = (
            f"From the {cardinal} ({int(deg)}°) "
            f"at {speed_mph} mph ({round(speed_kt)} kt)"
        )

    if obs.wind_gust:
        gust_mph = round(obs.wind_gust.value("MPH"))
        result += f", gusting to {gust_mph} mph"

    return result


def decode_visibility(obs):
    """Decode prevailing visibility from a parsed METAR observation.

    Qualitative labels (excellent / good / reduced / very poor) are added
    to help non-pilots interpret the value quickly.

    Args:
        obs (Metar): A parsed python-metar observation object.

    Returns:
        str: Plain-English visibility description.
    """
    if obs.vis is None:
        return "Not reported"

    miles = obs.vis.value("SM")

    if miles >= 10:
        return "10 miles or more (excellent)"
    if miles >= 5:
        return f"{miles:.1f} miles (good)"
    if miles >= 1:
        return f"{miles:.1f} miles (reduced)"
    return f"{miles:.2f} miles (very poor)"


def decode_phenomena(obs):
    """Decode present-weather phenomena from a parsed METAR observation.

    Each entry in obs.weather is a 5-tuple:
        (intensity, descriptor, precipitation, obscuration, other)
    All five fields are strings; an empty string means that component
    is absent from the report.

    Args:
        obs (Metar): A parsed python-metar observation object.

    Returns:
        list[str]: Each active weather condition as a readable phrase,
                   e.g. ["Light rain", "Mist"].
    """
    result = []
    for intensity, descriptor, precip, obscuration, other in obs.weather:
        parts = []
        if intensity:
            parts.append(WEATHER_INTENSITY.get(intensity, intensity))
        if descriptor:
            parts.append(WEATHER_DESCRIPTOR.get(descriptor, descriptor))
        if precip:
            parts.append(WEATHER_PRECIP.get(precip, precip))
        if obscuration:
            parts.append(WEATHER_OBSCURATION.get(obscuration, obscuration))
        if other:
            parts.append(WEATHER_OTHER.get(other, other))
        if parts:
            result.append(" ".join(p for p in parts if p).capitalize())
    return result


def decode_metar(raw):
    """Parse a raw METAR string and return a plain-English weather summary.

    Delegates field-level decoding to dedicated helper functions and
    assembles the results into a flat dictionary suitable for template
    rendering.

    Args:
        raw (str): A complete raw METAR string.

    Returns:
        dict: Keys — station, time, sky, temperature, dewpoint, wind,
              visibility, phenomena, pressure, raw.

    Raises:
        metar.Metar.ParserError: If the raw string cannot be parsed.
    """
    obs = Metar(raw)

    # Temperature and dewpoint — both can be absent in automated reports
    temp_str, dewpt_str = "Not reported", "Not reported"
    if obs.temp is not None:
        temp_str = f"{c_to_f(obs.temp.value())}°F ({round(obs.temp.value())}°C)"
    if obs.dewpt is not None:
        dewpt_str = (
            f"{c_to_f(obs.dewpt.value())}°F "
            f"({round(obs.dewpt.value())}°C)"
        )

    # Altimeter setting — reported in both inHg (US) and hPa (international)
    pressure_str = "Not reported"
    if obs.press is not None:
        pressure_str = (
            f"{obs.press.value('IN'):.2f} inHg "
            f"({round(obs.press.value('MB'))} hPa)"
        )

    obs_time = obs.time.strftime("%H:%M UTC") if obs.time else "Unknown"

    return {
        "station":     obs.station_id or "Unknown",
        "time":        obs_time,
        "sky":         decode_sky(obs),
        "temperature": temp_str,
        "dewpoint":    dewpt_str,
        "wind":        decode_wind(obs),
        "visibility":  decode_visibility(obs),
        "phenomena":   decode_phenomena(obs),
        "pressure":    pressure_str,
        "raw":         raw,
    }


# ---------------------------------------------------------------------------
# Flask routes
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def index():
    """Render the main page and handle airport code submissions.

    GET:  Display the search form with no results.
    POST: Fetch and decode the METAR for the submitted airport code,
          then re-render the page with the weather report or an error message.
    """
    weather, error, icao = None, None, ""

    if request.method == "POST":
        icao = request.form.get("icao", "").strip().upper()

        if not icao:
            error = "Please enter an airport ICAO code."
        else:
            try:
                raw = fetch_metar(icao)
                weather = decode_metar(raw)
            except ValueError as e:
                error = str(e)
            except requests.RequestException as e:
                error = f"Could not reach the weather service: {e}"
            except ParserError as e:
                error = f"Could not parse the METAR data: {e}"
            except Exception as e:
                error = f"Unexpected error: {e}"

    return render_template(
        "index.html", weather=weather, error=error, icao=icao
    )


if __name__ == "__main__":
    # Run the development server.
    # For production, use a WSGI server such as gunicorn:
    #   gunicorn app:app
    app.run(debug=True)
