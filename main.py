from fastapi import FastAPI, HTTPException
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from contextlib import asynccontextmanager
import firebase_admin
from firebase_admin import credentials, firestore
from models import Ride
from typing import List

class Settings(BaseSettings):
    PORT: int
    DATABASE_URL: str

    model_config = ConfigDict(env_file='.env')
settings = Settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    try:
        cred = credentials.Certificate('credentials.json')
        firebase_app = firebase_admin.initialize_app(cred, {
            'databaseURL': settings.DATABASE_URL
        })
        db = firestore.client(app=firebase_app, database_id="rides")
        rides_ref = db.collection("rides")
        print("Firebase Admin SDK initialized successfully.")
    except Exception as e:
        print(f"Error initializing Firebase Admin SDK: {e}")
        rides_ref = None
        db = None
        firebase_app = None

    app.state.rides_ref = rides_ref
    app.state.db = db
    app.state.firebase_app = firebase_app
    yield

    # --- Shutdown ---
    try:
        if db:
            print("Closing Firestore client...")
            db.close()
            print("Firestore client closed.")
        if firebase_app:
            firebase_admin.delete_app(firebase_app)
            print("Firebase Admin SDK app deleted successfully.")
    except Exception as e:
        print(f"Error deleting Firebase Admin SDK app: {e}")

app = FastAPI(
    root_path="/rides",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
    )

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/", response_model=List[Ride])
async def get_rides():
    rides_ref = app.state.rides_ref
    if not rides_ref:
        raise HTTPException(status_code=500, detail="Firestore not initialized")
        
    docs = rides_ref.stream()
    rides = []
    for doc in docs:
        ride_data = doc.to_dict()
        try:
            ride_model = Ride.model_validate(ride_data)
            rides.append(ride_model.model_dump())
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Error parsing ride document: {exc}")
    return rides

@app.post("/", response_model=Ride)
async def create_ride(ride: Ride):
    ride_data = ride.model_dump()
    rides_ref = app.state.rides_ref
    if not rides_ref:
        raise HTTPException(status_code=500, detail="Firestore not initialized")

    ride_ref = rides_ref.document(ride.rideId)
    # Check if a ride document already exists.
    existing = ride_ref.get()
    if existing.exists:
        raise HTTPException(status_code=400, detail="Ride already exists")
    
    try:
        ride_ref.set(ride_data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error creating ride document: {exc}")
    
    return ride

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)