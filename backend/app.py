from flask import Flask, request
import json
import model
import validation
from mongoengine import connect
import mongoengine.errors
from os import environ
from datetime import datetime
from enum import Enum

from search import search_blueprint
from add_item import add_item_blueprint

class Error(Enum):
    ITEM_DNE = 'Item does not exist in database'
    STORE_DNE = 'Store does not exist in database'
    INVALID_DIR = 'Invalid vote direction'
    ALREADY_UPVOTED = 'User has already upvoted'
    ALREADY_DOWNVOTED = 'User has already downvoted'
    NOT_VOTED = 'User has not voted, cannot undo'


class Vote(Enum):
    UP = 1
    NEUTRAL = 0
    DOWN = -1

    @classmethod
    def from_int(cls, i):
        mapping = {1: cls.UP, 0: cls.NEUTRAL, -1: cls.DOWN}
        return mapping[i]


app = Flask(__name__)
app.register_blueprint(search_blueprint)
app.register_blueprint(add_item_blueprint)

try:
    connect('grocery-db', host=environ['MONGO_HOST'])
except KeyError:
    pass

HELLO_WORLD = 'Hello, Grocery buddies!'
@app.route('/')
def hello_world():
    return HELLO_WORLD





@app.route('/price', methods=['POST'])
def add_price():
    '''
        Body: {"upc", "price", "user", "store", "lat", "long"}
        Response:
            - {"success": true or false},
            - {"error": error description}
    '''
    data = request.get_json(force=True)

    required_fields = ['upc', 'price', 'user', 'store', 'lat', 'long']
    if not validation.has_required(data, required_fields):
        return json.dumps({'success': False, 'error': Error.MISSING_FIELDS.value})

    item = model.Item.objects(upc=data['upc']).first()
    if item is None:
        return json.dumps({'success': False, 'error': Error.ITEM_DNE.value})

    new_price = model.Price(
        user=data['user'],
        upvotes=[],
        downvotes=[],
        price=data['price'],
        date=request.date
    )

    loc = {'lat': data['lat'], 'long': data['long']}
    store = item.stores.filter(name=data['store'], location=loc).first()
    if store is not None:
        store.prices.append(new_price)
    else:
        new_store = model.Store(
            name=data['store'],
            location=loc,
            prices=[new_price]
        )
        item.stores.append(new_store)

    try:
        item.save()
    except (validation.ValidationException, mongoengine.errors.ValidationError) as e:
        return json.dumps({'success': False, 'error': str(e)})

    return json.dumps({'success': True, 'error': None})


@app.route('/vote', methods=['POST'])
def vote():
    '''
        Body: {"upc", "user", "store", "lat", "long", "dir"}
        Response:
            - {"success": true or false},
            - {"error": error description}
    '''
    data = request.get_json(force=True)

    required_fields = ['upc', 'user', 'store', 'lat', 'long', 'dir']
    if not validation.has_required(data, required_fields):
        return json.dumps({'success': False, 'error': Error.MISSING_FIELDS.value})
    if not validation.is_valid_dir(data['dir']):
        return json.dumps({'success': False, 'error': Error.INVALID_DIR.value})

    direction = Vote.from_int(data['dir'])

    item = model.Item.objects(upc=data['upc']).first()
    if item is None:
        return json.dumps({'success': False, 'error': Error.ITEM_DNE.value})

    loc = {'lat': data['lat'], 'long': data['long']}
    store = item.stores.filter(name=data['store'], location=loc).first()
    if store is None:
        return json.dumps({'success': False, 'error': Error.STORE_DNE.value})
    else:
        price = store.prices[-1]
        if direction == Vote.UP:
            if data['user'] in price.upvotes:
                return json.dumps({'success': False, 'error': Error.ALREADY_UPVOTED.value})
            else:
                price.upvotes.append(data['user'])
            if data['user'] in price.downvotes:
                price.downvotes.remove(data['user'])
        elif direction == Vote.DOWN:
            if data['user'] in price.downvotes:
                return json.dumps({'success': False, 'error': Error.ALREADY_DOWNVOTED.value})
            else:
                price.downvotes.append(data['user'])
            if data['user'] in price.upvotes:
                price.upvotes.remove(data['user'])
        else:
            if data['user'] in price.upvotes:
                price.upvotes.remove(data['user'])
            elif data['user'] in price.downvotes:
                price.downvotes.remove(data['user'])
            else:
                return json.dumps({'success': False, 'error': Error.NOT_VOTED.value})

    try:
        item.save()
    except (validation.ValidationException, mongoengine.errors.ValidationError) as e:
        return json.dumps({'success': False, 'error': str(e)})

    return json.dumps({'success': True, 'error': None})





@app.route('/optimal_store', methods=['POST'])
def get_optimal_store():
    """
        Body: {"single_store": boolean, single or multiple stores, "items": [upc:String]}
        Response:   {"success": True or False,
                    "error": error description,
                    "optimal_prices":
                            [{"store": store,
                              "upcs": list of upcs,
                              "price": total price of items associated with store}]
                    }
    """
    error = None
    data = request.get_json(force=True)
    if data is None:
        error = 'Could not parse JSON body'
        return json.dumps({'success': False, 'error': error, 'optimal_prices': None})

    item_list = []
    items = data['items']
    if items is None:
        error = 'No UPCs provided'
        return json.dumps({'success': False, 'error': error, 'optimal_prices': None})
    for upc in items:
        result = model.Item.objects(upc=upc)
        if len(result) == 0:
            error = "Some UPCs provided were not found in the database"
        else:
            item_list.append(result.to_json())

    upc_dict = {}
    for item in item_list:
        item = json.loads(item)
        upc = item[0]['upc']
        for store in item[0]['stores']:
            store_key = str(store['name']) + '|' + str(store['location']
                                                       ['lat']) + '|' + str(store['location']['long'])
            latest_price = store['prices'][-1]['price']
            upc_list = upc_dict.get(upc)
            if upc_list is None:
                upc_dict[upc] = [(store_key, latest_price)]
            else:
                upc_list.append((store_key, latest_price))

    single_store = data['single_store']
    if single_store:
        store_dict_price = {}  # key: store, value: list of prices
        store_dict_upc = {}
        for upc, store_price_list in upc_dict.items():
            for store_price in store_price_list:
                store = store_dict_price.get(store_price[0])
                if store is None:
                    store_dict_price[store_price[0]] = [store_price[1]]
                    store_dict_upc[store_price[0]] = [upc]
                else:
                    store.append(store_price[1])
                    store_dict_upc[store_price[0]].append(upc)
        lowest_price = None  # tuple (store unique str, total_price)
        item_count = 0
        for store, price_list in store_dict_price.items():
            total_price = sum(price_list)
            bigger = len(price_list) > item_count
            equal_and_cheaper = len(
                price_list) == item_count and total_price < lowest_price[1]
            if lowest_price is None or bigger or equal_and_cheaper:
                lowest_price = (store, total_price)
                item_count = len(price_list)

        store_info = lowest_price[0].split('|')
        store_obj = {
            'name': store_info[0],
            'location': {
                'lat': store_info[1],
                'long': store_info[2]
            },
            'prices': []
        }
        return json.dumps({'success': True, 'error': error, 'optimal_prices':
                                            [{"store": store_obj,
                                                "upcs": store_dict_upc[lowest_price[0]],
                                                "price": lowest_price[1]}]
                           })
    else:
        store_dict = {}  # key: store, value: list of tuples (upc, price)
        for upc, store_price_list in upc_dict.items():
            best_store_price = None
            for store_price in store_price_list:
                if best_store_price is None or store_price[1] < best_store_price[1]:
                    best_store_price = store_price
            store_dict_entry = store_dict.get(best_store_price[0])
            if store_dict_entry is None:
                store_dict[best_store_price[0]] = [(upc, best_store_price[1])]
            else:
                store_dict[best_store_price[0]].append(
                    (upc, best_store_price[1]))
        optimal_prices = []
        for store, upc_price_list in store_dict.items():
            store_info = store.split('|')
            store_obj = {
                'name': store_info[0],
                'location': {
                    'lat': store_info[1],
                    'long': store_info[2]
                },
                'prices': []
            }
            upcs = []
            total_price = 0
            for upc_price in upc_price_list:
                upcs.append(upc_price[0])
                total_price += upc_price[1]
            optimal_prices.append(
                {'store': store_obj, 'upcs': upcs, 'price': total_price})
        return json.dumps({'success': True, 'error': error, 'optimal_prices': optimal_prices})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
