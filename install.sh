#!/usr/bin/env bash
set -e

echo -e "\033[0;36m⚡ Installing UniversalResume...\033[0m"

# Check for Python
if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
  echo -e "\033[0;31mError: Python 3.9+ is required but not found in PATH.\033[0m"
  exit 1
fi
PYTHON_CMD=$(command -v python3 || command -v python)

# Check or install Bun
if ! command -v bun &>/dev/null; then
  echo -e "\033[0;33mInstalling Bun...\033[0m"
  curl -fsSL https://bun.sh/install | bash
  export BUN_INSTALL="$HOME/.bun"
  export PATH="$BUN_INSTALL/bin:$PATH"
fi

# Target directory
TARGET_DIR="$HOME/.samethread-repo"
if [ -d "$TARGET_DIR" ]; then
  echo "Updating repository in $TARGET_DIR..."
  git -C "$TARGET_DIR" pull --quiet
else
  echo "Cloning repository to $TARGET_DIR..."
  git clone --quiet https://github.com/AliSharjeell/UniversalResume.git "$TARGET_DIR"
fi

cd "$TARGET_DIR"
echo "Setting up OpenTUI and agent hooks..."
bun install --silent
npm link --silent 2>/dev/null || true
$PYTHON_CMD -m pip install -e . --quiet

# Link binary to ~/.local/bin or /usr/local/bin
mkdir -p "$HOME/.local/bin"
ln -sf "$TARGET_DIR/bin/resume.js" "$HOME/.local/bin/resume"
chmod +x "$TARGET_DIR/bin/resume.js" "$HOME/.local/bin/resume"

# Run hop install and initial sync
hop install || true
hop sync || true

echo -e "\033[0;32m✨ UniversalResume installed successfully!\033[0m"
echo -e "\033[0;36mType 'resume' anywhere in your terminal to start.\033[0m"
