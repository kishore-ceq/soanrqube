
import json
import boto3
import datetime
import os
import requests

client = boto3.client('ec2')
all_regions=client.describe_regions()
list_of_regions=[]
for each_reg in all_regions['Regions']:
    list_of_regions.append(each_reg['RegionName'])

ct_client = boto3.client('cloudtrail')

# Get the current AWS Account ID
sts = boto3.client("sts")
account_id = sts.get_caller_identity()["Account"]

def lambda_handler(event, context):
    
    client_id = os.environ['CLIENT_ID']
    client_secret = os.environ['CLIENT_SECRET']
    username = os.environ['USERNAME']
    password = os.environ['PASSWORD']
    # #oAuth Response
    url = "https://servicecafedev.service-now.com/oauth_token.do"
    payload="grant_type=password&client_id=" + client_id + "&client_secret=" + client_secret + "&username=" + username + "&password=" + password
    
    headers = {
         'Content-Type': 'application/x-www-form-urlencoded',
         'Cookie': 'BIGipServerpool_servicecafedev=2541902346.40766.0000; JSESSIONID=C0FFB74F88A66ED5E90835E3CB0F8B4D; glide_user_route=glide.8145274ea778054324de3882d975bce4'
    }
    responseSNOW = requests.request("POST", url, headers=headers, data=payload)
    token = json.loads(responseSNOW.text)["access_token"]
    
    result = []
    
    for region in list_of_regions:
        volume = get_volumes(region)
        
        result = result + volume
    
    url = "https://servicecafedev.service-now.com/api/sn_cmp/resource_optimization"
    headers1 = {
      'Authorization': 'Bearer ' + token,
      'Content-Type': 'application/json'
    }   
    
    data = result
    print(data)
   
    #print(json.dumps(data))
    responseSNOW = requests.request("POST", url, headers=headers1, data=json.dumps(data))
    print(responseSNOW)

 
    return {
        # 'statusCode': 200,
        'body': json.loads(json.dumps(result, default=datetime_handler))
        #'data': json.loads(json.dumps(event_res, default=datetime_handler))
    }
    
    
def get_volumes(region):
    outcome = []
    today = datetime.date.today()
    client = boto3.client('ec2', region_name = region)
    ebs_volumes = client.describe_volumes(Filters = [{
                        'Name': 'status',
                        'Values': ['available']
                    }])
    for ebs_volume in ebs_volumes['Volumes']:
       
        event_res = ct_client.lookup_events(LookupAttributes = [{
                        'AttributeKey':'ResourceName',
                        'AttributeValue':ebs_volume['VolumeId']
                    }])
        
        detach_time = ebs_volume['CreateTime']
        #Run a for loop on event_res data
        for ct_event in event_res['Events']:
            if (ct_event['EventName'] == 'DetachVolume'):
                detach_time = ct_event['EventTime']
                break
        
        volume_name = ""
        if('Tags' in ebs_volume):
            for tag in ebs_volume['Tags']:
                if tag['Key'] == "Name":
                    volume_name = tag['Value']
                    break
                
        print(detach_time)
        # Get the number of days since device is 
        idle_days = age_indays(detach_time.date(), today)
        
        outcome.append({
            'id': ebs_volume['VolumeId'],
            'size': ebs_volume['Size'],
            'name': volume_name,
            'disk_type': ebs_volume['VolumeType'],
            'location': region,
            'idle_days': idle_days,
            'provider': "AWS",
            'resource_type': 'disk',
            'account': account_id,
        })
    return outcome
    

def age_indays(last_day, present_day):
    difference = present_day - last_day
    age = difference.days
    return age


    
def datetime_handler(x):
    if isinstance(x, datetime.datetime):
        return x.isoformat()
    raise TypeError("Unknown type")
