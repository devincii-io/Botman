from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/slack/events', methods=['POST'])
def slack_endpoint():
    """Endpoint for receiving Slack webhook messages"""
    try:
        # Extract incoming Slack webhook data
        data = request.form.to_dict() if request.form else request.json
        
        # Print the message to console
        print(f"[SLACK] Incoming webhook received:")
        for key, value in data.items():
            print(f"  {key}: {value}")
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        print(f"Error processing Slack message: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/chime/webhook', methods=['POST'])
def chime_endpoint():
    """Endpoint for receiving Amazon Chime webhook messages"""
    try:
        # Extract simple Chime message data
        data = request.json
        
        # Expecting simple format: {content: "message"}
        message = data.get('content', '')
        
        # Print the message to console
        print(f"[CHIME] Message received: {message}")
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        print(f"Error processing Chime message: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    print("Starting server on http://localhost:5000")
    print("Slack endpoint: http://localhost:5000/slack/events")
    print("Chime endpoint: http://localhost:5000/chime/webhook")
    app.run(debug=True) 