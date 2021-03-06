#!/usr/bin/env python

"""happn.py: API for making Happn API calls."""

__author__      = "Rick Housley"
__email__       = "RickyHousley@gmail.com"
__copyright__   = "Copyright 2014"

import requests
import logging
import json
import urllib2
from decouple import config

#Phone specific IDs for generating oauth tokens
CLIENT_ID = config('CLIENT_ID')
CLIENT_SECRET = config('CLIENT_SECRET')

# Default headers for making Happn API calls
headers = {
    'User-Agent':'Happn/19.1.0 AndroidSDK/19',
    'platform': 'android',
    'Host':'api.happn.fr',
    'connection' : 'Keep-Alive',
    'Accept-Encoding':'gzip'
}

httpErrors = {
    200 : 'OK',
    201 : 'Created',
    202 : 'Accepted',
    203 : 'Non-authoritative Information',
    204 : 'No Content',
    205 : 'Reset Content',
    206 : 'Partial Content',
    207 : 'Multi-Status',
    208 : 'Already Reported',
    226 : 'IM Used',
    300 : 'Multiple Choices',
    301 : 'Moved Permanently',
    302 : 'Found',
    303 : 'See Other',
    304 : 'Not Modified',
    305 : 'Use Proxy',
    307 : 'Temporary Redirect',
    308 : 'Permanent Redirect',
    400 : 'Bad Request',
    401 : 'Unauthorized',
    402 : 'Payment Required',
    403 : 'Forbidden',
    404 : 'Not Found',
    405 : 'Method Not Allowed',
    406 : 'Not Acceptable',
    407 : 'Proxy Authentication Required',
    408 : 'Request Timeout',
    409 : 'Conflict',
    410 : 'Gone',
    411 : 'Length Required',
    412 : 'Precondition Failed',
    413 : 'Payload Too Large',
    414 : 'Request-URI Too Long',
    415 : 'Unsupported Media Type',
    416 : 'Requested Range Not Satisfiable',
    417 : 'Expectation Failed',
    418 : 'I\'m a teapot',
    421 : 'Misdirected Request',
    422 : 'Unprocessable Entity',
    423 : 'Locked',
    424 : 'Failed Dependency',
    426 : 'Upgrade Required',
    428 : 'Precondition Required',
    429 : 'Too Many Requests',
    431 : 'Request Header Fields Too Large',
    444 : 'No Response (Nginx)',
    451 : 'Unavailable For Legal Reasons',
    499 : 'Client Closed Request',
    500 : 'Internal Server Error',
    501 : 'Not Implemented',
    502 : 'Bad Gateway',
    503 : 'Service Unavailable',
    504 : 'Gateway Timeout',
    505 : 'HTTP Version Not Supported',
    506 : 'Variant Also Negotiates',
    507 : 'Insufficient Storage',
    508 : 'Loop Detected',
    510 : 'Not Extended',
    511 : 'Network Authentication Required',
    522 : 'Connection timed out, server denied request for OAuth token',
    599 : 'Network Connect Timeout Error',
    #@TODO Add full list
}

class Relations(object):
    none  = 0
    liked  = 1
    matched = 4

class User:
    """ User class for making Happn API calls from """

    def __init__(self, fbtoken=None, latitude=None, longitude=None):
        """ Constructor for generating the Happn User object
            :param fbtoken Facebook user access token used to fetch the Happn OAuth token
            :param latitude Latitude to position the User
            :param longitude Longitude to position the User
        """
        self.fbtoken = fbtoken
        self.oauth, self.id = self.get_oauth()

        if (latitude and longitude) is None:
            self.lat = None
            self.lon = None
        else:
            self.set_position(latitude, longitude)

        logging.debug('Happn User Generated. ID: %s', self.id)

    def set_position(self, latitude, longitude):
        """ Set the position of the user using Happn's API
            :param latitude Latitude to position the User
            :param longitude Longitude to position the User
        """

        # Create & Send the HTTP Post to Happn server
        h=headers
        h.update({
            'Authorization' : 'OAuth="'+ self.oauth + '"',
            'Content-Length':  53, #@TODO Figure out length calculation
            'Content-Type'  : 'application/json'
            })

        url = 'https://api.happn.fr/api/users/' + self.id + '/position/'
        payload = {
            "alt"       : 0.0,
            "latitude"  : round(latitude,7),
            "longitude" : round(longitude,7)
        }
        r = requests.post(url,headers=h,data=json.dumps(payload))

        # Check status of Position Update
        if r.status_code == 200:    #OK HTTP status
            self.lat = latitude
            self.lon = longitude
            logging.debug('Set User position at %f, %f', self.lat, self.lon)
        else:
            # Status failed, get the current location according to the server
            #@TODO IMPLEMENT ^
            self.lat = latitude
            self.lon = longitude

            logging.warning("""Server denied request for position change: %s,
                                will revert to server known location""", httpErrors[r.status_code])

            # If unable to change location raise an exception
            raise HTTP_MethodError(httpErrors[r.status_code])


    def set_device(self):
        """ Set device, necessary for updating position
            :TODO Add params for settings
        """

        # Create and send HTTP PUT to Happn server
        h=headers
        h.update({
          'Authorization'   : 'OAuth="'+ self.oauth + '"',
          'Content-Length'  :  342, #@TODO figure out length calculation
          'Content-Type'    : 'application/json'})

        # Device specific payload, specific to my phone. @TODO offload to settings file?
        payload ={
            "app_build" : config('APP_BUILD'),
            "country_id": config('COUNTRY_ID'),
            "gps_adid"  : config('GPS_ADID'),
            "idfa"      : config('IDFA'),
            "language_id":"en",
            "os_version": config('OS_VERSION'),
            "token"     : config('GPS_TOKEN'),
            "type"      : config('TYPE')
        }

        url = 'https://api.happn.fr/api/users/' + self.id + '/devices/'+ config('DEVICE_ID')
        try:
            r = requests.put(url,headers=h,data=json.dumps(payload))
        except Exception as e:
            raise HTTP_MethodError('Error Setting Device: {}'.format(e))

        if r.status_code == 200: #200 = 'OK'
            logging.debug('Device Set')
        else:
            # Device set denied by server
            logging.warning('Server denied request for device set change: %d', r.status_code)
            raise HTTP_MethodError(httpErrors[r.status_code])

    def set_settings(self, settings):
        h=headers
        h.update({
          'Authorization'   : 'OAuth="'+ self.oauth + '"',
          'Content-Length'  :  1089, #@TODO figure out length calculation
          'Content-Type'    : 'application/json'})

        # Happn preferences
        url = 'https://api.happn.fr/api/users/' + self.id
        try:
            r = requests.put(url, headers=h, data = json.dumps(settings))
        except Exception as e:
            raise HTTP_MethodError('Error Setting Settings: {}'.format(e))

        if r.status_code == 200: #200 = 'OK'
            logging.debug('Updated Settings')
        else:
            # Unable to fetch distance
            raise HTTP_MethodError(httpErrors[r.status_code])


    def get_distance(self, userID):
        """ Fetches the distance from another user
            :param userID User ID of target user.
        """

        # Create and send HTTP Get to Happn server
        h=headers
        h.update({
            'Authorization' : 'OAuth="' + self.oauth+'"',
            'Content-Type'  : 'application/json',
        })
        #@TODO Trim query to just distance request
        query='{"fields":"id,first_name,gender,last_name,birth_date,login,workplace,distance"}'
        url = 'https://api.happn.fr/api/users/' + str(userID) + '?' + urllib2.quote(query)

        try:
            r = requests.get(url, headers=h)
        except Exception as e:
            raise HTTP_MethodError('Error Connecting to Happn Server: {}'.format(e))

        if r.status_code == 200: #200 = 'OK'
            self.distance = r.json()['data']['distance']
            logging.info('Sybil %d m from target',self.distance)
        else:
            raise HTTP_MethodError(httpErrors[r.status_code])


    def get_oauth(self):
        """ Gets the OAuth tokens using Happn's API """

        # Create and send HTTP POST to Happn server
        h=headers
        h.update({
            'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',
            'Content-Length': '374'
            })

        payload = {
            'client_id'     : CLIENT_ID,
            'client_secret' : CLIENT_SECRET,
            'grant_type'    : 'assertion',
            'assertion_type': 'facebook_access_token',
            'assertion'     : self.fbtoken,
            'scope'         : 'mobile_app'
        }
        url = 'https://api.happn.fr/connect/oauth/token'
        try:
            r = requests.post(url,headers=h,data=payload)
        except Exception as e:
            raise HTTP_MethodError('Error Connecting to Happn Server: {}'.format(e))

        # Check response validity
        if r.status_code == 200: #200 = 'OK'
            logging.debug('Fetched Happn OAuth token:, %s', r.json()['access_token'])
            return r.json()['access_token'], r.json()['user_id']
        else:
            # Error code returned from server (but server was accessible)
            logging.warning('Server denied request for OAuth token. Status: %d', r.status_code)
            raise HTTP_MethodError(httpErrors[r.status_code])


    #@TODO Update with more query fields (last name, birthday, etc)
    def get_user_info(self, userID):
        """ Fetches userInfo
            :param userID User ID of target user.

            Returns dictionary packed with:
                user id, facebook id, twitter id (not implemented), first name, last name,
                birth date, login (nulled), workplace, distance
        """
        h={ #For some reason header update doesnt work
            'http.useragent' : 'Happn/1.0 AndroidSDK/0',
            'Authorization'  : 'OAuth="' + self.oauth+'"',
            'Content-Type'   : 'application/json',
            'User-Agent'     : 'Happn/19.1.0 AndroidSDK/19',
            'Host'           : 'api.happn.fr',
            'Connection'     : 'Keep-Alive',
            'Accept-Encoding': 'gzip'
        }

        query = '?query=%7B%22fields%22%3A%22about%2Cis_accepted%2Cfirst_name%2Cage%2Cjob%2Cworkplace%2Cmodification_date%2Cprofiles.mode%281%29.width%28720%29.height%281280%29.fields%28url%2Cwidth%2Cheight%2Cmode%29%2Clast_meet_position%2Cmy_relation%2Cis_charmed%2Cdistance%2Cgender%2Cmy_conversation%22%7D'
        url = 'https://api.happn.fr/api/users/' + userID + query
        try:
            r = requests.get(url, headers=h)
        except Exception as e:
            raise HTTP_MethodError('Error Connecting to Happn Server: {}'.format(e))

        # Check if successful
        if r.status_code == 200: #200 = 'OK'
            # Load response into a python dictionary, syntax seems redundant
            return json.loads(json.dumps(r.json()['data'], sort_keys=True, indent=4, separators=(',', ': ')))
        else:
            raise HTTP_MethodError(httpErrors[r.status_code])
    
            
    def get_recommendations(self, limit=16, offset=0):
        """ Get recs from Happn server
            :param limit Number of reccomendations to recieve
            :param offset Offset index for reccomendation list
        """
        
        # Create and send HTTP Get to Happn server
        h={ #For some reason header update doesnt work
            'http.useragent' : 'Happn/1.0 AndroidSDK/0',
            'Authorization'  : 'OAuth="' + self.oauth+'"',
            'Content-Type'   : 'application/json',
            'User-Agent'     : 'Happn/19.1.0 AndroidSDK/19',
            'Host'           : 'api.happn.fr',
            'Connection'     : 'Keep-Alive',
            'Accept-Encoding': 'gzip'
        }
        query = '{"types":"468","limit":'+str(limit)+',"offset":'+str(offset)+',"fields":"id,modification_date,notification_type,nb_times,notifier.fields(id,job,is_accepted,workplace,my_relation,distance,gender,my_conversation,is_charmed,nb_photos,first_name,age,profiles.mode(1).width(360).height(640).fields(width,height,mode,url))"}'
        url = 'https://api.happn.fr/api/users/' + self.id +'/notifications/?query=' + urllib2.quote(query)

        try:
            r = requests.get(url, headers=h)
        except Exception as e:
            raise HTTP_MethodError('Error Connecting to Happn Server: {}'.format(e))
            
        if r.status_code == 200: #200 = 'OK'
            return json.loads(json.dumps(r.json()['data'], sort_keys=True, indent=4, separators=(',', ': ')))
        else:
            raise HTTP_MethodError(httpErrors[r.status_code])
            
    def get_declined(self, limit=128, offset=0):
        """ Get declined people from Happn server
            :param limit Number of people to recieve
            :param offset Offset index for reccomendation list
        """
        
        # Create and send HTTP Get to Happn server
        h={ #For some reason header update doesnt work
            'http.useragent' : 'Happn/1.0 AndroidSDK/0',
            'Authorization'  : 'OAuth="' + self.oauth+'"',
            'Content-Type'   : 'application/json',
            'User-Agent'     : 'Happn/19.1.0 AndroidSDK/19',
            'Host'           : 'api.happn.fr',
            'Connection'     : 'Keep-Alive',
            'Accept-Encoding': 'gzip'
        }
        query = '{"types":"468","limit":'+str(limit)+',"offset":'+str(offset)+',"fields":"is_charmed,modification_date,age,id,my_relation,distance,first_name"}'
        url = 'https://api.happn.fr/api/users/me/rejected?' + urllib2.quote(query)

        try:
            r = requests.get(url, headers=h)
        except Exception as e:
            raise HTTP_MethodError('Error Connecting to Happn Server: {}'.format(e))
            
        if r.status_code == 200: #200 = 'OK'
            return json.loads(json.dumps(r.json()['data'], sort_keys=True, indent=4, separators=(',', ': ')))
        else:
            raise HTTP_MethodError(httpErrors[r.status_code])
    
    def set_matching_age_min(self, age):
        """ Set matching min. age
            :mininum age to like
        """

        # Create and send HTTP PUT to Happn server
        h = headers
        h.update({
            'Authorization' : 'OAuth="'+ self.oauth + '"',
            'Content-Type'  : 'application/x-www-form-urlencoded; charset=UTF-8',
            'Content-Length': '20'
        })
        payload = {
            'matching_age_min' : age
        }
        url = 'https://api.happn.fr/api/users/' + self.id
        try:
            r = requests.put(url, headers=h, data = payload,verify=False)
        except Exception as e:
            raise HTTP_MethodError('Error Connecting to Happn Server: {}'.format(e))

        if r.status_code == 200: #200 = 'OK'
            logging.debug('Set minimum accept age to '+str(age))
        else:
            # Unable to fetch distance
            raise HTTP_MethodError(httpErrors[r.status_code])
            
            
    def set_matching_age_max(self, age):
        """ Set matching max. age
            :maximum age to like
        """

        # Create and send HTTP PUT to Happn server
        h = headers
        h.update({
            'Authorization' : 'OAuth="'+ self.oauth + '"',
            'Content-Type'  : 'application/x-www-form-urlencoded; charset=UTF-8',
            'Content-Length': '20'
        })
        payload = {
            'matching_age_max' : age
        }
        url = 'https://api.happn.fr/api/users/' + self.id
        try:
            r = requests.put(url, headers=h, data = payload,verify=False)
        except Exception as e:
            raise HTTP_MethodError('Error Connecting to Happn Server: {}'.format(e))

        if r.status_code == 200: #200 = 'OK'
            logging.debug('Set maximum accept age to '+str(age))
        else:
            # Unable to fetch distance
            raise HTTP_MethodError(httpErrors[r.status_code])
    
    def update_activity(self):
        """ Updates User activity """

        # Create and send HTTP PUT to Happn server
        h = headers
        h.update({
            'Authorization' : 'OAuth="'+ self.oauth + '"',
            'Content-Type'  : 'application/x-www-form-urlencoded; charset=UTF-8',
            'Content-Length': '20'
        })
        payload = {
            'update_activity' :  'true'
        }
        url = 'https://api.happn.fr/api/users/'+self.id
        try:
            r = requests.put(url, headers=h, data = payload)
        except Exception as e:
            raise HTTP_MethodError('Error Connecting to Happn Server: {}'.format(e))

        if r.status_code == 200: #200 = 'OK'
            logging.debug('Updated User activity')
        else:
            # Unable to fetch distance
            raise HTTP_MethodError(httpErrors[r.status_code])

    def like_user(self, user_id):
        """ Like user
            :user_id id of the user to like
        """

        # Create and send HTTP PUT to Happn server
        h = headers
        h.update({
            'Authorization' : 'OAuth="'+ self.oauth + '"',
            'Content-Type'  : 'application/x-www-form-urlencoded; charset=UTF-8',
            'Content-Length': '20'
        })
        payload = {
            'id' :  user_id
        }
        url = 'https://api.happn.fr/api/users/' + self.id +'/accepted/'+str(user_id)
        try:
            r = requests.post(url, headers=h, data = payload)
        except Exception as e:
            raise HTTP_MethodError('Error Connecting to Happn Server: {}'.format(e))

        if r.status_code == 200: #200 = 'OK'
            logging.debug('Liked User '+str(user_id))
        else:
            # Unable to fetch distance
            raise HTTP_MethodError(httpErrors[r.status_code])
    
    def unreject_user(self, user_id):
        """ Un-decline user
            :user_id id of the user to unreject
        """

        # Create and send HTTP DELETE to Happn server
        h = headers
        h.update({
            'Authorization' : 'OAuth="'+ self.oauth + '"',
            'Content-Type'  : 'application/x-www-form-urlencoded; charset=UTF-8',
            'Content-Length': '20'
        })
        payload = {
            'id' :  user_id
        }
        url = 'https://api.happn.fr/api/users/me/rejected/'+str(user_id)
        try:
            r = requests.delete(url, headers=h, data = payload,verify=False)
        except Exception as e:
            raise HTTP_MethodError('Error Connecting to Happn Server: {}'.format(e))

        if r.status_code == 200: #200 = 'OK'
            logging.info('Un-declined User '+str(user_id))
			
        else:
            # Unable to fetch distance
            raise HTTP_MethodError(httpErrors[r.status_code])
    
    def decline_user(self, user_id):
        """ Decline user
            :user_id id of the user to decline
        """

        # Create and send HTTP PUT to Happn server
        h = headers
        h.update({
            'Authorization' : 'OAuth="'+ self.oauth + '"',
            'Content-Type'  : 'application/x-www-form-urlencoded; charset=UTF-8',
            'Content-Length': '20'
        })
        payload = {
            'id' :  user_id
        }
        url = 'https://api.happn.fr/api/users/' + self.id +'/rejected/'+str(user_id)
        try:
            r = requests.post(url, headers=h, data = payload)
        except Exception as e:
            raise HTTP_MethodError('Error Connecting to Happn Server: {}'.format(e))

        if r.status_code == 200: #200 = 'OK'
            logging.debug('Declined User '+str(user_id))
        else:
            # Unable to fetch distance
            raise HTTP_MethodError(httpErrors[r.status_code])


class HTTP_MethodError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
