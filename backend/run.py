import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        print("start running server......")
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)
