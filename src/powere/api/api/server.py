# src/api/server.py

from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.responses import RedirectResponse

# 1) Deinen Dash-App importieren
from powere.powere.dashboard.app import app as dash_app

# 2) FastAPI-Instanz anlegen
app = FastAPI(
    title="PowerE API",
    description="REST API + Dash-Dashboard in einem Server",
    version="0.1.0",
)


# 3) Root ("/") auf das Dash unter "/dashboard" weiterleiten
@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/dashboard")


# 4) Dash als WSGI-Middleware unter "/dashboard" mounten
app.mount("/dashboard", WSGIMiddleware(dash_app.server))

# 5) (Optional) hier kannst du später deine API-Router mounten,
#    sobald du sie unter src/api/routers/* implementiert hast:
#
# from powere.api.routers import jasm, market, tertiary, survey
# app.include_router(jasm.router,     prefix="/jasm",     tags=["jasm"])
# app.include_router(market.router,   prefix="/market",   tags=["market"])
# app.include_router(tertiary.router, prefix="/tertiary", tags=["tertiary"])
# app.include_router(survey.router,   prefix="/survey",   tags=["survey"])

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api.server:app", host="0.0.0.0", port=8000, reload=True)
