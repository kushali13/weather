from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("weather")

# Constants
OPENWEATHER_API_BASE = "https://api.openweathermap.org/data/2.5"
OPENWEATHER_API_KEY = "162689b8f4e4ebb26d831abc46160b0f"
USER_AGENT = "weather-app/1.0"

async def make_openweather_request(url: str, params: dict[str, Any]) -> dict[str, Any] | None:
    """Make a request to the OpenWeatherMap API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT
    }
    
    # Add API key to parameters
    params["appid"] = OPENWEATHER_API_KEY
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"API request failed: {e}")
            return None

def kelvin_to_celsius(kelvin: float) -> float:
    """Convert Kelvin to Celsius."""
    return kelvin - 273.15

def kelvin_to_fahrenheit(kelvin: float) -> float:
    """Convert Kelvin to Fahrenheit."""
    return (kelvin - 273.15) * 9/5 + 32

@mcp.tool()
async def get_alerts(state: str) -> str:
    """Get weather alerts for a US state.
    
    Args:
        state: Two-letter US state code (e.g. CA, NY)
    """
    # OpenWeatherMap doesn't have state-specific alerts like NWS
    # We'll get alerts for major cities in the state instead
    
    # State to major city mapping (sample - you can expand this)
    state_cities = {
        "CA": "San Francisco",
        "NY": "New York",
        "TX": "Houston",
        "FL": "Miami",
        "IL": "Chicago",
        "PA": "Philadelphia",
        "OH": "Columbus",
        "GA": "Atlanta",
        "NC": "Charlotte",
        "MI": "Detroit"
    }
    
    city = state_cities.get(state.upper())
    if not city:
        return f"Alert data not available for state: {state}. Supported states: {', '.join(state_cities.keys())}"
    
    # Get current weather to check for severe conditions
    url = f"{OPENWEATHER_API_BASE}/weather"
    params = {
        "q": f"{city},{state},US",
        "units": "metric"
    }
    
    data = await make_openweather_request(url, params)
    
    if not data:
        return "Unable to fetch weather alert data."
    
    # Check for severe weather conditions
    weather = data.get("weather", [{}])[0]
    main_weather = weather.get("main", "").lower()
    description = weather.get("description", "")
    
    alerts = []
    
    # Check for severe conditions
    if "thunderstorm" in main_weather:
        alerts.append(f"⚡ Thunderstorm Alert for {city}, {state}: {description.title()}")
    elif "snow" in main_weather or "blizzard" in description:
        alerts.append(f"🌨️ Winter Weather Alert for {city}, {state}: {description.title()}")
    elif "rain" in main_weather and "heavy" in description:
        alerts.append(f"🌧️ Heavy Rain Alert for {city}, {state}: {description.title()}")
    
    # Check temperature extremes
    temp = data.get("main", {}).get("temp", 0)
    if temp > 35:  # > 95°F
        alerts.append(f"🔥 Heat Warning for {city}, {state}: Temperature {temp:.1f}°C ({temp*9/5+32:.1f}°F)")
    elif temp < -10:  # < 14°F
        alerts.append(f"🥶 Cold Warning for {city}, {state}: Temperature {temp:.1f}°C ({temp*9/5+32:.1f}°F)")
    
    if not alerts:
        return f"No severe weather alerts for {city}, {state} at this time."
    
    return "\n".join(alerts)

@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location.
    
    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    """
    # Get 5-day forecast
    url = f"{OPENWEATHER_API_BASE}/forecast"
    params = {
        "lat": latitude,
        "lon": longitude,
        "units": "metric"
    }
    
    data = await make_openweather_request(url, params)
    
    if not data or "list" not in data:
        return "Unable to fetch forecast data for this location."
    
    # Get current weather as well
    current_url = f"{OPENWEATHER_API_BASE}/weather"
    current_data = await make_openweather_request(current_url, params)
    
    forecasts = []
    
    # Add current weather
    if current_data:
        current_temp = current_data["main"]["temp"]
        current_feels_like = current_data["main"]["feels_like"]
        current_humidity = current_data["main"]["humidity"]
        current_pressure = current_data["main"]["pressure"]
        current_weather = current_data["weather"][0]
        wind = current_data.get("wind", {})
        
        current_forecast = f"""Current Weather:
Temperature: {current_temp:.1f}°C ({current_temp*9/5+32:.1f}°F)
Feels like: {current_feels_like:.1f}°C ({current_feels_like*9/5+32:.1f}°F)
Humidity: {current_humidity}%
Pressure: {current_pressure} hPa
Wind: {wind.get('speed', 0)} m/s
Conditions: {current_weather['description'].title()}"""
        forecasts.append(current_forecast)
    
    # Process forecast data (next 24 hours, every 3 hours)
    forecast_list = data["list"][:8]  # Next 24 hours (8 * 3-hour intervals)
    
    for i, period in enumerate(forecast_list):
        dt_txt = period["dt_txt"]
        temp = period["main"]["temp"]
        feels_like = period["main"]["feels_like"]
        humidity = period["main"]["humidity"]
        weather_desc = period["weather"][0]["description"]
        wind_speed = period["wind"]["speed"]
        
        # Calculate hours from now
        hours_ahead = (i + 1) * 3
        
        forecast = f"""In {hours_ahead} hours ({dt_txt}):
Temperature: {temp:.1f}°C ({temp*9/5+32:.1f}°F)
Feels like: {feels_like:.1f}°C ({feels_like*9/5+32:.1f}°F)
Humidity: {humidity}%
Wind: {wind_speed} m/s
Conditions: {weather_desc.title()}"""
        forecasts.append(forecast)
    
    return "\n---\n".join(forecasts)

@mcp.tool()
async def get_weather_by_city(city: str, country_code: str = "US") -> str:
    """Get current weather for a city.
    
    Args:
        city: City name
        country_code: Two-letter country code (default: US)
    """
    url = f"{OPENWEATHER_API_BASE}/weather"
    params = {
        "q": f"{city},{country_code}",
        "units": "metric"
    }
    
    data = await make_openweather_request(url, params)
    
    if not data:
        return f"Unable to fetch weather data for {city}, {country_code}."
    
    # Extract weather information
    main = data["main"]
    weather = data["weather"][0]
    wind = data.get("wind", {})
    clouds = data.get("clouds", {})
    sys = data.get("sys", {})
    
    temp = main["temp"]
    feels_like = main["feels_like"]
    
    weather_report = f"""Weather for {data['name']}, {sys.get('country', country_code)}:

Temperature: {temp:.1f}°C ({temp*9/5+32:.1f}°F)
Feels like: {feels_like:.1f}°C ({feels_like*9/5+32:.1f}°F)
Conditions: {weather['description'].title()}
Humidity: {main['humidity']}%
Pressure: {main['pressure']} hPa
Wind Speed: {wind.get('speed', 0)} m/s
Wind Direction: {wind.get('deg', 0)}°
Cloudiness: {clouds.get('all', 0)}%
Visibility: {data.get('visibility', 'N/A')} meters"""
    
    return weather_report

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')