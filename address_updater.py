import pymongo
from scraper import Property

__author__ = 'momchilrogelov'
import logging
import os

from pymongo import MongoClient


mongo_url = os.environ.get("MONGOHQ_URL")
if mongo_url:
    client = MongoClient(mongo_url)
    db = client.app21891500
else:
    client = MongoClient()

    # db = client.app21891500
    db = client.rentomatic


col = db["properties"]

logging.info("STARTING UPDATE OF ADDRESSES")

if __name__ == "__main__":
    properties = col.find({
                        "directions_info": None,
                        "price_month":{"$lte":1500, "$gte":500},
                        }
        ).sort("added", pymongo.DESCENDING)
    all_number = properties.count()
    for i, p in enumerate(properties):
        prop = Property(mongo_obj=p)
        prop.update_address()
        print "prop {} of {}  addded address {}".format(i, all_number, p["added"])