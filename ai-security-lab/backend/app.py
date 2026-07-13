from flask import Flask, jsonify, request
from flask_cors import CORS

from engine import state, knowledge_base, llm_simulator, explanations

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


@app.get("/api/kb/<mission_id>")
def get_mission_kb(mission_id):
    return jsonify(knowledge_base.get_mission_docs(mission_id))


@app.post("/api/kb/poison")
def poison_kb():
    body = request.get_json(force=True) or {}
    mission_id = body.get("mission_id")
    doc_id = body.get("doc_id")
    content = body.get("content")
    title = body.get("title", doc_id)
    classification = body.get("classification", "public")
    if not mission_id or not doc_id or not content:
        return jsonify({"error": "mission_id, doc_id, and content are required"}), 400
    doc = knowledge_base.poison_doc(mission_id, doc_id, title, content, classification)
    state.add_signal(f'Knowledge base modified: {doc_id}', "critical")
    return jsonify(doc)


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
            "blocked": True, "flag_captured": False,
            "response": "This mission's attack engine isn't wired up yet - check back soon.",
            "retrieved_docs": [], "trace": [],
        })
    if not message:
        return jsonify({"error": "message is required"}), 400

    defenses = {d["id"]: d["enabled"] for d in state.get_defenses()}
    result = llm_simulator.run_attack(mission_id, message, persona, defenses)

    if result.get("signal"):
        label, severity = result["signal"]
        state.add_signal(label, severity)

    if result["flag_captured"] and mission["status"] != "cleared":
        state.clear_mission(mission_id)

    if result["flag_captured"]:
        result["explain"] = explanations.get_explanation(mission_id)

    result["mission_status"] = state.get_mission(mission_id)["status"]
    return jsonify(result)


@app.post("/api/reset")
def reset():
    state.reset()
    knowledge_base.reset()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True, port=5000, use_reloader=False)
