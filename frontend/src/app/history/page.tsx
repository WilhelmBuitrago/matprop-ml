// frontend/src/app/history/page.tsx
"use client";

import { useEffect, useState } from "react";

export default function HistoryPage() {
  const [data, setData] = useState(null);

  useEffect(() => {

    fetch(`${process.env.NEXT_PUBLIC_API_URL}/v1/conversation_history`)
      .then(r => r.json())
      .then(setData)
      .catch(console.error);
  }, []);

  return (
    <pre>{JSON.stringify(data, null, 2)}</pre>
  );
}
