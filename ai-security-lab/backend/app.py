from flask import Flask, jsonify, request
from flask_cors import CORS

from engine import state, knowledge_base, llm_simulator

app = Flask(__name__)
CORS(app)


@app.get("/api/missions")
def get_missions():
    return jsonify(state.get_missions())


@app.get("/api/missions/<mission_id>")
def get_mission(mission_id):
    mission = state.get_mission(mission_id)
    if not mission:
        return jsonify({"error": "not found"}), 404
    return jsonify(mission)


@app.get("/api/state")
def get_state():
    return jsonify({
        "score": state.get_score(),
        "signals": state.get_signals(),
        "defenses": state.get_defenses(),
        "missions": state.get_missions(),
    })


@app.get("/api/kb")
def get_kb():
    return jsonify(knowledge_base.get_all_docs())


@app.get("/api/defenses")
def get_defenses():
    return jsonify(state.get_defenses())


@app.post("/api/defenses/<defense_id>/toggle")
def toggle_defense(defense_id):
    updated = state.toggle_defense(defense_id)
    if not updated:
        return jsonify({"error": "not found"}), 404
    state.add_signal(f'{updated["label"]} {"enabled" if updated["enabled"] else "disabled"}', "info")
    return jsonify({"defense": updated, "score": state.get_score()})


@app.post("/api/attack")
def attack():
    body = request.get_json(force=True) or {}
    mission_id = body.get("mission_id", "prompt-injection")
    message = (body.get("message") or "").strip()
    persona = body.get("persona", "intern")

    mission = state.get_mission(mission_id)
    if not mission:
        return jsonify({"error": "unknown mission"}), 404
    if not mission["implemented"]:
        return jsonify({
            "blocked": True,
            "flag_captured": False,
            "response": "This mission's attack engine isn't wired up yet - check back soon.",
            "retrieved_docs": [],
            "trace": [],
        })
    if not message:
        return jsonify({"error": "message is required"}), 400

    defenses = {d["id"]: d["enabled"] for d in state.get_defenses()}
    result = llm_simulator.run_attack(message, persona, defenses)

    if result.get("signal"):
        label, severity = result["signal"]
        state.add_signal(label, severity)

    if result["flag_captured"] and mission["status"] != "cleared":
        state.clear_mission(mission_id)

    result["mission_status"] = state.get_mission(mission_id)["status"]
    return jsonify(result)


@app.post("/api/reset")
def reset():
    state.reset()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True, port=5000, use_reloader=False)
