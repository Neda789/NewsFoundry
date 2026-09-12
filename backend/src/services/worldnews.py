import httpx

from config import settings

WORLDNEWS_BASE_URL = "https://api.worldnewsapi.com"


class WorldNewsAPIError(Exception):
    """Levée lorsque l'appel à WorldNewsAPI échoue (réseau, timeout, erreur HTTP)."""


async def get_top_news(source_country: str = "fr", language: str = "fr") -> list[dict]:
    """
    Récupère les articles "top news" depuis WorldNewsAPI pour un pays/langue donnés.

    Lève une WorldNewsAPIError en cas d'échec, pour que la couche API
    (routers/news.py) puisse la transformer en réponse HTTP appropriée.
    """
    params = {
        "source-country": source_country,
        "language": language,
        "api-key": settings.worldnews_api_key,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{WORLDNEWS_BASE_URL}/top-news", params=params)
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise WorldNewsAPIError("WorldNewsAPI n'a pas répondu à temps.") from exc
    except httpx.HTTPStatusError as exc:
        raise WorldNewsAPIError(
            f"WorldNewsAPI a retourné une erreur ({exc.response.status_code})."
        ) from exc
    except httpx.RequestError as exc:
        raise WorldNewsAPIError("Impossible de contacter WorldNewsAPI.") from exc

    data = response.json()

    # WorldNewsAPI renvoie les articles regroupés par "cluster" (top_news -> news[]).
    # On aplatit cette structure pour renvoyer une simple liste d'articles au frontend.
    articles = []
    for cluster in data.get("top_news", []):
        articles.extend(cluster.get("news", []))

    return articles