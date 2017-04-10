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
            temp = str(int(round(data['list'][cnt-1]['temp']['day'])))
            description = data['list'][cnt-1]['weather'][0]['description']
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


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))

    print("Starting app on port %d" % port)

    app.run(debug=False, port=port, host='0.0.0.0')