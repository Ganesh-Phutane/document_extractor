# Stage 1: Build the React application
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies
# Using layer caching for node_modules
COPY package.json package-lock.json ./
RUN npm install

# Copy source code and build
COPY . .
# Note: In a real CI/CD, we might inject VITE_ environment variables here
RUN npm run build

# Stage 2: Serve the application with Nginx
FROM nginx:alpine

# Copy the build output from the build stage
# Default Vite output directory is 'dist'
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration for SPA routing and API proxying
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
