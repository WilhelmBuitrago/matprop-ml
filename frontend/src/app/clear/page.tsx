// frontend/src/app/clear/page.tsx
"use client";

import { useEffect, useState } from "react";
import { ENV } from "@/env.client";

export default function ClearPage() {
  const [data, setData] = useState(null);

  useEffect(() => {
    const endpoint = `${ENV.API_URL}/v1/clear_history`;

    fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    })
      .then(async response => {
        if (response.ok) {
          return response.json();
        }
        // Temporary compatibility while GET is deprecated for one release.
        const fallback = await fetch(endpoint);
        return fallback.json();
      })
      .then(setData)
      .catch(console.error);
  }, []);

  return (
    <pre>{JSON.stringify(data, null, 2)}</pre>
  );
}
