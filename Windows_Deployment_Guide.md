This guide will help you set up and run LedgerSG on your Windows 10 or 11 computer using Docker. Docker packages the application with everything it needs, so you don't have to install programming languages or databases manually. Follow these steps carefully, and you'll have your own accounting platform running locally in about 30–60 minutes.

---

## 📋 Before You Start – What You Need

*   A **Windows 10 (64-bit) or Windows 11** PC.
*   At least **8 GB of RAM** (16 GB recommended).
*   About **10 GB of free disk space**.
*   **Administrator access** to your computer (to install software).
*   A stable internet connection.

If you're unsure about any of the technical terms below, don't worry – just follow the steps exactly as written.

---

## ✅ Step 1: Enable Virtualization & WSL2

Docker needs two Windows features to work properly: **virtualization** (hardware support) and **WSL2** (Windows Subsystem for Linux).

### 1.1 Enable Virtualization in BIOS
Most modern PCs have this already enabled. If Docker later complains, you may need to restart your computer, press a key like `F2` or `Delete` during startup to enter BIOS settings, and turn on “Intel VT-x” or “AMD-V”. This step varies by manufacturer; if you're unsure, skip it for now and return if Docker installation fails.

### 1.2 Enable WSL2

1. Press the **Windows key**, type **PowerShell**, right‑click **Windows PowerShell** and choose **Run as administrator**.
2. In the blue PowerShell window, copy and paste this command, then press **Enter**:
   ```powershell
   dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
   ```
3. Wait for it to complete, then copy and paste this second command and press **Enter**:
   ```powershell
   dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
   ```
4. After both commands finish, **restart your computer**.

### 1.3 Set WSL2 as the Default Version

After restarting, open PowerShell **as administrator** again and run:
```powershell
wsl --set-default-version 2
```
If you see a message about needing the Linux kernel update, visit the link provided, download and install the update, then run the command again.

---

## 🐳 Step 2: Install Docker Desktop

1. Go to [Docker's official website](https://www.docker.com/products/docker-desktop/) and click **Download for Windows** (it’s a large file, ~500 MB).
2. Once downloaded, double‑click the installer (e.g., `Docker Desktop Installer.exe`).
3. If a security warning appears, click **Run**.
4. In the installation wizard:
   * Make sure **“Use WSL 2 instead of Hyper‑V”** is **checked** (it should be by default).
   * Leave the other options as they are.
   * Click **OK** and let it install. This may take 5–10 minutes.
5. When finished, check **“Close and restart”** or **“Restart now”** if prompted. Docker will start automatically after restart.

### 2.1 Accept the Docker Subscription Agreement

After restart, you may see a Docker Dashboard window. If it asks you to accept the **Docker Subscription Service Agreement**, read it and click **Accept** to continue. Docker Desktop is free for personal use.

### 2.2 Verify Docker Installation

1. Open a new **Command Prompt** or **PowerShell** window (press Windows key, type `cmd` and press Enter).
2. Type:
   ```cmd
   docker --version
   ```
   You should see something like `Docker version 24.0.7, build ...`. If you get an error, Docker may still be starting – wait a minute and try again.

3. Also check WSL integration:
   ```cmd
   wsl -l -v
   ```
   You should see at least one Linux distribution listed (e.g., `docker-desktop`) with version 2. If not, Docker will create one automatically when needed.

---

## 📦 Step 3: Download LedgerSG Source Code

You need to get the LedgerSG files onto your computer. We’ll use **Git** to clone (download) the repository.

### 3.1 Install Git (if not already installed)

1. Go to [git-scm.com](https://git-scm.com/download/win) – the download should start automatically.
2. Run the installer. You can accept all default options by clicking **Next** repeatedly. No need to change anything.
3. After installation, close and reopen any open Command Prompt / PowerShell windows.

### 3.2 Clone the Repository

1. Decide where you want to store LedgerSG on your computer. For example, you can create a folder `C:\MyApps`.
2. Open **Command Prompt** (or PowerShell) and navigate to that folder:
   ```cmd
   cd C:\MyApps
   ```
3. Now clone the repository:
   ```cmd
   git clone https://github.com/nordeim/ledgersg.git
   ```
   This will create a new folder `ledgersg` inside `C:\MyApps`. Wait until it finishes (it may take a minute or two).

4. Move into that folder:
   ```cmd
   cd ledgersg
   ```

---

## 🐘 Step 4: Run LedgerSG with Docker Compose

LedgerSG includes a `docker-compose.yml` file that tells Docker how to start all the required pieces (database, backend, frontend). We will use this file to launch the application.

### 4.1 Start the Containers

In the same Command Prompt window (still inside the `ledgersg` folder), run:

```cmd
docker-compose up -d
```

* `docker-compose` is the command to manage multi‑container applications.
* `up` means start the containers.
* `-d` runs them in the background (detached mode), so you can continue using the terminal.

This command will download several pre‑built images (like PostgreSQL, Python, Node.js) and then build the LedgerSG containers. The first run may take **10–20 minutes** depending on your internet speed. You’ll see lots of text scrolling by – that’s normal.

**Important:** If you get an error like “docker-compose is not recognized”, try `docker compose up -d` (without the hyphen). Docker now includes Compose as a plugin.

### 4.2 Wait for Everything to Start

While the containers are building, you can check their status. Open another Command Prompt window and type:

```cmd
docker ps
```

This shows running containers. You should eventually see three containers with names like `ledgersg-backend-1`, `ledgersg-frontend-1`, and `ledgersg-db-1`. Their **STATUS** should be “Up” or “healthy”. If any show “exited”, wait a few more minutes – the database may need extra time to initialize.

### 4.3 Verify Logs (Optional)

To see if there are any errors, you can view logs for a container. For example:

```cmd
docker logs ledgersg-backend-1
```

Press `Ctrl+C` to exit the log view.

---

## 🌐 Step 5: Access LedgerSG in Your Browser

Once all containers are running, open your web browser (Chrome, Edge, etc.) and go to:

```
http://localhost:3000
```

You should see the LedgerSG login screen or landing page.

* **If the page doesn’t load**, wait another 2–3 minutes – the frontend container may still be compiling.
* If you get a “connection refused” error, check that the frontend container is actually running (`docker ps`). Also ensure no other program is using port 3000.

### 5.1 Create a User Account (if required)

The first time you access the app, you may need to register an organisation. Look for a **Sign up** or **Register** link. If the app opens directly to a login page, you might need to use a default admin account – check the repository’s `README.md` for default credentials (often `admin` / `admin` or similar). If none are listed, you may have to create a superuser via the command line:

1. In a terminal, run:
   ```cmd
   docker exec -it ledgersg-backend-1 python manage.py createsuperuser
   ```
2. Follow the prompts to set a username, email, and password.

Then log in with that account.

---

## 🧹 Step 6: Stopping and Restarting

When you’re done exploring, you can stop the containers to free up system resources.

* To stop the application (without deleting data):
  ```cmd
  docker-compose down
  ```
  This stops the containers but keeps your database data in a Docker volume, so you won’t lose anything.

* To start again later:
  ```cmd
  docker-compose up -d
  ```

* To completely remove everything (including database data):
  ```cmd
  docker-compose down -v
  ```
  **Only do this if you want a fresh start.**

---

## 🔧 Troubleshooting Common Issues

| Problem | Likely Cause | Solution |
|--------|--------------|----------|
| `docker: command not found` | Docker not installed correctly. | Reinstall Docker Desktop and ensure it’s running. |
| Port 3000 already in use | Another program (like another Node app) is using the port. | Stop that program, or edit the `docker-compose.yml` to change the host port (e.g., `"3001:3000"`). |
| Containers exit immediately | Missing environment variables or configuration. | Check logs with `docker logs <container-name>`. Look for error messages. The repository may need a `.env` file – check its README. |
| Docker Desktop fails to start | WSL2 not installed or virtualization disabled. | Revisit Step 1, ensure WSL2 is installed and set as default. |
| `docker-compose` not recognized | Using an older Docker version. | Try `docker compose` (without hyphen) or update Docker Desktop. |
| Browser shows “This site can’t be reached” | Containers not fully started. | Wait a few more minutes, then run `docker ps` to confirm all are “Up”. |

---

## 🎉 You're Done!

You now have a fully functional LedgerSG accounting platform running on your Windows PC. You can explore its features, create invoices, view the ledger, and test IRAS compliance tools – all locally.

If you encounter any problem not covered here, visit the [LedgerSG GitHub Issues page](https://github.com/nordeim/ledgersg/issues) and search for similar problems, or open a new issue with a description of what happened and the error messages you saw.

https://chat.deepseek.com/share/yo3tgii7o904z3y8ga
