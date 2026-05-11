# Build stage
FROM node:16-alpine as build-stage

# Set locale to support UTF-8
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

WORKDIR /app

# Copy package files and patches folder
COPY package*.json ./
COPY patches ./patches

# Install dependencies - npm install pentru a rula postinstall (patch-package)
RUN npm install

# Copy project files
COPY . .

# Build the app with UTF-8 encoding
RUN npm run build

# Production stage
FROM nginx:alpine as production-stage

# Copy built files from build stage
COPY --from=build-stage /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
