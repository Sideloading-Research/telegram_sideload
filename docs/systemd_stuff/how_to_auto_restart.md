# Intro

This guide shows how to set up your Telegram Sideload bot to run automatically as a system service using systemd. Systemd ensures your bot starts automatically when the server boots, restarts if it crashes, and can be easily managed through standard system administration commands.

The setup process involves 4 main phases: preparing the system user, configuring the service, activating it, and verifying operation.

# Initial System Preparation

## Setting up the Service User

```bash
sudo useradd -m -s /bin/bash sideload
```

## Creating the Service Definition File

```bash
sudo nano /etc/systemd/system/telegram-sideload.service
```

# Service Configuration Setup

## Applying the Service Configuration

Copy the configuration content from [sample_systemd_file.txt](sample_systemd_file.txt) into the service file you just created.

## Log File Preparation

### Creating Application Log Files

```bash
sudo touch /var/log/telegram-sideload.log
sudo touch /var/log/telegram-sideload-error.log
```

### Configuring Log File Permissions

```bash
sudo chown sideload:sideload /var/log/telegram-sideload.log
sudo chown sideload:sideload /var/log/telegram-sideload-error.log
```

# Service Activation Process

## Systemd Configuration Update

```bash
sudo systemctl daemon-reload
```

## Configuring Automatic Startup

```bash
sudo systemctl enable telegram-sideload.service
```

## Launching the Service

```bash
sudo systemctl start telegram-sideload.service
```

## Initial Service Health Check

```bash
sudo systemctl status telegram-sideload.service
```

# Various maintainance commands

```bash
sudo systemctl stop telegram-sideload.service
```

```bash
sudo systemctl restart telegram-sideload.service
```


```bash
tail -f /var/log/telegram-sideload.log
tail -f /var/log/telegram-sideload-error.log
```

```bash
sudo journalctl -u telegram-sideload.service -n 20
```

```bash
sudo journalctl -u telegram-sideload.service -f
```

```bash
sudo nano /etc/systemd/system/telegram-sideload.service
```

```bash
sudo systemctl daemon-reload
sudo systemctl restart telegram-sideload.service
```