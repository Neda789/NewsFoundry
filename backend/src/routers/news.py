from fastapi import APIRouter, HTTPException, Query

from services.worldnews import get_top_news, WorldNewsAPIError

router = APIRouter(prefix="/news", tags=["news"])


@router.get("/top")
async def read_top_news(
    source_country: str = Query(default="fr", description="Code pays ISO (ex: fr, us, gb)"),
    language: str = Query(default="fr", description="Code langue (ex: fr, en)"),
):
    """Retourne les breaking news pour un pays/langue donnés."""
    try:
        articles = await get_top_news(source_country=source_country, language=language)
    except WorldNewsAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"articles": articles}