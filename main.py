from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI()

# -------------------------
# U4: Error Page Improvements
# -------------------------
@app.exception_handler(HTTPException)
async def http_error_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.get("/error-test")
def error_test():
    raise HTTPException(status_code=400, detail="Something broke 😅")


# -------------------------
# U5: Keyboard Nav / A11y (simple API indicator)
# -------------------------
@app.get("/accessibility-info")
def accessibility_info():
    return {
        "keyboard_navigation": "supported via API endpoints",
        "a11y_features": [
            "clear JSON responses",
            "structured error messages",
            "screen-reader friendly data format"
        ]
    }


# -------------------------
# U6: Dark Mode (frontend flag simulation)
# -------------------------
@app.get("/theme")
def theme():
    return {
        "mode": "dark",
        "ui": {
            "background": "#0f0f0f",
            "text": "#ffffff"
        }
    }


@app.get("/")
def root():
    return {"message": "Server is alive 🚀"}
