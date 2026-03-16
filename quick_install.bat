@echo off
echo ========================================
echo HPCL Lead Intelligence - Quick Install
echo ========================================
echo.

echo Step 1: Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
echo ✓ Virtual environment activated
echo.

echo Step 2: Upgrading pip...
python -m pip install --upgrade pip
echo ✓ Pip upgraded
echo.

echo Step 3: Installing core dependencies (this may take a few minutes)...
pip install fastapi uvicorn[standard] pydantic pydantic-settings
echo ✓ Web framework installed
echo.

echo Step 4: Installing database dependencies...
pip install sqlalchemy psycopg alembic
echo ✓ Database libraries installed
echo.

echo Step 5: Installing AI/ML dependencies...
pip install google-generativeai sentence-transformers
echo ✓ AI/ML libraries installed
echo.

echo Step 6: Installing vector database...
pip install pinecone
echo ✓ Pinecone installed
echo.

echo Step 7: Installing testing frameworks...
pip install pytest pytest-cov hypothesis
echo ✓ Testing frameworks installed
echo.

echo Step 8: Installing utilities...
pip install requests feedparser beautifulsoup4 lxml python-dotenv
echo ✓ Utilities installed
echo.

echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Verify .env file has your API keys
echo 2. Start PostgreSQL database
echo 3. Run: python scripts\init_db.py
echo 4. Run: uvicorn app.main:app --reload
echo.
pause
