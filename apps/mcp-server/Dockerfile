FROM node:20-slim AS deps
WORKDIR /repo
RUN corepack enable
COPY package.json pnpm-workspace.yaml ./
COPY packages/shared/package.json packages/shared/package.json
COPY apps/mcp-server/package.json apps/mcp-server/package.json
RUN pnpm install --frozen-lockfile=false

FROM deps AS build
COPY packages/shared packages/shared
COPY apps/mcp-server apps/mcp-server
RUN pnpm --filter @netsuite-cfo/shared build
RUN pnpm --filter @netsuite-cfo/mcp-server build

FROM node:20-slim AS runtime
WORKDIR /repo
ENV NODE_ENV=production
RUN corepack enable
COPY --from=deps /repo/node_modules ./node_modules
COPY --from=deps /repo/apps/mcp-server/node_modules ./apps/mcp-server/node_modules
COPY --from=build /repo/packages/shared ./packages/shared
COPY --from=build /repo/apps/mcp-server ./apps/mcp-server
COPY package.json pnpm-workspace.yaml ./
CMD ["pnpm", "--filter", "@netsuite-cfo/mcp-server", "start"]
