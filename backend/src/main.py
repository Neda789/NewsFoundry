from database import init_db
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, chat, news
import uvicorn

app = FastAPI()

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://tvoj-projekat.vercel.app",  # zamijeni sa tvojim stvarnim Vercel URL-om
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(news.router)

@app.get("/")
async def hello():
    return {"message": "👋"}

if __name__ == "__main__":
    init_db()

    uvicorn.run(app, host="0.0.0.0", port=8000)