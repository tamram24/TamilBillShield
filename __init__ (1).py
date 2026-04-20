# Environment
.env
*.env

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
dist/
*.egg-info/
.eggs/

# Virtual environments
venv/
env/
.venv/

# ChromaDB local data
.chroma_db/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Streamlit
.streamlit/secrets.toml

# Test outputs
tests/output/

# Uploaded documents (never commit patient data)
uploads/
*.pdf
*.jpg
*.jpeg
*.png
!data/*.json
