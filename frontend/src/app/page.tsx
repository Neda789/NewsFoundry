"use client";

import React, { useState, useEffect } from 'react';
import { MessageSquare, FileText, LogOut, Send, LayoutDashboard } from 'lucide-react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';

interface Discussion {
  id: string;
  title: string;
  date: string;
}

export default function Home() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<'chat' | 'press'>('chat');
  const [message, setMessage] = useState('');

  // Provjera tokena odmah pri učitavanju (izbjegava setState u useEffect-u)
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.replace("/login");
    }
  }, [router]);

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    router.replace("/login");
  };
  
  const discussions: Discussion[] = [
    { id: '1', title: 'Discussion du', date: '10/12/2026' },
    { id: '2', title: 'Discussion du', date: '10/12/2026' },
    { id: '3', title: 'Discussion du', date: '10/12/2026' },
    { id: '4', title: 'Discussion du', date: '10/12/2026' },
    { id: '5', title: 'Discussion du', date: '10/12/2026' },
    { id: '6', title: 'Discussion du', date: '10/12/2026' },
    { id: '7', title: 'Discussion du', date: '10/12/2026' },
    { id: '8', title: 'Discussion du', date: '10/12/2026' },
  ];

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;
    console.log('Message:', message);
    setMessage('');
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-100 font-sans">
      
      {/* ----------------- BARRE LATÉRALE (SIDEBAR) ----------------- */}
      <aside className="flex w-80 flex-col border-r border-slate-200 bg-white">
        
        <div className="flex items-center justify-between px-6 py-5 border-b border-slate-100">
          <div className="flex items-center space-x-2">
            <span className="text-base font-bold tracking-wider text-purple-600">NEWSFOUNDRY</span>
            <LayoutDashboard className="h-4 w-4 text-purple-600" />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
          {discussions.map((item) => (
            <div 
              key={item.id} 
              className="cursor-pointer px-6 py-4 transition-colors hover:bg-slate-50"
            >
              <h4 className="text-sm font-medium text-slate-700">{item.title}</h4>
              <span className="text-xs text-slate-400">{item.date}</span>
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
        
        <header className="flex items-center border-b border-slate-200 bg-white px-8 py-3.5 shadow-sm">
          <div className="flex space-x-3">
            <button
              onClick={() => setActiveTab('chat')}
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

        <div className="border-t border-slate-200 bg-white p-4">
          <form onSubmit={handleSend} className="mx-auto flex max-w-4xl items-center rounded-xl bg-slate-50 px-4 py-2 border border-slate-200 focus-within:border-purple-400 transition-all">
            <input
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Tapez votre message ici..."
              className="flex-1 bg-transparent text-sm text-slate-700 placeholder-slate-400 focus:outline-none"
            />
            <button
              type="submit"
              className="ml-3 flex h-9 w-9 items-center justify-center rounded-lg bg-slate-300 text-white transition-colors hover:bg-purple-600 disabled:opacity-50"
              disabled={!message.trim()}
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
        </div>

      </main>
    </div>
  );
}