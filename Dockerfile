Dockerfile# SmartAssist AI - Multi-stage Docker Build

FROM node:18-alpine AS builder
WORKDIR /app
COPY backend/package*.json ./
RUN npm ci --only=production

# Production stage
FROM node:18-alpine
WORKDIR /app

# Set environment
ENV NODE_ENV=production
ENV PORT=3000

# Copy dependencies from builder
COPY --from=builder /app/node_modules ./node_modules

# Copy application code
COPY backend/index.js ./
COPY backend/.env* ./

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000/api/health', (r) => {if (r.statusCode !== 200) throw new Error(r.statusCode)})" || exit 1

# Expose port
EXPOSE 3000

# Start application
CMD ["node", "index.js"]
