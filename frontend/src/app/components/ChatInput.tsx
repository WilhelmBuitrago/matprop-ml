//frontend/src/app/components/ChatInput.tsx

"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  moreContextEnabled: boolean;
  onToggleMoreContext: () => void;
}

export default function ChatInput({
  onSend,
  disabled = false,
  moreContextEnabled,
  onToggleMoreContext,
}: ChatInputProps) {
  const [text, setText] = useState("");
  const [isPopoverOpen, setIsPopoverOpen] = useState(false);
  const popoverRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!isPopoverOpen) {
      return;
    }

    const handlePointerDown = (event: MouseEvent) => {
      const target = event.target;
      if (!(target instanceof Node)) {
        return;
      }
      if (!popoverRef.current?.contains(target)) {
        setIsPopoverOpen(false);
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsPopoverOpen(false);
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleEscape);

    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [isPopoverOpen]);

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
        <div className="context-controls" ref={popoverRef}>
          <button
            aria-controls="more-context-popover"
            aria-expanded={isPopoverOpen}
            aria-haspopup="menu"
            aria-label="Abrir opciones de contexto"
            className="context-trigger"
            disabled={disabled}
            onClick={() => setIsPopoverOpen(previous => !previous)}
            type="button"
          >
            +
          </button>

          {isPopoverOpen && (
            <div className="popover" id="more-context-popover" role="menu">
              <button
                aria-label={
                  moreContextEnabled
                    ? "Desactivar More context"
                    : "Activar More context"
                }
                className={`more-context-item ${moreContextEnabled ? "is-selected" : ""}`}
                disabled={disabled}
                onClick={() => {
                  onToggleMoreContext();
                  setIsPopoverOpen(false);
                }}
                role="menuitemcheckbox"
                aria-checked={moreContextEnabled}
                type="button"
              >
                <span className="item-text">More context</span>
              </button>
            </div>
          )}
        </div>

        <input
          aria-label="Escribe un mensaje"
          autoComplete="off"
          disabled={disabled}
          placeholder="Escribe un mensaje..."
          value={text}
          onChange={event => setText(event.target.value)}
        />
        <button aria-label="Enviar mensaje" disabled={disabled || !text.trim()} type="submit">
          <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            width="18"
            height="18"
            focusable="false"
          >
            <path
              d="M5 12h12M11 6l6 6-6 6"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
      </form>

      <style jsx>{`
        .chat-input {
          display: flex;
          align-items: center;
          gap: 12px;
          padding-top: 16px;
          border-top: 1px solid rgba(255, 255, 255, 0.08);
        }

        .context-controls {
          position: relative;
          flex-shrink: 0;
        }

        .context-trigger {
          width: 44px;
          height: 44px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          border-radius: 12px;
          border: 1px solid rgba(255, 255, 255, 0.16);
          background: transparent;
          color: rgba(255, 255, 255, 0.9);
          font-size: 1.45rem;
          line-height: 0;
          cursor: pointer;
          transition: border-color 0.2s ease, color 0.2s ease, transform 0.2s ease;
        }

        .context-trigger:hover:not(:disabled),
        .context-trigger:focus-visible:not(:disabled) {
          color: #ffffff;
          border-color: rgba(255, 255, 255, 0.32);
          transform: translateY(-1px);
          outline: none;
        }

        .context-trigger:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .popover {
          position: absolute;
          left: 0;
          bottom: calc(100% + 10px);
          min-width: 210px;
          border-radius: 12px;
          border: 1px solid rgba(255, 255, 255, 0.14);
          background: rgba(11, 11, 11, 0.95);
          box-shadow: 0 12px 28px rgba(0, 0, 0, 0.35);
          padding: 8px;
          z-index: 20;
        }

        .more-context-item {
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: flex-start;
          border-radius: 10px;
          border: 1px solid transparent;
          background: rgba(255, 255, 255, 0.02);
          color: rgba(255, 255, 255, 0.88);
          padding: 9px 11px;
          cursor: pointer;
          font-size: 0.9rem;
          transition: opacity 0.2s ease, transform 0.2s ease, border-color 0.2s ease,
            box-shadow 0.2s ease;
        }

        .more-context-item:hover:not(:disabled) {
          opacity: 0.95;
        }

        .more-context-item:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .more-context-item.is-selected {
          opacity: 1;
          border-color: rgba(183, 172, 255, 0.52);
          background: rgba(109, 93, 252, 0.18);
          box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06);
        }

        .item-text {
          font-weight: 600;
          letter-spacing: 0.01em;
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

        .chat-input > button[type="submit"] {
          width: 44px;
          height: 44px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          border-radius: 999px;
          border: none;
          cursor: pointer;
          background: linear-gradient(135deg, #6d5dfc, #5036ef);
          color: #ffffff;
          transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
        }

        .chat-input > button[type="submit"] svg {
          transform: translateX(1px);
        }

        .chat-input > button[type="submit"]:disabled {
          opacity: 0.5;
          cursor: not-allowed;
          box-shadow: none;
        }

        .chat-input > button[type="submit"]:not(:disabled):hover {
          transform: translateY(-1px);
          box-shadow: 0 8px 20px rgba(80, 54, 239, 0.35);
        }

        @media (max-width: 640px) {
          .chat-input {
            gap: 8px;
          }

          .context-trigger {
            width: 40px;
            height: 40px;
            border-radius: 10px;
            font-size: 1.3rem;
          }

          .chat-input > button[type="submit"] {
            width: 40px;
            height: 40px;
          }

          .popover {
            left: 0;
            min-width: min(220px, 86vw);
          }
        }
      `}</style>
    </>
  );
}