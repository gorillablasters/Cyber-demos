"""Warm the small local model once; remain alive for supervisor monitoring."""
import json
import os
import time
import urllib.request

payload = json.dumps({'model': os.environ['OLLAMA_MODEL'], 'prompt': 'Hi',
                      'stream': False, 'keep_alive': -1,
                      'options': {'num_predict': 1, 'num_ctx': 4096}}).encode()
for attempt in range(30):
    try:
        request = urllib.request.Request('http://127.0.0.1:11434/api/generate', data=payload,
                                         headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(request, timeout=180) as response:
            json.load(response)
        print('Conversation model ready.', flush=True)
        break
    except Exception:
        time.sleep(2)
else:
    raise SystemExit('Model warmup failed; inspect API logs.')
while True:
    time.sleep(3600)
