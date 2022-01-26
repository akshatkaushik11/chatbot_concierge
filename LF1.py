import json
import os
import math
import dateutil.parser
import datetime
import time
import logging
import boto3
from botocore.vendored import requests

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


# Utility function to return slot
def get_slots(intent_request):
    return intent_request['currentIntent']['slots']


def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }
    return response


def build_validation_result(is_valid, violated_slot, message_content):
    if message_content is None:
        return {
            "isValid": is_valid,
            "violatedSlot": violated_slot
        }

    return {
        'isValid': is_valid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }


""" --- Functions that control the bot's behavior --- """


def isvalid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False


def parse_int(n):
    try:
        return int(n)
    except ValueError:
        return float('nan')


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }

# Action Functions

def Greeting(intent_request):
    return {
        'dialogAction': {
            "type": "ElicitIntent",
            'message': {
                'contentType': 'PlainText',
                'content': 'Hi there, how can I help you today?'}
        }
    }


def ThankyouIntent(intent_request):
    return {
        'dialogAction': {
            "type": "ElicitIntent",
            'message': {
                'contentType': 'PlainText',
                'content': 'Nice to talk to you! Glad to be of help!'}
        }
    }


def validateIntentSlots(location, cuisine, num_people, date, given_time):
    """
    Perform basic validations to make sure that user has entered expected values for intent slots.
    """

    locations = ['new york', 'manhattan']
    if location is not None and location.lower() not in locations:
        return build_validation_result(False,
                                       'location',
                                       'Sorry! We do not serve recommendations for this location right now!')

    cuisines = ['french', 'indian', 'mexican', 'italian', 'chinese', 'thai']
    if cuisine is not None and cuisine.lower() not in cuisines:
        return build_validation_result(False,
                                       'cuisine',
                                       'We are sorry! We do not serve recommendations for this cuisine right now!')

    if num_people is not None:
        num_people = int(num_people)
        if num_people > 20 or num_people <= 0:
            return build_validation_result(False,
                                           'numPeople',
                                           'Number of people can only be between 0 and 20')

    if date:
        # invalid date
        if not isvalid_date(date):
            return build_validation_result(False, 'date', 'I did not understand that, what date would you like to add?')
        # user entered a date before today
        elif datetime.datetime.strptime(date, '%Y-%m-%d').date() < datetime.date.today():
            return build_validation_result(False, 'date',
                                           'You can search restaurant from today onwards. What day would you like to search?')

    if given_time:
        d = datetime.datetime.now()
        hour, minute = given_time.split(':')
        hour = parse_int(hour)
        minute = parse_int(minute)

        if math.isnan(hour) or math.isnan(minute):
            # Not a valid time; use a prompt defined on the build-time model.
            return build_validation_result(False, 'time', 'Not a valid time')
        if parse_int(d.hour) > hour and d.day == datetime.datetime.strptime(date, '%Y-%m-%d').date().day :
            return build_validation_result(False,'time','This app does not support time travel :) Please enter a valid time')

    return build_validation_result(True, None, None)


def dining_suggestion_intent(intent_request):
    '''
    1. Suggests restaurants based on the slot values that user gave to LEX.
    2. Perform basic validations on the slot values.
    '''

    location = get_slots(intent_request)["location"]
    cuisine = get_slots(intent_request)["cuisine"]
    num_people = get_slots(intent_request)["numPeople"]
    date = get_slots(intent_request)["date"]
    given_time = get_slots(intent_request)["time"]
    phone = get_slots(intent_request)["phone"]
    # emailId = get_slots(intent_request)["email"]
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}

    requestData = {
        "cuisine": cuisine,
        "location": location,
        "limit": "3",
        "peoplenum": num_people,
        "Date": date,
        "Time": given_time,
        "phone":phone
    }

    session_attributes['requestData'] = json.dumps(requestData)

    if intent_request['invocationSource'] == 'DialogCodeHook':
        slots = get_slots(intent_request)

        validation_result = validateIntentSlots(location, cuisine, num_people, date, given_time)
        # If validation fails, elicit the slot again
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            print
            ("elicit slot")
            return elicit_slot(session_attributes,
                               intent_request['currentIntent']['name'],
                               slots,
                               validation_result['violatedSlot'],
                               validation_result['message'])
        return delegate(session_attributes, intent_request['currentIntent']['slots'])

    messageId = sendSQSMessage(requestData)
    print(messageId)

    return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': 'Got all the data, You will receive recommendation soon.'})


def sendSQSMessage(requestData):
    # sqs = boto3.client('sqs',region_name='us-west-2')
    # queue_url = 'https://sqs.us-west-2.amazonaws.com/351860240039/Q1'
    sqs = boto3.resource('sqs', region_name='us-west-2')
    queue = sqs.get_queue_by_name(QueueName='restaurant_chatbot')
    messageAttributes = {
        'Cuisine': {
            'DataType': 'String',
            'StringValue': requestData['cuisine']
        },
        'Location': {
            'DataType': 'String',
            'StringValue': requestData['location']
        },
        'Phone': {
            'DataType': 'Number',
            'StringValue': requestData['phone']
        },
        "DiningTime": {
            'DataType': "String",
            'StringValue': requestData['Time']
        },
        "DiningDate": {
            'DataType': "String",
            'StringValue': requestData['Date']
        },
        'PeopleNum': {
            'DataType': 'Number',
            'StringValue': requestData['peoplenum']
        }
    }
    mesAtrributes = json.dumps(messageAttributes)
    print("mesAtrributes",mesAtrributes)
    response = queue.send_message(
        MessageAttributes=messageAttributes,
        MessageBody=mesAtrributes
    )
    print("response",response)
    return response.get('MessageId')


""" --- Intents --- """


def dispatch(intent_request):
    """
    Dispatches the to the appropriate intent
    """
    intent_name = intent_request['currentIntent']['name']
    # intent_name = 'GreetingIntent'
    # Dispatch to your bot's intent handlers
    if intent_name == 'GreetingIntent':
        return Greeting(intent_request)
    elif intent_name == 'DiningSuggestionsIntent':
        return dining_suggestion_intent(intent_request)
    elif intent_name == 'ThankYouIntent':
        return ThankyouIntent(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported')


# Lambda Handler

def lambda_handler(event, context):
    ''' Send the request to the appropriate intent. '''
    os.environ['TZ'] = 'America/New_York'
    time.tzset()

    return dispatch(event)
