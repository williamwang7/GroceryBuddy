import pytest
import json
import model
import app
from test_data import valid_items
import copy


def test_invalid_upc(db, client):
    for item in valid_items:
        copy.deepcopy(item).save()
    result = model.Item.objects()

    upcs = ["000000000000"]
    for item in result:
        upcs.append(item.upc)

    rv = client.post('/optimal_store', data=json.dumps({
        'single_store': True,
        'items': upcs
    }))
    response = json.loads(rv.data)
    assert response['success'] is True
    assert response['error'] == "Some UPCs provided were not found in the database"
    assert len(response['optimal_prices']) == 1
    assert len(response['optimal_prices'][0]['upcs']) == (len(upcs) - 1)


def test_single_store(db, client):
    for item in valid_items:
        copy.deepcopy(item).save()
    result = model.Item.objects()

    upcs = []
    for item in result:
        upcs.append(item.upc)

    rv = client.post('/optimal_store', data=json.dumps({
        'single_store': True,
        'items': upcs
    }))
    response = json.loads(rv.data)
    assert response['success'] is True
    assert len(response['optimal_prices']) == 1
    assert len(response['optimal_prices'][0]['upcs']) == len(upcs)


def test_multiple_stores(db, client):
    for item in valid_items:
        copy.deepcopy(item).save()
    result = model.Item.objects()

    upcs = []
    for item in result:
        upcs.append(item.upc)

    rv = client.post('/optimal_store', data=json.dumps({
        'single_store': False,
        'items': upcs
    }))
    response = json.loads(rv.data)
    assert response['success'] is True
    assert len(response['optimal_prices']) >= 1
    assert sum(len(dct['upcs']) for dct in response['optimal_prices']) == len(upcs)