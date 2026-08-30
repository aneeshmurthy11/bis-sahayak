"use client";

import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import { Source, CorrectionInfo, ProductInfo } from "@/lib/api";
import SourceCitation from "./SourceCitation";

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  streaming?: boolean;
  showSources?: boolean;
  correction?: CorrectionInfo | null;
  confidence?: number | null;
  productInfo?: ProductInfo | null;
  followUpQuestions?: string[];
  onFollowUp?: (question: string) => void;
  onRegenerate?: () => void;
  onEdit?: (newContent: string) => void;
}

export default function MessageBubble({
  role,
  content,
  sources,
  streaming = false,
  showSources = true,
  correction,
  confidence,
  productInfo,
  followUpQuestions = [],
  onFollowUp,
  onRegenerate,
  onEdit,
}: MessageBubbleProps) {
  const isUser = role === "user";
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(content);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(isUser ? content : processedContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSaveEdit = () => {
    if (onEdit) onEdit(editContent);
    setIsEditing(false);
  };

  const now = new Date();
  const timestamp = now.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  const hasSources = sources && sources.length > 0 && !isUser;

  // Bold IS codes in assistant responses (e.g., IS 302, IS 1417, IS 10500)
  const formatISCodes = (text: string): string => {
    if (isUser) return text;
    // Match IS followed by digits (with optional Part/Section suffixes)
    // Only bold if not already inside markdown bold (**...**)
    return text.replace(/(?<!\*\*)\b(IS\s+\d+(?:\.\d+)?(?:\s+Part\s+\d+)?)\b(?!\*\*)/g, "**$1**");
  };

  const processedContent = isUser ? content : formatISCodes(content);

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-6 ${isUser ? "animate-slide-in-right" : "animate-slide-in-left"} message-row`}>
      <div className={`max-w-[75%] ${isUser ? "" : "w-full max-w-[75%]"}`}>
        {/* Avatar + name for AI */}
        {!isUser && (
          <div className="flex items-center gap-2 mb-1.5 ml-1">
            <div className="w-6 h-6 rounded-full bg-gray-200 dark:bg-[#3F3F46] flex items-center justify-center shrink-0">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-gray-500 dark:text-[#A1A1AA]" aria-hidden="true">
                <path d="M3 21h18M5 21V7l7-4 7 4v14M9 21v-6h6v6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <span className="text-xs font-medium text-gray-500 dark:text-[#A1A1AA]">
              BIS Sahayak
            </span>
            {/* Verified seal for source-backed answers */}
            {hasSources && showSources && !streaming && (
              <div className="verified-seal" aria-label="Source-verified answer">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" aria-hidden="true">
                  <path d="M20 6L9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                Verified
              </div>
            )}
          </div>
        )}

        {/* Correction chip -- Did you mean...? */}
        {correction && !isUser && !streaming && (
          <div className="mb-2 ml-1 animate-fade-in">
            {correction.suggestions.length > 1 ? (
              <div className="inline-flex flex-wrap items-center gap-1.5 px-3 py-1.5 rounded-full bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800/40 text-sm">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3B82F6" strokeWidth="2" className="shrink-0" aria-hidden="true">
                  <circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
                </svg>
                <span className="text-gray-600 dark:text-[#A1A1AA]">Did you mean:</span>
                {correction.suggestions.map((s, i) => (
                  <span key={s} className="font-medium text-[#3B82F6] dark:text-[#60A5FA]">{s}{i < correction.suggestions.length - 1 ? ',' : '?'}</span>
                ))}
              </div>
            ) : (
              <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800/40 text-sm">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3B82F6" strokeWidth="2" className="shrink-0" aria-hidden="true">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle cx="12" cy="12" r="3" />
                </svg>
                <span className="text-gray-600 dark:text-[#A1A1AA]">Did you mean:</span>
                <span className="font-medium text-[#3B82F6] dark:text-[#60A5FA]">{correction.corrected_word}?</span>
              </div>
            )}
          </div>
        )}

        {/* Confidence badge */}
        {confidence !== null && confidence !== undefined && !isUser && !streaming && (
          <div className="mb-2 ml-1 animate-fade-in">
            <div className={"inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium " + (
              confidence >= 85 ? "bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800/40 text-green-700 dark:text-green-400" :
              confidence >= 65 ? "bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/40 text-amber-700 dark:text-amber-400" :
              "bg-gray-50 dark:bg-gray-800/20 border border-gray-200 dark:border-gray-700/40 text-gray-600 dark:text-gray-400"
            )}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true"><path d="M22 11.08V12a10 10 0 11-5.93-9.14" strokeLinecap="round" strokeLinejoin="round" /><path d="M22 4L12 14.01l-3-3" strokeLinecap="round" strokeLinejoin="round" /></svg>
              {confidence >= 85 ? "Verified from BIS Documents" : confidence >= 65 ? "AI Summary from BIS Documents" : "Based on available information"}
            </div>
          </div>
        )}

        {/* Product Info Card */}
        {productInfo && !isUser && !streaming && (
          <div className="mb-3 ml-1 animate-fade-in-up">
            <div className="rounded-xl border border-gray-200 dark:border-[#3F3F46] bg-white dark:bg-[#1E1E1E] overflow-hidden shadow-sm">
              {/* Card header */}
              <div className="px-4 py-3 bg-gradient-to-r from-blue-50 to-blue-100/50 dark:from-blue-900/20 dark:to-blue-900/10 border-b border-gray-200 dark:border-[#3F3F46]">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-[#ECECEC]">{productInfo.name}</h3>
                  <span className={"text-[10px] font-medium px-2 py-0.5 rounded-full " + (
                    productInfo.certification === "Mandatory" ? "bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-400" :
                    productInfo.certification === "CRS" ? "bg-orange-100 dark:bg-orange-900/20 text-orange-700 dark:text-orange-400" :
                    "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400"
                  )}>
                    {productInfo.certification}
                  </span>
                </div>
                <div className="flex flex-wrap gap-1.5 mt-1.5">
                  {productInfo.is_codes.map((code) => (
                    <span key={code} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400">{code}</span>
                  ))}
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400">{productInfo.category}</span>
                </div>
              </div>
              {/* Card body */}
              <div className="px-4 py-3 space-y-2 text-xs text-gray-600 dark:text-[#A1A1AA]">
                <p className="text-gray-500 dark:text-[#71717A] italic">{productInfo.description}</p>
                {productInfo.key_requirements.length > 0 && (
                  <div>
                    <p className="font-medium text-gray-700 dark:text-[#D4D4D8] mb-1">Key Requirements:</p>
                    <ul className="space-y-0.5 ml-3 list-disc list-inside">
                      {productInfo.key_requirements.map((req, i) => (
                        <li key={i}>{req}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Message content */}
        {isEditing ? (
          <div className="rounded-2xl px-4 py-3 bg-gray-100 dark:bg-[#2F2F2F]">
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              className="w-full bg-white dark:bg-[#303030] border border-gray-300 dark:border-[#3F3F46] rounded-lg p-2 text-sm text-gray-800 dark:text-[#ECECEC] resize-none focus:outline-none focus:ring-2 focus:ring-blue-500/30"
              rows={4}
              aria-label="Edit message"
            />
            <div className="flex gap-2 mt-2 justify-end">
              <button onClick={() => setIsEditing(false)} className="px-3 py-1 text-xs text-gray-500 hover:text-gray-700 dark:text-[#A1A1AA] dark:hover:text-[#ECECEC] transition-colors">
                Cancel
              </button>
              <button onClick={handleSaveEdit} className="px-3 py-1 text-xs bg-gray-200 dark:bg-[#3F3F46] text-gray-700 dark:text-[#ECECEC] rounded-lg hover:bg-gray-300 dark:hover:bg-[#52525B] transition-colors">
                Save
              </button>
            </div>
          </div>
        ) : (
          <div className={`rounded-2xl px-4 py-3 ${isUser ? "bg-gray-100 dark:bg-[#2F2F2F] text-gray-800 dark:text-[#ECECEC] rounded-br-md" : "text-gray-800 dark:text-[#ECECEC] rounded-bl-md"} ${streaming ? "streaming-cursor" : ""}`}>
            <div className="prose prose-sm max-w-none">
              <ReactMarkdown>{processedContent}</ReactMarkdown>
            </div>
          </div>
        )}

        {/* Bottom row: timestamp + actions */}
        <div className={`flex items-center gap-1 mt-1 ${isUser ? "justify-end mr-1" : "justify-start ml-1"}`}>
          <span className="text-[10px] text-gray-400 dark:text-[#71717A]">
            {timestamp}
          </span>
          
          {/* Message actions (hover to reveal) */}
          <div className="message-actions flex items-center gap-0.5">
            {/* Copy button (AI messages) */}
            {!isUser && !streaming && (
              <button
                onClick={handleCopy}
                className={`copy-tooltip text-xs px-1.5 py-0.5 rounded transition-all duration-150 btn-press ${copied ? "text-green-500" : "text-gray-400 hover:text-gray-600 dark:hover:text-[#ECECEC] hover:bg-gray-100 dark:hover:bg-[#3F3F46]"}`}
                data-tooltip={copied ? "Copied!" : "Copy"}
                aria-label="Copy response"
              >
                {copied ? (
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                    <path d="M20 6L9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                ) : (
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                    <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
                  </svg>
                )}
              </button>
            )}

            {/* Thumbs up (AI messages) */}
            {!isUser && !streaming && (
              <button
                onClick={() => setFeedback(feedback === "up" ? null : "up")}
                className={`feedback-btn text-xs px-1.5 py-0.5 rounded transition-all duration-150 ${feedback === "up" ? "text-blue-500" : "text-gray-400 hover:text-gray-600 dark:hover:text-[#ECECEC] hover:bg-gray-100 dark:hover:bg-[#3F3F46]"}`}
                aria-label="Thumbs up"
                aria-pressed={feedback === "up"}
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill={feedback === "up" ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" aria-hidden="true">
                  <path d="M14 9V5a3 3 0 00-3-3l-4 9v11h11.28a2 2 0 002-1.7l1.38-9a2 2 0 00-2-2.3zM7 22H4a2 2 0 01-2-2v-7a2 2 0 012-2h3" />
                </svg>
              </button>
            )}

            {/* Thumbs down (AI messages) */}
            {!isUser && !streaming && (
              <button
                onClick={() => setFeedback(feedback === "down" ? null : "down")}
                className={`feedback-btn text-xs px-1.5 py-0.5 rounded transition-all duration-150 ${feedback === "down" ? "text-blue-500" : "text-gray-400 hover:text-gray-600 dark:hover:text-[#ECECEC] hover:bg-gray-100 dark:hover:bg-[#3F3F46]"}`}
                aria-label="Thumbs down"
                aria-pressed={feedback === "down"}
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill={feedback === "down" ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" aria-hidden="true">
                  <path d="M10 15v4a3 3 0 003 3l4-9V2H5.72a2 2 0 00-2 1.7l-1.38 9a2 2 0 002 2.3zm7-13h2.67A2.31 2.31 0 0122 4v7a2.31 2.31 0 01-2.33 2H17" />
                </svg>
              </button>
            )}

            {/* Regenerate (AI messages) */}
            {!isUser && !streaming && onRegenerate && (
              <button
                onClick={onRegenerate}
                className="text-xs px-1.5 py-0.5 rounded text-gray-400 hover:text-gray-600 dark:hover:text-[#ECECEC] hover:bg-gray-100 dark:hover:bg-[#3F3F46] transition-all duration-150"
                aria-label="Regenerate response">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M1 4v6h6M23 20v-6h-6" strokeLinecap="round" strokeLinejoin="round" /><path d="M20.49 9A9 9 0 005.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 013.51 15" strokeLinecap="round" strokeLinejoin="round" /></svg>
              </button>
            )}
            {isUser && onEdit && !isEditing && (
              <button onClick={() => setIsEditing(true)} className="text-xs px-1.5 py-0.5 rounded text-gray-400 hover:text-gray-600 dark:hover:text-[#ECECEC] hover:bg-gray-100 dark:hover:bg-[#3F3F46] transition-all duration-150" aria-label="Edit message">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
              </button>
            )}
          </div>
        </div>

        {hasSources && showSources && !streaming && (
          <div className="mt-2 ml-1 animate-fade-in">
            <div className="flex flex-wrap gap-1.5">
              {sources!.map((src, i) => (<SourceCitation key={i} source={src} />))}
            </div>
          </div>
        )}

        {!hasSources && !isUser && showSources && !streaming && content && !content.includes("Sorry") && (
          <div className="mt-2 ml-1">
            <span className="text-[10px] text-gray-400 dark:text-[#71717A] italic">No exact match found in indexed standards</span>
          </div>
        )}

        {/* Follow-up question pills */}
        {followUpQuestions.length > 0 && !isUser && !streaming && onFollowUp && (
          <div className="mt-3 ml-1 animate-fade-in-up">
            <p className="text-[10px] font-medium text-gray-400 dark:text-[#71717A] mb-1.5 uppercase tracking-wide">Suggested follow-ups</p>
            <div className="flex flex-wrap gap-1.5">
              {followUpQuestions.slice(0, 5).map((q, i) => (
                <button
                  key={i}
                  onClick={() => onFollowUp(q)}
                  className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] rounded-full border border-gray-200 dark:border-[#3F3F46] bg-white dark:bg-[#1E1E1E] text-gray-600 dark:text-[#A1A1AA] hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:border-blue-300 dark:hover:border-blue-700 hover:text-blue-600 dark:hover:text-blue-400 transition-all duration-150 btn-press"
                  aria-label={q}
                >
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="shrink-0 opacity-50" aria-hidden="true"><path d="M5 12h14M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" /></svg>
                  {q.length > 50 ? q.slice(0, 50) + '...' : q}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
