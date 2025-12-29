"use client";

import Link from "next/link";

import { useState, useEffect } from "react";
interface SidebarProps {
  open: boolean;
  onToggle: () => void;
}

export default function Sidebar({ open, onToggle }: SidebarProps) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
  }, []);


  return (
    <>
      <div className={`sidebar-shell ${open ? "open" : "closed"}`}>
        <button
          aria-label={open ? "Cerrar panel de información" : "Abrir panel de información"}
          aria-expanded={open}
          className={`toggle ${open ? "open" : ""}`}
          onClick={onToggle}
          type="button"
        >
          <span className="bar top" />
          <span className="bar middle" />
          <span className="bar bottom" />
        </button>

        <div className={`bubble ${open ? "open" : ""} ${mounted ? "mounted" : ""}`}>
          <div
            className={`panel ${open ? "open" : ""}`}
            aria-hidden={!open}
            style={{ display: mounted ? undefined : "none" }}
          >
            <div className="heading">
              <span className="badge">MatProp</span>
              <h1>Asistente de materiales</h1>
              <p>
                Consulta propiedades, procesos y recomendaciones sobre materiales con un modelo
                especializado entrenado para el dominio científico.
              </p>
            </div>
            <ul>
              <li>Resume papers y hojas de datos al instante.</li>
              <li>Explora predicciones de modelos MEGNet existentes.</li>
              <li>Recibe sugerencias para nuevos experimentos.</li>
            </ul>
            <Link className="config" href="/configuration" tabIndex={open ? 0 : -1}>
              <span className="config-bubble">
                <svg fill="none" height="22" viewBox="0 0 24 24" width="22" xmlns="http://www.w3.org/2000/svg">
                  <path
                    d="M12 4.2 13.18 5.9l2.02.3.3 2.02 1.68 1.18-1.68 1.18-.3 2.02-2.02.3L12 15.8l-1.18-1.68-2.02-.3-.3-2.02-1.68-1.18 1.68-1.18.3-2.02 2.02-.3L12 4.2Z"
                    stroke="currentColor"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="1.4"
                  />
                  <circle cx="12" cy="12" fill="none" r="2.4" stroke="currentColor" strokeWidth="1.4" />
                </svg>
                <span className="config-label">Configuración</span>
              </span>
            </Link>
          </div>
        </div>
      </div>

      <style jsx>{`
        .sidebar-shell {
          position: relative;
          display: flex;
          align-items: flex-start;
          flex: 0 0 auto;
          height: 100%;
          --toggle-offset: 0px;
          --toggle-scale: 1;
          --toggle-top: clamp(40px, 8vw, 60px);
          --toggle-translate-y: -50%;
        }

        .bubble {
          position: relative;
          width: 54px;
          height: 54px;
          border-radius: 50%;
          background: transparent;
          border: none;
          box-shadow: none;
          transition: width 0.45s ease, height 0.45s ease, border-radius 0.45s ease, background 0.45s ease,
            box-shadow 0.45s ease, padding 0.45s ease;
          overflow: hidden;
          display: flex;
          flex-direction: column;
          align-items: stretch;
          justify-content: flex-start;
          box-sizing: border-box;
        }

        .bubble.open {
          width: clamp(280px, 30vw, 320px);
          height: 100%;
          border-radius: 26px;
          background: linear-gradient(135deg, rgba(80, 54, 239, 0.35), rgba(109, 93, 252, 0.18));
          border: 1px solid rgba(109, 93, 252, 0.4);
          box-shadow: 0 26px 54px rgba(36, 20, 98, 0.36);
          padding: clamp(96px, 12vw, 120px) clamp(24px, 3vw, 28px) clamp(28px, 4vw, 36px);
        }

        .sidebar-shell.open {
          --toggle-offset: clamp(96px, 18vw, 128px);
        }

        .toggle {
          position: absolute;
          top: var(--toggle-top);
          left: 50%;
          width: 44px;
          height: 44px;
          border-radius: 50%;
          border: none;
          background: radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.12), rgba(16, 14, 40, 0.96));
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          outline: none;
          --toggle-scale: 1;
          transition: transform 0.42s cubic-bezier(0.65, 0, 0.35, 1);
          transform: translate(calc(-50% + var(--toggle-offset)), var(--toggle-translate-y))
            scale(var(--toggle-scale));
          z-index: 1;
          box-shadow: 0 12px 24px rgba(18, 12, 60, 0.32);
          isolation: isolate;
        }

        .toggle:hover {
          --toggle-scale: 1.06;
        }

        .toggle:focus-visible {
          outline: 2px solid rgba(160, 140, 255, 0.82);
          outline-offset: 4px;
        }

        .toggle::after {
          content: "";
          position: absolute;
          inset: 0;
          border-radius: 50%;
          background: linear-gradient(135deg, rgba(109, 93, 252, 0.55), rgba(80, 54, 239, 0.35));
          border: 1px solid rgba(255, 255, 255, 0.18);
          box-shadow: 0 10px 24px rgba(42, 24, 120, 0.45);
          opacity: 0;
          transform: scale(0.6);
          transition: opacity 0.32s ease, transform 0.32s ease;
          z-index: 0;
          visibility: hidden;
          pointer-events: none;
        }

        .toggle.open::after {
          opacity: 1;
          transform: scale(1);
          visibility: visible;
        }

        .bar {
          pointer-events: none;
          position: absolute;
          left: 50%;
          top: 50%;
          width: 22px;
          height: 2px;
          background: #fdfdfd;
          border-radius: 999px;
          --bar-offset: 0px;
          --bar-rotation: 0deg;
          transform: translate(-50%, var(--bar-offset)) rotate(var(--bar-rotation));
          transition: transform 0.42s cubic-bezier(0.65, 0, 0.35, 1),
            opacity 0.32s cubic-bezier(0.65, 0, 0.35, 1);
          z-index: 1;
        }

        .toggle:not(.open) .bar {
          background: #0c0c0c;
          box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.65);
        }

        .bar.top {
          --bar-offset: -7px;
        }

        .bar.middle {
          --bar-offset: 0px;
        }

        .bar.bottom {
          --bar-offset: 7px;
        }

        .toggle.open .bar.top {
          --bar-offset: 0px;
          --bar-rotation: 45deg;
        }

        .toggle.open .bar.middle {
          opacity: 0;
        }

        .toggle.open .bar.bottom {
          --bar-offset: 0px;
          --bar-rotation: -45deg;
        }

        .panel {
          display: flex;
          flex-direction: column;
          gap: clamp(18px, 3vw, 24px);
          color: #f4f4f4;
          opacity: 0;
          visibility: hidden;
          transform: translateY(14px);
          transition: opacity 0.32s cubic-bezier(0.65, 0, 0.35, 1),
            transform 0.32s cubic-bezier(0.65, 0, 0.35, 1);
          pointer-events: none;
          flex: 1;
          min-height: 0;
        }

        .panel.open {
          opacity: 1;
          visibility: visible;
          transform: translateY(0);
          pointer-events: auto;
          transition-delay: 0.12s;
        }

        .bubble:not(.mounted) .panel {
          display: none;
        }

        .badge {
          display: inline-flex;
          align-items: center;
          padding: 4px 12px;
          border-radius: 999px;
          background: rgba(12, 12, 12, 0.45);
          border: 1px solid rgba(255, 255, 255, 0.12);
          font-size: 0.74rem;
          font-weight: 600;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          margin-bottom: 8px;
        }

        h1 {
          margin: 0;
          font-size: clamp(1.8rem, 2.4vw, 2.3rem);
          font-weight: 700;
          line-height: 1.2;
        }

        p {
          margin: 0;
          line-height: 1.6;
          color: rgba(244, 244, 244, 0.86);
          font-size: 0.96rem;
        }

        ul {
          margin: 0;
          padding-left: 20px;
          display: grid;
          gap: 10px;
          color: rgba(244, 244, 244, 0.92);
          font-size: 0.94rem;
        }

        .config {
          margin-top: auto;
          display: inline-flex;
          align-items: center;
          justify-content: flex-start;
          gap: 16px;
          padding: 14px 18px;
          border-radius: 18px;
          background: linear-gradient(135deg, rgba(15, 12, 45, 0.72), rgba(80, 54, 239, 0.48));
          border: 1px solid rgba(160, 140, 255, 0.32);
          color: #ffffff;
          text-decoration: none;
          box-shadow: 0 14px 32px rgba(24, 14, 78, 0.42);
          transition: transform 0.25s ease, box-shadow 0.25s ease;
        }

        .config:hover {
          transform: translateY(-2px);
          box-shadow: 0 18px 36px rgba(30, 18, 90, 0.55);
        }

        .config-bubble {
          display: inline-flex;
          align-items: center;
          gap: 10px;
          padding: 10px 18px;
          border-radius: 999px;
          background: linear-gradient(135deg, rgba(109, 93, 252, 0.52), rgba(80, 54, 239, 0.36));
          border: 1px solid rgba(255, 255, 255, 0.18);
          box-shadow: inset 0 0 12px rgba(255, 255, 255, 0.08);
          font-weight: 600;
          font-size: 0.95rem;
          color: #ffffff;
        }

        .config-bubble svg {
          flex-shrink: 0;
        }

        .config-label {
          letter-spacing: 0.01em;
        }

        @media (max-width: 900px) {
          .bubble.open {
            width: min(320px, 82vw);
          }
        }

        @media (max-width: 720px) {
          .sidebar-shell {
            width: 100%;
            align-items: stretch;
          }

          .bubble.open {
            width: 100%;
            padding: clamp(68px, 20vw, 82px) clamp(22px, 6vw, 28px) clamp(28px, 8vw, 32px);
          }

          .sidebar-shell.open {
            --toggle-offset: clamp(64px, 26vw, 92px);
            --toggle-top: clamp(32px, 10vw, 48px);
          }
        }
      `}</style>
    </>
  );
}

