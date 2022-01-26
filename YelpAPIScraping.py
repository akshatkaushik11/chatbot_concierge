import json
import boto3
# from elasticsearch import Elasticsearch, RequestsHttpConnection
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

TABLE_NAME = 'yelp-restaurants'
SAMPLE_N = '5'
SEARCH_URL = 'https://search-restaurants-i6vpb7aoab5uqzmzg57xczr6fy.us-west-2.es.amazonaws.com'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, 'us-west-2', 'es',session_token=credentials.token)

sqs = boto3.resource('sqs',region_name='us-west-2')
es = OpenSearch(SEARCH_URL, http_auth=awsauth, connection_class=RequestsHttpConnection)


def sendsms(number, message):

    send_sms = boto3.client('sns',region_name='us-west-2')

    smsattrs = {
        'AWS.SNS.SMS.SenderID': {
            'DataType': 'String',
            'StringValue': 'TestSender'
        },
        'AWS.SNS.SMS.SMSType': {
            'DataType': 'String',
            'StringValue': 'Transactional'  # change to Transactional from Promotional for dev
        }
    }
    response = send_sms.publish(
        PhoneNumber=number,
        Message=message,
        MessageAttributes=smsattrs
    )
    print(number)
    print(response)
    print("The message is: ", message)


def search(cuisine):
    data = es.search(index="restaurants", body={"query": {"match": {'cuisine':cuisine}}})
    print("search complete", data['hits']['hits'])
    return data['hits']['hits']


def get_restaurant_data(ids):
    dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
    table = dynamodb.Table('yelp-restaurants')
    ans = 'Hi! Here are your suggestions,\n '
    i = 1
    for id in ids:
        if i<6:
            response = table.get_item(
                Key={
                    'restaurantID': id
                }
            )
            response_item = response.get("Item")
            restaurant_name = response_item['name']

            restaurant_address = response_item['address']
            restaurant_city = response_item['city:']
            restaurant_zipcode = response_item['zip_code']
            restaurant_rating = str(response_item['rating'])
            ans += "{}. {}, located at {}\n".format(i, restaurant_name, restaurant_address)
            # return ans
            i += 1
        else:
            break
    print("db pass")
    return ans # string type


def lambda_handler(event=None, context=None):
    print('Hello')
    queue = sqs.get_queue_by_name(QueueName='restaurant_chatbot')
    messages = queue.receive_messages(MessageAttributeNames=['All'])

    try:
        message = messages[0]
        print('Hello')
        location = message.message_attributes.get('Location').get('StringValue')
        cuisine = message.message_attributes.get('Cuisine').get('StringValue')
        dining_date = message.message_attributes.get('DiningDate').get('StringValue')
        dining_time = message.message_attributes.get('DiningTime').get('StringValue')
        num_people = message.message_attributes.get('PeopleNum').get('StringValue')
        phone = message.message_attributes.get('Phone').get('StringValue')
        print(location, cuisine, dining_date, dining_time, num_people, phone)
        ids = search(cuisine)
        ids = list(map(lambda x: x['_id'], ids))
        rest_details = get_restaurant_data(ids)
        sendsms("+1"+phone, rest_details)
        message.delete()
    except Exception as e:
        print(e)
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda LF2!')
    }

lambda_handler()
