//frontend/src/app/components/ChatInput.tsx

"use client";

import { FormEvent, useState } from "react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export default function ChatInput({ onSend, disabled = false }: ChatInputProps) {
  const [text, setText] = useState("");

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    const value = text.trim();
    if (!value || disabled) {
      return;
    }
    onSend(value);
    setText("");
  };

  return (
    <>
      <form className="chat-input" onSubmit={handleSubmit}>
        <input
          aria-label="Escribe un mensaje"
          autoComplete="off"
          disabled={disabled}
          placeholder="Escribe un mensaje..."
          value={text}
          onChange={event => setText(event.target.value)}
        />
        <button disabled={disabled || !text.trim()} type="submit">
          Enviar
        </button>
      </form>

      <style jsx>{`
        .chat-input {
          display: flex;
          gap: 12px;
          padding-top: 16px;
          border-top: 1px solid rgba(255, 255, 255, 0.08);
        }

        input {
          flex: 1;
          padding: 12px 16px;
          border-radius: 999px;
          border: 1px solid rgba(255, 255, 255, 0.12);
          background: rgba(12, 12, 12, 0.75);
          color: #f5f5f5;
          font-size: 0.95rem;
          transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }

        input:focus {
          border-color: rgba(173, 155, 255, 0.9);
          box-shadow: 0 0 0 3px rgba(173, 155, 255, 0.2);
          outline: none;
        }

        input:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        button {
          padding: 0 20px;
          border-radius: 999px;
          border: none;
          cursor: pointer;
          background: linear-gradient(135deg, #6d5dfc, #5036ef);
          color: #ffffff;
          font-weight: 600;
          transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
        }

        button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
          box-shadow: none;
        }

        button:not(:disabled):hover {
          transform: translateY(-1px);
          box-shadow: 0 8px 20px rgba(80, 54, 239, 0.35);
        }

        @media (max-width: 640px) {
          .chat-input {
            flex-direction: column;
            gap: 8px;
          }

          button {
            width: 100%;
            padding: 12px 0;
          }
        }
      `}</style>
    </>
  );
}