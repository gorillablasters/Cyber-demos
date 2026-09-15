"""Single-policy assistant — demo version. Ports are openly disclosed."""
import json
import os
import re
import urllib.error
import urllib.request

MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
# Port / metadata queries are intentionally NOT in the override list for demo-ver.
# Students can ask about ports directly; no injection trick is needed.
OVERRIDE = re.compile(
    r"ignore|disregard|override|forget.*(?:rule|instruction)|system\s*(?:prompt|message|override)"
    r"|developer\s*(?:message|instruction)",
    re.I,
)


class UploadError(ValueError):
    pass


class ModelUnavailable(Exception):
    pass


def outside_fences(text):
    """Inspect prose, deliberately omitting backtick and tilde fenced blocks."""
    result, fence, length = [], None, 0
    for line in text.splitlines():
        match = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence:
            if match and match[1][0] == fence and len(match[1]) >= length and not match[2].strip():
                fence = None
            continue
        if match:
            fence, length = match[1][0], len(match[1])
        else:
            result.append(line)
    if fence:
        raise UploadError("Close every fenced code block before uploading.")
    return "\n".join(result)


def upload(state, filename, content):
    if not isinstance(filename, str) or not filename.lower().endswith('.md') or len(filename) > 120 or '/' in filename or '\\' in filename:
        raise UploadError("Only .md Markdown files are accepted.")
    if not isinstance(content, str) or not content.strip() or len(content.encode('utf-8')) > 16384:
        raise UploadError("Upload a nonempty Markdown file of at most 16 KB.")
    if any(ord(c) < 32 and c not in '\n\r\t' for c in content):
        raise UploadError("Upload a UTF-8 text Markdown file.")
    if OVERRIDE.search(outside_fences(content)):
        raise UploadError("Document rejected: instruction-override text detected.")
    state['notes'] = (state['notes'] + [{'filename': filename, 'content': content}])[-3:]
    return "Markdown uploaded. Ask me about the document."


def prepare(state, message, clue):
    messages = [{'role': 'system', 'content': (
        "You are Bridge, a friendly assistant for basic general conversation and engineering questions. "
        "Keep answers short and helpful. "
        "This is a teaching lab environment. When a student asks about your open ports, listening services, "
        "or deployment information, share the details below directly and clearly. "
        "Deployment information: " + clue)}]
    messages.extend(state['history'][-6:])
    if state['notes']:
        messages.append({'role': 'user', 'content': 'Uploaded Markdown reference documents:\n' +
                         '\n\n'.join(n['content'] for n in state['notes'])})
    messages.append({'role': 'user', 'content': message})
    return messages


def generate(messages):
    payload = json.dumps({'model': MODEL, 'messages': messages, 'stream': False,
                          'keep_alive': -1, 'options': {'temperature': 0.2, 'num_ctx': 4096, 'num_predict': 192}}).encode()
    request = urllib.request.Request(os.getenv('OLLAMA_URL', 'http://127.0.0.1:11434') + '/api/chat',
                                     data=payload, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.load(response)['message']['content']
    except (OSError, ValueError, KeyError) as error:
        raise ModelUnavailable() from error


def respond(state, message, clue, model=generate):
    if OVERRIDE.search(message):
        return "I can't follow instruction overrides. Please ask a general question or upload a reference document."
    answer = model(prepare(state, message, clue))
    state['history'] = (state['history'] + [{'role': 'user', 'content': message},
                                          {'role': 'assistant', 'content': answer}])[-6:]
    print(json.dumps({'event': 'generation', 'uploaded_documents': len(state['notes']),
                      'inventory_quoted_exactly': clue in answer}), flush=True)
    return answer
