#!/usr/bin/env python3
import os
import sys
import paramiko
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file
# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
VM_HOST = os.getenv("REMOTE_HOST")
VM_USER = os.getenv("REMOTE_USER")
SSH_KEY_PATH = os.path.expanduser("~/.ssh/google_compute_engine")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")

TARGET_PROMPT = """ claude --dangerously-skip-permissions -p 'Perform the following setup non-interactively:
1. Install git if not already present.
2. Export PATH="\$HOME/.local/bin:\$PATH\".
3. Use uv to download and install Python 3.12 by running: uv python install 3.12.
4. Verify and print the versions of git and python (via python --version).'
"""


def run_ssh_command(ssh_client, command: str, stream_output: bool = True):
    """Executes a command over SSH and streams standard output and error."""
    print(f"\n[RUNNING]: {command}")
    stdin, stdout, stderr = ssh_client.exec_command(command, get_pty=True)

    if stream_output:
        for line in iter(stdout.readline, ""):
            print(line, end="")

    exit_status = stdout.channel.recv_exit_status()
    if exit_status != 0:
        err = stderr.read().decode()
        print(f"[ERROR] Exit code {exit_status}: {err}")
        return False
    return True


def main():
    if not os.path.exists(SSH_KEY_PATH):
        print(f"[FATAL] Private key not found at {SSH_KEY_PATH}")
        sys.exit(1)

    print(f"Connecting to {VM_USER}@{VM_HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(
            hostname=VM_HOST,
            username=VM_USER,
            key_filename=SSH_KEY_PATH,
            timeout=30,
        )
        print("Connected successfully.")

        # Step 1: Run Claude Code headlessly to install target software
        # Using export ANTHROPIC_API_KEY in the subshell and invoking claude in non-interactive print mode (-p)
        claude_run_cmd = (
            f'export ANTHROPIC_API_KEY="{ANTHROPIC_KEY}" && '
            # f'claude -p "{TARGET_PROMPT}"'
            f'{TARGET_PROMPT}'
        )
        if not run_ssh_command(ssh, claude_run_cmd):
            raise RuntimeError("Claude Code encountered an issue during software setup.")

        # Step 2: Final verification check
        verify_cmd = "python3 --version && git --version"
        run_ssh_command(ssh, verify_cmd)

        print("\n[SUCCESS] Setup and installation completed successfully via Claude Code.")

    except Exception as e:
        print(f"\n[FATAL] Pipeline failed: {str(e)}")
        sys.exit(1)
    finally:
        ssh.close()


if __name__ == "__main__":
    main()
