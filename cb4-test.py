#!/usr/bin/env python

import hashlib
import time
import urllib #for url encoding
import urllib2 #for sending requests
import base64
import datetime
from datetime import date, timedelta
import clearbit
from clearbit import Enrichment as cb_enc
import calendar
import pandas as pd
import json
import gspread
from oauth2client.client import SignedJwtAssertionCredentials
import traceback
import sys

clearbit.key = '906cf0605ba68c6dfc2a331f1a552b96'
email_list = []


# # Get users!

# In[25]:



try:
    import json
except ImportError:
    import simplejson as json

class Mixpanel(object):

   def __init__(self, api_key, api_secret, token):
       self.api_key = api_key
       self.api_secret = api_secret
       self.token = token

   def request(self, params, format = 'json'):
       '''let's craft the http request'''
       params['api_key']=self.api_key
       params['expire'] = int(time.time())+600 # 600 is ten minutes from now
       if 'sig' in params: del params['sig']
       params['sig'] = self.hash_args(params)

       request_url = 'http://mixpanel.com/api/2.0/engage/?' + self.unicode_urlencode(params)

       request = urllib.urlopen(request_url)
       data = request.read()

       #print request_url

       return data

   def hash_args(self, args, secret=None):
       '''Hash dem arguments in the proper way
       join keys - values and append a secret -> md5 it'''

       for a in args:
           if isinstance(args[a], list): args[a] = json.dumps(args[a])

       args_joined = ''
       for a in sorted(args.keys()):
           if isinstance(a, unicode):
               args_joined += a.encode('utf-8')
           else:
               args_joined += str(a)

           args_joined += "="

           if isinstance(args[a], unicode):
               args_joined += args[a].encode('utf-8')
           else:
               args_joined += str(args[a])

       hash = hashlib.md5(args_joined)

       if secret:
           hash.update(secret)
       elif self.api_secret:
           hash.update(self.api_secret)
       return hash.hexdigest()

   def unicode_urlencode(self, params):
       ''' Convert stuff to json format and correctly handle unicode url parameters'''

       if isinstance(params, dict):
           params = params.items()
       for i, param in enumerate(params):
           if isinstance(param[1], list):
               params[i] = (param[0], json.dumps(param[1]),)

       result = urllib.urlencode([(k, isinstance(v, unicode) and v.encode('utf-8') or v) for k, v in params])
       return result


# In[26]:

# Secret Stuff!
api = Mixpanel(
    api_key = 'a44c33645f6868776261a18b2bf2d746',
    api_secret = 'f8f3514e18b8963488e058d7457e9a6d',
    token = 'ad6df61d0b9400400b240631576c24d4'
)
'''Here is the place to define your selector to target only the users that you're after'''
'''parameters = {'selector':'(properties["$email"] == "Albany") or (properties["$city"] == "Alexandria")'}'''

yesterday = datetime.datetime.now() - timedelta(hours=24)
yesterday = yesterday.strftime("%s")
today = datetime.datetime.utcnow().strftime("%s")

parameters = {'selector': '(datetime('+yesterday+') < properties["date_joined"]     and not ".org" in properties["$email"] and not ".net" in properties["$email"]     and not".edu" in properties["$email"] and not"k12" in properties["$email"]     and not"schools" in properties["$email"])'}
print parameters
response = api.request(parameters)

try:
    parameters['session_id'] = json.loads(response)['session_id']
except:
    print json.loads(response)

parameters['page']=0
global_total = json.loads(response)['total']

print "Session id is %s \n" % parameters['session_id']
print "Here are the # of people %d" % global_total
fname = "output_people.txt"
has_results = True
total = 0
with open(fname,'w') as f:
    while has_results:
        responser = json.loads(response)['results']
        total += len(responser)
        has_results = len(responser) == 1000
        for data in responser:
            if not (u'platform_python' in data['$properties']):
                data['$properties'][u'platform_python'] = False
            if not (u'platform_matlab' in data['$properties']):
                data['$properties'][u'platform_matlab'] = False
            if not (u'platform_r' in data['$properties']):
                data['$properties'][u'platform_r'] = False
            email_list.append( [data['$properties']['$email'], data['$properties']['platform_python'],
                                data['$properties'][u'platform_matlab'], data['$properties'][u'platform_r']] )
            data_list.append(data)
            #f.write(data['$properties']['$email']+'\n')
        print "%d / %d" % (total,global_total)
        parameters['page'] += 1
        if has_results:
            response = api.request(parameters)


# In[ ]:

if email_list == []:
    print "no emails found"
    sys.exit("no emails found")


# # Call Clearbit

# In[3]:

users = {}
for em in email_list[0:10]:
    if em[0] != '' and '@' in em[0]:
        users[em[0]] = dict(
            python = em[1],
            matlab = em[2],
            r = em[3]
        )
        try:
            resp = cb_enc.find(email=em[0],stream=True)
        except:
            print 'error finding email ', em[0]
            print traceback.print_exc()
        try:
            users[em[0]]['company'] = resp['person']['employment']['name']
        except:
            pass
        try:
            users[em[0]]['title'] = resp['person']['employment']['title']
        except:
            pass
        try:
            users[em[0]]['full_name'] = resp['person']['name']['fullName']
        except:
            pass
        try:
            users[em[0]]['sector'] = resp['company']['category']['sector']
        except:
            pass
        try:
            users[em[0]]['employees'] = resp['company']['metrics']['employees']
        except:
            pass
        try:
            users[em[0]]['phone_numbers'] = resp['company']['site']['phoneNumbers']
        except:
            pass
        try:
            users[em[0]]['country'] = resp['person']['geo']['country']
        except:
            pass
        try:
            users[em[0]]['city'] = resp['person']['geo']['city']
        except:
            pass


# In[ ]:

if users == {}:
    sys.exit("no users found")


# In[4]:

print users


# # Sort in Pandas

# In[5]:

df = pd.DataFrame.from_dict(users).transpose().reset_index()


# In[8]:

df.head()


# In[9]:

df = df.sort_values(['company'],ascending=[1])


# In[10]:

df_list = df.values.tolist()


# In[11]:

cols = list(df.columns)
cols = [ ea.upper() for ea in cols ]
cols.pop(0)
cols.insert(0,'EMAIL')
cols


# In[12]:

df_list.insert(0,cols)


# In[13]:

print df_list[0:3]


# # Connect to Google sheets!

# In[14]:

now = datetime.datetime.now()
MONTH = 'CB-'+ (calendar.month_name[ now.month ]).upper()
print MONTH


# In[15]:

sheets_auth = {
  "type": "service_account",
  "project_id": "clearbit-leads",
  "private_key_id": "f2e333a5b7e968f11e553d37021e7b95ff70ca66",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQCND8qBOIh8VKPX\nWbnGy6daOjfoGPntqWzULD3cyoqW9h7SgDq0jZrYX5Y4KtI0uHJATX8WAWPsg8ip\ndTPkqdonT1DC48ZAe4cmQzBXhEmmeJOmdt53gNUSmB97hIXOyuNn5WX+avmU2tFF\na3JhMWyplsNRPxZ/L2xyN334WDZWT3XPN7rPb66wQhFMaFMkDvs8NEH+yboyddhL\npQM8lshql7KHDhRX3Whp49nDX59P6T/hF01auHqmzXad9j3JNieBg8MKMAPtv2hn\nOAwcauZfC/m4Onxf2cF/PjcQx/vz7F1AyhXN92206WvD284d9B8Si/R3w2fs3+oV\n63CAge65AgMBAAECggEAah8vIff99ktW13RRJxWfWWnjFWF05S9JCHYgNDLMALY4\nifSeNacyjwWaZbcRXUhF68phiZSSMCUUmSfrWmPOEzTAdV4Wj/xeuJJjk/OZ1Ptx\nWRKkWxM5OTvos2wHnoNUgZ07FiQ0j5/vQGKNMkGUliEt37mumxB6bZMB2gvDFTqi\n97+/KOfXa5wgc5jo66b4AHxWrz9n1zkhaO1LpGe8UeFix1aXUrieKeSi5OMatHrl\nXdbm+TX1pyFy5s+225XDF/6K5U+0vw4YFhXMGerdGRIhpCo+kw4lbk0h0FO1gKCK\nTFpffCLvAm+uTjfqS4WI6a5KQp5yYJuINojffv4Q4QKBgQDR4E+Egh6fk+F6Ociw\nVDFThI3GSQdXf0KR/pQxHlqmEPH7ObE1oP3LBLCJuHCYJQXFJQjAxLsBZj1Kly3b\nzVlOnqFyy1vEhkUzV1HTVbTYQdOqXgveogZ/HrWl1c2BLurV+BLsU/b9Z4w3Us5c\ntuPeNtlAhXx5fqp/B/jYgEigLwKBgQCsD/UYOZdXCYAjWUXj1k4J4ADABZBreMBA\nhDw0WN6LeZok6vOefU1FZ4MVLNba2TIEwyNAch32YWIN061afWV5Jv+KliuiJZ/j\nC0INKZ53b0MN5ZsO59ZfQ7vzEOnAPY9dwxATTYsTr4aSs+WQSgd3PFyS4JQAFtK4\nGN3VujP9lwKBgHtRfeeyPSQu1FHpGg7hqYoVXOihiHrU/9yg5Zpm54SkeErRf1qv\nmfBsdP63LRF4z4cjV51M+0S7OlBVvFBmvI8BjoPREb7L1mVwbVfsCDL5mtGEKR1L\nvt16wekLU5EQbFQFS7kpLPuAmFb5hN/dZs7vE4Bh7t3Em5HAsWslFYdpAoGBAICl\nTbNXG/hPeibz0HWQ/bgUa3smrdws5FFYjUr2Ry4xNTb1FEEjnmqOAkwKwnnOer9k\nxy6gJBbaqN19rtdBemUi611K+kS5rNmsyS3eOEVEQvZY/Z4faQDBO/14X80EOfT4\nq0RDbgDB8/Qr3TAMqZhU4UJP91g5uEM9FF+AYO7xAoGBAL/4Lsdyx6r+2asCebUM\nHsOx9ol8AO3vYWz4r2oJ3DS0r6HfMy/JzISZJvmhsbtHynWIpRP12JFWfPwQkXJg\n2/HOOzqdqLSgKOQYC9mPhYNUaL6Y87ygkG/EVJJ+tZsCp2BvRs85R1tHJwulwiR7\nVZQ/67tHa2tikUJcNUAvw3Kq\n-----END PRIVATE KEY-----\n",
  "client_email": "jack-leads@clearbit-leads.iam.gserviceaccount.com",
  "client_id": "100772913091370034587",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://accounts.google.com/o/oauth2/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/jack-leads%40clearbit-leads.iam.gserviceaccount.com"
}


# In[16]:

#json_key = json.load(open('/Users/jackparmer/Downloads/ClearBit Leads-f2e333a5b7e9.json'))
json_key = sheets_auth

scope = ['https://spreadsheets.google.com/feeds']

credentials = SignedJwtAssertionCredentials(json_key['client_email'],                                             json_key['private_key'].encode(), scope)

gc = gspread.authorize(credentials)

print json_key['client_email']

wks = gc.open(MONTH)


# # Last step! Write to google drive

# In[ ]:

# Get Worksheet

DAY = 'DAY-test'

try:
    sh = wks.worksheet(DAY)
except:
    sh = wks.add_worksheet(title=DAY, rows="600", cols="25")

if sh == None:
    sh = wks.add_worksheet(title=DAY, rows="600", cols="25")

print "GETTING SHEET", DAY

# In[ ]:

# Test connection / auth by writing dummy data

cell_list = sh.range('A1:A7')
cell_values = [1,2,3,4,5,6,7]

for i, val in enumerate(cell_values):  #gives us a tuple of an index and value
    cell_list[i].value = val    #use the index on cell_list and the val from cell_values

print 'updating '+str(sh)

sh.update_cells(cell_list)


# In[ ]:

row_num = 1
for row in df_list:
    print 'Adding row... ' + str(row)
    try:
        query = 'A'+str(row_num)+':L'+str(row_num)
        print 'RANGE QUERY:', query
        cell_list = sh.range(query)
        cell_values = row
        print cell_values
        for i, val in enumerate(cell_values):  #gives us a tuple of an index and value
            cell_list[i].value = val
        sh.update_cells(cell_list)
    except:
        print 'Issue with row '+str(row)
        traceback.print_exc()
    row_num = row_num+1


# In[ ]:
