#!/usr/bin/env bash
# apt-get install for CI runners, resilient to mirror problems.
# GitHub's Ubuntu runners download from an Azure-hosted mirror; when that mirror's hostname
# doesn't resolve, every download fails. This retries, and after the first failure switches
# apt to Ubuntu's own servers (archive.ubuntu.com / security.ubuntu.com).
# Usage: ci_apt_install.sh <package>...
set -uo pipefail

use_ubuntu_mirrors() {
  echo "Switching apt to archive.ubuntu.com"
  for f in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do
    [ -f "$f" ] || continue
    sudo sed -i \
      -e 's#mirror+file:/etc/apt/apt-mirrors.txt#http://archive.ubuntu.com/ubuntu/#g' \
      -e 's#https\?://azure\.archive\.ubuntu\.com/ubuntu/\?#http://archive.ubuntu.com/ubuntu/#g' \
      "$f"
  done
}

echo 'Acquire::Retries "5";' | sudo tee /etc/apt/apt.conf.d/80-retries >/dev/null

for attempt in 1 2 3 4; do
  if sudo apt-get update && sudo apt-get install -y --no-install-recommends "$@"; then
    exit 0
  fi
  echo "apt attempt $attempt failed"
  [ "$attempt" -eq 1 ] && use_ubuntu_mirrors
  sleep $((attempt * 15))
done
echo "apt-get install failed after 4 attempts" >&2
exit 1
