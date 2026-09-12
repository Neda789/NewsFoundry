from database import init_db
from fastapi import FastAPI
from routers import news
import uvicorn

app = FastAPI()

app.include_router(news.router)


@app.get("/")
async def hello():
    return {"message": "👋"}


if __name__ == "__main__":
    init_db()

    uvicorn.run(app, host="0.0.0.0", port=8000)