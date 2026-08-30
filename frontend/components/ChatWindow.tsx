"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { ChatMode, Source } from "@/lib/api";
import MessageBubble from "./MessageBubble";
import TypingIndicator from "./TypingIndicator";
import QuickActions from "./QuickActions";
import LanguageToggle from "./LanguageToggle";
import Sidebar from "./Sidebar";
import AboutModal from "./AboutModal";

export interface ChatSession {
  id: string;
  title: string;
  timestamp: string;
  messages: { role: "user" | "assistant"; content: string }[];
}

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  mode?: ChatMode;
  streaming?: boolean;
}

const MODE_TABS: { mode: ChatMode; label: string; icon: string }[] = [
  { mode: "general", label: "Chat", icon: "\uD83D\uDCAC" },
  { mode: "recommend", label: "Find Standard", icon: "\uD83D\uDD0D" },
  { mode: "certify", label: "Certification", icon: "\uD83D\uDCCB" },
  { mode: "hallmark", label: "Hallmarking", icon: "\uD83D\uDC8D" },
  { mode: "lab", label: "Find Lab", icon: "\uD83D\uDD2C" },
];

const SUGGESTION_POOL = [
  // Standards lookup
  "Which IS standard applies to plastic water bottles?",
  "Explain IS 302 in simple English.",
  "Which standard applies to PVC pipes?",
  "What does IS 1417 say about gold jewellery?",
  "Which Indian Standard covers electrical wiring?",
  "What is IS 10500 and when does it apply?",
  // Certification
  "How do I get BIS certification?",
  "What is the difference between ISI mark and CRS?",
  "Explain the BIS certification process step by step.",
  "How long does BIS certification take?",
  // Hallmarking
  "What are the hallmarking rules for gold jewellery?",
  "What is HUID and how do I verify my gold?",
  "Which metals require hallmarking in India?",
  // Lab finder
  "Find a BIS testing lab near me.",
  "Which labs test electrical products in Mumbai?",
  "List BIS-approved labs for food testing.",
  // General BIS queries
  "What does BIS stand for and what does it do?",
  "How can I check if a product has ISI mark?",
  "What consumer rights do I have for BIS-certified products?",
];

function pickRandomChips(pool: string[], count: number): string[] {
  const shuffled = [...pool].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, count);
}

const STORAGE_KEY = "bis-sahayak-history";
const THEME_KEY = "bis-sahayak-theme";

function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
}

function formatTime(ts: number) {
  const d = new Date(ts);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  if (diff < 60000) return "Just now";
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
}

export default function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<ChatMode>("general");
  const [language, setLanguage] = useState("auto");
  const [thinkingPhase, setThinkingPhase] = useState<"thinking" | "searching">("thinking");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [aboutOpen, setAboutOpen] = useState(false);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [toolsOpen, setToolsOpen] = useState(false);
  const [displayedChips, setDisplayedChips] = useState<string[]>([]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const toolsRef = useRef<HTMLDivElement>(null);

  // Load from localStorage
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        setSessions(parsed.sessions || []);
        if (parsed.activeSessionId) {
          setActiveSessionId(parsed.activeSessionId);
          const active = (parsed.sessions || []).find(
            (s: ChatSession) => s.id === parsed.activeSessionId
          );
          if (active) setMessages(active.messages as Message[]);
        }
      }
      const theme = localStorage.getItem(THEME_KEY);
      if (theme === "dark") {
        setDarkMode(true);
        document.documentElement.classList.add("dark");
      }
    } catch {}
  }, []);

  useEffect(() => {
    if (sessions.length > 0 || activeSessionId) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ sessions, activeSessionId }));
    }
  }, [sessions, activeSessionId]);

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
    localStorage.setItem(THEME_KEY, darkMode ? "dark" : "light");
  }, [darkMode]);

  // Populate chips client-side only to avoid hydration mismatch
  useEffect(() => {
    setDisplayedChips(pickRandomChips(SUGGESTION_POOL, 6));
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    if (!loading) return;
    setThinkingPhase("thinking");
    const timer = setTimeout(() => setThinkingPhase("searching"), 5000);
    return () => clearTimeout(timer);
  }, [loading]);

  // Close tools dropdown on outside click
  useEffect(() => {
    if (!toolsOpen) return;
    const handleClick = (e: MouseEvent) => {
      if (toolsRef.current && !toolsRef.current.contains(e.target as Node)) setToolsOpen(false);
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [toolsOpen]);

  const handleNewChat = useCallback(() => {
    setMessages([]);
    setInput("");
    setMode("general");
    setActiveSessionId(null);
    setDisplayedChips(pickRandomChips(SUGGESTION_POOL, 6));
  }, []);

  const handleClearHistory = useCallback(() => {
    setSessions([]);
    setActiveSessionId(null);
    setMessages([]);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  const handleRenameSession = useCallback((id: string, newTitle: string) => {
    setSessions((prev) =>
      prev.map((s) => (s.id === id ? { ...s, title: newTitle } : s))
    );
  }, []);

  const handleDeleteSession = useCallback((id: string) => {
    setSessions((prev) => prev.filter((s) => s.id !== id));
    if (activeSessionId === id) {
      setActiveSessionId(null);
      setMessages([]);
    }
  }, [activeSessionId]);

  const handleSelectSession = useCallback(
    (id: string) => {
      const session = sessions.find((s) => s.id === id);
      if (session) {
        setActiveSessionId(id);
        setMessages(session.messages as Message[]);
      }
    },
    [sessions]
  );

  const sendMessage = useCallback(
    async (msg?: string, msgMode?: ChatMode) => {
      const text = msg || input.trim();
      const activeMode = msgMode || mode;
      if (!text || loading) return;

      const userMsg: Message = { role: "user", content: text, mode: activeMode };
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setLoading(true);

      if (inputRef.current) inputRef.current.style.height = "auto";

      try {
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text, language, mode: activeMode }),
        });

        if (!res.ok) throw new Error(`Chat API error: ${res.status}`);
        const data = await res.json();

        const assistantMsg: Message = {
          role: "assistant",
          content: "",
          sources: data.sources,
          mode: activeMode,
          streaming: true,
        };
        setMessages((prev) => [...prev, assistantMsg]);

        const fullText: string = data.answer || "";
        for (let i = 0; i < fullText.length; i += 3) {
          const chunk = fullText.slice(0, i + 3);
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last?.role === "assistant") {
              updated[updated.length - 1] = { ...last, content: chunk };
            }
            return updated;
          });
          await new Promise((r) => setTimeout(r, 20));
        }

        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last?.role === "assistant") {
            updated[updated.length - 1] = { ...last, content: fullText, streaming: false };
          }
          return updated;
        });

        setMessages((prevMessages) => {
          const allMessages = [...prevMessages];
          setSessions((prevSessions) => {
            const sessionTitle = text.slice(0, 60) + (text.length > 60 ? "..." : "");
            const now = Date.now();
            let updated: ChatSession[];
            if (activeSessionId) {
              updated = prevSessions.map((s) =>
                s.id === activeSessionId
                  ? { ...s, messages: allMessages.map((m) => ({ role: m.role, content: m.content })), timestamp: formatTime(now) }
                  : s
              );
            } else {
              const newSession: ChatSession = {
                id: generateId(),
                title: sessionTitle,
                timestamp: formatTime(now),
                messages: allMessages.map((m) => ({ role: m.role, content: m.content })),
              };
              updated = [newSession, ...prevSessions];
              setActiveSessionId(newSession.id);
            }
            return updated;
          });
          return prevMessages;
        });
      } catch {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: "Something went wrong. Please check if the backend is running and try again." },
        ]);
      }

      setLoading(false);
      inputRef.current?.focus();
    },
    [input, loading, language, mode, activeSessionId]
  );

  const handleRegenerate = useCallback(async () => {
    if (loading || messages.length === 0) return;
    const lastUserMsg = [...messages].reverse().find(m => m.role === "user");
    if (lastUserMsg) {
      setMessages(prev => prev.slice(0, -1));
      await sendMessage(lastUserMsg.content, lastUserMsg.mode);
    }
  }, [loading, messages, sendMessage]);

  const handleEditMessage = useCallback((index: number, newContent: string) => {
    setMessages(prev => prev.map((msg, i) => i === index ? { ...msg, content: newContent } : msg));
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleCardClick = (actionMode: ChatMode, prompt: string) => {
    setMode(actionMode);
    setInput(prompt);
    inputRef.current?.focus();
  };

  const handleChipClick = (chip: string) => {
    setInput(chip);
    inputRef.current?.focus();
  };

  const currentModeTab = MODE_TABS.find((t) => t.mode === mode);

  return (
    <div className="flex h-screen max-h-screen transition-colors duration-300 bg-white dark:bg-[#212121]">
      {/* Sidebar */}
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        onNewChat={handleNewChat}
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={handleSelectSession}
        onClearHistory={handleClearHistory}
        onRenameSession={handleRenameSession}
        onDeleteSession={handleDeleteSession}
        darkMode={darkMode}
        onToggleDarkMode={() => setDarkMode(!darkMode)}
        onAbout={() => setAboutOpen(true)}
        mode={mode}
        onModeChange={setMode}
      />

      {/* Main area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header — logo removed, only Tools dropdown + LanguageToggle */}
        <header className="bg-white dark:bg-[#171717] border-b border-[#E5E7EB] dark:border-[#3F3F46] px-4 py-2.5 flex items-center justify-between shrink-0 transition-colors duration-300">
          <div className="flex items-center gap-3">
            {/* Tools dropdown button — replaces the old tab bar */}
            <div className="relative" ref={toolsRef}>
              <button
                onClick={() => setToolsOpen(!toolsOpen)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium text-gray-600 dark:text-[#A1A1AA] hover:bg-gray-100 dark:hover:bg-[#2A2A2A] transition-all duration-200 btn-press"
              >
                <span>{currentModeTab?.icon}</span>
                <span>{currentModeTab?.label}</span>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={`transition-transform duration-200 ${toolsOpen ? "rotate-180" : ""}`}>
                  <polyline points="6 9 12 15 18 9" />
                </svg>
              </button>

              {toolsOpen && (
                <div className="absolute top-full left-0 mt-1 bg-white dark:bg-[#2A2A2A] border border-[#E5E7EB] dark:border-[#3F3F46] rounded-xl shadow-xl py-1.5 w-48 animate-fade-in-up z-50">
                  {MODE_TABS.map((tab) => (
                    <button
                      key={tab.mode}
                      onClick={() => { setMode(tab.mode); setToolsOpen(false); }}
                      className={`w-full flex items-center gap-2.5 px-3 py-2 text-sm transition-colors text-left ${
                        mode === tab.mode
                          ? "bg-gray-100 dark:bg-[#303030] text-gray-900 dark:text-[#ECECEC] font-medium"
                          : "text-gray-600 dark:text-[#A1A1AA] hover:bg-gray-50 dark:hover:bg-[#303030]"
                      }`}
                    >
                      <span>{tab.icon}</span>
                      {tab.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
          <LanguageToggle language={language} onChange={setLanguage} />
        </header>

        <AboutModal open={aboutOpen} onClose={() => setAboutOpen(false)} />

        {/* Messages area */}
        <div className="flex-1 overflow-y-auto px-4 py-6">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full gap-6 animate-fade-in">
              <div className="text-center">
                <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-bis-500 to-bis-600 flex items-center justify-center mx-auto mb-4">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
                    <path d="M3 21h18M5 21V7l7-4 7 4v14M9 21v-6h6v6" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
                <h2 className="text-xl font-semibold text-gray-900 dark:text-[#ECECEC] mb-2">
                  Welcome to BIS Sahayak
                </h2>
                <p className="text-gray-500 dark:text-[#A1A1AA] max-w-md mx-auto text-sm leading-relaxed">
                  Your AI assistant for Indian Standards, BIS certification,
                  hallmarking, and testing labs.
                </p>
              </div>

              <QuickActions onSelect={handleCardClick} />
            </div>
          ) : (
            <div className="max-w-3xl mx-auto">
              {messages.map((msg, i) => (
                <MessageBubble
                  key={i}
                  role={msg.role}
                  content={msg.content}
                  sources={msg.sources}
                  streaming={msg.streaming}
                  showSources={!msg.streaming}
                  onRegenerate={msg.role === "assistant" && i === messages.length - 1 ? handleRegenerate : undefined}
                  onEdit={msg.role === "user" ? (newContent) => handleEditMessage(i, newContent) : undefined}
                />
              ))}
              {loading && <TypingIndicator phase={thinkingPhase} />}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Chat input — ChatGPT style */}
        <div className="px-4 pb-4 pt-2 shrink-0">
          <div className="max-w-3xl mx-auto">
            {mode !== "general" && (
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs bg-gray-100 dark:bg-[#2A2A2A] text-gray-600 dark:text-[#A1A1AA] px-2 py-0.5 rounded-full font-medium border border-gray-200 dark:border-[#3F3F46]">
                  {currentModeTab?.icon}{" "}
                  {currentModeTab?.label} mode
                </span>
                <button
                  onClick={() => setMode("general")}
                  className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                >
                  {"\u2715"} clear
                </button>
              </div>
            )}

            <div className="flex items-end gap-2 bg-white dark:bg-[#303030] rounded-2xl border border-gray-200 dark:border-[#3F3F46] px-3 py-2 shadow-sm transition-all duration-200 input-glow">
              {/* Attachment icon */}
              <button className="shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-gray-400 dark:text-[#71717A] hover:text-gray-600 dark:hover:text-[#A1A1AA] hover:bg-gray-100 dark:hover:bg-[#3F3F46] transition-colors btn-press" aria-label="Attach file">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" />
                </svg>
              </button>

              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Message BIS Sahayak..."
                rows={1}
                disabled={loading}
                className="flex-1 resize-none border-0 bg-transparent px-1 py-2 text-sm
                           focus:outline-none focus:ring-0 max-h-32 placeholder-gray-400 dark:placeholder-[#71717A]
                           disabled:opacity-50 disabled:cursor-not-allowed
                           text-gray-800 dark:text-[#ECECEC] chat-input"
                style={{ minHeight: "40px", outline: "none", boxShadow: "none" }}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement;
                  target.style.height = "auto";
                  target.style.height = Math.min(target.scrollHeight, 128) + "px";
                }}
              />

              {/* Microphone placeholder */}
              <button className="shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-gray-400 dark:text-[#71717A] hover:text-gray-600 dark:hover:text-[#A1A1AA] hover:bg-gray-100 dark:hover:bg-[#3F3F46] transition-colors btn-press" aria-label="Voice input">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z" />
                  <path d="M19 10v2a7 7 0 01-14 0v-2M12 19v4M8 23h8" />
                </svg>
              </button>

              {/* Send button */}
              <button
                onClick={() => sendMessage()}
                disabled={loading || !input.trim()}
                className="shrink-0 w-8 h-8 rounded-full bg-gray-200 dark:bg-[#3F3F46] text-gray-500 dark:text-[#A1A1AA] flex items-center
                           justify-center hover:bg-gray-300 dark:hover:bg-[#52525B] transition-all duration-200 disabled:opacity-30
                           disabled:cursor-not-allowed btn-press"
                aria-label="Send message"
              >
                {loading ? (
                  <svg className="animate-spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
                  </svg>
                ) : (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M5 12h14" strokeLinecap="round" />
                    <path d="M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                )}
              </button>
            </div>

            {/* Suggestion chips */}
            {messages.length === 0 && (
              <div className="flex flex-wrap gap-1.5 justify-center mt-3">
                {displayedChips.map((chip) => (
                  <button
                    key={chip}
                    onClick={() => handleChipClick(chip)}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-gray-100 dark:bg-[#2A2A2A] text-gray-600 dark:text-[#A1A1AA]
                               text-[11px] font-medium hover:bg-gray-200 dark:hover:bg-[#3F3F46] transition-colors cursor-pointer border border-gray-200 dark:border-[#3F3F46]
                               btn-press"
                  >
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="shrink-0 text-gray-400 dark:text-[#71717A]">
                      <circle cx="11" cy="11" r="8" />
                      <path d="M21 21l-4.35-4.35" />
                    </svg>
                    {chip}
                  </button>
                ))}
              </div>
            )}

            <p className="text-[10px] text-gray-400 dark:text-[#71717A] mt-1.5 text-center">
              BIS Sahayak provides information sourced from official BIS documents. Always
              verify critical compliance details at{" "}
              <a href="https://bis.gov.in" target="_blank" rel="noopener noreferrer" className="text-[#3B82F6] hover:underline">
                bis.gov.in
              </a>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
