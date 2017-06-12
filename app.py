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

# Определяем тип запроса
def getService(req):
    result = req.get("result")
    action = result.get("action")
    if action=="weather":
        return serviceWeather(result)
    elif action=="translate.text":
        return serviceTranslate(result)
    elif action=="dar.wiki":
        return serviceWiki(result)

# Создаем запрос к Wikipedia
def makeWikiRequest(text):
    baseUrl = "https://ru.wikipedia.org/w/api.php"
    params = "?action=query&prop=extracts&exintro&indexpageids=true&format=json&generator=search&gsrlimit=1&exsentences=6&explaintext&gsrsearch=" + text
    return baseUrl + params

# Уменьшает возвращаемый текст до определенной длины
def beautifyWikiText(text, textLength):
    total = 0
    brackets = 0
    str = ""
    for letter in text:
        str = str + letter
        total +=1
        if letter=='(':
            brackets +=1
        if letter==')':
            brackets -=1
        if letter=='.'and brackets==0 and total>textLength:
          return str
    return str

#-----Сервис энциклопедия Wikipedia-----
def serviceWiki(result):
    parameters = result.get("parameters")
    text = parameters.get("text")
    req = makeWikiRequest(text)

    try:
        res = requests.get(req)
        data = res.json()
        speech = data['query']['pages'].values()[0]['extract']
        speech = beautifyWikiText(speech, 150)
    except:
        speech = u"К сожалению, я пока не знаю ответ на этот вопрос 😕"

    return returnJsonFunction(speech, "wiki")


#Функция для корректировки некоторых языков
def getLanguage(lang):
    if lang=="zh-CHT":
        return "zh-CN"
    return lang


# Создаем запрос для Перевода текста
def makeTranslateRequest(q, langCode):

    # Google translate key
    key = 'AIzaSyAhP5cBWEpmUhIOavwZ2GFlMTFdhJrwxAQ'
    target = getLanguage(langCode)
    url = "https://translation.googleapis.com/language/translate/v2?"
    params = "q="+q+"&format=text"+"&target="+target+"&key="+key

    return url+params


#-----Сервис Google translate-----
def serviceTranslate(result):
    parameters = result.get("parameters")
    q = parameters.get("text")

    if "langCode" in parameters:
        langCode = parameters.get("langCode")
    else:
        langCode = parameters.get("to").get("langCode")

    req = makeTranslateRequest(q, langCode)
    res = requests.get(req)
    data = res.json()
    speech = data['data']['translations'][0]['translatedText']

    return returnJsonFunction(speech, "translate")



#--------------Погода на сегодня------------------------------------------------
def getWeatherSpeechToday(s_city, latitude, longitude, appid):

    res = requests.get("http://api.openweathermap.org/data/2.5/find",
        params={'lat': latitude, 'lon': longitude, 'type': 'accurate', 'lang': 'ru', 'units': 'metric', 'APPID': appid})
    data = res.json()
    temp = str(int(round(data['list'][0]['main']['temp'])))
    description = data['list'][0]['weather'][0]['description']
    description = localize(description, temp)

    return u"Сегодня в "+s_city+": "+description+ u", температура "+temp + u" °C "


#-------------Погода на другие дни----------------------------------------------
def getWeatherSpeech(s_city, latitude, longitude, appid, cnt, d1 ,d2):
    res = requests.get("http://api.openweathermap.org/data/2.5/forecast/daily",
            params={'lat': latitude, 'lon': longitude, 'type': 'accurate', 'lang': 'ru', 'units': 'metric', 'APPID': appid, 'cnt': cnt+1})
    data = res.json()
    temp = str(int(round(data['list'][cnt]['temp']['day'])))
    description = data['list'][cnt]['weather'][0]['description']
    description = localize(description, temp)

    s_day = localizeDay(d1.strftime("%a"), d1.strftime("%d"))

    return u"Погода на " + s_day +  u" в " +s_city+": "+description+ u", температура "+temp + u" °C "


def getCorrectCityName(s_city):
    if s_city == "":
        s_city = u"Алматы "
    str = ""
    for letter in s_city:
        if letter==' ':
            return str
            return s_city
        str = str + letter

#-------------Достаем данные города с Google response--------------
def getWeatherCityCoordinates(s_city):

    s_city = getCorrectCityName(s_city)
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {'sensor': 'false', 'language': 'ru', 'address': s_city}
    res = requests.get(url, params=params)
    results = res.json()
    response_status = results['status']

    if response_status!="OK":
        #return "ERROR", "1", "1", "No city"
        return "ERROR", "1", "1", str(s_city)

    latitude = results["results"][0]["geometry"]["location"]["lat"]
    longitude = results["results"][0]["geometry"]["location"]["lng"]

    locality_type = results["results"][0]["address_components"][0]["types"][0]
    address_components = results["results"][0]["address_components"]

    isKZ = False
    i = 0
    for obj in address_components:
        if results["results"][0]["address_components"][i]["short_name"] == "KZ":
            isKZ = True
        i = i+1
    if locality_type != "locality" or isKZ==False:
        return "OK", latitude, longitude, results["results"][0]["formatted_address"]
    else:
        return "OK", latitude, longitude, results["results"][0]["address_components"][0]["short_name"]

    return "ERROR", "1", "1", "Something went wrong"


#------NEW WEATHER SERVICE VIA GOOGLE MAPS AND OPENWEATHERMAP------------------
def serviceWeather(result):

    parameters = result.get("parameters")
    s_city = parameters.get("geo-city")
    s_day = str(parameters.get("date"))
    isWeather = parameters.get("weather")

    if isWeather=="":
        speech = u"Я пока не до конца понимаю тебя, но я учусь"
        return returnJsonFunction(speech, "weather")

    # *******Определяем корректное наименование города и координаты********
    try:
        status, latitude, longitude, s_city = getWeatherCityCoordinates(s_city)

        if status == "ERROR":
            speech = u"Кажется такого города не существует..."+s_city
            return returnJsonFunction(speech, "weather")

        if s_day == "" or len(s_day)<10:
            speech = getWeatherSpeechToday(s_city, latitude, longitude, "01e9d712127bbffa4c9e669f39d3a127")
        else:
            d1 = datetime.strptime(s_day, "%Y-%m-%d").date()
            d2 = datetime.today().date()
            cnt = (d1-d2).days

            if cnt>=0 and cnt<16:
                speech = getWeatherSpeech(s_city, latitude, longitude, "01e9d712127bbffa4c9e669f39d3a127", cnt, d1, d2)
            elif cnt>=16:
                speech = u"Так далеко я не могу предсказать 🤔"
            else:
                speech = u"Прости, прошлое вне моей погодной компетенции..."

    except Exception as E:
        print("Error in weather webhook: " + str(E))
        pass

    return returnJsonFunction(speech, "weather")
#-------------------------------------------------------------------------------

# заворачиваем ответ с кнопками в JSON
def returnJsonFunction(speech, source):
    return {
        "speech": speech,
        "displayText": speech,
        "source": source,
        "messages": [
            {
            "type": 0,
            "speech": speech
            },
        {
        "type": 4,
        "payload": {
            "chatControl": {
                "chatButtons": {
                    "buttons": [
                      {
                        "title": "Список команд",
                        "command": "Список команд"
                      },
                      {
                        "title": "👍",
                        "command": "👍"
                      },
                      {
                        "title": "👎",
                        "command": "👎"
                      }
                ]
            }
        }
        }
        }
        ]
    }

#--------------- костыль----------спасибо OpenWeatherMap
def localize(desc, temp):
    if (temp>0) and (desc==u"небольшой снегопад" or desc==u"снегопад"):
        return u"возможны осадки"
    if desc=="shower sleet":
        return u"снегопад"
    return desc

def localizeDay(day_of_week, day):
    day = str(int(day))
    if day=="3" or day=="23":
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
