//frontend/src/app/components/ChatWindow.tsx
"use client";

import { useState, useRef, useEffect } from "react";
import { ENV } from '@/env.client'
import ChatMessage from "./ChatMessage";
import ChatInput from "./ChatInput";

const resolveChatEndpoint = (moreContextEnabled: boolean) => {
  const rawBase = ENV.API_URL;
  let trimmedBase = rawBase;
  while (trimmedBase.endsWith("/")) {
    trimmedBase = trimmedBase.slice(0, -1);
  }
  const versionPath = moreContextEnabled ? "/v2/completions" : "/v1/completions";
  return trimmedBase ? `${trimmedBase}${versionPath}` : versionPath;
};

interface Message {
  id: string;
  text: string;
  sender: "user" | "agent" | "system";
  mode?: "v1" | "v2";
  kind?: "default" | "thinking" | "status";
}

export default function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [moreContextEnabled, setMoreContextEnabled] = useState(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const createMessageId = () =>
    `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

  // Keep the latest message in view as the list grows.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const hasUserMessage = messages.some(message => message.sender === "user");

  const sendMessage = async (text: string) => {
    const mode: "v1" | "v2" = moreContextEnabled ? "v2" : "v1";
    const userMessage: Message = { id: createMessageId(), text, sender: "user" };
    setMessages(prev => [...prev, userMessage]);
    setLoading(true);

    try {
      const endpoint = resolveChatEndpoint(moreContextEnabled);

      let responseText = "";

      if (mode === "v1") {
        const thinkingId = createMessageId();
        setMessages(prev => [
          ...prev,
          { id: thinkingId, text: "", sender: "agent", mode: "v1", kind: "thinking" },
        ]);

        const response = await fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt: text }),
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        if (!data?.choices?.length) {
          throw new Error("Invalid completion response");
        }

        responseText = data.choices[0].text;

        setMessages(prev =>
          prev.map(message =>
            message.id === thinkingId
              ? {
                  id: thinkingId,
                  text: "",
                  sender: "agent",
                  mode: "v1",
                  kind: "default",
                }
              : message
          )
        );
      } else {
        const statusId = createMessageId();
        setMessages(prev => [
          ...prev,
          {
            id: statusId,
            text: "Iniciando analisis del contexto...",
            sender: "agent",
            mode: "v2",
            kind: "status",
          },
        ]);

        const response = await fetch(endpoint, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "text/event-stream",
          },
          body: JSON.stringify({ prompt: text, stream: true }),
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        if (!response.body) {
          throw new Error("Streaming body not available");
        }

        const decoder = new TextDecoder("utf-8");
        const reader = response.body.getReader();
        let buffer = "";

        while (true) {
          const { value, done } = await reader.read();
          if (done) {
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          buffer = buffer.replace(/\r/g, "");

          let eventSeparator = buffer.indexOf("\n\n");
          while (eventSeparator !== -1) {
            const rawEvent = buffer.slice(0, eventSeparator);
            buffer = buffer.slice(eventSeparator + 2);

            const lines = rawEvent.split("\n");
            let eventType = "message";
            const dataLines: string[] = [];

            for (const line of lines) {
              if (line.startsWith("event:")) {
                eventType = line.slice("event:".length).trim();
              }
              if (line.startsWith("data:")) {
                dataLines.push(line.slice("data:".length).trim());
              }
            }

            if (dataLines.length > 0) {
              try {
                const payload = JSON.parse(dataLines.join(""));
                if (eventType === "status" && payload?.text) {
                  setMessages(prev =>
                    prev.map(message =>
                      message.id === statusId
                        ? {
                            ...message,
                            text: String(payload.text),
                          }
                        : message
                    )
                  );
                }

                if (eventType === "final" && payload?.text) {
                  responseText = String(payload.text);
                }
              } catch {
                // Ignore malformed chunks and keep reading stream events.
              }
            }

            eventSeparator = buffer.indexOf("\n\n");
          }
        }

        setMessages(prev =>
          prev.map(message =>
            message.id === statusId
              ? {
                  id: statusId,
                  text: "",
                  sender: "agent",
                  mode: "v2",
                  kind: "default",
                }
              : message
          )
        );
      }

      if (!responseText) {
        setMessages(prev => [
          ...prev.filter(message => {
            return !(
              message.sender === "agent" &&
              message.mode === mode &&
              message.kind === "default" &&
              message.text.length === 0
            );
          }),
          {
            id: createMessageId(),
            text: "No se recibió respuesta del modelo.",
            sender: "system",
          },
        ]);
        return;
      }

      const CHUNK_SIZE = 16;
      const CHUNK_DELAY_MS = 40;

      for (let index = 0; index < responseText.length; index += CHUNK_SIZE) {
        const chunk = responseText.slice(index, index + CHUNK_SIZE);
        await new Promise(resolve => setTimeout(resolve, CHUNK_DELAY_MS));
        setMessages(prev => {
          const next = [...prev];
          for (let reverseIndex = next.length - 1; reverseIndex >= 0; reverseIndex -= 1) {
            const candidate = next[reverseIndex];
            if (candidate.sender !== "agent" || candidate.mode !== mode) {
              continue;
            }
            next[reverseIndex] = {
              ...candidate,
              kind: "default",
              text: `${candidate.text}${chunk}`,
            };
            return next;
          }
          next.push({
            id: createMessageId(),
            sender: "agent",
            mode,
            kind: "default",
            text: chunk,
          });
          return next;
        });
      }
    } catch (error) {
      console.error("Error al consultar el backend LLM:", error);
      setMessages(prev => [
        ...prev,
        {
          id: createMessageId(),
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
              <div className="message-item" key={message.id || `${index}-${message.sender}`}>
                <ChatMessage
                  kind={message.kind}
                  message={message.text}
                  mode={message.mode}
                  sender={message.sender}
                />
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          <ChatInput
            disabled={loading}
            moreContextEnabled={moreContextEnabled}
            onSend={sendMessage}
            onToggleMoreContext={() => setMoreContextEnabled(previous => !previous)}
          />
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