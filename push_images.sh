#!/bin/bash

# Configuration
IMAGE_NAME="ganesh200111/document-extractor"
TAG="latest"
FULL_IMAGE_NAME="${IMAGE_NAME}:${TAG}"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Production Build and Push for ${FULL_IMAGE_NAME}...${NC}"

# 1. Check if Docker is installed
if ! [ -x "$(command -v docker)" ]; then
  echo -e "${RED}Error: docker is not installed.${NC}" >&2
  exit 1
fi

# 2. Check if logged into Docker Hub
# We try to inspect a private image or just check config, but a simple way is 'docker info' or just attempt push logic.
# A better way is to see if the user has auth for the specific repository.
echo "Checking Docker Hub authentication..."
docker info | grep -q "Username"
if [ $? -ne 0 ]; then
  echo -e "${RED}Warning: You might not be logged into Docker Hub. Please run 'docker login' if the push fails.${NC}"
fi

# 3. Build the image
echo -e "${GREEN}Building Docker image...${NC}"
docker build -t "${FULL_IMAGE_NAME}" .

if [ $? -ne 0 ]; then
  echo -e "${RED}Docker build failed. Exiting.${NC}"
  exit 1
fi

# 4. Push to Docker Hub
echo -e "${GREEN}Pushing image to Docker Hub...${NC}"
docker push "${FULL_IMAGE_NAME}"

if [ $? -ne 0 ]; then
  echo -e "${RED}Docker push failed. Did you run 'docker login'?${NC}"
  exit 1
fi

echo -e "${GREEN}Successfully built and pushed ${FULL_IMAGE_NAME}${NC}"
