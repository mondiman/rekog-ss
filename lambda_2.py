from __future__ import print_function

import boto3
from decimal import Decimal
import json
import urllib

from copy import deepcopy

from httplib import HTTPSConnection
#from urlparse import urlparse

print('Loading function')

rekognition = boto3.client('rekognition')
client = boto3.client('sns')

rekog_max_labels = 10
rekog_min_conf = 80.0
label_watch_list = ["Human", "People", "Person", "Automobile", "Car"]
label_watch_min_conf = 80.0

# --------------- Helper Functions to call Rekognition APIs ------------------

def detect_labels(bucket, key):
    response = rekognition.detect_labels(Image={"S3Object": {"Bucket": bucket, "Name": key}}, MaxLabels=rekog_max_labels, MinConfidence=rekog_min_conf,)


    return response


    
# --------------- Main handler ------------------


def lambda_handler(event, context):
    '''Demonstrates S3 trigger that uses
    Rekognition APIs to detect faces, labels and index faces in S3 Object.
    '''
    #print("Received event: " + json.dumps(event, indent=2))

    # Get the object from the event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.unquote_plus(event['Records'][0]['s3']['object']['key'].encode('utf8'))
    try:
        # Calls rekognition DetectFaces API to detect faces in S3 object
        # response = detect_faces(bucket, key)

        # Calls rekognition DetectLabels API to detect labels in S3 object
        response = detect_labels(bucket, key)

        for record in event['Records']:
            filename = record['s3']['object']['key'];
            #filesize = record['s3']['object']['size'];
            #source = record['requestParameters']['sourceIPAddress'];
            eventTime = record['eventTime'];
    
     #Iterate on rekognition labels. Enrich and prep them for storage in DynamoDB
        labels_on_watch_list = []
        for label in response['Labels']:
            
            lbl = label['Name']
            conf = label['Confidence']
            label['OnWatchList'] = False

            #Print labels and confidence to lambda console
            print('{} .. conf %{:.2f}'.format(lbl, conf))

            #Check label watch list and trigger action
            if (lbl.upper() in (label.upper() for label in label_watch_list)
                and conf >= label_watch_min_conf):

                label['OnWatchList'] = True
                labels_on_watch_list.append(deepcopy(label))
                
        tosend=""
        
        for Label in response["Labels"]:
            print ('{0} - {1}%'.format(Label["Name"], Label["Confidence"]))
            tosend+= '{0} - {1}%'.format(Label["Name"], round(Label["Confidence"], 2))
            
        # Calls rekognition IndexFaces API to detect faces in S3 object and index faces into specified collection
        #response = index_faces(bucket, key)

        # Print response to console.
        print(response)
        
        def pushover_handler(message):
            """ Send parsed message to Pushover """
            #logger.info('Received message' + json.dumps(message))
            conn = HTTPSConnection("api.pushover.net:443")
            conn.request("POST", "/1/messages.json",
                        urllib.urlencode({
                            "token": '----',
                            "user": '----',
                            "message": filename+"  "+tosend,
                            "sound": 'pushover',
                            "priority": 0,
                            "title": "SecuritySpy"
                        }), {"Content-type": "application/x-www-form-urlencoded"})
            response = conn.getresponse()
            return response.status
    
        if len(labels_on_watch_list) > 0:
            return pushover_handler(tosend)
        
        return response
    except Exception as e:
        print(e)
        print("Error processing object {} from bucket {}. ".format(key, bucket) +
              "Make sure your object and bucket exist and your bucket is in the same region as this function.")
        raise e
