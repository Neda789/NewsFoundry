from sqlalchemy import JSON
from sqlmodel import Column, Field, SQLModel
from typing import Optional


class User(SQLModel, table=True):
    id: Optional[int] = Field(primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str = Field()


class Chat(SQLModel, table=True):
    id: Optional[int] = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    title: str = Field(default="Nouvelle discussion")
    system_prompt: str = Field(default="")
    messages: list = Field(default_factory=list, sa_column=Column(JSON))