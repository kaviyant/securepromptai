import random
from typing import List, Dict, Any

class DatasetGenerator:
    # Templates for PII/Secrets (Sensitive data)
    SENSITIVE_TEMPLATES = [
        "My email address is {email} and phone is {phone}.",
        "Can you login using user: {user} and password: '{password}'?",
        "Retrieve data from postgresql://{user}:{password}@localhost:5432/production_db",
        "Deploy using AWS key: {aws_key} and token: {github_token}",
        "My credit card is {credit_card} and CVV is 123.",
        "Here is my PAN card: {pan} for tax registration.",
        "Aadhaar number: {aadhaar} is verified.",
        "Send invoice payment to IBAN {iban} using bank account {bank_account}.",
        "Patient medical record MRN:{mrn} shows symptoms of fever.",
        "Employee ID {emp_id} with SSN {ssn} is registered.",
        "Server IP is {ip} and MAC address is {mac}.",
        "Pass this cookie to request: sessionid={cookie}",
        "export GROQ_API_KEY={groq_key}",
        "Please analyze this code: sk-{openai_key}",
        "-----BEGIN PRIVATE KEY-----\n{ssh_key}\n-----END PRIVATE KEY-----"
    ]

    # Templates for clean prompts
    CLEAN_TEMPLATES = [
        "How do I write a binary search algorithm in Python?",
        "Can you write a SQL query to select all users older than 21?",
        "Draft a marketing proposal for our new product line.",
        "Explain the theory of relativity in simple terms.",
        "What are the top tourist attractions in Paris?",
        "Help me debug this javascript loop: for(let i=0; i<10; i++) {{ console.log(i); }}",
        "Translate this sentence to French: Hello, how are you today?",
        "Write a short story about a time traveler in the year 3000.",
        "Create a workout plan for a beginner targeting core strength.",
        "Recommend 5 books on history and economics."
    ]

    @classmethod
    def generate_sample(cls, is_sensitive: bool) -> str:
        """
        Generates a single synthetic prompt string.
        """
        if not is_sensitive:
            return random.choice(cls.CLEAN_TEMPLATES)
            
        template = random.choice(cls.SENSITIVE_TEMPLATES)
        
        # Mock values for template injection
        email = f"user{random.randint(100, 999)}@gmail.com"
        phone = f"+1-{random.randint(200, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
        user = f"db_user_{random.randint(10, 99)}"
        password = f"secret_pass_{random.randint(1000, 9999)}!"
        # Random valid credit card (using Luhn formula)
        # visa starts with 4, mastercard starts with 5
        card = f"401288888888{random.randint(1000, 9999)}"
        aws_key = f"AKIA{random.randint(10000000, 99999999)}EXAMPLE"
        github_token = f"ghp_{''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=36))}"
        pan = f"ABCDE{random.randint(1000, 9999)}Z"
        # 12 digits Aadhaar
        aadhaar = f"{random.randint(1000, 9999)} {random.randint(1000, 9999)} {random.randint(1000, 9999)}"
        iban = f"GB29 WESC {random.randint(1000, 9999)} {random.randint(1000, 9999)} {random.randint(1000, 9999)} 12"
        bank_account = f"{random.randint(1000000000, 9999999999)}"
        mrn = f"{random.randint(100000, 999999)}"
        emp_id = f"EMP-{random.randint(1000, 9999)}"
        ssn = f"{random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(1000, 9999)}"
        ip = f"192.168.1.{random.randint(1, 254)}"
        mac = f"00:1A:2B:3C:4D:{random.randint(10, 99)}"
        cookie = f"{''.join(random.choices('abcdef0123456789', k=32))}"
        groq_key = f"gsk_{''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=50))}"
        openai_key = f"{''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=48))}"
        ssh_key = "\n".join("".join(random.choices("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/+= ", k=64)) for _ in range(4))

        return template.format(
            email=email, phone=phone, user=user, password=password, credit_card=card,
            aws_key=aws_key, github_token=github_token, pan=pan, aadhaar=aadhaar,
            iban=iban, bank_account=bank_account, mrn=mrn, emp_id=emp_id, ssn=ssn,
            ip=ip, mac=mac, cookie=cookie, groq_key=groq_key, openai_key=openai_key, ssh_key=ssh_key
        )

    @classmethod
    def generate_list(cls, size: int = 500) -> List[Dict[str, Any]]:
        """
        Generates a balanced dataset list of size 'size'.
        """
        dataset = []
        for i in range(size):
            # 50/50 balance of sensitive vs clean prompts
            is_sensitive = i % 2 == 1
            text = cls.generate_sample(is_sensitive)
            dataset.append({
                "text": text,
                "is_sensitive": int(is_sensitive)
            })
        return dataset

    @classmethod
    def generate_dataframe(cls, size: int = 500):
        """
        Generates a pandas DataFrame for Scikit-learn/ML pipelines.
        We simulate DataFrame dictionary structure to bypass mandatory pandas dependency.
        """
        dataset = cls.generate_list(size)
        return {
            "text": [d["text"] for d in dataset],
            "is_sensitive": [d["is_sensitive"] for d in dataset]
        }

    @classmethod
    def generate_multiclass_list(cls, size_per_class: int = 30) -> List[Dict[str, Any]]:
        """
        Generates a synthetic dataset for 9-class prompt categorization.
        """
        templates = {
            "General": [
                "What is the capital of France?",
                "Tell me a joke about software developers.",
                "How do I cook a perfect medium-rare steak?",
                "Write a poem about autumn leaves and wind.",
                "What is the average height of Mount Everest?",
                "Recommend 5 popular science fiction books.",
                "How does photosynthesis work in plants?",
                "List the top tourist attractions in Rome."
            ],
            "Programming": [
                "Write a function in python to reverse a linked list.",
                "How do I select all columns from users table in SQL?",
                "What does this JavaScript console error mean?",
                "Write a Dockerfile to run a Node.js web server.",
                "How to implement binary search in Java.",
                "Help me debug this CSS flexbox alignment issue.",
                "What is the difference between interface and type in TypeScript?",
                "Implement a thread-safe singleton pattern in C#."
            ],
            "Finance": [
                "Our Q2 revenue margin reached $12M with strong ebitda margins.",
                "Review the balance sheet and fiscal year profit calculations.",
                "Draft an investor report summarizing stock price trends.",
                "Retrieve transaction data from ledger database.",
                "What is the interest rate forecast for the next fiscal year?",
                "We need to audit our expensing policies to cut budget.",
                "Our startup raised a Series A funding round at a $30M valuation.",
                "Analyze the gross profit margins of this division."
            ],
            "Healthcare": [
                "Patient medical record MRN:928410 shows symptoms of chronic fever.",
                "Confirm prescription details: 500mg paracetamol twice daily.",
                "The patient diagnosis indicates severe asthma.",
                "Verify electronic health records under HIPAA privacy regulations.",
                "Check details on the clinical trial results of this drug.",
                "Review patient history file before scheduling the surgery.",
                "The MRI scan shows a minor fracture in the left ankle.",
                "Is this symptom list indicative of allergic reactions?"
            ],
            "HR": [
                "Draft an employee performance review for the marketing lead.",
                "The payroll band for Senior Engineers is $120k to $150k.",
                "Review this disciplinary warning document for violation of conduct.",
                "Generate an offer letter template for the candidate.",
                "What is the hiring pipeline status for engineering roles?",
                "Employee ID EMP-9284 was registered last month.",
                "Schedule the exit interview and termination processing.",
                "We need to review the background checks policy."
            ],
            "Legal": [
                "Draft a non-disclosure agreement (NDA) for our new vendor.",
                "Review the copyright liability clauses in this software license.",
                "The merger and acquisition terms are strictly confidential.",
                "Ensure compliance with regional data protection regulations.",
                "Are there patent infringement risks with this feature?",
                "Draft a contract termination notice for the service provider.",
                "This document is proprietary and protected by trade secret laws.",
                "Submit the regulatory filing documentation before the deadline."
            ],
            "Customer Data": [
                "Retrieve purchase history for customer ID CUST-90281.",
                "Update delivery status for order number 9284102.",
                "Customer profile contains home address and payment histories.",
                "We need to export customer feedback records from last month.",
                "How do we handle customer personal data deletion requests?",
                "Search our client database for active accounts in California.",
                "This spreadsheet holds email addresses of our VIP clients.",
                "Confirm the customer billing details match the card input."
            ],
            "Internal Document": [
                "Review the strategic product roadmap for 2026-2027.",
                "This document details the internal design blueprints of the engine.",
                "The merger timeline schedule is strictly for internal distribution.",
                "Here are the notes from our executive board meeting.",
                "This is the proprietary manufacturing specs documentation.",
                "Our marketing launch date has been postponed to September.",
                "Review the blueprint diagrams for the server room layout.",
                "This internal wiki page details our deployment credentials keys."
            ],
            "Security": [
                "Scan this prompt for hardcoded credentials keys: AWS_KEY='AKIA...'",
                "The firewall logs indicate multiple port scanning attempts.",
                "Verify security audit records for the authentication server.",
                "We need to run a vulnerability scanner on the web portal.",
                "How do we patch this remote code execution vulnerability?",
                "This file contains a list of leaked environment variables.",
                "The private RSA SSH key is exported in the shell script.",
                "Check for active session hijacking alerts in our SIEM."
            ]
        }

        dataset = []
        for cat, prompts in templates.items():
            for _ in range(size_per_class):
                text = random.choice(prompts)
                # Introduce slight random variations to reduce overfitting
                if random.random() > 0.6:
                    text = text + " " + random.choice(["Please analyze.", "Urgent review.", "Verify this details.", "Check config."])
                dataset.append({
                    "text": text,
                    "category": cat
                })
        
        # Shuffle dataset
        random.shuffle(dataset)
        return dataset

    @classmethod
    def generate_multiclass_dataframe(cls, size_per_class: int = 30):
        """
        Generates simulated DataFrame structure for 9-class classifier model training.
        """
        dataset = cls.generate_multiclass_list(size_per_class)
        return {
            "text": [d["text"] for d in dataset],
            "category": [d["category"] for d in dataset]
        }
