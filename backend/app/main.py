try:
	from app.api.app import app
except ModuleNotFoundError:
	from backend.app.api.app import app
