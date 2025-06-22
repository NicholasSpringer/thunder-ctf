#!/bin/bash
set -e

LEVEL=$1

# Helper functions
print() { echo -e "\033[1;32m$1\033[0m"; }
warn()  { echo -e "\033[1;33m$1\033[0m"; }
error() { echo -e "\033[1;31m$1\033[0m"; }

if [ -z "$LEVEL" ]; then
  error "❌ Usage: ./run-level.sh <level_module_name>"
  echo "Example: ./run-level.sh a1openbucket"
  exit 1
fi

print "🚀 Deploying level: $LEVEL"
terraform apply -target=module.${LEVEL} -auto-approve > /dev/null

# Write active level tracker
mkdir -p config

# # Run post-provision Python script, if applicable
# PROVISION_SCRIPT="modules/${LEVEL}/${LEVEL}_provision.py"
# if [ -f "$PROVISION_SCRIPT" ]; then
#   print "⚙️  Running post-provision script for $LEVEL..."
#   python3 "$PROVISION_SCRIPT"
# fi

echo
print "✅ Level deployed!"

echo
print "📜 Level Instructions:"
INSTRUCTION_FILE="instructions/${LEVEL}.txt"
if [ -f "$INSTRUCTION_FILE" ]; then
  cat "$INSTRUCTION_FILE"
else
  warn "⚠️ No instructions found for $LEVEL."
fi
