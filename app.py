#!/usr/bin/env python
from __future__ import print_function
from future.standard_library import install_aliases
install_aliases()

from urllib.parse import urlparse, urlencode
from urllib.request import urlopen, Request
from urllib.error import HTTPError

import json
import os
import requests
import codecs

from datetime import datetime

from flask import Flask
from flask import request
from flask import make_response

# Flask app should start in global layout
app = Flask(__name__)


@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)
    print("Request:")
    print(json.dumps(req, indent=4))

    #res = processRequest(req)
    res = test(req)
    
    res = json.dumps(res, indent=4)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r


def test(req):    
    result = req.get("result")
    parameters = result.get("parameters")
    s_city = parameters.get("geo-city")
    s_day = str(parameters.get("date"))
    if s_city == "":
		s_city = u"Алматы"
	
    appid = "01e9d712127bbffa4c9e669f39d3a127"
    lang = "ru"
    try:
	if s_day == "":
		res = requests.get("http://api.openweathermap.org/data/2.5/find",
				params={'q': s_city, 'type': 'like', 'lang': lang, 'units': 'metric', 'APPID': appid}) 
		data = res.json()
		temp = str(int(round(data['list'][0]['main']['temp'])))
		description = data['list'][0]['weather'][0]['description']
		description = localize(description)
		speech = u"Сегодня в "+s_city+" "+description+ u", температура "+temp + u" °C "
	else:
		d1 = datetime.strptime(s_day, "%Y-%m-%d").date()
		d2 = datetime.today().date()	
		cnt = (d1-d2).days        
		if cnt>=0 and cnt<17:
			res = requests.get("http://api.openweathermap.org/data/2.5/forecast/daily",
					params={'q': s_city, 'type': 'like', 'lang': lang, 'units': 'metric', 'APPID': appid, 'cnt': cnt+1})        
			data = res.json()
			temp = str(int(round(data['list'][cnt]['temp']['day'])))
			description = data['list'][cnt]['weather'][0]['description']
			description = localize(description)
			speech = u"Погода на " + s_day +  u" в " +s_city+": "+description+ u", температура "+temp + u" °C "
		elif cnt>16: 
			speech = u"Так далеко я не могу предсказать."
		else:
			speech = u"Прости, прошлое вне моей погодной компетенции..."
    except Exception as e:
        speech = u"Кажется такого города не существует..." + str(e)
        pass
    
    return {
        "speech": speech,
        "displayText": speech,
        # "data": data,
        # "contextOut": [],
        "source": "apiai-weather-webhook-sample"
    }

def localize(desc):
	if desc=="shower sleet":
		return u"снегопад"
	return desc

def localizeDay(day):
    if day=="Mon" or day==0:
        return u"Понедельник"
    elif day=="Tue" or day==1:
        return u"Вторник"
    elif day=="Wed" or day==2:
        return u"Среда"
    elif day=="Thu" or day==3:
        return u"Четверг"
    elif day=="Fri" or day==4:
        return u"Пятница"
    elif day=="Sat" or day==5:
        return u"Суббота"
    elif day=="Sun" or day==6:
        return u"Воскресенье"
    return u"Нет такого дня"

def processRequest(req):
    if req.get("result").get("action") != "yahooWeatherForecast":
        return {}
    baseurl = "https://query.yahooapis.com/v1/public/yql?"
    yql_query = makeYqlQuery(req)
    if yql_query is None:
        return {}
    yql_url = baseurl + urlencode({'q': yql_query}) + "&format=json"
    result = urlopen(yql_url).read()
    data = json.loads(result)
    res = makeWebhookResult(data)
    return res


def makeYqlQuery(req):
    result = req.get("result")
    parameters = result.get("parameters")
    city = parameters.get("geo-city")
    if city is None:
        return None

    return "select * from weather.forecast where woeid in (select woeid from geo.places(1) where text='" + city + "')"


def makeWebhookResult(data):
    query = data.get('query')
    if query is None:
        return {}

    result = query.get('results')
    if result is None:
        return {}

    channel = result.get('channel')
    if channel is None:
        return {}

    item = channel.get('item')
    location = channel.get('location')
    units = channel.get('units')
    if (location is None) or (item is None) or (units is None):
        return {}

    condition = item.get('condition')
    if condition is None:
        return {}

    # print(json.dumps(item, indent=4))

    speech = "Today in " + location.get('city') + ": " + condition.get('text') + \
             ", the temperature is " + condition.get('temp') + " " + units.get('temperature')

    print("Response:")
    print(speech)

    return {
        "speech": speech,
        "displayText": speech,
        # "data": data,
        # "contextOut": [],
        "source": "apiai-weather-webhook-sample"
    }


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))

    print("Starting app on port %d" % port)

    app.run(debug=False, port=port, host='0.0.0.0')
