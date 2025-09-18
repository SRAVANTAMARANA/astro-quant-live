from flask import Flask, send_from_directory, jsonify
app = Flask(__name__, static_folder='public', static_url_path='/')
@app.route("/")
def index():
    return send_from_directory('public','index.html')
@app.route("/ping")
def ping():
    return jsonify({"pong":"ok"})
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
