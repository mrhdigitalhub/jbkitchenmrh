"""
main.py di ROOT - WRAPPER TIPIS - 1 Sumber Kebenaran di app/main.py
"""
from app.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
