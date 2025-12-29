"use client";

import { useState } from "react";
import Sidebar from "./components/Sidebar";
import ChatWindow from "./components/ChatWindow";

export default function Page() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleToggleSidebar = () => {
    setSidebarOpen(current => !current);
  };

  return (
    <>
      <main className={`page ${sidebarOpen ? "sidebar-open" : "sidebar-closed"}`}>
        <Sidebar onToggle={handleToggleSidebar} open={sidebarOpen} />
        <div className="chat-area">
          <ChatWindow />
        </div>
      </main>

      <style jsx>{`
        .page {
          height: 100vh;
          width: 100%;
          display: flex;
          gap: clamp(16px, 4vw, 32px);
          padding: clamp(18px, 5vw, 48px);
          overflow: hidden;
          background: radial-gradient(circle at top, rgba(109, 93, 252, 0.32), transparent 55%),
            radial-gradient(circle at bottom, rgba(80, 54, 239, 0.25), transparent 60%),
            #050505;
          transition: gap 0.3s ease;
        }

        .page.sidebar-closed {
          gap: clamp(12px, 3vw, 24px);
        }

        .chat-area {
          flex: 1;
          height: 100%;
          display: flex;
          justify-content: center;
          align-items: center;
          padding-right: clamp(12px, 3vw, 22px);
          transition: padding 0.3s ease;
        }

        .page.sidebar-open .chat-area {
          padding-right: clamp(24px, 4vw, 40px);
        }

        @media (max-width: 1024px) {
          .page {
            gap: clamp(12px, 4vw, 24px);
            padding: clamp(16px, 5vw, 32px);
          }

          .chat-area {
            align-items: stretch;
            padding-right: clamp(12px, 3vw, 20px);
          }

          .page.sidebar-open .chat-area {
            padding-right: clamp(18px, 4vw, 30px);
          }
        }

        @media (max-width: 900px) {
          .page {
            padding: clamp(16px, 6vw, 28px);
          }

          .page.sidebar-open .chat-area {
            padding-right: clamp(16px, 4vw, 28px);
          }

          .page.sidebar-closed .chat-area {
            padding-right: clamp(10px, 3vw, 18px);
          }
        }

        @media (max-width: 720px) {
          .page {
            flex-direction: column;
            align-items: stretch;
            gap: clamp(18px, 5vw, 32px);
          }

          .chat-area,
          .page.sidebar-open .chat-area,
          .page.sidebar-closed .chat-area {
            padding-right: 0;
            padding-top: clamp(12px, 4vw, 24px);
          }
        }
      `}</style>
    </>
  );
}
