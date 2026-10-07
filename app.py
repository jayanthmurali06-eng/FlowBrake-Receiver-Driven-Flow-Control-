from flask import Flask, jsonify, render_template, request, send_from_directory
from werkzeug.utils import secure_filename
import os
from simulator import FlowBrakeSimulator

app = Flask(__name__)
sim = FlowBrakeSimulator()

UPLOAD_DIR = os.path.join(app.root_path, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500 MB

@app.post("/api/upload")
def upload_file():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "No file field received."}), 400

    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"ok": False, "error": "Please choose a file."}), 400

    filename = secure_filename(file.filename)
    if not filename:
        return jsonify({"ok": False, "error": "Invalid file name."}), 400

    # Keep only one active demo file.
    for old_name in os.listdir(UPLOAD_DIR):
        old_path = os.path.join(UPLOAD_DIR, old_name)
        if os.path.isfile(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass

    path = os.path.join(UPLOAD_DIR, filename)
    file.save(path)
    size = os.path.getsize(path)

    sim.set_file(filename, size)

    return jsonify({
        "ok": True,
        "filename": filename,
        "size": size,
        "size_human": human_size(size),
        "packet_size": sim.PACKET_SIZE,
        "total_packets": sim.total_packets,
        "download_url": f"/api/download/{filename}",
        "state": sim.state()
    })

@app.get("/api/download/<path:filename>")
def download_file(filename):
    return send_from_directory(UPLOAD_DIR, filename, as_attachment=True)

def human_size(size):
    size = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}"
        size /= 1024


@app.get("/")
def index():
    return render_template("index.html")

@app.get("/api/state")
def state():
    return jsonify(sim.state())

@app.post("/api/reset")
def reset():
    data = request.get_json(silent=True) or {}
    sim.reset(
        buffer_capacity=int(data.get("buffer_capacity", 100)),
        drain_rate=int(data.get("drain_rate", 12)),
        base_send_rate=int(data.get("base_send_rate", 25)),
        adaptive=bool(data.get("adaptive", True)),
    )
    if sim.file_size:
        sim.print_terminal_header()
    return jsonify(sim.state())

@app.post("/api/step")
def step():
    data = request.get_json(silent=True) or {}
    return jsonify(sim.step(
        incoming_rate=int(data.get("incoming_rate", sim.base_send_rate)),
        drain_rate=int(data.get("drain_rate", sim.drain_rate)),
        adaptive=bool(data.get("adaptive", sim.adaptive)),
    ))

@app.errorhandler(413)
def too_large(_error):
    return jsonify({"ok": False, "error": "File is too large. Maximum size is 500 MB."}), 413

if __name__ == "__main__":
    print("\\nFlowBrake server starting...", flush=True)
    print("Open http://127.0.0.1:5000 in your browser.", flush=True)
    print("Terminal output will show every receiver-flow-control tick.\\n", flush=True)
    app.run(debug=True, host="127.0.0.1", port=5000, use_reloader=False)
