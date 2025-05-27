# ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
# ░░░░ЗАПУСКАЕМ░ГУСЕЙ-РАЗВЕДЧИКОВ░░░░
# ░░░░░▄▀▀▀▄░░░▄▀▀▀▀▄░░░▄▀▀▀▄░░░░░
# ▄███▀░◐░░░▌░▐0░░░░0▌░▐░░░◐░▀███▄
# ░░░░▌░░░░░▐░▌░▐▀▀▌░▐░▌░░░░░▐░░░░
# ░░░░▐░░░░░▐░▌░▌▒▒▐░▐░▌░░░░░▌░░░░
# ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░

# Check if migration directory exists, if not initialize it
if [ ! -d "migration" ]; then
    echo "Initializing Alembic migrations..."
    alembic init migration
    
    # Update env.py to import our models
    sed -i "s/target_metadata = None/from model import Base\ntarget_metadata = Base.metadata/" migration/env.py
fi

# Generate migration if needed
echo "Checking for new migrations..."
alembic revision --autogenerate -m "Auto-generated migration"

# Run migrations
echo "Running database migrations..."
alembic upgrade head

echo "Starting bot..."
python bot.py