const API_URL = process.env.NEXT_PUBLIC_EVAL_API_URL;

if (!API_URL) {
  throw new Error("Missing NEXT_PUBLIC_EVAL_API_URL");
}

export const ENV = {
  API_URL,
};