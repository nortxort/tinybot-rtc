""" Contains functions to fetch info from different simple online APIs."""
import util.web


def urbandictionary_search(search):
    """
    Searches urbandictionary's API for a given search term.
    :param search: The search term str to search for.
    :return: defenition str or None on no match or error.
    """
    if str(search).strip():
        urban_api_url = 'http://api.urbandictionary.com/v0/define?term=%s' % search
        response = util.web.http_get(url=urban_api_url, json=True)
        if response['json'] is not None:
            try:
                definition = response['json']['list'][0]['definition']
                return definition.encode('ascii', 'ignore')
            except (KeyError, IndexError):
                return None
    else:
        return None


def weather_search(city):
    """
    Searches worldweatheronline's API for weather data for a given city.
    You must have a working API key to be able to use this function.

    :param city: The city str to search for.
    :return: weather data str or None on no match or error.
    """
    if str(city).strip():
        api_key = ''
        if not api_key:
            return 'Missing api key.'
        else:
            weather_api_url = 'http://api.worldweatheronline.com/premium/v1/weather.ashx?key=%s&q=%s&format=json' % \
                              (api_key, city)

            response = util.web.http_get(url=weather_api_url, json=True)
            if response['json'] is not None:
                try:
                    pressure = response['json']['data']['current_condition'][0]['pressure']
                    temp_c = response['json']['data']['current_condition'][0]['temp_C']
                    temp_f = response['json']['data']['current_condition'][0]['temp_F']
                    query = response['json']['data']['request'][0]['query'].encode('ascii', 'ignore')
                    result = '%s. Temperature: %sC (%sF) Pressure: %s millibars' % (query, temp_c, temp_f, pressure)
                    return result
                except (IndexError, KeyError):
                    return None
    else:
        return None


def whois(ip):
    """
    Searches ip-api for information about a given IP.
    :param ip: The ip str to search for.
    :return: information str or None on error.
    """
    if str(ip).strip():
        url = 'http://ip-api.com/json/%s' % ip
        response = util.web.http_get(url=url, json=True)
        if response['json'] is not None:
            try:
                city = response['json']['city']
                country = response['json']['country']
                isp = response['json']['isp']
                org = response['json']['org']
                region = response['json']['regionName']
                zipcode = response['json']['zip']
                info = country + ', ' + city + ', ' + region + ', Zipcode: ' + zipcode + '  Isp: ' + isp + '/' + org
                return info
            except KeyError:
                return None
    else:
        return None


def chuck_norris():
    """
    Finds a random Chuck Norris joke/quote.
    :return: joke str or None on failure.
    """
    url = 'http://api.icndb.com/jokes/random/?escape=javascript'
    response = util.web.http_get(url=url, json=True)
    if response['json'] is not None:
        if response['json']['type'] == 'success':
            joke = response['json']['value']['joke']
            return joke
        return None
