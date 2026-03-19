//frontend/src/app/components/ChatMessage.tsx
"use client";

interface ChatMessageProps {
  message: string;
  sender: "user" | "agent" | "system";
  mode?: "v1" | "v2";
  kind?: "default" | "thinking" | "status";
}

export default function ChatMessage({
  message,
  sender,
  mode = "v1",
  kind = "default",
}: ChatMessageProps) {
  const isUser = sender === "user";
  const isSystem = sender === "system";
  const isAgent = sender === "agent";
  const showModeIndicator = isAgent;

  const alignmentClass = isSystem ? "center" : isUser ? "right" : "left";
  const bubbleClass = `${isSystem ? "system" : isUser ? "user" : "agent"} ${
    kind === "status" ? "status" : ""
  }`;

  return (
    <>
      <div className={`row ${alignmentClass}`}>
        {showModeIndicator && <span className={`mode-indicator ${mode}`} aria-hidden="true" />}
        <div className={`bubble ${bubbleClass}`}>
          {kind === "thinking" ? (
            <span className="thinking-dots" aria-label="Pensando">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
            </span>
          ) : (
            message
          )}
        </div>
      </div>

      <style jsx>{`
        .row {
          display: flex;
          align-items: flex-end;
          gap: 8px;
          margin-bottom: 12px;
        }

        .row.left {
          justify-content: flex-start;
        }

        .row.right {
          justify-content: flex-end;
        }

        .row.center {
          justify-content: center;
        }

        .bubble {
          padding: 12px 16px;
          border-radius: 18px;
          max-width: 70%;
          line-height: 1.45;
          word-break: break-word;
          border: 1px solid transparent;
          box-shadow: 0 8px 20px rgba(0, 0, 0, 0.18);
        }

        .bubble.agent {
          background: rgba(18, 18, 18, 0.82);
          border-color: rgba(255, 255, 255, 0.04);
          color: #f1f1f1;
        }

        .bubble.agent.status {
          color: rgba(241, 241, 241, 0.85);
          border-color: rgba(255, 255, 255, 0.08);
          font-style: italic;
        }

        .bubble.user {
          background: linear-gradient(135deg, #6d5dfc, #5036ef);
          border-color: rgba(255, 255, 255, 0.12);
          color: #ffffff;
        }

        .bubble.system {
          background: #ffe08a;
          border-color: #f3c650;
          color: #2b1600;
        }

        .mode-indicator {
          width: 7px;
          height: 7px;
          border-radius: 50%;
          flex-shrink: 0;
          margin-bottom: 8px;
          background: rgba(172, 172, 172, 0.62);
          box-shadow: 0 0 0 4px rgba(255, 255, 255, 0.03);
        }

        .mode-indicator.v2 {
          background: rgba(109, 93, 252, 0.8);
          box-shadow: 0 0 0 4px rgba(109, 93, 252, 0.12);
        }

        .thinking-dots {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          min-height: 1em;
        }

        .dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.88);
          animation: wave 0.95s ease-in-out infinite;
        }

        .dot:nth-child(2) {
          animation-delay: 0.13s;
        }

        .dot:nth-child(3) {
          animation-delay: 0.26s;
        }

        @keyframes wave {
          0%,
          100% {
            transform: translateY(0);
            opacity: 0.55;
          }
          50% {
            transform: translateY(-5px);
            opacity: 1;
          }
        }

        @media (max-width: 640px) {
          .bubble {
            max-width: 90%;
          }
        }
      `}</style>
    </>
  );
}