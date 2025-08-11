from flask import Flask
from bot_dialog import handle_teams_message

app = Flask(__name__)

@app.route('/api/messages', methods=['POST'])
def messages():
    return handle_teams_message()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3978) 