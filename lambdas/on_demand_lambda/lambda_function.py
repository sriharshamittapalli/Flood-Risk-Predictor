import os
import json
import boto3
import requests
import google.generativeai as genai
from datetime import datetime, timezone, timedelta

# --- Initialize Clients ---
dynamodb = boto3.resource('dynamodb')
RESULTS_TABLE_NAME = os.environ.get('RESULTS_TABLE_NAME')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
OWM_API_KEY = os.environ.get('OPENWEATHERMAP_API_KEY')
NEWS_API_KEY = os.environ.get('NEWS_API_KEY')

genai.configure(api_key=GEMINI_API_KEY)
results_table = dynamodb.Table(RESULTS_TABLE_NAME)

# --- Helper Functions ---
def get_weather_data(city_name):
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {'q': city_name, 'appid': OWM_API_KEY, 'units': 'metric'}
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as err: return None

def get_refined_news_headlines(city_name):
    query = f'("flash flood" OR "heavy rain" OR "flooding" OR "severe weather") AND "{city_name}"'
    two_days_ago = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
    base_url = "https://newsapi.org/v2/everything"
    params = {'qInTitle': query, 'language': 'en', 'sortBy': 'publishedAt', 'from': two_days_ago, 'apiKey': NEWS_API_KEY}
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        return [{'title': a['title']} for a in response.json().get('articles', [])]
    except Exception as err: return []

def analyze_flood_risk_with_gemini(data):
    weather = data.get('weather_data', {}).get('main', {})
    news_titles = [h['title'] for h in data.get('news_headlines', [])[:5]]
    prompt = f"""
    Based on the following real-time data for {data.get('target_city')}, provide a flood risk analysis.
    Current Weather Data:
    - Temperature: {weather.get('temp')}°C
    - Humidity: {weather.get('humidity')}%
    Recent News Headlines:
    {json.dumps(news_titles, indent=2)}
    Analysis Task:
    1. Assess the current flood risk.
    2. Provide a clear risk level: "Low", "Medium", "High", or "Very High".
    3. Provide a concise, one-paragraph explanation.
    4. Format the output as a JSON object with two keys: "risk_level" and "explanation". Do not include any other text or markdown.
    """
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt)
    cleaned_json_text = response.text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(cleaned_json_text)

# --- Main Lambda Handler ---
def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        target_city = body.get('location')

        if not target_city:
            return {'statusCode': 400, 'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}, 'body': json.dumps({'error': 'Missing required field: location.'})}

        weather_data = get_weather_data(f"{target_city},US")
        news_headlines = get_refined_news_headlines(target_city)
        raw_data = {'target_city': f"{target_city},US", 'weather_data': weather_data, 'news_headlines': news_headlines}

        analysis_result = analyze_flood_risk_with_gemini(raw_data)
        
        timestamp = datetime.now(timezone.utc).isoformat()
        results_table.put_item(
            Item={
                'location': target_city.lower(),
                'timestamp': timestamp,
                'risk_level': analysis_result.get('risk_level'),
                'explanation': analysis_result.get('explanation'),
                'raw_weather_data': json.dumps(weather_data),
                'raw_news_data': json.dumps(news_headlines)
            }
        )
        return {'statusCode': 200, 'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}, 'body': json.dumps(analysis_result)}

    except Exception as e:
        print(f"An error occurred in on-demand-lambda: {e}")
        return {'statusCode': 500, 'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}, 'body': json.dumps({'error': 'An internal server error occurred.'})}