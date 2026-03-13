import os
from flask import Flask, jsonify, request
from google.cloud import firestore

app = Flask(__name__)

# Initialize Firestore DB client
db = firestore.Client()
collection_name = 'messages'

@app.route('/')
def hello_world():
    return 'Hello from Containerized Flask App on Cloud Run!'

@app.route('/messages', methods=['POST'])
def add_message():
    content_type = request.headers.get('Content-Type')
    if (content_type == 'application/json'):
        request_json = request.json
        message = request_json.get('message')
        if message:
            doc_ref = db.collection(collection_name).add({'message': message})
            return jsonify({"id": doc_ref[1].id, "message": message}), 201
        return jsonify({"error": "Message field is required"}), 400
    return jsonify({"error": "Content-Type must be application/json"}), 400

@app.route('/messages', methods=['GET'])
def get_messages():
    messages = []
    docs = db.collection(collection_name).stream()
    for doc in docs:
        messages.append(doc.to_dict())
    return jsonify(messages), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
