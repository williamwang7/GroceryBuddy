from flask import Blueprint, request
from enum import Enum
import json
import validation
from utils import Error
import mongoengine.errors
import model

vote_blueprint = Blueprint("vote", __name__)


class Vote(Enum):
    '''
    An enum of the 3 possible votes:
    upvote, downvote, and unvote.
    '''
    UP = 1
    NEUTRAL = 0
    DOWN = -1

    @classmethod
    def from_int(cls, i):
        '''
        Returns the corresponding enum for the integers -1, 0, 1.
        '''
        mapping = {1: cls.UP, 0: cls.NEUTRAL, -1: cls.DOWN}
        return mapping[i]


@vote_blueprint.route('/vote', methods=['POST'])
def vote():
    '''
    Saves the vote of a user for a price, or undos
    the user's vote if dir = 0.
    Users cannot upvote twice, downvote twice, or
    undo their vote if they have not voted.
    However, they can change their upvote to a downvote
    or vice versa.

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
