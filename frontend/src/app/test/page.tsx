//frontend/src/app/test/page.tsx
"use client";

import { useEffect, useState } from "react";

export default function TestPage() {
  const [data, setData] = useState(null);

  useEffect(() => {

    fetch(`${process.env.NEXT_PUBLIC_API_URL}/v1/health`)
      .then(r => r.json())
      .then(setData)
      .catch(console.error);
  }, []);

  return (
    <pre>{JSON.stringify(data, null, 2)}</pre>
  );
}
