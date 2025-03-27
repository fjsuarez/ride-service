from contextlib import asynccontextmanager
from fastapi import FastAPI
import firebase_admin
from firebase_admin import credentials, firestore
from config import settings
from google.maps import routing_v2
from google.oauth2 import service_account

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
        requests_ref = db.collection("ride_requests")
        commutes_ref = db.collection("commutes")
        print("Firebase Admin SDK initialized successfully.")

        routes_credentials = service_account.Credentials.from_service_account_file(
            'credentials.json',
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        routes_client = routing_v2.RoutesAsyncClient(credentials=routes_credentials)
        print("Google Maps Routes API client initialized successfully.")
    except Exception as e:
        print(f"Error initializing Firebase Admin SDK: {e}")
        rides_ref = None
        requests_ref = None
        commutes_ref = None
        db = None
        firebase_app = None

    app.state.rides_ref = rides_ref
    app.state.requests_ref = requests_ref
    app.state.commutes_ref = commutes_ref
    app.state.db = db
    app.state.firebase_app = firebase_app
    app.state.routes_client = routes_client
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