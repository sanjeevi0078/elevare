# Docker Instructions for Elevare

## Prerequisites

- Docker
- Docker Compose

## Running the Application

1.  **Build and start the containers:**

    ```bash
    docker-compose up --build
    ```

2.  **Access the application:**

    Open your browser and navigate to `http://localhost:8000`.

3.  **Stop the containers:**

    ```bash
    docker-compose down
    ```

## Running Tests in Docker

To run the tests inside the Docker container:

```bash
docker-compose run --rm web pytest
```

## Troubleshooting

-   If you encounter permission issues with the database file, ensure the permissions on `elevare.db` allow the Docker user to write to it.
-   If Redis connection fails, check if the `redis` service is running.
