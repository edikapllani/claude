import requests
from flask import Flask, render_template, request
from metar.Metar import Metar, ParserError

app = Flask(__name__)

# --- Lookup tables ---

SKY_COVERAGE = {
    "CLR": "Clear skies",
    "SKC": "Clear skies",
    "NSC": "No significant clouds",
    "NCD": "No clouds detected",
    "FEW": "Few clouds",
    "SCT": "Scattered clouds",
    "BKN": "Broken clouds",
    "OVC": "Overcast",
    "VV":  "Vertical visibility",
}

WEATHER_INTENSITY = {
    "-":  "Light",
    "+":  "Heavy",
    "VC": "In vicinity",
    "":   "",
}

WEATHER_DESCRIPTOR = {
    "MI": "shallow", "BC": "patchy", "PR": "partial",
    "DR": "low drifting", "BL": "blowing", "SH": "shower",
    "TS": "thunderstorm", "FZ": "freezing",
}

WEATHER_PRECIP = {
    "DZ": "drizzle", "RA": "rain", "SN": "snow", "SG": "snow grains",
    "IC": "ice crystals", "PL": "ice pellets", "GR": "hail",
    "GS": "small hail", "UP": "unknown precipitation",
}

WEATHER_OBSCURATION = {
    "BR": "mist", "FG": "fog", "FU": "smoke", "VA": "volcanic ash",
    "DU": "dust", "SA": "sand", "HZ": "haze", "PY": "spray",
}

WEATHER_OTHER = {
    "PO": "dust whirls", "SQ": "squalls", "FC": "tornado/waterspout",
    "SS": "sandstorm", "DS": "dust storm",
}

WIND_DIRECTIONS = [
    "North", "Northeast", "East", "Southeast",
    "South", "Southwest", "West", "Northwest",
]


# --- Helpers ---

def degrees_to_cardinal(degrees):
    return WIND_DIRECTIONS[round(degrees / 45) % 8]


def c_to_f(c):
    return round(c * 9 / 5 + 32)


# --- Core functions ---

def fetch_metar(icao):
    url = f"https://aviationweather.gov/api/data/metar?ids={icao.upper()}&format=raw"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    raw = resp.text.strip()
    if not raw:
        raise ValueError(f"No METAR data found for '{icao.upper()}'. Check the airport code.")
    return raw


def decode_sky(obs):
    if not obs.sky:
        return ["Sky condition not reported"]
    layers = []
    for coverage, height, cloud_type in obs.sky:
        desc = SKY_COVERAGE.get(coverage, coverage)
        if height is not None:
            alt_ft = int(height.value("FT"))
            desc += f" at {alt_ft:,} ft"
        if cloud_type == "CB":
            desc += " (cumulonimbus — thunderstorm potential)"
        elif cloud_type == "TCU":
            desc += " (towering cumulus)"
        layers.append(desc)
    return layers


def decode_wind(obs):
    if obs.wind_speed is None:
        return "Not reported"
    speed_kt = obs.wind_speed.value("KT")
    speed_mph = round(obs.wind_speed.value("MPH"))
    if speed_kt == 0:
        return "Calm"
    if obs.wind_dir is None:
        result = f"Variable at {speed_mph} mph ({round(speed_kt)} kt)"
    else:
        deg = obs.wind_dir.value()
        cardinal = degrees_to_cardinal(deg)
        result = f"From the {cardinal} ({int(deg)}°) at {speed_mph} mph ({round(speed_kt)} kt)"
    if obs.wind_gust:
        gust_mph = round(obs.wind_gust.value("MPH"))
        result += f", gusting to {gust_mph} mph"
    return result


def decode_visibility(obs):
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
    obs = Metar(raw)

    temp_str, dewpt_str = "Not reported", "Not reported"
    if obs.temp is not None:
        temp_f = c_to_f(obs.temp.value())
        temp_c = round(obs.temp.value())
        temp_str = f"{temp_f}°F ({temp_c}°C)"
    if obs.dewpt is not None:
        dp_f = c_to_f(obs.dewpt.value())
        dp_c = round(obs.dewpt.value())
        dewpt_str = f"{dp_f}°F ({dp_c}°C)"

    pressure_str = "Not reported"
    if obs.press is not None:
        pressure_str = f"{obs.press.value('IN'):.2f} inHg ({round(obs.press.value('MB'))} hPa)"

    obs_time = obs.time.strftime("%H:%M UTC") if obs.time else "Unknown"

    phenomena = decode_phenomena(obs)

    return {
        "station":    obs.station_id or "Unknown",
        "time":       obs_time,
        "sky":        decode_sky(obs),
        "temperature": temp_str,
        "dewpoint":   dewpt_str,
        "wind":       decode_wind(obs),
        "visibility": decode_visibility(obs),
        "phenomena":  phenomena,
        "pressure":   pressure_str,
        "raw":        raw,
    }


# --- Routes ---

@app.route("/", methods=["GET", "POST"])
def index():
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
    return render_template("index.html", weather=weather, error=error, icao=icao)


if __name__ == "__main__":
    app.run(debug=True)
