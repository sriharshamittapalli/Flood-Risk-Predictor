import json
import boto3
import os
from datetime import datetime

# Initialize the DynamoDB client
dynamodb = boto3.resource('dynamodb')
sns_client = boto3.client('sns') # Add this line
# Get the table name from an environment variable for flexibility
SUBSCRIPTIONS_TABLE_NAME = os.environ.get('SUBSCRIPTIONS_TABLE_NAME')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN') # You will need to add this environment variable
table = dynamodb.Table(SUBSCRIPTIONS_TABLE_NAME)

def lambda_handler(event, context):
    """
    Handles a user's request to subscribe to flood alerts for a location.
    Expects a JSON body with 'location' and 'email'.
    """
    print(f"Received event: {json.dumps(event)}")

    try:
        # API Gateway wraps the request body in a string, so we need to parse it
        body = json.loads(event.get('body', '{}'))

        location = body.get('location')
        email = body.get('email')

        # Basic input validation
        if not location or not email:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*' # Required for CORS
                },
                'body': json.dumps({'error': 'Missing required fields: location and email.'})
            }

        # The user_id will be the email address for this example
        user_id = email
        
        print(f"Attempting to add subscription for {email} to location {location} in table {SUBSCRIPTIONS_TABLE_NAME}")

        # Put the item into the DynamoDB table
        table.put_item(
            Item={
                'location': location.lower(), # Store location in lowercase for consistency
                'user_id': user_id,
                'email': email,
                'subscribed_at': datetime.utcnow().isoformat()
            }
        )

        print("Successfully saved subscription to DynamoDB.")
        
        # --- NEW IMPROVEMENT ---
        # Programmatically subscribe the user's email to the SNS topic
        try:
            sns_client.subscribe(
                TopicArn=SNS_TOPIC_ARN,
                Protocol='email',
                Endpoint=email
            )
            print(f"Successfully initiated SNS subscription for {email}. A confirmation email will be sent.")
        except Exception as e:
            print(f"Error subscribing user to SNS topic: {e}")
        # --- END OF IMPROVEMENT ---

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'message': f'Successfully subscribed {email} to alerts for {location}.'})
        }

    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps({'error': 'Invalid JSON format in request body.'})
        }
    except Exception as e:
        print(f"Error processing subscription: {e}")
        return {
            'statusCode': 500,
            'headers': { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps({'error': 'An internal error occurred.'})
        }