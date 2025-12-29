//frontend/src/app/components/ChatWindow.tsx
"use client";

import { useState, useRef, useEffect } from "react";
import ChatMessage from "./ChatMessage";
import ChatInput from "./ChatInput";

const resolveChatEndpoint = () => {
  const envProcess = (globalThis as {
    process?: { env?: Record<string, string | undefined> };
  }).process;
  //const rawBase = envProcess?.env?.NEXT_PUBLIC_API_URL ?? "";
  const rawBase = process.env.NEXT_PUBLIC_API_URL;
  let trimmedBase = rawBase;
  while (trimmedBase.endsWith("/")) {
    trimmedBase = trimmedBase.slice(0, -1);
  }
  return trimmedBase ? `${trimmedBase}/v1/chat` : "/v1/chat";
};

interface Message {
  text: string;
  sender: "user" | "agent" | "system";
}

export default function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  // Keep the latest message in view as the list grows.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const hasUserMessage = messages.some(message => message.sender === "user");

  const sendMessage = async (text: string) => {
    const userMessage: Message = { text, sender: "user" };
    const updatedHistory = [...messages, userMessage];
    setMessages(updatedHistory);
    setLoading(true);

    try {
      const endpoint = resolveChatEndpoint();
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      const responseText = typeof data?.response === "string" ? data.response : "";

      if (!responseText) {
        setMessages(prev => [
          ...prev,
          {
            text: "No se recibió respuesta del modelo.",
            sender: "system",
          },
        ]);
        return;
      }

      const agentMessage: Message = { text: "", sender: "agent" };
      setMessages(prev => [...prev, agentMessage]);

      for (const char of responseText) {
        await new Promise(resolve => setTimeout(resolve, 12));
        setMessages(prev => {
          if (prev.length === 0) {
            return prev;
          }
          const next = [...prev];
          const lastIndex = next.length - 1;
          const last = next[lastIndex];
          if (last.sender !== "agent") {
            return prev;
          }
          next[lastIndex] = { ...last, text: `${last.text}${char}` };
          return next;
        });
      }
    } catch (error) {
      console.error("Error al consultar el backend LLM:", error);
      setMessages(prev => [
        ...prev,
        {
          text: "Error al contactar al agente. Por favor intenta nuevamente.",
          sender: "system",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="chat-wrapper">
        <section className="chat-card">
          {!hasUserMessage && (
            <div className="welcome" role="note">
              <h2>Bienvenido</h2>
              <p>
                Comienza la conversación contándonos qué necesitas. El asistente conserva el contexto
                para mantener el hilo técnico y puede apoyarse en modelos predictivos cuando sea
                necesario.
              </p>
            </div>
          )}

          <div className="messages" role="log" aria-live="polite">
            {messages.map((message, index) => (
              <div className="message-item" key={`${index}-${message.sender}-${message.text.length}`}>
                <ChatMessage message={message.text} sender={message.sender} />
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          <ChatInput disabled={loading} onSend={sendMessage} />
        </section>
      </div>

      <style jsx>{`
        .chat-wrapper {
          width: 100%;
          height: 100%;
          display: flex;
          justify-content: center;
          align-items: center;
          padding: 32px;
        }

        .chat-card {
          width: 100%;
          max-width: 900px;
          height: min(820px, 100%);
          background: rgba(12, 12, 12, 0.65);
          border: 1px solid rgba(255, 255, 255, 0.04);
          border-radius: 18px;
          padding: 24px;
          display: flex;
          flex-direction: column;
          gap: 20px;
          min-height: 0;
          backdrop-filter: blur(6px);
          box-shadow: 0 18px 45px rgba(0, 0, 0, 0.32);
        }

        .welcome {
          background: linear-gradient(135deg, rgba(109, 93, 252, 0.35), rgba(80, 54, 239, 0.18));
          border: 1px solid rgba(109, 93, 252, 0.3);
          border-radius: 16px;
          padding: 20px;
          color: #f5f5f5;
          flex-shrink: 0;
        }

        .chat-card :global(.chat-input) {
          flex-shrink: 0;
        }

        .welcome h2 {
          margin: 0 0 8px;
          font-size: 1.4rem;
        }

        .welcome p {
          margin: 0;
          line-height: 1.6;
          font-size: 0.95rem;
        }

        .messages {
          flex: 1;
          min-height: 0;
          overflow-y: auto;
          padding-right: 10px;
          margin-right: -10px;
          overscroll-behavior: contain;
        }

        .message-item {
          display: contents;
        }

        .messages::-webkit-scrollbar {
          width: 6px;
        }

        .messages::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.2);
          border-radius: 999px;
        }

        @media (min-width: 1024px) {
          .chat-card {
            padding: 32px;
          }
        }

        @media (max-width: 1023px) {
          .chat-wrapper {
            padding: 24px;
          }

          .chat-card {
            height: min(760px, 100%);
          }
        }

        @media (max-width: 640px) {
          .chat-wrapper {
            padding: 16px;
          }

          .chat-card {
            padding: 20px;
            height: min(720px, 100%);
          }
        }
      `}</style>
    </>
  );
}