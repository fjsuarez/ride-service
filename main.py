from fastapi import FastAPI
from config import settings
from firebase_client import lifespan
from routes import ride_routes, commute_routes, request_routes
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(
    root_path="/rides",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

@app.get("/health", include_in_schema=False)
async def health_check():
    return {"status": "ok"}

app.include_router(ride_routes.router, tags=["Rides"])
app.include_router(commute_routes.router, tags=["Commutes"])
app.include_router(request_routes.router, tags=["Requests"])

if __name__ == "__main__":
    import uvicorn
    print(f"PORT {settings.PORT}")
    print(f"DATABASE_URL {settings.DATABASE_URL}")
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)