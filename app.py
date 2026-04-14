"""
Termite-Inspired Stigmergy Data Center Cooling
Main Flask application
"""

from flask import Flask, render_template, jsonify, request
from simulation.datacenter import DataCenter
import threading
import time

app = Flask(__name__)

# Global simulation instance
dc = DataCenter(rows=4, cols=6)
sim_running = True
sim_thread = None


def simulation_loop():
    """Background thread: advances simulation every 0.5s"""
    while True:
        if sim_running:
            dc.step()
        time.sleep(0.5)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/state")
def get_state():
    return jsonify(dc.get_state())


@app.route("/api/control", methods=["POST"])
def control():
    data = request.json
    action = data.get("action")

    if action == "add_hotspot":
        idx = data.get("rack_index")
        dc.add_hotspot(idx)
        return jsonify({"ok": True, "msg": f"Hotspot added to rack {idx + 1}"})

    elif action == "set_ambient":
        dc.ambient = float(data.get("value", 24))
        return jsonify({"ok": True})

    elif action == "set_evaporation":
        dc.evaporation_rate = float(data.get("value", 5))
        return jsonify({"ok": True})

    elif action == "set_load":
        rack_idx = data.get("rack_index")
        val = float(data.get("value", 0.5))
        dc.racks[rack_idx].load = val
        return jsonify({"ok": True})

    elif action == "reset":
        dc.reset()
        return jsonify({"ok": True})

    elif action == "toggle_pause":
        global sim_running
        sim_running = not sim_running
        return jsonify({"ok": True, "running": sim_running})

    elif action == "add_random_load_spike":
        dc.random_load_spike()
        return jsonify({"ok": True})

    return jsonify({"ok": False, "msg": "Unknown action"}), 400


if __name__ == "__main__":
    sim_thread = threading.Thread(target=simulation_loop, daemon=True)
    sim_thread.start()
    print("🐜 Termite Cooling Simulation running at http://localhost:5000")
    app.run(debug=False, port=5000)
