# frontend/Dockerfile
FROM node:18-alpine AS build

WORKDIR /app
COPY ./ /app

# Install simple static server
RUN npm install -g serve

EXPOSE 3000

# Serve ictPanel.html on port 3000
CMD ["serve", "-s", ".", "-l", "3000"]
