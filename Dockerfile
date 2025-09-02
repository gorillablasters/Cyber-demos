FROM python:3.11-slim AS backend

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --upgrade pip && pip install pip-tools

RUN python - <<EOF
import tomllib, sys
from pathlib import Path
data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
deps = data.get("project", {}).get("dependencies", [])
Path("requirements.txt").write_text("\n".join(deps))
EOF


RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host","0.0.0.0","--port","8000"]