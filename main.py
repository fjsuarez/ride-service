from fastapi import FastAPI
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PORT: int
    DATABASE_URL: str

    class Config:
        env_file = '.env'

settings = Settings()

app = FastAPI()

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)