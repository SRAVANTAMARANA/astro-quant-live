# Use Node.js image
FROM node:18-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm install

COPY . .

# Production image with serve
FROM node:18-alpine
WORKDIR /app

RUN npm install -g serve
COPY --from=build /app .

EXPOSE 3000
CMD ["serve", "-s", ".", "-l", "3000"]
