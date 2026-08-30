"use client";

import React, { useState } from "react";
import { Source } from "@/lib/api";

interface SourceCitationProps {
  source: Source;
}

export default function SourceCitation({ source }: SourceCitationProps) {
  const [expanded, setExpanded] = useState(false);

  // Detect IS code in document name for badge
  const isCodeMatch = source.document.match(/IS\s*(\d+)/i);
  const isCode = isCodeMatch ? `IS ${isCodeMatch[1]}` : null;

  return (
    <div className="relative inline-block">
      <button
        onClick={() => setExpanded(!expanded)}
        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-gray-100 dark:bg-[#2A2A2A] text-gray-600 dark:text-[#A1A1AA]
                   text-[11px] font-medium hover:bg-gray-200 dark:hover:bg-[#3F3F46] transition-colors cursor-pointer border border-gray-200 dark:border-[#3F3F46]
                   btn-press"
      >
        {isCode && (
          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-bold bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-800/40">
            {isCode}
          </span>
        )}
        {!isCode && (
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="shrink-0">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
          </svg>
        )}
        <span className="truncate max-w-[180px]">{source.document}</span>
        {source.clause && <span className="text-gray-400 dark:text-[#71717A]"> {source.clause}</span>}
      </button>

      {expanded && (
        <div className="absolute z-50 bottom-full left-0 mb-2 w-80 bg-white dark:bg-[#2A2A2A] border border-[#E5E7EB] dark:border-[#3F3F46] rounded-xl shadow-lg p-3 animate-fade-in">
          <div className="flex items-center gap-2 mb-2">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-gray-500 dark:text-[#A1A1AA]">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
            <span className="font-semibold text-sm text-gray-800 dark:text-[#ECECEC]">{source.document}</span>
          </div>
          {source.clause && (
            <p className="text-xs text-gray-500 dark:text-[#A1A1AA] mb-1">
              <span className="font-medium">Section:</span> {source.clause}
            </p>
          )}
          {source.excerpt && (
            <p className="text-xs text-gray-500 dark:text-[#A1A1AA] leading-relaxed mt-2 pt-2 border-t border-[#E5E7EB] dark:border-[#3F3F46] italic">
              &ldquo;{source.excerpt}...&rdquo;
            </p>
          )}
          <div className="absolute top-full left-6 w-2 h-2 bg-white dark:bg-[#2A2A2A] border-r border-b border-[#E5E7EB] dark:border-[#3F3F46] transform rotate-45 -translate-y-1" />
        </div>
      )}
    </div>
  );
}
