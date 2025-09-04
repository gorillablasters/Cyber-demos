migrate:
	python -m alembic upgrade head

revision:
	python -m alembic revision --autogenerate -m "$(m)"
