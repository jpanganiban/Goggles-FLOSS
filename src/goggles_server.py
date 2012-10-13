from gevent import monkey
monkey.patch_all()
from gevent import pywsgi

from flask import Flask, request, abort, jsonify
from FlannManager import FlannManager
from bson.objectid import ObjectId
import pymongo
import os
import json


app = Flask(__name__)

# Flan manager instance
fm = FlannManager()

# Database
conn = pymongo.Connection()


def db(collection=None):
    """Returns database or collection"""
    if not collection:
        return conn['swag']

    return conn['swag'][collection]


def validate_photo(path):
    """Checks if path is a photo"""

    # Check if file exists
    if not os.path.exists(path):
        return (False, "Error: Path does not exist")

    # Check if it's a directory
    if os.path.isdir(path):
        return (False, "Error: Only takes a single photo")

    return (True, "Success")


@app.route('/recognize', methods=['GET', 'POST'])
def recognition_controller():
    """Photo Controller

    To query a photo, use GET:

        /recognize?swag_id=<swag_id>

    To add a photo, use POST:

        headers:

            Content-Type: application/json

        data:

            {
                'swag_id': <swag_id>
            }

    """

    if request.method == 'GET':

        # Get photo path
        swag_id = request.args.get('swag_id', None)

        # Check if necessary data is available
        if not swag_id:
            abort(400, "Error: required paramter swag_id")

        # Retrieve image data
        swag = db('swags').find_one({'_id': ObjectId(swag_id)})
        if not swag:
            abort(404, "Error: Swag not found")

        # Validate photo if it exists
        success, response = validate_photo(swag['image_path'])
        if not success:
            abort(400, response)

        # Execute the query and return the result
        result = json.loads(fm.query(swag['image_path'])).get('results')
        return jsonify({'result': result})

    elif request.method == 'POST':

        # Get photo path
        swag_id = request.json.get('swag_id', None)

        # Get swag
        swag = db('swags').find_one({'_id': ObjectId(swag_id)})

        # Validate photo
        success, response = validate_photo(swag['image_path'])
        if not success:
            abort(400, response)

        # Add photo to FlannManager, get flannd' data.
        fm.add_photo(swag['_id'], swag['image_path'])

        ## Index photo
        #fm.create_index()

        # Return response.
        return jsonify({'_id': str(swag['_id']), 'image_path': swag['image_path']})

    else:
        abort(405)


@app.route('/reindex')
def reindex_controller():

    # Only index  TODO: Include tagged photos
    swags = db('swags').find({'meta': {'$exists': True}})

    # Only index if swags return more than 1
    if len(list(swags)) > 0:

        # Reindex all swags
        for swag in list(swags):
            print swag
            fm.add_photo(swag['_id'], swag['image_path'])

        fm.create_index()

    return jsonify({'status': 'success'})


def runserver(debug=True, port=9085, host='0.0.0.0'):
    """Adds and indexes all photos in the mongodb database then starts the
    server"""
    # Run server
    #app.run(debug=debug, port=port, host=host)
    server = pywsgi.WSGIServer((host, port), application=app.wsgi_app)
    server.serve_forever()


if __name__ == '__main__':
    runserver()
