"""
Unit tests for app.py — METAR Weather Reader
=============================================
Strategy:
  - fetch_metar      : mock requests.get (no real network calls)
  - decode_sky/wind/visibility/phenomena : mock the obs object so each
    test controls exactly what the parser returns
  - decode_metar     : parse real METAR strings end-to-end
  - Flask routes     : Flask test client + mock fetch_metar
"""

import unittest
from unittest.mock import MagicMock, patch

import requests

from app import (
    app,
    decode_metar,
    decode_phenomena,
    decode_sky,
    decode_visibility,
    decode_wind,
    fetch_metar,
)


# ---------------------------------------------------------------------------
# Helpers — build mock quantity/speed/direction objects
# ---------------------------------------------------------------------------

def mock_qty(values_by_unit):
    """Create a mock pint-style quantity whose .value(unit) returns
    the matching entry from *values_by_unit*."""
    q = MagicMock()
    q.value.side_effect = lambda unit: values_by_unit[unit]
    return q


def mock_height(ft):
    """Create a mock height object that always returns *ft* regardless of unit.
    decode_sky always calls height.value("FT"), so a single return_value is fine.
    """
    h = MagicMock()
    h.value.return_value = float(ft)
    return h


def mock_obs(**kwargs):
    """Build a minimal mock Metar observation object.

    Pass only the attributes your test needs; everything else defaults
    to None so the decoder treats it as "not reported".
    """
    obs = MagicMock()
    obs.sky = kwargs.get("sky", [])
    obs.wind_speed = kwargs.get("wind_speed", None)
    obs.wind_dir = kwargs.get("wind_dir", None)
    obs.wind_gust = kwargs.get("wind_gust", None)
    obs.vis = kwargs.get("vis", None)
    obs.weather = kwargs.get("weather", [])
    return obs


# ---------------------------------------------------------------------------
# fetch_metar
# ---------------------------------------------------------------------------

class TestFetchMetar(unittest.TestCase):

    @patch("app.requests.get")
    def test_returns_raw_string(self, mock_get):
        """A successful API response returns the raw METAR string."""
        mock_get.return_value.text = "METAR KHIO 220853Z AUTO 00000KT 10SM CLR 07/02 A2992\n"
        result = fetch_metar("KHIO")
        self.assertEqual(result, "METAR KHIO 220853Z AUTO 00000KT 10SM CLR 07/02 A2992")

    @patch("app.requests.get")
    def test_uppercases_icao_in_url(self, mock_get):
        """The ICAO code is uppercased before building the request URL."""
        mock_get.return_value.text = "METAR KJFK 220853Z 00000KT 10SM CLR 15/10 A2990"
        fetch_metar("kjfk")
        call_url = mock_get.call_args[0][0]
        self.assertIn("KJFK", call_url)

    @patch("app.requests.get")
    def test_empty_response_raises_value_error(self, mock_get):
        """An empty API body (airport not found) raises ValueError."""
        mock_get.return_value.text = "   "
        with self.assertRaises(ValueError) as ctx:
            fetch_metar("ZZZZ")
        self.assertIn("ZZZZ", str(ctx.exception))

    @patch("app.requests.get")
    def test_network_error_propagates(self, mock_get):
        """A network failure raises requests.RequestException."""
        mock_get.side_effect = requests.ConnectionError("timeout")
        with self.assertRaises(requests.RequestException):
            fetch_metar("KHIO")


# ---------------------------------------------------------------------------
# decode_sky
# ---------------------------------------------------------------------------

class TestDecodeSky(unittest.TestCase):

    def test_clear_skies(self):
        """CLR coverage with no height returns 'Clear skies'."""
        obs = mock_obs(sky=[("CLR", None, None)])
        result = decode_sky(obs)
        self.assertEqual(result, ["Clear skies"])

    def test_few_clouds_with_altitude(self):
        """FEW layer includes the altitude in feet."""
        obs = mock_obs(sky=[("FEW", mock_height(2500), None)])
        result = decode_sky(obs)
        self.assertIn("Few clouds", result[0])
        self.assertIn("2,500 ft", result[0])

    def test_broken_cumulonimbus(self):
        """BKN layer with CB cloud type warns of thunderstorm potential."""
        obs = mock_obs(sky=[("BKN", mock_height(3000), "CB")])
        result = decode_sky(obs)
        self.assertIn("Broken clouds", result[0])
        self.assertIn("cumulonimbus", result[0])

    def test_overcast(self):
        """OVC coverage at altitude produces 'Overcast at X ft'."""
        obs = mock_obs(sky=[("OVC", mock_height(1200), None)])
        result = decode_sky(obs)
        self.assertIn("Overcast", result[0])
        self.assertIn("1,200 ft", result[0])

    def test_multiple_layers(self):
        """Multiple sky layers are returned as separate list entries."""
        obs = mock_obs(sky=[
            ("FEW", mock_height(2500), None),
            ("BKN", mock_height(6000), None),
        ])
        result = decode_sky(obs)
        self.assertEqual(len(result), 2)
        self.assertIn("Few clouds", result[0])
        self.assertIn("Broken clouds", result[1])

    def test_empty_sky_list(self):
        """No sky data returns a single 'not reported' entry."""
        obs = mock_obs(sky=[])
        result = decode_sky(obs)
        self.assertEqual(len(result), 1)
        self.assertIn("not reported", result[0].lower())

    def test_towering_cumulus(self):
        """TCU cloud type appends '(towering cumulus)' to the description."""
        obs = mock_obs(sky=[("SCT", mock_height(4000), "TCU")])
        result = decode_sky(obs)
        self.assertIn("towering cumulus", result[0])


# ---------------------------------------------------------------------------
# decode_wind
# ---------------------------------------------------------------------------

class TestDecodeWind(unittest.TestCase):

    def test_calm_winds(self):
        """Zero knots returns 'Calm' regardless of direction."""
        obs = mock_obs(
            wind_speed=mock_qty({"KT": 0.0, "MPH": 0.0}),
            wind_dir=MagicMock(),
        )
        self.assertEqual(decode_wind(obs), "Calm")

    def test_not_reported(self):
        """Missing wind_speed returns 'Not reported'."""
        obs = mock_obs(wind_speed=None)
        self.assertEqual(decode_wind(obs), "Not reported")

    def test_variable_direction(self):
        """VRB winds (wind_dir is None) mention 'Variable'."""
        obs = mock_obs(
            wind_speed=mock_qty({"KT": 8.0, "MPH": 9.2}),
            wind_dir=None,
        )
        result = decode_wind(obs)
        self.assertIn("Variable", result)

    def test_fixed_direction_west(self):
        """270° wind maps to 'West' with speed in both mph and kt."""
        wind_dir = MagicMock()
        wind_dir.value.return_value = 270.0
        obs = mock_obs(
            wind_speed=mock_qty({"KT": 15.0, "MPH": 17.0}),
            wind_dir=wind_dir,
        )
        result = decode_wind(obs)
        self.assertIn("West", result)
        self.assertIn("270", result)
        self.assertIn("17 mph", result)

    def test_with_gusts(self):
        """Gust speed is appended when obs.wind_gust is present."""
        wind_dir = MagicMock()
        wind_dir.value.return_value = 90.0
        obs = mock_obs(
            wind_speed=mock_qty({"KT": 20.0, "MPH": 23.0}),
            wind_dir=wind_dir,
            wind_gust=mock_qty({"KT": 35.0, "MPH": 40.0}),
        )
        result = decode_wind(obs)
        self.assertIn("gusting", result)
        self.assertIn("40 mph", result)

    def test_northeast_direction(self):
        """45° wind maps to 'Northeast'."""
        wind_dir = MagicMock()
        wind_dir.value.return_value = 45.0
        obs = mock_obs(
            wind_speed=mock_qty({"KT": 10.0, "MPH": 11.5}),
            wind_dir=wind_dir,
        )
        result = decode_wind(obs)
        self.assertIn("Northeast", result)


# ---------------------------------------------------------------------------
# decode_visibility
# ---------------------------------------------------------------------------

class TestDecodeVisibility(unittest.TestCase):

    def _obs(self, sm):
        """Build an obs mock with visibility set to *sm* statute miles."""
        return mock_obs(vis=mock_qty({"SM": sm}))

    def test_not_reported(self):
        obs = mock_obs(vis=None)
        self.assertEqual(decode_visibility(obs), "Not reported")

    def test_ten_miles_or_more(self):
        self.assertIn("excellent", decode_visibility(self._obs(10)))

    def test_good_visibility(self):
        self.assertIn("good", decode_visibility(self._obs(7.0)))

    def test_reduced_visibility(self):
        self.assertIn("reduced", decode_visibility(self._obs(2.5)))

    def test_very_poor_visibility(self):
        self.assertIn("very poor", decode_visibility(self._obs(0.25)))

    def test_boundary_exactly_five(self):
        """5 SM is classified as 'good', not 'reduced'."""
        self.assertIn("good", decode_visibility(self._obs(5.0)))

    def test_boundary_exactly_one(self):
        """1 SM is classified as 'reduced', not 'very poor'."""
        self.assertIn("reduced", decode_visibility(self._obs(1.0)))


# ---------------------------------------------------------------------------
# decode_phenomena
# ---------------------------------------------------------------------------

class TestDecodePhenomena(unittest.TestCase):

    def test_no_weather(self):
        """Empty weather list returns an empty list."""
        obs = mock_obs(weather=[])
        self.assertEqual(decode_phenomena(obs), [])

    def test_light_rain(self):
        """Light rain (-RA) is decoded as 'Light rain'."""
        obs = mock_obs(weather=[("-", "", "RA", "", "")])
        result = decode_phenomena(obs)
        self.assertEqual(len(result), 1)
        self.assertIn("Light", result[0])
        self.assertIn("rain", result[0])

    def test_heavy_rain(self):
        """Heavy rain (+RA) is decoded as 'Heavy rain'."""
        obs = mock_obs(weather=[("+", "", "RA", "", "")])
        result = decode_phenomena(obs)
        self.assertIn("Heavy", result[0])

    def test_thunderstorm_with_rain(self):
        """Thunderstorm + rain (TSRA) includes both 'thunderstorm' and 'rain'."""
        obs = mock_obs(weather=[("", "TS", "RA", "", "")])
        result = decode_phenomena(obs)
        self.assertIn("thunderstorm", result[0].lower())
        self.assertIn("rain", result[0].lower())

    def test_fog(self):
        """Fog (FG) as obscuration is decoded as 'Fog'."""
        obs = mock_obs(weather=[("", "", "", "FG", "")])
        result = decode_phenomena(obs)
        self.assertIn("fog", result[0].lower())

    def test_light_freezing_rain(self):
        """Light freezing rain (-FZRA) includes 'freezing' and 'rain'."""
        obs = mock_obs(weather=[("-", "FZ", "RA", "", "")])
        result = decode_phenomena(obs)
        self.assertIn("freezing", result[0].lower())
        self.assertIn("rain", result[0].lower())

    def test_multiple_phenomena(self):
        """Two simultaneous weather events return two list entries."""
        obs = mock_obs(weather=[
            ("-", "", "RA", "", ""),
            ("", "", "", "BR", ""),
        ])
        result = decode_phenomena(obs)
        self.assertEqual(len(result), 2)

    def test_result_is_capitalized(self):
        """Each decoded phenomenon string starts with a capital letter."""
        obs = mock_obs(weather=[("-", "", "SN", "", "")])
        result = decode_phenomena(obs)
        self.assertTrue(result[0][0].isupper())


# ---------------------------------------------------------------------------
# decode_metar — integration tests with real METAR strings
# ---------------------------------------------------------------------------

class TestDecodeMetar(unittest.TestCase):
    """Parse realistic METAR strings end-to-end through decode_metar.

    These tests verify the full decode pipeline rather than individual
    helpers. The strings are representative of actual airport reports.
    """

    def test_clear_calm_day(self):
        """Clear skies + calm winds are decoded correctly."""
        raw = "METAR KHIO 220853Z AUTO 00000KT 10SM CLR 07/02 A2992"
        result = decode_metar(raw)

        self.assertEqual(result["station"], "KHIO")
        self.assertIn("Clear", result["sky"][0])
        self.assertEqual(result["wind"], "Calm")
        self.assertIn("excellent", result["visibility"])
        self.assertIn("°F", result["temperature"])
        self.assertEqual(result["phenomena"], [])

    def test_wind_and_multiple_cloud_layers(self):
        """Fixed-direction wind and two cloud layers decode correctly."""
        raw = "METAR KJFK 221456Z 27015KT 10SM FEW025 BKN060 18/10 A2992"
        result = decode_metar(raw)

        self.assertIn("West", result["wind"])
        self.assertEqual(len(result["sky"]), 2)
        self.assertIn("Few clouds", result["sky"][0])
        self.assertIn("Broken clouds", result["sky"][1])

    def test_variable_wind_and_rain(self):
        """Variable winds, rain, and reduced visibility decode correctly."""
        raw = "METAR KORD 221456Z VRB05KT 3SM -RA OVC015 10/08 A2985"
        result = decode_metar(raw)

        self.assertIn("Variable", result["wind"])
        self.assertIn("reduced", result["visibility"])
        self.assertIn("Overcast", result["sky"][0])
        # At least one phenomenon should mention rain
        self.assertTrue(
            any("rain" in p.lower() for p in result["phenomena"]),
            msg=f"Expected rain in phenomena, got: {result['phenomena']}",
        )

    def test_gusting_wind(self):
        """Gust speed appears in the wind field."""
        raw = "METAR KMIA 221456Z 25020G35KT 6SM FEW030 28/20 A2970"
        result = decode_metar(raw)
        self.assertIn("gusting", result["wind"])

    def test_all_required_keys_present(self):
        """decode_metar always returns all expected dictionary keys."""
        raw = "METAR KSFO 221456Z 00000KT 10SM CLR 15/08 A3005"
        result = decode_metar(raw)
        expected_keys = {
            "station", "time", "sky", "temperature", "dewpoint",
            "wind", "visibility", "phenomena", "pressure", "raw",
        }
        self.assertEqual(set(result.keys()), expected_keys)

    def test_raw_metar_preserved(self):
        """The original raw string is stored unchanged in the result."""
        raw = "METAR KHIO 220853Z AUTO 00000KT 10SM CLR 07/02 A2992"
        result = decode_metar(raw)
        self.assertEqual(result["raw"], raw)


# ---------------------------------------------------------------------------
# Flask routes
# ---------------------------------------------------------------------------

class TestFlaskRoutes(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_get_returns_200(self):
        """GET / renders the search form successfully."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"ICAO", response.data)

    def test_post_empty_code_shows_error(self):
        """POST with an empty airport code returns a validation error."""
        response = self.client.post("/", data={"icao": ""})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Please enter", response.data)

    @patch("app.fetch_metar")
    def test_post_invalid_code_shows_error(self, mock_fetch):
        """POST with an unknown airport code surfaces the error message."""
        mock_fetch.side_effect = ValueError("No METAR data found for 'ZZZZ'.")
        response = self.client.post("/", data={"icao": "ZZZZ"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No METAR data", response.data)

    @patch("app.fetch_metar")
    def test_post_valid_code_shows_weather(self, mock_fetch):
        """POST with a valid code renders the decoded weather report."""
        mock_fetch.return_value = (
            "METAR KHIO 220853Z AUTO 00000KT 10SM CLR 07/02 A2992"
        )
        response = self.client.post("/", data={"icao": "KHIO"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"KHIO", response.data)
        self.assertIn(b"Calm", response.data)

    @patch("app.fetch_metar")
    def test_post_network_error_shows_error(self, mock_fetch):
        """A network failure during fetch displays a friendly error."""
        mock_fetch.side_effect = requests.ConnectionError("timeout")
        response = self.client.post("/", data={"icao": "KHIO"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"weather service", response.data)

    @patch("app.fetch_metar")
    def test_icao_input_preserved_on_error(self, mock_fetch):
        """After an error the airport code stays visible in the form."""
        mock_fetch.side_effect = ValueError("not found")
        response = self.client.post("/", data={"icao": "ZZZZ"})
        self.assertIn(b"ZZZZ", response.data)


if __name__ == "__main__":
    unittest.main()
