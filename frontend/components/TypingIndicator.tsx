"use client";

import React from "react";

interface TypingIndicatorProps {
  phase?: "thinking" | "searching" | "generating";
}

export default function TypingIndicator({ phase = "thinking" }: TypingIndicatorProps) {
  const label =
    phase === "generating"
      ? "Generating verified answer..."
    : phase === "searching"
      ? "Reading official BIS documents..."
      : "Searching BIS Standards...";

  return (
    <div className="flex justify-start mb-6 animate-slide-in-left">
      <div className="max-w-[75%]">
        <div className="flex items-center gap-2 mb-1.5 ml-1">
          <div className="w-6 h-6 rounded-full bg-gray-200 dark:bg-[#3F3F46] flex items-center justify-center shrink-0">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-gray-500 dark:text-[#A1A1AA]">
              <path d="M3 21h18M5 21V7l7-4 7 4v14M9 21v-6h6v6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <span className="text-xs font-medium text-gray-500 dark:text-[#A1A1AA]">{label}</span>
        </div>
        <div className="rounded-2xl rounded-bl-md px-4 py-3">
          <div className="shimmer-line rounded-full w-48 mb-3" />
          <div className="flex gap-1">
            <div className="w-1.5 h-1.5 rounded-full bg-gray-300 dark:bg-[#71717A] animate-bounce-dot" style={{ animationDelay: "0s" }} />
            <div className="w-1.5 h-1.5 rounded-full bg-gray-300 dark:bg-[#71717A] animate-bounce-dot" style={{ animationDelay: "0.15s" }} />
            <div className="w-1.5 h-1.5 rounded-full bg-gray-300 dark:bg-[#71717A] animate-bounce-dot" style={{ animationDelay: "0.3s" }} />
          </div>
        </div>
      </div>
    </div>
  );
}
