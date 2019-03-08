import pytest
import json
import app
import model
import test_data


def test_add_existing_store(client, existing_item):
    upc = str(existing_item.upc)
    store = existing_item.stores[0]
    store_name = str(store.name)
    lat = float(store.location['lat'])
    long_arg = float(store.location['long'])

    price_data = test_data.valid_prices[5]
    price = float(price_data.price)
    user = str(price_data.user)

    num_existing_prices = len(store.prices)

    rv = client.post('/price', data=json.dumps({
        'upc': upc,
        'price': price,
        'user': user,
        'store': store_name,
        'lat': lat,
        'long': long_arg
    }))
    response = json.loads(rv.data)
    assert response == {'success': True, 'error': None}

    new_price = model.Item.objects(
        upc=upc).first().stores[0].prices[num_existing_prices]
    assert float(new_price.price) == price
    assert new_price.upvotes == []
    assert new_price.downvotes == []


def test_add_new_store(client, existing_item):
    upc = str(existing_item.upc)
    new_store = test_data.store10
    store_name = str(new_store.name)
    lat = float(new_store.location['lat'])
    long_arg = float(new_store.location['long'])

    price_data = test_data.valid_prices[5]
    price = float(price_data.price)
    user = str(price_data.user)

    rv = client.post('/price', data=json.dumps({
        'upc': upc,
        'price': price,
        'user': user,
        'store': store_name,
        'lat': lat,
        'long': long_arg
    }))
    response = json.loads(rv.data)
    assert response == {'success': True, 'error': None}

    loc = {'lat': lat, 'long': long_arg}
    new_price = model.Item.objects(upc=upc).first().stores.filter(
        name=store_name, location=loc).first().prices[0]
    assert float(new_price.price) == price
    assert new_price.upvotes == []
    assert new_price.downvotes == []


def test_nonexistent_item(client, nonexistent_item):
    upc = str(nonexistent_item.upc)
    store = nonexistent_item.stores[0]
    store_name = str(store.name)
    lat = float(store.location['lat'])
    long_arg = float(store.location['long'])

    price_data = test_data.valid_prices[5]
    price = float(price_data.price)
    user = str(price_data.user)

    rv = client.post('/price', data=json.dumps({
        'upc': upc,
        'price': price,
        'user': user,
        'store': store_name,
        'lat': lat,
        'long': long_arg
    }))
    response = json.loads(rv.data)
    assert response == {'success': False, 'error': app.Error.ITEM_DNE.value}