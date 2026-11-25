#!/usr/bin/env python3
"""Double-fork daemonizer — gives child processes tool-call survival
(the P13 environment lesson: pg_ctl/redis survive because they are true
daemons; a double-fork + setsid + exec gives runserver/next dev the same).
Usage: daemonize.py <name> <logfile> <cwd> <command...>
"""
import os
import sys

def main():
    name, logfile, cwd = sys.argv[1], sys.argv[2], sys.argv[3]
    cmd = sys.argv[4:]
    if os.fork() > 0:
        sys.exit(0)  # parent exits immediately
    os.setsid()
    if os.fork() > 0:
        sys.exit(0)  # session leader exits — reparented to init
    os.umask(0o022)
    os.chdir(cwd)
    fd = os.open(logfile, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    os.dup2(fd, 0); os.dup2(fd, 1); os.dup2(fd, 2)
    if fd > 2:
        os.close(fd)
    # write pid to a file so teardown can find it
    with open(f"/tmp/daemon-{name}.pid", "w") as f:
        f.write(str(os.getpid()))
    os.execvp(cmd[0], cmd)

if __name__ == "__main__":
    main()
