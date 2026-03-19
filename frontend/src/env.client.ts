// env.client.ts
const apiUrl = process.env.NEXT_PUBLIC_API_URL;

if (!apiUrl) {
  throw new Error("Missing required NEXT_PUBLIC_API_URL environment variable");
}

export const ENV = {
  API_URL: apiUrl,
};