"""Chat avec un agent PydanticAI (Mistral).

L'historique complet de chaque discussion est sauvegardé dans le champ
JSON `Chat.messages`, au format natif de PydanticAI, pour reprendre la
conversation avec le contexte complet à chaque nouveau message.
"""

import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from pydantic_ai import Agent
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

router = APIRouter(prefix="/chats", tags=["chats"])

SYSTEM_PROMPT = (
    "Tu es l'assistant de NewsFoundry, une application qui aide les "
    "utilisateurs à comprendre l'actualité. Réponds de façon claire, "
    "concise et neutre, en français sauf si l'utilisateur écrit dans une "
    "autre langue. Quand c'est pertinent, structure tes réponses avec du "
    "Markdown (titres, listes, gras) pour faciliter la lecture."
)

agent = Agent(
    os.getenv("CHAT_MODEL", "mistral:mistral-small-latest"),
    system_prompt=SYSTEM_PROMPT,
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
    """Démarre une nouvelle discussion pour l'utilisateur connecté."""
    chat = Chat(
        user_id=current_user.id,
        title=chat_in.title or "Nouvelle discussion",
        messages=[],
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

        result = await agent.run(message_in.content, message_history=history)

        chat.messages = ModelMessagesTypeAdapter.dump_python(
            result.all_messages(), mode="json"
        )
        session.add(chat)
        session.commit()

        return MessageOut(role="assistant", content=result.output)