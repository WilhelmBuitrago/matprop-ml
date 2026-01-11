# =========================
# Stage 1: Build
# =========================
FROM node:20-alpine AS builder
WORKDIR /app

# Variables recibidas en build-time
ARG NEXT_PUBLIC_API_URL
ARG INTERNAL_API_URL

ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV INTERNAL_API_URL=${INTERNAL_API_URL}

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# DEBUG opcional
RUN echo "➡ NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}"
RUN echo "➡ INTERNAL_API_URL=${INTERNAL_API_URL}"

RUN npm run build

# =========================
# Stage 2: Runner
# =========================
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production

# Estas variables siguen siendo útiles en runtime
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV INTERNAL_API_URL=${INTERNAL_API_URL}

COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./

RUN npm install --omit=dev

EXPOSE 3000
CMD ["npm", "start"]
