"use client";

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { MessageSquare, FileText, LogOut, Send, LayoutDashboard, ArrowLeft, User, Newspaper } from 'lucide-react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';

interface Discussion {
  id: string;
  title: string;
}

interface ChatMessage {
  role: string;
  content: string;
}

function authHeaders() {
  const token = localStorage.getItem("access_token");
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };
}

export default function Home() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<'chat' | 'press'>('chat');
  const [message, setMessage] = useState('');
  const [chats, setChats] = useState<Discussion[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [activeChatTitle, setActiveChatTitle] = useState<string>('Nouvelle discussion');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);
  const [chatStarted, setChatStarted] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const fetchChats = useCallback(async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/chats`, {
        headers: authHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setChats(data.map((c: { id: number; title: string }) => ({ id: String(c.id), title: c.title })));
      }
    } catch {
      // silencieux pour le moment
    }
  }, []);

  // Provjera tokena odmah pri učitavanju (izbjegava setState u useEffect-u)
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.replace("/login");
      return;
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchChats();
  }, [router, fetchChats]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    router.replace("/login");
  };

  async function openChat(chatId: string, title: string) {
    setActiveChatId(chatId);
    setActiveChatTitle(title);
    setChatStarted(true);
    setLoadingMessages(true);
    setMessages([]);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/chats/${chatId}`, {
        headers: authHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setMessages(data.messages);
      }
    } finally {
      setLoadingMessages(false);
    }
  }

  function startNewChat() {
    setActiveChatId(null);
    setActiveChatTitle('Nouvelle discussion');
    setMessages([]);
    setChatStarted(true);
  }

  function goHome() {
    setActiveChatId(null);
    setMessages([]);
    setChatStarted(false);
  }

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    const content = message.trim();
    if (!content || sending) return;
    setMessage('');
    setSending(true);

    let chatId = activeChatId;

    try {
      if (!chatId) {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/chats`, {
          method: "POST",
          headers: authHeaders(),
          body: JSON.stringify({}),
        });
        const newChat = await res.json();
        chatId = String(newChat.id);
        setActiveChatId(chatId);
        setActiveChatTitle(newChat.title);
        setChatStarted(true);
        setChats((prev) => [{ id: chatId as string, title: newChat.title }, ...prev]);
      }

      setMessages((prev) => [...prev, { role: "user", content }]);

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/chats/${chatId}/messages`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ content }),
      });

      if (res.ok) {
        const data = await res.json();
        setMessages((prev) => [...prev, { role: data.role, content: data.content }]);
      } else {
        setMessages((prev) => [...prev, { role: "assistant", content: "Désolé, une erreur est survenue." }]);
      }
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", content: "Impossible de contacter le serveur." }]);
    } finally {
      setSending(false);
    }
  }

  async function handleGeneratePressReview() {
    if (!activeChatId) return;
    const topic = window.prompt("Sur quel sujet voulez-vous générer la revue de presse ?");
    if (!topic || !topic.trim()) return;

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/chats/${activeChatId}/press-review`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ topic: topic.trim() }),
      });
      if (res.ok) {
        const data = await res.json();
        alert(`Revue de presse générée : "${data.title}"`);
      } else {
        alert("Erreur lors de la génération de la revue de presse.");
      }
    } catch {
      alert("Impossible de contacter le serveur.");
    }
  }

  const inConversation = chatStarted || activeChatId !== null || messages.length > 0;

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-100 font-sans">

      {/* ----------------- BARRE LATÉRALE (SIDEBAR) ----------------- */}
      <aside className="flex w-80 flex-col border-r border-slate-200 bg-white">

        <div className="flex items-center justify-between px-6 py-5 border-b border-slate-100">
          <button onClick={goHome} className="flex items-center space-x-2">
            <span className="text-base font-bold tracking-wider text-purple-600">NEWSFOUNDRY</span>
            <LayoutDashboard className="h-4 w-4 text-purple-600" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
          {chats.length === 0 && (
            <p className="px-6 py-4 text-xs text-slate-400">Aucune discussion pour le moment.</p>
          )}
          {chats.map((item) => (
            <div
              key={item.id}
              onClick={() => openChat(item.id, item.title)}
              className={`cursor-pointer px-6 py-4 transition-colors hover:bg-slate-50 ${
                activeChatId === item.id ? "bg-purple-50" : ""
              }`}
            >
              <h4 className="text-sm font-medium text-slate-700">{item.title}</h4>
            </div>
          ))}
        </div>

        <div className="border-t border-slate-100 p-4">
          <button
            onClick={handleLogout}
            className="flex w-full items-center space-x-3 rounded-lg px-3 py-2.5 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-50 hover:text-slate-900"
          >
            <LogOut className="h-4 w-4 text-slate-500" />
            <span>Se déconnecter</span>
          </button>
        </div>
      </aside>

      {/* ----------------- CONTENU PRINCIPAL ----------------- */}
      <main className="flex flex-1 flex-col bg-slate-100">

        {inConversation ? (
          <header className="flex items-center justify-between border-b border-slate-200 bg-white px-8 py-3.5 shadow-sm">
            <div className="flex items-center space-x-3">
              <button onClick={goHome} className="rounded-full p-2 hover:bg-slate-100">
                <ArrowLeft className="h-4 w-4 text-slate-600" />
              </button>
              <div>
                <h2 className="text-sm font-semibold text-slate-800">{activeChatTitle}</h2>
                <span className="text-xs text-slate-400">Conversation active</span>
              </div>
            </div>
            <button
              onClick={handleGeneratePressReview}
              className="flex items-center space-x-2 rounded-full bg-purple-600 px-5 py-2 text-sm font-medium text-white shadow-sm transition-all hover:bg-purple-700"
            >
              <FileText className="h-4 w-4" />
              <span>Générer une revue de presse</span>
            </button>
          </header>
        ) : (
          <header className="flex items-center border-b border-slate-200 bg-white px-8 py-3.5 shadow-sm">
            <div className="flex space-x-3">
              <button
                onClick={() => { setActiveTab('chat'); startNewChat(); }}
                className={`flex items-center space-x-2 rounded-full px-5 py-2 text-sm font-medium transition-all ${
                  activeTab === 'chat'
                    ? 'bg-purple-600 text-white shadow-sm'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                <MessageSquare className="h-4 w-4" />
                <span>Chat</span>
              </button>

              <button
                onClick={() => setActiveTab('press')}
                className={`flex items-center space-x-2 rounded-full px-5 py-2 text-sm font-medium transition-all ${
                  activeTab === 'press'
                    ? 'bg-purple-600 text-white shadow-sm'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                <FileText className="h-4 w-4" />
                <span>Revue de presse</span>
              </button>
            </div>
          </header>
        )}

        {inConversation ? (
          <div className="flex flex-1 flex-col overflow-y-auto p-8 space-y-4">
            {loadingMessages && (
              <p className="text-center text-sm text-slate-400">Chargement...</p>
            )}
            {!loadingMessages && messages.length === 0 && (
              <p className="text-center text-sm text-slate-400">
                Envoyez votre premier message pour démarrer la discussion.
              </p>
            )}
            {messages.map((m, i) =>
              m.role === "user" ? (
                <div key={i} className="flex items-start justify-end space-x-3">
                  <div className="max-w-md rounded-2xl bg-slate-900 px-4 py-3 text-sm text-white">
                    {m.content}
                  </div>
                  <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-slate-900">
                    <User className="h-4 w-4 text-white" />
                  </div>
                </div>
              ) : (
                <div key={i} className="flex items-start space-x-3">
                  <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-purple-50">
                    <Newspaper className="h-4 w-4 text-purple-600" />
                  </div>
                  <div className="max-w-md whitespace-pre-wrap rounded-2xl bg-white px-4 py-3 text-sm text-slate-700 shadow-sm border border-slate-100">
                    {m.content}
                  </div>
                </div>
              )
            )}
            <div ref={messagesEndRef} />
          </div>
        ) : activeTab === 'chat' ? (
          <div className="flex flex-1 items-center justify-center p-8 overflow-y-auto">
            <div className="w-full max-w-xl rounded-2xl bg-white p-10 shadow-sm border border-slate-100 text-center">

              <div className="mb-6 flex justify-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-purple-50 text-purple-600 overflow-hidden">
                  <Image
                    src="/images/Logo.png"
                    alt="NewsFoundry"
                    width={40}
                    height={40}
                    className="object-contain"
                  />
                </div>
              </div>

              <h1 className="mb-4 text-2xl font-semibold text-purple-800">
                Assistant Revue de Presse IA
              </h1>

              <p className="mb-8 text-sm leading-relaxed text-slate-500">
                {"Posez-moi des questions sur l'actualité récente ou demandez-moi de générer une revue de presse sur un sujet spécifique."}
              </p>

              <div className="rounded-xl bg-slate-50 p-5 text-left border border-slate-100">
                <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400 text-center">
                  Exemples :
                </h3>
                <ul className="space-y-2 text-xs text-slate-600">
                  <li className="flex items-center space-x-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-slate-400"></span>
                    <span>{'"Quelles sont les dernières nouvelles en politique ?"'}</span>
                  </li>
                  <li className="flex items-center space-x-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-slate-400"></span>
                    <span>{'"Génère une revue de presse sur la technologie"'}</span>
                  </li>
                  <li className="flex items-center space-x-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-slate-400"></span>
                    <span>{'"Résume l\'actualité économique de la semaine"'}</span>
                  </li>
                </ul>
              </div>

            </div>
          </div>
        ) : (
          <div className="flex flex-1 items-center justify-center p-8">
            <p className="text-sm text-slate-400">La liste des revues de presse arrive dans la prochaine étape.</p>
          </div>
        )}

        {(inConversation || activeTab === 'chat') && (
          <div className="border-t border-slate-200 bg-white p-4">
            <form onSubmit={handleSend} className="mx-auto flex max-w-4xl items-center rounded-xl bg-slate-50 px-4 py-2 border border-slate-200 focus-within:border-purple-400 transition-all">
              <input
                type="text"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Tapez votre message ici..."
                className="flex-1 bg-transparent text-sm text-slate-700 placeholder-slate-400 focus:outline-none"
                disabled={sending}
              />
              <button
                type="submit"
                className="ml-3 flex h-9 w-9 items-center justify-center rounded-lg bg-slate-300 text-white transition-colors hover:bg-purple-600 disabled:opacity-50"
                disabled={!message.trim() || sending}
              >
                <Send className="h-4 w-4" />
              </button>
            </form>
          </div>
        )}

      </main>
    </div>
  );
}