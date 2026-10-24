# Litestream Replication Guide

To enable continuous SQLite replication to a cloud storage bucket (e.g., AWS S3, GCS, Azure Blob Storage), we recommend using a Litestream sidecar container.

## Configuration (litestream.yml)

Create a `litestream.yml` file in your stack:

```yaml
dbs:
  - path: /data/garage_inventory.db
    replicas:
      - type: s3
        bucket: <your-bucket-name>
        path: db/garage_inventory.db
```

## Docker Compose Sidecar

Add the Litestream service to your `docker-compose.yml`:

```yaml
services:
  garage-storage:
    ...
    volumes:
      - garage_data:/data
    environment:
      ...
  
  litestream:
    image: litestream/litestream:latest
    volumes:
      - garage_data:/data
      - ./litestream.yml:/etc/litestream.yml
    environment:
      AWS_ACCESS_KEY_ID: <key>
      AWS_SECRET_ACCESS_KEY: <secret>
      AWS_DEFAULT_REGION: <region>
    command: replicate
```

## Restore Procedure

To restore the database from a backup:

1. Stop the `garage-storage` container.
2. Run the restore command using the Litestream CLI:
   ```bash
   docker run --rm -v garage_data:/data -v ./litestream.yml:/etc/litestream.yml \
     litestream/litestream restore /data/garage_inventory.db
   ```
3. Restart `garage-storage`.
