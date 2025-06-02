#!/bin/bash
set -e

# Helper functions
print() { echo -e "\033[1;32m$1\033[0m"; }
warn()  { echo -e "\033[1;33m$1\033[0m"; }
error() { echo -e "\033[1;31m$1\033[0m"; }

# Determine level
if [ -n "$1" ]; then
  LEVEL="$1"
  CONFIG_FILE="config/${LEVEL}_active.txt"
else
  # Auto-discover active level file
  ACTIVE_FILES=(config/*_active.txt)
  if [ ${#ACTIVE_FILES[@]} -eq 0 ]; then
    error "❌ No active level tracking files found in config/"
    exit 1
  elif [ ${#ACTIVE_FILES[@]} -gt 1 ]; then
    error "❌ Multiple active level files found. Please specify the level explicitly:"
    for f in "${ACTIVE_FILES[@]}"; do
      echo " - ${f#config/}" | sed 's/_active\.txt$//'
    done
    exit 1
  fi
  CONFIG_FILE="${ACTIVE_FILES[0]}"
  LEVEL=$(basename "$CONFIG_FILE" | sed 's/_active\.txt$//')
fi

# Verify file exists
if [ ! -f "$CONFIG_FILE" ]; then
  error "❌ Active file not found: $CONFIG_FILE"
  exit 1
fi

# Check Terraform state
if ! terraform state list | grep -q "module.${LEVEL}"; then
  warn "⚠️ Terraform state does not contain module '${LEVEL}'. Skipping destroy."
  exit 1
fi

# Confirm
read -p "🔥 Destroy the running instance of '$LEVEL'? [y/N]: " confirm
if [[ ! $confirm =~ ^[yY]$ ]]; then
  warn "⚠️ Destruction cancelled."
  exit 0
fi

# Destroy
print "🧨 Destroying module: $LEVEL"
if ! terraform destroy -target="module.${LEVEL}" -auto-approve > destroy.log 2>&1; then
  error "❌ Terraform destroy failed. Last 20 log lines:"
  tail -n 20 destroy.log
  exit 1
fi

# Clean up start directory if it matches this level
LEVEL_FILE="start/${LEVEL}.txt"
if [ -d "start" ]; then
  chmod -R u+w start/ 2>/dev/null || true  # ensure we can delete files even if locked
  rm -rf start
  print "🗑 Removed 'start/' directory"
fi

# Remove tracker
rm -f "$CONFIG_FILE"
print "🗑 Removed $CONFIG_FILE"

print "✅ Level '${LEVEL}' has been destroyed successfully."
