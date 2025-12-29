"use client";

export default function ConfigurationPage() {
  return (
    <main className="configuration-page">
      <div className="panel">
        <h1>Configuración</h1>
        <p>Próximamente podrás ajustar el comportamiento del asistente desde este panel.</p>
      </div>
      <style jsx>{`
        .configuration-page {
          height: 100vh;
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: clamp(24px, 6vw, 60px);
          background: radial-gradient(circle at top, rgba(109, 93, 252, 0.28), transparent 55%),
            radial-gradient(circle at bottom, rgba(80, 54, 239, 0.22), transparent 60%),
            #050505;
          color: #f4f4f4;
        }

        .panel {
          max-width: 560px;
          width: 100%;
          background: rgba(12, 12, 12, 0.6);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 24px;
          padding: clamp(24px, 4vw, 40px);
          box-shadow: 0 20px 55px rgba(0, 0, 0, 0.35);
          backdrop-filter: blur(10px);
          text-align: center;
        }

        h1 {
          margin: 0 0 16px;
          font-size: clamp(1.8rem, 2.5vw, 2.4rem);
        }

        p {
          margin: 0;
          line-height: 1.6;
          color: rgba(244, 244, 244, 0.82);
        }
      `}</style>
    </main>
  );
}
