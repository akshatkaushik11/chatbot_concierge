import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth


def put_into_elasticsearch():
    host = 'search-restaurants-i6vpb7aoab5uqzmzg57xczr6fy.us-west-2.es.amazonaws.com'
    region = 'us-west-2'
    service = 'es'
    credentials = boto3.Session().get_credentials()
    print(credentials.token)
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service,session_token=credentials.token)

    es = OpenSearch(
        hosts=[{'host': host, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )
    dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
    table = dynamodb.Table("yelp-restaurants")
    response = None
    while True:
        if response is None:
            response = table.scan()
        else:
            # Scan from where you stopped previously.
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        counter = 0
        for business in response['Items']:
            if not response:
                # Scan from the start.
                response = table.scan()
            restaurantID = business["ID"]
            doc = {
                "ID": restaurantID,
                "cuisine": business["cuisine"]
            }
            es.index(
                index="restaurants",
                doc_type="Restaurant",
                id=restaurantID,
                body=doc,
            )
            check = es.get(index="restaurants", doc_type="Restaurant", id=restaurantID)
            if check["found"]:
                print("Index %s succeeded" % restaurantID)
            counter = counter + 1
# if __name__ == '__main__':
def lambda_handler(event, context):
    put_into_elasticsearch()
