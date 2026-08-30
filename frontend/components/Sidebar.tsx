"use client";

import React, { useState, useMemo, useRef, useEffect } from "react";
import { ChatSession } from "./ChatWindow";
import { ChatMode } from "@/lib/api";

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  onNewChat: () => void;
  sessions: ChatSession[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onClearHistory: () => void;
  onRenameSession: (id: string, newTitle: string) => void;
  onDeleteSession: (id: string) => void;
  darkMode: boolean;
  onToggleDarkMode: () => void;
  onAbout: () => void;
  mode: ChatMode;
  onModeChange: (mode: ChatMode) => void;
}

const MODE_TABS: { mode: ChatMode; label: string; icon: string }[] = [
  { mode: "general", label: "Chat", icon: "\uD83D\uDCAC" },
  { mode: "recommend", label: "Find Standard", icon: "\uD83D\uDD0D" },
  { mode: "certify", label: "Certification", icon: "\uD83D\uDCCB" },
  { mode: "hallmark", label: "Hallmarking", icon: "\uD83D\uDC8D" },
  { mode: "lab", label: "Find Lab", icon: "\uD83D\uDD2C" },
];

export default function Sidebar({
  collapsed, onToggle, onNewChat, sessions, activeSessionId, onSelectSession,
  onClearHistory, onRenameSession, onDeleteSession, darkMode, onToggleDarkMode,
  onAbout, mode, onModeChange,
}: SidebarProps) {
  const [search, setSearch] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const [contextMenu, setContextMenu] = useState<{ sessionId: string; x: number; y: number } | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const menuRef = useRef<HTMLDivElement>(null);
  const contextMenuRef = useRef<HTMLDivElement>(null);
  const renameInputRef = useRef<HTMLInputElement>(null);

  const filteredSessions = useMemo(() => {
    if (!search.trim()) return sessions;
    const q = search.toLowerCase();
    return sessions.filter((s) =>
      s.title.toLowerCase().includes(q) || s.messages.some((m) => m.content.toLowerCase().includes(q))
    );
  }, [sessions, search]);

  useEffect(() => {
    if (!menuOpen) return;
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false);
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [menuOpen]);

  useEffect(() => {
    if (!contextMenu) return;
    const handleClick = (e: MouseEvent) => {
      if (contextMenuRef.current && !contextMenuRef.current.contains(e.target as Node)) setContextMenu(null);
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [contextMenu]);

  useEffect(() => {
    if (renamingId && renameInputRef.current) {
      renameInputRef.current.focus();
      renameInputRef.current.select();
    }
  }, [renamingId]);

  const handleContextMenu = (e: React.MouseEvent, sessionId: string) => {
    e.preventDefault();
    setContextMenu({ sessionId, x: e.clientX, y: e.clientY });
  };

  const handleRename = (sessionId: string) => {
    const session = sessions.find((s) => s.id === sessionId);
    if (session) {
      setRenamingId(sessionId);
      setRenameValue(session.title);
    }
    setContextMenu(null);
  };

  const confirmRename = () => {
    if (renamingId && renameValue.trim()) {
      onRenameSession(renamingId, renameValue.trim());
    }
    setRenamingId(null);
    setRenameValue("");
  };

  const handleDelete = (sessionId: string) => {
    onDeleteSession(sessionId);
    setContextMenu(null);
  };

  const highlightText = (text: string, query: string) => {
    if (!query.trim()) return text;
    const lower = query.toLowerCase();
    const idx = text.toLowerCase().indexOf(lower);
    if (idx === -1) return text;
    return (
      <>
        {text.slice(0, idx)}
        <mark className="search-highlight">{text.slice(idx, idx + query.length)}</mark>
        {text.slice(idx + query.length)}
      </>
    );
  };

  return (
    <>
      {!collapsed && (
        <div className="fixed inset-0 bg-black/40 z-40 md:hidden" onClick={onToggle} aria-hidden="true" />
      )}

      <div className={`shrink-0 h-screen flex flex-col border-r border-[#E5E7EB] dark:border-[#3F3F46] transition-all duration-300 ease-in-out z-50 ${collapsed ? "w-[72px]" : "w-[280px]"} ${collapsed ? "hidden md:flex" : "fixed md:relative inset-y-0 left-0"} bg-[#F7F7F8] dark:bg-[#171717]`}>
        {/* Logo + Close */}
        <div className={`flex items-center shrink-0 px-3 pt-3 pb-2 ${collapsed ? "justify-center" : "justify-between"}`}>
          {collapsed ? (
            <button onClick={onToggle} className="group relative w-10 h-10 rounded-xl bg-gradient-to-br from-bis-500 to-bis-600 flex items-center justify-center hover:scale-105 transition-transform btn-press" aria-label="Open Sidebar">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" aria-hidden="true"><path d="M3 21h18M5 21V7l7-4 7 4v14M9 21v-6h6v6" strokeLinecap="round" strokeLinejoin="round" /></svg>
              <span className="sidebar-tooltip">Open Sidebar</span>
            </button>
          ) : (
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-bis-500 to-bis-600 flex items-center justify-center shrink-0">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" aria-hidden="true"><path d="M3 21h18M5 21V7l7-4 7 4v14M9 21v-6h6v6" strokeLinecap="round" strokeLinejoin="round" /></svg>
              </div>
              <div className="min-w-0">
                <h1 className="text-sm font-semibold text-gray-900 dark:text-[#ECECEC] truncate">BIS Sahayak</h1>
                <p className="text-[10px] text-gray-400 dark:text-[#71717A] truncate">Indian Standards AI</p>
              </div>
            </div>
          )}
          {!collapsed && (
            <button onClick={onToggle} className="w-7 h-7 rounded-lg flex items-center justify-center text-gray-400 hover:text-gray-600 dark:hover:text-[#A1A1AA] hover:bg-gray-200 dark:hover:bg-[#3F3F46] transition-colors btn-press" aria-label="Close Sidebar">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M11 19l-7-7 7-7M18 19l-7-7 7-7" strokeLinecap="round" strokeLinejoin="round" /></svg>
            </button>
          )}
        </div>

        {!collapsed && (
          <>
            {/* New Chat button */}
            <div className="px-3 pb-2">
              <button onClick={onNewChat} className="w-full flex items-center gap-2 px-3 py-2.5 rounded-xl border border-gray-200 dark:border-[#3F3F46] bg-white dark:bg-[#2A2A2A] text-sm text-gray-700 dark:text-[#ECECEC] hover:bg-gray-100 dark:hover:bg-[#303030] transition-colors btn-press font-medium">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M12 5v14M5 12h14" strokeLinecap="round" /></svg>
                New Chat
              </button>
            </div>

            {/* Mode selector */}
            <div className="px-3 pb-2">
              <div className="flex flex-wrap gap-1">
                {MODE_TABS.map((tab) => (
                  <button
                    key={tab.mode}
                    onClick={() => onModeChange(tab.mode)}
                    className={`flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-medium transition-all duration-150 btn-press ${
                      mode === tab.mode
                        ? "bg-gray-200 dark:bg-[#3F3F46] text-gray-900 dark:text-[#ECECEC]"
                        : "text-gray-500 dark:text-[#71717A] hover:bg-gray-100 dark:hover:bg-[#2A2A2A] hover:text-gray-700 dark:hover:text-[#A1A1AA]"
                    }`}
                  >
                    <span>{tab.icon}</span>
                    <span className="hidden lg:inline">{tab.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Search */}
            <div className="px-3 pb-3">
              <div className="relative">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400 dark:text-[#71717A]" aria-hidden="true"><circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" /></svg>
                <input type="text" placeholder="Search chats..." value={search} onChange={(e) => setSearch(e.target.value)} className="w-full pl-8 pr-3 py-2 text-xs rounded-lg bg-gray-100 dark:bg-[#2A2A2A] border border-gray-200 dark:border-[#3F3F46] text-gray-700 dark:text-[#ECECEC] placeholder-gray-400 dark:placeholder-[#71717A] focus:outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-[#52525B] transition-colors" aria-label="Search chats" />
              </div>
            </div>

            <div className="border-t border-gray-200 dark:border-[#3F3F46] mx-3" />

            {/* Chat history */}
            <div className="flex-1 overflow-y-auto px-3 py-2 space-y-0.5">
              {filteredSessions.length === 0 ? (
                <p className="text-xs text-gray-400 dark:text-[#71717A] text-center py-6">No conversations yet</p>
              ) : (
                filteredSessions.map((session) => (
                  <div key={session.id} className="relative group">
                    {renamingId === session.id ? (
                      <div className="px-2 py-1.5">
                        <input
                          ref={renameInputRef}
                          type="text"
                          value={renameValue}
                          onChange={(e) => setRenameValue(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") confirmRename();
                            if (e.key === "Escape") { setRenamingId(null); setRenameValue(""); }
                          }}
                          onBlur={confirmRename}
                          className="w-full px-2 py-1 text-sm rounded-md bg-white dark:bg-[#303030] border border-[#3B82F6] text-gray-700 dark:text-[#ECECEC] focus:outline-none"
                        />
                      </div>
                    ) : (
                      <button
                        onClick={() => onSelectSession(session.id)}
                        onContextMenu={(e) => handleContextMenu(e, session.id)}
                        className={`sidebar-history-item w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors ${activeSessionId === session.id ? "active bg-gray-200/60 dark:bg-[#2A2A2A] font-medium" : "hover:bg-gray-100 dark:hover:bg-[#2A2A2A]"}`}
                      >
                        <div className="truncate text-gray-700 dark:text-[#ECECEC] max-w-[180px]">{highlightText(session.title, search)}</div>
                        <div className="text-[10px] text-gray-400 dark:text-[#71717A] mt-0.5">{session.timestamp}</div>
                      </button>
                    )}
                    {renamingId !== session.id && (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleContextMenu(e, session.id); }}
                        className="absolute right-1 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 w-6 h-6 rounded flex items-center justify-center text-gray-400 hover:text-gray-600 dark:hover:text-[#A1A1AA] hover:bg-gray-200 dark:hover:bg-[#3F3F46] transition-all"
                        aria-label="Chat options"
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <circle cx="12" cy="5" r="1" /><circle cx="12" cy="12" r="1" /><circle cx="12" cy="19" r="1" />
                        </svg>
                      </button>
                    )}
                  </div>
                ))
              )}
            </div>

            {/* Context menu popup */}
            {contextMenu && (
              <div
                ref={contextMenuRef}
                className="fixed z-[100] bg-white dark:bg-[#2A2A2A] border border-[#E5E7EB] dark:border-[#3F3F46] rounded-xl shadow-xl py-1.5 w-40 animate-fade-in-up"
                style={{ left: contextMenu.x, top: contextMenu.y }}
              >
                <button
                  onClick={() => handleRename(contextMenu.sessionId)}
                  className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-gray-700 dark:text-[#ECECEC] hover:bg-gray-50 dark:hover:bg-[#303030] transition-colors text-left"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                    <path d="M17 3a2.828 2.828 0 114 4L7.5 20.5 2 22l1.5-5.5L17 3z" />
                  </svg>
                  Rename
                </button>
                <button
                  onClick={() => handleDelete(contextMenu.sessionId)}
                  className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors text-left"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                    <polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                  </svg>
                  Delete
                </button>
              </div>
            )}

            <div className="border-t border-gray-200 dark:border-[#3F3F46] mx-3" />

            {/* Profile menu */}
            <div className="shrink-0 p-3 relative" ref={menuRef}>
              <button onClick={() => setMenuOpen(!menuOpen)} className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl hover:bg-gray-100 dark:hover:bg-[#2A2A2A] transition-colors btn-press" aria-label="User menu">
                <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-[#3F3F46] flex items-center justify-center shrink-0">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-gray-500 dark:text-[#A1A1AA]" aria-hidden="true"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2M12 11a4 4 0 100-8 4 4 0 000 8z" /></svg>
                </div>
                <div className="flex-1 text-left min-w-0">
                  <p className="text-sm font-medium text-gray-700 dark:text-[#ECECEC] truncate">Guest User</p>
                  <p className="text-[10px] text-gray-400 dark:text-[#71717A]">Free Plan</p>
                </div>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={`text-gray-400 transition-transform duration-200 ${menuOpen ? "rotate-180" : ""}`} aria-hidden="true"><polyline points="6 9 12 15 18 9" /></svg>
              </button>

              {menuOpen && (
                <div className="absolute bottom-full left-3 right-3 mb-2 bg-white dark:bg-[#2A2A2A] border border-[#E5E7EB] dark:border-[#3F3F46] rounded-xl shadow-xl py-1 animate-fade-in-up z-50 w-56">
                  {/* Theme toggle row */}
                  <div className="flex items-center justify-between px-3 py-2 hover:bg-gray-50 dark:hover:bg-[#303030] transition-colors rounded-lg mx-1">
                    <div className="flex items-center gap-2.5">
                      {darkMode ? (
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-gray-500 dark:text-[#A1A1AA] shrink-0" aria-hidden="true"><path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" /></svg>
                      ) : (
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-gray-500 dark:text-[#A1A1AA] shrink-0" aria-hidden="true"><circle cx="12" cy="12" r="5" /><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" /></svg>
                      )}
                      <span className="text-sm text-gray-700 dark:text-[#ECECEC]">{darkMode ? "Dark Mode" : "Light Mode"}</span>
                    </div>
                    <label className="theme-switch" aria-label="Toggle dark mode">
                      <input type="checkbox" checked={darkMode} onChange={onToggleDarkMode} />
                      <span className="slider">
                        <span className="toggle-icons">
                          {darkMode ? (
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" className="toggle-icon"><path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" strokeLinecap="round" strokeLinejoin="round" /></svg>
                          ) : (
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" strokeWidth="2.5" className="toggle-icon"><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" strokeLinecap="round" strokeLinejoin="round" /></svg>
                          )}
                        </span>
                      </span>
                    </label>
                  </div>

                  <div className="border-t border-gray-100 dark:border-[#3F3F46] mx-3 my-1" />

                  {/* Chat management group */}
                  <button onClick={() => setMenuOpen(false)} className="w-full flex items-center gap-2.5 px-3 py-2 hover:bg-gray-50 dark:hover:bg-[#303030] transition-colors text-left rounded-lg mx-1">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-gray-500 dark:text-[#A1A1AA] shrink-0" aria-hidden="true"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" /></svg>
                    <span className="text-sm text-gray-700 dark:text-[#ECECEC]">My Chats</span>
                  </button>
                  <button onClick={() => { onClearHistory(); setMenuOpen(false); }} className="w-full flex items-center gap-2.5 px-3 py-2 hover:bg-gray-50 dark:hover:bg-[#303030] transition-colors text-left rounded-lg mx-1">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-gray-500 dark:text-[#A1A1AA] shrink-0" aria-hidden="true"><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" /></svg>
                    <span className="text-sm text-gray-700 dark:text-[#ECECEC]">Clear History</span>
                  </button>

                  <div className="border-t border-gray-100 dark:border-[#3F3F46] mx-3 my-1" />

                  {/* Settings & About group */}
                  <button onClick={() => setMenuOpen(false)} className="w-full flex items-center gap-2.5 px-3 py-2 hover:bg-gray-50 dark:hover:bg-[#303030] transition-colors text-left rounded-lg mx-1">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-gray-500 dark:text-[#A1A1AA] shrink-0" aria-hidden="true"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" /></svg>
                    <span className="text-sm text-gray-700 dark:text-[#ECECEC]">Settings</span>
                  </button>
                  <button onClick={() => { onAbout(); setMenuOpen(false); }} className="w-full flex items-center gap-2.5 px-3 py-2 hover:bg-gray-50 dark:hover:bg-[#303030] transition-colors text-left rounded-lg mx-1">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-gray-500 dark:text-[#A1A1AA] shrink-0" aria-hidden="true"><circle cx="12" cy="12" r="10" /><path d="M12 16v-4M12 8h.01" /></svg>
                    <span className="text-sm text-gray-700 dark:text-[#ECECEC]">About BIS Sahayak</span>
                  </button>
                </div>
              )}
            </div>
          </>
        )}

        {collapsed && (
          <div className="mt-auto p-3 flex flex-col items-center gap-2">
            <button onClick={onToggle} className="group relative w-10 h-10 rounded-xl flex items-center justify-center text-gray-400 hover:text-gray-600 dark:hover:text-[#A1A1AA] hover:bg-gray-200 dark:hover:bg-[#3F3F46] transition-colors btn-press" aria-label="Open Sidebar">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" /><rect x="3" y="14" width="7" height="7" /><rect x="14" y="14" width="7" height="7" /></svg>
            </button>
          </div>
        )}
      </div>
    </>
  );
}
