//frontend/src/app/layout.tsx
import type { ReactNode } from "react";
import "./globals.css";

export const metadata = {
  title: "MatProp",
  description: "Frontend en producción"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
