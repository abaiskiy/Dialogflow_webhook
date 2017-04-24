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


app = Flask(__name__)


@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)
    print("Request:")
    print(json.dumps(req, indent=4))

    res = getService(req)

    res = json.dumps(res, indent=4)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r


def getService(req):
    result = req.get("result")

    action = result.get("action")
    if action=="weather":
        return serviceWeather(result)
    elif action=="translate.text":
        return serviceTranslate(result)
    elif action=="dar.wiki":
        return serviceWiki(result)

def serviceWiki(result):

    speech = "Zdes 4to to umnoe"
    return {
        "speech": speech,
        "displayText": speech,
        "source": "DARvis wiki webhook"
    }

def serviceTranslate(result):

    parameters = result.get("parameters")
    q = parameters.get("text")

    if "langCode" in parameters:
        langCode = parameters.get("langCode")
    else:
        langCode = parameters.get("to").get("langCode")

    # Google translate key
    key = 'AIzaSyAhP5cBWEpmUhIOavwZ2GFlMTFdhJrwxAQ'
    target = getLanguage(langCode)
    format = "text"
    url = "https://translation.googleapis.com/language/translate/v2"
    params = {'q': q, 'format': format, 'target': target, 'key': key}

    res = requests.get(url, params=params)
    data = res.json()
    speech = data['data']['translations'][0]['translatedText']

    return {
        "speech": speech,
        "displayText": speech,
        "source": "DARvis translate webhook"
    }

def getLanguage(lang):
    if lang=="zh-CHT":
        return "zh-CN"
    return lang

def serviceWeather(result):

    parameters = result.get("parameters")
    s_city = parameters.get("geo-city")
    s_day = str(parameters.get("date"))
    if s_city == "":
        s_city = u"Алматы"
    isWeather = parameters.get("weather")

    # OpenWeatherMap key
    appid = "01e9d712127bbffa4c9e669f39d3a127"
    lang = "ru"

    if isWeather!="":
        try:
            if s_day == "":
                res = requests.get("http://api.openweathermap.org/data/2.5/find",
                        params={'q': s_city, 'type': 'like', 'lang': lang, 'units': 'metric', 'APPID': appid})
                data = res.json()
                temp = str(int(round(data['list'][0]['main']['temp'])))
                description = data['list'][0]['weather'][0]['description']
                description = localize(description, temp)
                speech = u"Сегодня в "+s_city+" "+description+ u", температура "+temp + u" °C "
            else:
                d1 = datetime.strptime(s_day, "%Y-%m-%d").date()
                d2 = datetime.today().date()
                cnt = (d1-d2).days

                if cnt>=0 and cnt<16:
                    res = requests.get("http://api.openweathermap.org/data/2.5/forecast/daily",
                            params={'q': s_city, 'type': 'like', 'lang': lang, 'units': 'metric', 'APPID': appid, 'cnt': cnt+1})
                    data = res.json()
                    temp = str(int(round(data['list'][cnt]['temp']['day'])))
                    description = data['list'][cnt]['weather'][0]['description']
                    description = localize(description, temp)

                    s_day = localizeDay(d1.strftime("%a"), d1.strftime("%d"))

                    speech = u"Погода на " + s_day +  u" в " +s_city+": "+description+ u", температура "+temp + u" °C "
                elif cnt>=16:
                    speech = u"Так далеко я не могу предсказать."
                else:
                    speech = u"Прости, прошлое вне моей погодной компетенции..."
        except Exception as e:
            speech = u"Кажется такого города не существует"
            pass
    else:
        speech = u"Я пока не до конца понимаю тебя, но я учусь"
    return {
        "speech": speech,
        "displayText": speech,
        "source": "DARvis weather webhook"
    }

def localize(desc, temp):
    if (temp>0) and (desc==u"небольшой снегопад" or desc==u"снегопад"):
        return u"возможны осадки"
    if desc=="shower sleet":
        return u"снегопад"
    return desc

def localizeDay(day_of_week, day):

    if day==3 or day==23:
        day = day + u"-е"
    else:
        day = day + u"-ое"

    if day_of_week=="Mon" or day_of_week==0:
        return u"понедельник, " + day
    elif day_of_week=="Tue" or day_of_week==1:
        return u"вторник, "  + day
    elif day_of_week=="Wed" or day_of_week==2:
        return u"среду, "  + day
    elif day_of_week=="Thu" or day_of_week==3:
        return u"четверг, "  + day
    elif day_of_week=="Fri" or day_of_week==4:
        return u"пятницу, "  + day
    elif day_of_week=="Sat" or day_of_week==5:
        return u"субботу, "  + day
    elif day_of_week=="Sun" or day_of_week==6:
        return u"воскресенье, " + day
    return u"Нет такого дня"


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))

    print("Starting app on port %d" % port)

    app.run(debug=False, port=port, host='0.0.0.0')
