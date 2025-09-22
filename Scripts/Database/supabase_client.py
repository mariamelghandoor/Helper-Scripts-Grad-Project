from supabase import create_client
import os
from dotenv import load_dotenv
import json
from pathlib import Path

load_dotenv()

# Initialize Supabase client
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

def transform_data_for_db(data):
    """Transform data keys to match database column names"""
    key_mapping = {
        'Link': 'link',
        'Domain': 'domain',
        'Sub_domain': 'sub_domain',
        'Idea': 'idea',
        'Description': 'description',
        'success_or_fail': 'success_or_fail',
        'Reason': 'reason',
        'Takeaway': 'takeaway',
        'Region': 'region',
        'Tags': 'tags'
    }
    
    return {key_mapping.get(k, k.lower()): v for k, v in data.items()}

def insert_startup_data(data):
    """
    Insert single startup data into Supabase
    
    Args:
        data (dict): Startup data matching the schema
    """
    try:
        # Transform the data to match database column names
        transformed_data = transform_data_for_db(data)
        result = supabase.table('startups').insert(transformed_data).execute()
        print(f"✅ Successfully inserted startup data")
        return result.data
    except Exception as e:
        print(f"❌ Error inserting data: {e}")
        return None

def bulk_insert_from_json(json_file_path):
    """Insert multiple startup records from a JSON file"""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            print("❌ JSON file must contain an array of startup objects")
            return False
            
        results = []
        for item in data:
            result = insert_startup_data(item)
            if result:
                results.append(result)
                
        print(f"✅ Successfully inserted {len(results)} records")
        return True
    except Exception as e:
        print(f"❌ Error processing JSON file: {e}")
        return False

def get_startups(filters=None):
    """
    Retrieve startups with optional filters
    
    Example filters:
    {
        'success_or_fail': 'fail',
        'domain': 'tech'
    }
    """
    try:
        query = supabase.table('startups').select('*')
        
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)
                
        result = query.execute()
        return result.data
    except Exception as e:
        print(f"❌ Error retrieving data: {e}")
        return None

def get_startup_by_id(startup_id):
    """Retrieve a specific startup by ID"""
    try:
        result = supabase.table('startups').select("*").eq('id', startup_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Error retrieving startup: {e}")
        return None

def get_startup_by_domain(domain):
    """
    Retrieve startup data by domain
    
    Args:
        domain (str): Domain name to search for
    """
    try:
        result = supabase.table('startups').select("*").eq('domain', domain).execute()
        return result.data
    except Exception as e:
        print(f"❌ Error retrieving data: {e}")
        return None
