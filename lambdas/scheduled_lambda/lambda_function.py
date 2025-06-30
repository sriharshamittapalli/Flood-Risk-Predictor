import os
import json
import boto3
import requests
import google.generativeai as genai
from datetime import datetime, timedelta, timezone
from collections import defaultdict

# --- Initialize Clients ---
ses_client = boto3.client('ses')
dynamodb = boto3.resource('dynamodb')

# --- Environment Variables ---
SUBSCRIPTIONS_TABLE_NAME = os.environ.get('SUBSCRIPTIONS_TABLE_NAME')
FROM_EMAIL_ADDRESS = os.environ.get('FROM_EMAIL_ADDRESS')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
OWM_API_KEY = os.environ.get('OPENWEATHERMAP_API_KEY')
NEWS_API_KEY = os.environ.get('NEWS_API_KEY')

subscriptions_table = dynamodb.Table(SUBSCRIPTIONS_TABLE_NAME)
genai.configure(api_key=GEMINI_API_KEY)

# --- Helper Functions (Identical to on-demand-lambda) ---
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

def generate_html_email_body(location, risk_level, explanation):
    return f"""
    <html><head></head><body style="font-family: Arial, sans-serif; color: #333;">
        <h2>Flood Risk Alert for {location.title()}</h2>
        <p>A potential flood risk has been detected for your subscribed location.</p>
        <div style="border: 1px solid #ddd; padding: 15px; border-radius: 5px; background-color: #f9f9f9;">
            <p><strong>Risk Level:</strong> <span style="font-weight: bold; color: #D8000C;">{risk_level.title()}</span></p>
            <p><strong>Analysis:</strong> {explanation}</p>
        </div>
        <p>Please monitor local news and weather advisories.</p><hr>
        <p style="font-size: 0.8em; color: #888;">
            You are receiving this email because you subscribed to flood alerts for {location.title()}. 
            To unsubscribe, please visit the application website.
        </p>
    </body></html>
    """

# --- Main Lambda Handler ---
def lambda_handler(event, context):
    try:
        response = subscriptions_table.scan()
        subscriptions = response.get('Items', [])
        subscribers_by_location = defaultdict(list)
        for item in subscriptions:
            subscribers_by_location[item['location']].append(item['email'])
    except Exception as e:
        print(f"Error scanning DynamoDB table: {e}")
        return

    # 2. Analyze each unique location
    for location, emails in subscribers_by_location.items():
        print(f"--- Analyzing location: {location} for {len(emails)} subscriber(s) ---")
        
        weather_data = get_weather_data(f"{location},US")
        news_headlines = get_refined_news_headlines(location)
        raw_data = {'target_city': f"{location},US", 'weather_data': weather_data, 'news_headlines': news_headlines}

        # Get the real analysis first
        analysis_result = analyze_flood_risk_with_gemini(raw_data)
        risk_level = analysis_result.get('risk_level', 'Unknown').lower()
        
        # IMPORTANT: Set the real explanation BEFORE the test code
        explanation = analysis_result.get('explanation', 'No explanation provided.')
        
        print(f"Analysis for {location}: Risk Level is {risk_level}")

        # 3. If risk is high, send a TARGETED email
        if risk_level in ["high", "very high"]:
            print(f"HIGH RISK DETECTED for {location}. Sending targeted emails...")
            
            # The 'explanation' variable is now correct (either real or test)
            subject = f"High Flood Risk Alert for {location.title()}"
            html_body = generate_html_email_body(location, risk_level, explanation)

            for email in emails:
                try:
                    ses_client.send_email(
                        Source=FROM_EMAIL_ADDRESS,
                        Destination={'ToAddresses': [email]},
                        Message={'Subject': {'Data': subject}, 'Body': {'Html': {'Data': html_body}}}
                    )
                except Exception as e:
                    print(f"FAILED to send alert to {email}: {e}")

    return {'statusCode': 200, 'body': json.dumps('Targeted analysis complete.')}