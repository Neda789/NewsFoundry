"""Chat avec un agent PydanticAI (Gemini), contextualisé avec l'actualité du jour.

L'historique complet de chaque discussion est sauvegardé dans le champ
JSON `Chat.messages`. Le prompt système (base + résumé des actualités du
jour via WorldNewsAPI) est généré une seule fois, à la création de la
discussion, et sauvegardé dans `Chat.system_prompt` pour rester stable
tout au long de la discussion (Étape 5).
"""

import os
from dataclasses import dataclass
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from sqlmodel import Session, select

from database import engine
from models import Chat, User
from routers.auth import get_current_user
from services.worldnews import WorldNewsAPIError, get_top_news, search_news as search_news_api

router = APIRouter(prefix="/chats", tags=["chats"])

BASE_SYSTEM_PROMPT = (
    "Tu es l'assistant de NewsFoundry, une application qui aide les "
    "utilisateurs à comprendre l'actualité. Réponds de façon claire, "
    "concise et neutre, en français sauf si l'utilisateur écrit dans une "
    "autre langue. Quand c'est pertinent, structure tes réponses avec du "
    "Markdown (titres, listes, gras) pour faciliter la lecture."
)


async def _build_news_digest() -> str:
    """Résumé compact (titre + résumé) des actualités du jour.

    On n'intègre que le titre et le résumé de chaque article (pas le
    texte complet) pour garder le prompt système court.
    """
    try:
        articles = await get_top_news()
    except WorldNewsAPIError:
        return ""

    lines = []
    for article in articles[:15]:
        title = (article.get("title") or "").strip()
        summary = (article.get("summary") or article.get("text") or "").strip()
        if not title:
            continue
        if summary:
            summary = summary[:280]
            lines.append(f"- {title} : {summary}")
        else:
            lines.append(f"- {title}")

    return "\n".join(lines)


async def build_system_prompt() -> str:
    """Prompt système complet (base + actualités), généré à la création d'une discussion."""
    digest = await _build_news_digest()
    if not digest:
        return BASE_SYSTEM_PROMPT

    return (
        f"{BASE_SYSTEM_PROMPT}\n\n"
        "Voici un résumé des principales actualités du jour, à utiliser "
        "pour répondre aux questions sur l'actualité récente (ces "
        "informations sont plus à jour que tes connaissances internes) :\n\n"
        f"{digest}"
    )


@dataclass
class ChatDeps:
    system_prompt: str


agent = Agent(
    os.getenv("CHAT_MODEL", "google:gemini-3.6-flash"),
    deps_type=ChatDeps,
)


@agent.system_prompt
def _dynamic_system_prompt(ctx: RunContext[ChatDeps]) -> str:
    return ctx.deps.system_prompt


@agent.tool_plain
async def search_news(query: str) -> str:
    """Recherche des articles d'actualité sur un sujet précis pour approfondir une discussion.

    À utiliser quand l'utilisateur demande plus de détails, d'exemples ou de contexte
    sur un sujet spécifique qui nécessite de charger des articles supplémentaires.

    Args:
        query: Les mots-clés ou le sujet à rechercher dans l'actualité.
    """
    try:
        articles = await search_news_api(query)
    except WorldNewsAPIError:
        return "Aucun article n'a pu être trouvé pour cette recherche."

    if not articles:
        return "Aucun article trouvé pour cette recherche."

    lines = []
    for article in articles[:5]:
        title = (article.get("title") or "").strip()
        summary = (article.get("summary") or article.get("text") or "").strip()
        url = (article.get("url") or "").strip()
        if not title:
            continue
        line = f"- {title}"
        if summary:
            line += f" : {summary[:280]}"
        if url:
            line += f" ({url})"
        lines.append(line)

    return "\n".join(lines) if lines else "Aucun article pertinent trouvé."


# --- Étape 7 : agent spécialisé pour générer une revue de presse ---------

class ArticleSynthese(BaseModel):
    title: str
    summary: str


class PressReviewOutput(BaseModel):
    title: str
    synthese_generale: str
    syntheses_articles: List[ArticleSynthese]


PRESS_REVIEW_SYSTEM_PROMPT = (
    "Tu es un journaliste qui rédige une revue de presse synthétique à "
    "partir d'une discussion entre un utilisateur et un assistant "
    "d'actualités. On te donnera un sujet précis sur lequel te concentrer : "
    "ignore le reste de la discussion qui n'est pas lié à ce sujet. Rédige "
    "un titre court et accrocheur, une synthèse générale claire et "
    "concise, et pour chaque article distinct mentionné dans la "
    "discussion en lien avec ce sujet, une courte synthèse de son "
    "contenu. Réponds en français."
)

press_review_agent = Agent(
    os.getenv("CHAT_MODEL", "google:gemini-3.6-flash"),
    output_type=PressReviewOutput,
    system_prompt=PRESS_REVIEW_SYSTEM_PROMPT,
)


class ChatCreate(BaseModel):
    title: Optional[str] = None


class ChatRead(BaseModel):
    id: int
    title: str


class MessageOut(BaseModel):
    role: str
    content: str


class ChatDetail(ChatRead):
    messages: List[MessageOut]


class MessageCreate(BaseModel):
    content: str


class PressReviewRequest(BaseModel):
    topic: str


class PressReviewRead(BaseModel):
    chat_id: int
    chat_title: str
    title: str
    summary: str
    articles: List[ArticleSynthese]


def _get_owned_chat(chat_id: int, current_user: User, session: Session) -> Chat:
    chat = session.get(Chat, chat_id)
    if not chat or chat.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discussion introuvable",
        )
    return chat


def _to_readable(messages: List[ModelMessage]) -> List[MessageOut]:
    """Transforme l'historique PydanticAI en liste simple {role, content}."""
    readable: List[MessageOut] = []
    for message in messages:
        if isinstance(message, ModelRequest):
            for part in message.parts:
                if isinstance(part, UserPromptPart):
                    readable.append(MessageOut(role="user", content=str(part.content)))
        elif isinstance(message, ModelResponse):
            for part in message.parts:
                if isinstance(part, TextPart):
                    readable.append(MessageOut(role="assistant", content=part.content))
    return readable


@router.post("", response_model=ChatRead, status_code=status.HTTP_201_CREATED)
async def create_chat(
    chat_in: ChatCreate,
    current_user: User = Depends(get_current_user),
):
    """Démarre une nouvelle discussion, avec un prompt système contextualisé par l'actualité du jour."""
    system_prompt = await build_system_prompt()

    chat = Chat(
        user_id=current_user.id,
        title=chat_in.title or "Nouvelle discussion",
        messages=[],
        system_prompt=system_prompt,
    )
    with Session(engine) as session:
        session.add(chat)
        session.commit()
        session.refresh(chat)
        return ChatRead(id=chat.id, title=chat.title)


@router.get("", response_model=List[ChatRead])
async def list_chats(current_user: User = Depends(get_current_user)):
    """Liste les discussions passées de l'utilisateur connecté."""
    with Session(engine) as session:
        chats = session.exec(
            select(Chat).where(Chat.user_id == current_user.id)
        ).all()
        return [ChatRead(id=c.id, title=c.title) for c in chats]


@router.get("/press-reviews", response_model=List[PressReviewRead])
async def list_press_reviews(current_user: User = Depends(get_current_user)):
    """Liste les revues de presse déjà générées, pour toutes les discussions de l'utilisateur.

    IMPORTANT : cette route doit être déclarée AVANT "/{chat_id}" ci-dessous,
    sinon FastAPI essaierait de traiter "press-reviews" comme un chat_id.
    """
    with Session(engine) as session:
        chats = session.exec(
            select(Chat).where(
                Chat.user_id == current_user.id,
                Chat.press_review_title.is_not(None),
            )
        ).all()
        return [
            PressReviewRead(
                chat_id=c.id,
                chat_title=c.title,
                title=c.press_review_title,
                summary=c.press_review_summary or "",
                articles=[ArticleSynthese(**a) for a in (c.press_review_articles or [])],
            )
            for c in chats
        ]


@router.get("/{chat_id}", response_model=ChatDetail)
async def get_chat(chat_id: int, current_user: User = Depends(get_current_user)):
    """Reprend une discussion existante avec son historique complet."""
    with Session(engine) as session:
        chat = _get_owned_chat(chat_id, current_user, session)
        history = ModelMessagesTypeAdapter.validate_python(chat.messages)
        return ChatDetail(id=chat.id, title=chat.title, messages=_to_readable(history))


@router.post(
    "/{chat_id}/messages",
    response_model=MessageOut,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    chat_id: int,
    message_in: MessageCreate,
    current_user: User = Depends(get_current_user),
):
    """Envoie un message utilisateur et renvoie la réponse du LLM."""
    with Session(engine) as session:
        chat = _get_owned_chat(chat_id, current_user, session)
        history = ModelMessagesTypeAdapter.validate_python(chat.messages)

        deps = ChatDeps(system_prompt=chat.system_prompt or BASE_SYSTEM_PROMPT)
        result = await agent.run(message_in.content, message_history=history, deps=deps)

        chat.messages = ModelMessagesTypeAdapter.dump_python(
            result.all_messages(), mode="json"
        )
        session.add(chat)
        session.commit()

        return MessageOut(role="assistant", content=result.output)


@router.post(
    "/{chat_id}/press-review",
    response_model=PressReviewRead,
    status_code=status.HTTP_201_CREATED,
)
async def generate_press_review(
    chat_id: int,
    review_in: PressReviewRequest,
    current_user: User = Depends(get_current_user),
):
    """Génère (ou régénère) la revue de presse d'une discussion, sur un sujet donné (Étape 7)."""
    with Session(engine) as session:
        chat = _get_owned_chat(chat_id, current_user, session)
        history = ModelMessagesTypeAdapter.validate_python(chat.messages)

        if not history:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cette discussion ne contient encore aucun message.",
            )

        result = await press_review_agent.run(
            f"Rédige la revue de presse sur le sujet suivant : {review_in.topic}",
            message_history=history,
        )
        output = result.output

        chat.press_review_title = output.title
        chat.press_review_summary = output.synthese_generale
        chat.press_review_articles = [a.model_dump() for a in output.syntheses_articles]
        session.add(chat)
        session.commit()

        return PressReviewRead(
            chat_id=chat.id,
            chat_title=chat.title,
            title=output.title,
            summary=output.synthese_generale,
            articles=output.syntheses_articles,
        )