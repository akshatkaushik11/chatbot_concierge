import json
import boto3

def lambda_handler(event, context):
    client = boto3.client('lex-runtime')
    print(event)
    msg = event['messages'][0]['unstructured']['text']
    user_id = 'root'
    lex_bot = 'DiningConciergeBot'
    bot_alias = 'Greeting'
    inputText = msg


    res = client.post_text(
        botName = lex_bot,
        botAlias = bot_alias,
        userId = user_id,
        inputText = inputText
    )
    print(res)
    response = {
        "messages" : [{
            "type" : "unstructured",
            "unstructured" : {
                "text" : res['message']
            }
        }]
    }
    return response
