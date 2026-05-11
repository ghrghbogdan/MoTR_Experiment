FROM node:18-alpine as build

WORKDIR /app

# Copy package files and install dependencies
COPY MoTR/run_motr_in_magpie/provo/package*.json ./
RUN npm install

# Copy source and build
COPY MoTR/run_motr_in_magpie/provo/ ./
RUN npm run build

# Production stage with Nginx
FROM nginx:alpine

# Copy built files from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx config (optional, for custom settings)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
