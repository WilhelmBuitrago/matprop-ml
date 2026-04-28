//frontend/src/app/components/ChatMessage.tsx
"use client";

interface ChatMessageProps {
  message: string;
  sender: "user" | "agent" | "system";
}

export default function ChatMessage({ message, sender }: ChatMessageProps) {
  const isUser = sender === "user";
  const isSystem = sender === "system";

  const alignmentClass = isSystem ? "center" : isUser ? "right" : "left";
  const bubbleClass = isSystem ? "system" : isUser ? "user" : "agent";

  return (
    <>
      <div className={`row ${alignmentClass}`}>
        <div className={`bubble ${bubbleClass}`}>{message}</div>
      </div>

      <style jsx>{`
        .row {
          display: flex;
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

        @media (max-width: 640px) {
          .bubble {
            max-width: 90%;
          }
        }
      `}</style>
    </>
  );
}