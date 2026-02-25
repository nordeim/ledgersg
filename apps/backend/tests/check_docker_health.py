import docker
import sys
# pip install psycopg2-binary

def check_postgres_health(container_name="ledgersg_db"):
    client = docker.from_env()
    try:
        container = client.containers.get(container_name)
        # Access the State/Health/Status attribute
        health = container.attrs.get("State", {}).get("Health", {}).get("Status", "no healthcheck")
        status = container.status  # e.g., 'running'
        
        print(f"Container: {container_name}")
        print(f"Status:    {status}")
        print(f"Health:    {health}")
        
        if health == "healthy":
            return True
        return False
    except docker.errors.NotFound:
        print(f"Error: Container '{container_name}' not found.")
        return False

if __name__ == "__main__":
    if check_postgres_health():
        sys.exit(0)
    else:
        sys.exit(1)

