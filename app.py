from flask import Flask, render_template
from app.subsystems.dashboard.routes import dashboard_bp

app = Flask(__name__)
app.register_blueprint(dashboard_bp)

@app.route("/")
def home():
    # Renders a simple HTML template for our MVP
    return render_template("index.html", title="AI Waste Sorting Assistant", message="Hello World! Flask is up and running.")

if __name__ == "__main__":
    # Host 0.0.0.0 allows Docker to expose the port to your local machine
    app.run(host="0.0.0.0", port=8000, debug=True)