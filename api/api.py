import json
import time
from bson import ObjectId
from flask import Flask, request, jsonify, Response

from youtube_live_chats import get_chat_collection
from youtube_live_details import get_active_sessions

app = Flask(__name__)

def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

@app.after_request
def after_request(response):
    return add_cors_headers(response)

@app.route('/api/active-sessions', methods=['GET'])
def get_sessions():
    """Return a list of currently active live sessions."""
    try:
        sessions = get_active_sessions()
        for session in sessions:
            session['_id'] = str(session['_id'])
            if session.get('created_at'): session['created_at'] = session['created_at'].isoformat()
            if session.get('updated_at'): session['updated_at'] = session['updated_at'].isoformat()
            if session.get('ended_at'): session['ended_at'] = session['ended_at'].isoformat()
        return jsonify({"sessions": sessions})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/chats/<video_id>', methods=['GET'])
def get_chats(video_id):
    """
    Get chats for a specific video.
    Query param `last_id` can be used to fetch only new messages.
    """
    try:
        chat_collection = get_chat_collection(video_id)
    except Exception as e:
        return jsonify({"error": str(e)}), 404

    last_id = request.args.get('last_id')
    query = {}
    if last_id:
        try:
            query = {"_id": {"$gt": ObjectId(last_id)}}
        except:
            return jsonify({"error": "Invalid last_id"}), 400

    try:
        cursor = chat_collection.find(query).sort("_id", 1).limit(100)
        chats = []
        for chat in cursor:
            chat['_id'] = str(chat['_id'])
            if chat.get('created_at'): chat['created_at'] = chat['created_at'].isoformat()
            if chat.get('updated_at'): chat['updated_at'] = chat['updated_at'].isoformat()
            chats.append(chat)
        return jsonify({"chats": chats})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/chats/stream/<video_id>', methods=['GET'])
def stream_chats(video_id):
    """
    Server-Sent Events (SSE) endpoint.
    Streams new chats to the frontend as soon as they are inserted into the database.
    """
    def event_stream():
        try:
            chat_collection = get_chat_collection(video_id)
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        last_id = None
        
        # Initial load: get last 50 messages to populate UI
        try:
            initial_chats = list(chat_collection.find().sort("_id", -1).limit(50))
            initial_chats.reverse()
            
            for chat in initial_chats:
                chat['_id'] = str(chat['_id'])
                if chat.get('created_at'): chat['created_at'] = chat['created_at'].isoformat()
                if chat.get('updated_at'): chat['updated_at'] = chat['updated_at'].isoformat()
                
                yield f"data: {json.dumps(chat)}\n\n"
                last_id = chat['_id']
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        while True:
            query = {}
            if last_id:
                query = {"_id": {"$gt": ObjectId(last_id)}}
            
            try:
                cursor = chat_collection.find(query).sort("_id", 1)
                
                for chat in cursor:
                    chat['_id'] = str(chat['_id'])
                    if chat.get('created_at'): chat['created_at'] = chat['created_at'].isoformat()
                    if chat.get('updated_at'): chat['updated_at'] = chat['updated_at'].isoformat()
                    
                    yield f"data: {json.dumps(chat)}\n\n"
                    last_id = chat['_id']
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                return
            
            time.sleep(1)

    return Response(event_stream(), mimetype="text/event-stream")

if __name__ == '__main__':
    # Default port 5000. For production, consider using gunicorn.
    print("Starting API Server on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
