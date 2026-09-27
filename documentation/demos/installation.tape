Output installation.gif

Set Shell "bash"
Set Theme "Catppuccin Mocha"
Set Width 1200
Set Height 650
Set FontSize 22
Set Padding 20
Set Margin 20
Set WindowBar Colorful
Set BorderRadius 12
Set TypingSpeed 45ms

Hide
Type `export PS1='\W> '`
Enter
Type `git() { if [ "$1" = "clone" ]; then mkdir -p stock-price/backend stock-price/frontend; touch stock-price/backend/requirements.txt stock-price/frontend/package.json; else command git "$@"; fi; }`
Enter
Type `python3() { if [ "$1" = "-m" ] && [ "$2" = "venv" ]; then mkdir -p "$3/bin"; printf '#!/bin/bash\nPS1="(venv) \\W> "\n' > "$3/bin/activate"; else command python3 "$@"; fi; }`
Enter
Type `pip() { if [ "$1" = "install" ]; then return 0; else command pip "$@"; fi; }`
Enter
Type `npm() { if [ "$1" = "install" ]; then return 0; else command npm "$@"; fi; }`
Enter
Type "clear"
Enter
Show

Type "git clone https://github.com/ankit02327/stock-price.git"
Enter
Sleep 500ms

Type "cd stock-price"
Enter
Sleep 300ms

Type "cd backend"
Enter
Sleep 300ms

Type "python3 -m venv venv"
Enter
Sleep 300ms

Type "source venv/bin/activate"
Enter
Sleep 300ms

Type "pip install -r requirements.txt"
Enter
Sleep 500ms

Type "touch .env"
Enter
Sleep 300ms

Type "cd ../frontend"
Enter
Sleep 300ms

Type "npm install"
Enter
Sleep 500ms

Type "echo Stock Price Prediction System is ready"
Enter
Sleep 2s
