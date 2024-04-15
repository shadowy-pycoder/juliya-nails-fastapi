FROM node:21.7-alpine3.18

RUN mkdir /app && chown node:node /app

WORKDIR /app

ENV PATH /app/node_modules/.bin:$PATH

RUN npm install --global npm@10.5.2

COPY --chown=node:node package.json .
COPY --chown=node:node package-lock.json .
RUN npm install

COPY --chown=node:node . .
USER node

CMD ["npm", "run", "serve"]