#!/usr/bin/env bash
set -e

cat << 'EOF'
   __  __      _                             __   ____                                
  / / / /___  (_)   _____  ______________ _ / /  / __ \___  _______  ______ ___  ___ 
 / / / / __ \/ / | / / _ \/ ___/ ___/ __ `// /  / /_/ / _ \/ ___/ / / / __ `__ \/ _ \
/ /_/ / / / / /| |/ /  __/ /  (__  ) /_/ // /  / _, _/  __(__  ) /_/ / / / / / /  __/
\____/_/ /_/_/ |___/\___/_/  /____/\__,_//_/  /_/ |_|\___/____/\__,_/_/ /_/ /_/\___/ 
EOF

echo "Installing UniversalResume..."

# Check for Python
if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
  echo "Error: Python 3.9+ is required but not found in PATH."
  exit 1
fi
PYTHON_CMD=$(command -v python3 || command -v python)

# Check or install Bun
if ! command -v bun &>/dev/null; then
  echo "Installing Bun..."
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

echo -e "\n\033[0;32mUniversalResume installed successfully!\033[0m"
echo "Type 'resume' anywhere in your terminal to start."
