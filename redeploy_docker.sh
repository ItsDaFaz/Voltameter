# Take down containers
docker compose down
if [ $? -ne 0 ]; then
    echo "Failed to bring down containers"
    exit 1
fi

# Pull latest master branch
git pull
if [ $? -ne 0 ]; then
    echo "Failed to pull latest changes from master branch"
    exit 1
fi

# Build containers
docker compose build
if [ $? -ne 0 ]; then
    echo "Failed to build containers"
    exit 1
fi

# Start containers
docker compose up -d
if [ $? -ne 0 ]; then
    echo "Failed to start containers"
    exit 1
fi