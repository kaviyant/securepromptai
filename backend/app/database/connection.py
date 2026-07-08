import logging
from motor.motor_asyncio import AsyncIOMotorClient
from app.config.settings import settings

logger = logging.getLogger("secureprompt")

class Database:
    client: AsyncIOMotorClient = None
    db = None

db = Database()

async def connect_to_mongo():
    """
    Establishes connection to MongoDB and creates default collections/indices
    across all 9 required tables.
    """
    logger.info(f"Connecting to MongoDB at {settings.MONGODB_URL}...")
    db.client = AsyncIOMotorClient(settings.MONGODB_URL)
    db.db = db.client[settings.DATABASE_NAME]
    logger.info("Connected to MongoDB successfully.")
    
    # Bootstrap MongoDB indices for efficient lookups across all 9 tables
    try:
        # 1. Users Collection
        await db.db.users.create_index("email", unique=True)
        await db.db.users.create_index("username", unique=True)
        
        # 2. Departments Collection
        await db.db.departments.create_index("name", unique=True)
        
        # 3. Prompts Collection
        await db.db.prompts.create_index("timestamp")
        await db.db.prompts.create_index("user_email")
        await db.db.prompts.create_index([("prompt_text", "text")])
        
        # 4. Logs Collection
        await db.db.logs.create_index("timestamp")
        await db.db.logs.create_index("level")
        
        # 5. Alerts Collection
        await db.db.alerts.create_index("timestamp")
        await db.db.alerts.create_index("severity")
        await db.db.alerts.create_index("user_email")
        
        # 6. History Collection
        await db.db.history.create_index("timestamp")
        await db.db.history.create_index("user_email")
        
        # 7. Policies Collection
        await db.db.policies.create_index("name", unique=True)
        
        # 8. Predictions Collection
        await db.db.predictions.create_index("timestamp")
        await db.db.predictions.create_index("category")
        
        # 9. Settings Collection
        await db.db.settings.create_index("key", unique=True)
        
        logger.info("Synchronized database indexes successfully for all 9 collections.")
        
        # Auto bootstrap default admin and seed databases
        await seed_departments()
        await bootstrap_admin()
        
    except Exception as e:
        logger.error(f"Error initializing indexes or bootstrapping database: {e}")

async def close_mongo_connection():
    """
    Closes the connection to MongoDB.
    """
    if db.client:
        logger.info("Closing MongoDB connection...")
        db.client.close()
        logger.info("MongoDB connection closed.")

def get_database():
    """
    Dependency injection helper to return database instance.
    """
    return db.db

async def seed_departments():
    """
    Seeds default corporate departments in the database.
    """
    dept_count = await db.db.departments.count_documents({})
    if dept_count == 0:
        default_depts = [
            {"name": "Engineering", "description": "Core software and systems engineering team"},
            {"name": "Finance", "description": "Accounting and strategic investments division"},
            {"name": "HR", "description": "Human Resources and recruitment operations"},
            {"name": "Legal", "description": "Compliance, copyrights, and NDAs oversight team"},
            {"name": "Marketing", "description": "Brand promotion and product campaigns division"},
            {"name": "Security Operations", "description": "Cybersecurity compliance and firewall operations"}
        ]
        await db.db.departments.insert_many(default_depts)
        logger.info("Default corporate departments seeded successfully.")

async def bootstrap_admin():
    """
    Seeds the initial admin account using settings if users collection is empty.
    """
    from app.utils.security import get_password_hash
    
    admin_exists = await db.db.users.find_one({"role": "Admin"})
    if not admin_exists:
        logger.info("No Admin account detected. Bootstrapping default administrator user...")
        hashed_password = get_password_hash(settings.SYSTEM_INIT_ADMIN_PASSWORD)
        
        admin_doc = {
            "username": "admin",
            "email": settings.SYSTEM_INIT_ADMIN_EMAIL,
            "hashed_password": hashed_password,
            "role": "Admin",
            "department": "Security Operations",
            "is_active": True
        }
        
        await db.db.users.insert_one(admin_doc)
        logger.info(f"Admin account bootstrapped: {settings.SYSTEM_INIT_ADMIN_EMAIL}")
        
        # Seed default policies and settings
        await seed_default_policies()
        await seed_default_settings()

async def seed_default_policies():
    """
    Seeds default security policies if collection is empty.
    """
    policy_count = await db.db.policies.count_documents({})
    if policy_count == 0:
        default_policies = [
            {
                "name": "PII Protection Policy",
                "description": "Flags Social Security Numbers, emails, phone numbers, and IP addresses.",
                "sensitivity": 50,
                "is_active": True
            },
            {
                "name": "Credential Leakage Policy",
                "description": "Blocks credentials like AWS keys, private SSH keys, Slack webhooks, and raw password tokens.",
                "sensitivity": 60,
                "is_active": True
            },
            {
                "name": "Financial Data Policy",
                "description": "Identifies credit cards and bank routing account combinations.",
                "sensitivity": 40,
                "is_active": True
            }
        ]
        await db.db.policies.insert_many(default_policies)
        logger.info("Default security policies seeded successfully.")

async def seed_default_settings():
    """
    Seeds default system firewall settings if collection is empty.
    """
    settings_count = await db.db.settings.count_documents({})
    if settings_count == 0:
        default_settings = [
            {"key": "firewall_mode", "value": "ENFORCE", "description": "Firewall enforcement mode: ENFORCE, MONITOR, BYPASS"},
            {"key": "auto_sanitize", "value": True, "description": "Automatically redact PII elements from outbound prompts"},
            {"key": "risk_threshold", "value": 70, "description": "Blocked action risk threshold limit (0-100)"}
        ]
        await db.db.settings.insert_many(default_settings)
        logger.info("Default system settings seeded successfully.")
