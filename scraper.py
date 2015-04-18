import calendar
from datetime import datetime
import json
import logging
import os

import requests
from BeautifulSoup import BeautifulSoup
from pymongo import MongoClient


mongo_url = os.environ.get("MONGOHQ_URL")
if mongo_url:
    client = MongoClient(mongo_url)
    db = client.app21891500
else:
    client = MongoClient()
    db = client.app21891500
col = db["properties"]

logging.info("STARTING A SCRAPE")


class Property(object):
    def __init__(self, summary=None, id=None, mongo_obj=None):
        self.properties_to_save = ["id", 'type', 'price_month', 'link', 'address', 'added', 'small_picture_link',
                                   'valid', 'raw_failsafe', 'exception']

        self.id = ""
        self.type = ""
        self.price_month = None
        self.link = ""
        self.address = ""
        self.added = datetime.utcnow()
        self.small_picture_link = ""

        self.saved = False
        self.valid = True
        self.raw_failsafe = None
        self.exception = None
        if summary:
            logging.info("parsing a property")
            print ("parsing a property")
            try:
                self.id = int(summary.attrMap["id"][7:])
                address_and_type_link = summary.find(id="standardPropertySummary" + str(self.id))
                self.address = address_and_type_link.findAll("span")[1].text
                self.type = address_and_type_link.findAll("span")[0].text
                self.link = "http://www.rightmove.co.uk/property-to-rent/property-" + str(self.id) + ".html"

                price_text = summary.find('p', {"class": "price-new"}).text.split(";")[-1]
                price_num = ''.join(c for c in price_text if c.isdigit())
                self.price_month = int(price_num)
                self.small_picture_link = summary.find("img", {"class": "fixedPic"}).attrMap['src']

            #todo asserts
            except Exception as e:
                logging.warning("failed to parse property with id {}".format(self.id))
                print("failed to parse property with id {} because {}".format(self.id, e))
                self.valid = False
        if id:
            #todo
            pass
        if mongo_obj:
            for property in self.properties_to_save:
                if property in mongo_obj:
                    setattr(self, property, mongo_obj.get(property))

    def save(self):
        if not col.find_one(self.id):
            logging.info("found new property with id {}".format(self.id))
            print("found new property with id {}".format(self.id))
            obj = {}
            for property_name in self.properties_to_save:
                obj[property_name] = getattr(self, property_name)
            obj["_id"] = self.id
            col.save(obj)
            logging.info("new property with id {} saved".format(self.id))
            print("new property with id {} saved".format(self.id))
        else:
            print("already know this")

    def update_address(self):
        directions_info = find_transport(self.address + ", London, UK")
        if not directions_info:
            print "AAAAAAAAAAAAA not cool no adress"
            return None
        print(json.dumps(directions_info))
        col.find_and_modify({"_id": self.id}, {"$set": {"directions_info": directions_info}})
        print "saved the directions info"


def get_property_result_page(index=0):
    url = "http://www.rightmove.co.uk/" \
          "property-to-rent/London-87490.html?sortType=6&" \
          "numberOfPropertiesPerPage=50" \
          "&index=" + str(index * 50)

    r = requests.get(url)
    if r.status_code != requests.codes.ok:
        raise FailedFetch()
        #record successfull page grab
    return r.content


def parse_result_page(content):
    parsed_object = BeautifulSoup(content)
    summaries = parsed_object.findAll("li", {"name": "summary-list-item"})

    result = []
    for summary in summaries:
        result.append(Property(summary))
    return result


class FailedFetch(Exception):
    pass


def find_transport(address):
    print u"finding address {}".format(address)
    import time
    time.sleep(1.5)
    destination = "Old Street Station, London, UK"
    url = "http://maps.googleapis.com/maps/api/directions/json"
    arrival_time = datetime.utcnow().replace(hour=10)
    arrival_time = calendar.timegm(arrival_time.timetuple())
    params = {
        "origin": address,
        "destination": destination,
        'sensor': "false",
        'mode': "transit",
        'alternatives': 'true',
        'arrival_time': arrival_time
    }
    resp = requests.get(url, params=params)
    data = resp.json()
    if data['status'] == "OK":
        print "address found"
        result = []
        for route in data['routes']:
            trip = {
                "total": None,
                "bus": 0,
                'walking': 0,
                'tube': 0,
                'other': 0,
                "uncaught_types": [],
                'bus_seconds': 0,
                "walking_seconds": 0,
                "tube_seconds": 0
            }
            leg = route["legs"][0]
            steps = leg['steps']
            trip['total'] = leg["duration"]["value"]
            for step in steps:
                if step["travel_mode"] == "WALKING":
                    trip['walking'] += 1
                    trip['walking_seconds'] += step['duration']['value']

                elif step["travel_mode"] == "TRANSIT" and step['transit_details']['line']['vehicle']['type'] == 'TRAM':
                    trip['tube'] += 1
                    trip['tube_seconds'] += step['duration']['value']

                elif step["travel_mode"] == "TRANSIT" and step['transit_details']['line']['vehicle'][
                    'type'] == 'SUBWAY':
                    trip['tube'] += 1
                    trip['tube_seconds'] += step['duration']['value']

                elif step["travel_mode"] == "TRANSIT" and step['transit_details']['line']['vehicle']['type'] == 'TRAIN':
                    trip['tube'] += 1
                    trip['tube_seconds'] += step['duration']['value']

                elif step["travel_mode"] == "TRANSIT" and step['transit_details']['line']['vehicle']['type'] == 'HEAVY_RAIL':
                    trip['tube'] += 1
                    trip['tube_seconds'] += step['duration']['value']

                elif step["travel_mode"] == "TRANSIT" and step['transit_details']['line']['vehicle']['type'] == 'BUS':
                    trip['bus'] += 1
                    trip['bus_seconds'] += step['duration']['value']

                else:
                    trip['other'] += 1
                    trip["uncaught_types"].append(step["travel_mode"])
                    try:
                        trip["uncaught_types"].append(step['transit_details']['line']['vehicle']['type'])
                    except Exception:
                        pass
            result.append(trip)

        return result
    else:
        print data["status"]

if __name__ == '__main__':
    import time
    for index in range(0, 3):
        print('page {}'.format(index))
        content = get_property_result_page(index)
        results = parse_result_page(content)
        for property in results:
            property.save()
        time.sleep(5)
