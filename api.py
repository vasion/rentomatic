import os
import re
import datetime
from pymongo import MongoClient
import pymongo

__author__ = 'momchilrogelov'

from flask import Flask, request
from bson.json_util import dumps

mongo_url = os.environ.get("MONGOHQ_URL")

if mongo_url:
    client = MongoClient(mongo_url)
    db = client.app21891500
else:
    client = MongoClient()
    # db = client.app21891500
    db = client.rentomatic
col = db.properties

app = Flask(__name__)
app.debug = True


@app.route('/properties')
def properties():
    view_results = request.args.get("view_results", None)
    if view_results:
        results = col.find({"rate_result": {"$gt": 0}}).sort([("rate_result", pymongo.DESCENDING)])
        return dumps({"result": results})

    limit = int(request.args.get("limit", 50))
    offset = int(request.args.get("skip", 0))
    time = int(request.args.get("time", 180)) * 60
    order = request.args.get('order', 'price_month')
    age = request.args.get('age', 14)

    regx_share = re.compile("share", re.IGNORECASE)
    regx_office = re.compile("office", re.IGNORECASE)
    regx_commercial = re.compile("commercial", re.IGNORECASE)
    regx_shop = re.compile("shop", re.IGNORECASE)
    added_cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=int(age))
    data = col.aggregate([
        {"$match": {
            "added": {"$gte": added_cutoff},
            "rate_result": None,
            "price_month": {"$lte": 1200}
        }
        },
        {"$unwind": "$directions_info"},
        {"$match": {
            "directions_info.bus": 1,
            "directions_info.tube": 0,
            "directions_info.total": {"$lte": time},
            "$or": [{"other": 0}, {"other": None}],
            "type": {"$not": regx_share},
            # {"type": regx_office}, {"type": regx_commercial}, {"type": regx_shop}]}
        }
        },
        {"$group":
             {
                 "_id": "$_id",
                 "type": {"$first": "$type"},
                 "id": {"$first": "$id"},
                 "link": {"$first": "$link"},
                 'address': {"$first": "$address"},
                 "price_month": {"$first": "$price_month"},
                 "small_picture_link": {"$first": "$small_picture_link"},
                 "directions_info": {"$addToSet": "$directions_info"},
                 "lowest_travel": {"$min": "$directions_info.total"},
             }
        },
        {"$sort": {order: 1}},
        {"$skip": offset},
        {"$limit": limit},

    ])

    count = col.aggregate([
        {"$match": {
            "added": {"$gte": added_cutoff},
            "rate_result": None,
            "price_month": {"$lte": 1200}
        }
        },
        {"$unwind": "$directions_info"},
        {"$match": {
            "directions_info.bus": 1,
            "directions_info.tube": 0,
            "directions_info.total": {"$lte": time},
            "$or": [{"other": 0}, {"other": None}],
            "type": {"$not": regx_share},
            # {"type": regx_office}, {"type": regx_commercial}, {"type": regx_shop}]}
        }
        },
        {"$group":
             {
                 "_id": "$_id",
             }
        },
        {
            "$group":
                {"_id": 0,
                 "count": {"$sum": 1}
                }
        }])["result"][0]["count"]

    return dumps({"count": count, "result": data["result"]})


@app.route("/properties/<int:prop_id>/rate/", methods=['POST'])
def rate(prop_id):
    value = request.form["value"]
    col.find_and_modify({"id": prop_id}, {"$set": {"rate_result": float(value)}}, upsert=False)
    return "res"

@app.route("/properties/<int:prop_id>/comment/", methods=['POST'])
def comment(prop_id):
    value = request.form["comment"]
    col.find_and_modify({"id": prop_id}, {"$set": {"comments": value}}, upsert=False)

if __name__ == "__main__":
    app.run()

