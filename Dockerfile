FROM node:20 AS base

WORKDIR /app

COPY package*.json ./
RUN npm install --omit=optional

COPY . . 

RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
