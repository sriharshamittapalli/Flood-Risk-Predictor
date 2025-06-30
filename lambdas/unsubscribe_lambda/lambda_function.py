import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
SUBSCRIPTIONS_TABLE_NAME = os.environ.get('SUBSCRIPTIONS_TABLE_NAME')
table = dynamodb.Table(SUBSCRIPTIONS_TABLE_NAME)

def lambda_handler(event, context):
    """
    Handles a user's request to unsubscribe from ALL alerts using only their email.
    """
    print(f"Received unsubscribe event: {json.dumps(event)}")

    try:
        body = json.loads(event.get('body', '{}'))
        email = body.get('email')

        if not email:
            return {'statusCode': 400, 'body': json.dumps({'error': 'Email address is required.'})}

        print(f"Querying all subscriptions for {email}...")

        # Step 1: Query the index to find all subscriptions for the email
        response = table.query(
            IndexName='user_id-index',
            KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(email)
        )
        
        subscriptions_to_delete = response.get('Items', [])
        
        if not subscriptions_to_delete:
            return {'statusCode': 200, 'body': json.dumps({'message': 'No active subscriptions found for that email.'})}

        print(f"Found {len(subscriptions_to_delete)} subscription(s) to delete.")

        # Step 2: Loop through the results and delete each item
        for item in subscriptions_to_delete:
            table.delete_item(
                Key={
                    'location': item['location'],
                    'user_id': item['user_id']
                }
            )
        
        print(f"Successfully deleted all subscriptions for {email}.")
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'You have been unsubscribed from all flood alerts.'})
        }

    except Exception as e:
        print(f"Error processing unsubscription: {e}")
        return {'statusCode': 500, 'body': json.dumps({'error': 'An internal error occurred.'})}