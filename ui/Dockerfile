FROM node:20-alpine

WORKDIR /ui

# Ensure Vite API base can be overridden at container runtime.
ENV VITE_PM_BOT_API_BASE=http://127.0.0.1:8000

COPY package.json package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY . .

EXPOSE 4173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "4173"]
