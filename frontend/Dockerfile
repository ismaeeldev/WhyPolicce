# WhyPolice frontend — AgentGuide/03_MasterPromptGuide.md Step 9.
# Multi-stage build: deps -> build -> runner. Relies on next.config.ts's
# `output: "standalone"` for a minimal, self-contained production image.

# ---- deps: install once, cached across builds unless package*.json change ----
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

# ---- build: compile the app against the deps layer above ----
FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# NEXT_PUBLIC_* vars are inlined into the client JS bundle at BUILD time,
# not read at runtime — setting NEXT_PUBLIC_BACKEND_URL only in compose's
# `environment:` would have zero effect on an already-built image. Passed
# as a build ARG instead (see docker-compose.yml's `build.args`). This is
# the only frontend value that needs to cross the build boundary — every
# other secret (Auth0 client secret, etc.) is server-only, read at request
# time via process.env, and correctly never touches this build stage.
ARG NEXT_PUBLIC_BACKEND_URL
ENV NEXT_PUBLIC_BACKEND_URL=${NEXT_PUBLIC_BACKEND_URL}
RUN npm run build

# ---- runner: minimal final image, only the standalone output + static assets ----
FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs \
  && adduser --system --uid 1001 nextjs

# Standalone output already contains a pruned node_modules + server.js, but
# NOT .next/static or public/ — Next.js's own documented gap, copied
# explicitly here (see https://nextjs.org/docs/app/api-reference/config/next-config-js/output).
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

CMD ["node", "server.js"]
