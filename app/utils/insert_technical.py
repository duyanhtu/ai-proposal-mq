import datetime
import json
 
from app.storage.postgre import executeSQL
 
# The DB_PARAMS and connect_to_db() are no longer needed as we'll use postgre.py
 
def generate_fixed_proposal_id():
    """Generate a fixed proposal ID based on current datetime in format ddMMyyyyHHmmss"""
    now = datetime.datetime.now()
    datetime_str = now.strftime("%d%m%Y%H%M%S")
 
    # Since proposal_id is smallint in the database (max 32767),
    # we'll use the last 5 digits of the timestamp as integer
    short_id = int(datetime_str[-5:]) % 32767
    print(
        f"Generated fixed proposal_id: {short_id} (from datetime: {datetime_str})")
    return short_id
 
 
def insert_requirement(requirement_name, proposal_id, id_original=None):
    """Insert a requirement into technical_requirement table and return its ID"""
    try:
        query = """
            INSERT INTO technical_requirement
            (proposal_id, requirements, id_original)
            VALUES (%s, %s, %s)
            RETURNING id
        """
        params = (proposal_id, requirement_name, id_original)
        requirement_id = executeSQL(query, params)
        return requirement_id
    except Exception as e:
        print(f"Error inserting requirement: {e}")
        raise
 
 
def insert_detail_requirement(requirement_id, description):
    """Insert a description into technical_detail_requirement table"""
    try:
        query = """
            INSERT INTO technical_detail_requirement
            (requirement_id, description)
            VALUES (%s, %s)
        """
        params = (str(requirement_id), description)
        executeSQL(query, params)
    except Exception as e:
        print(f"Error inserting detail requirement: {e}")
        raise
 
 
def process_requirement(requirement, level, proposal_id, parent_id=None):
    """Process a requirement at any level and its sub-requirements or descriptions"""
    requirement_key = f"requirement_level_{level}"
 
    if requirement_key in requirement:
        req_data = requirement[requirement_key]
        requirement_name = req_data.get("requirement_name")
        muc = req_data.get("muc")
 
        # Format combined requirement text
        if muc is not None:
            concat = f"{muc} {requirement_name}"
        else:
            concat = requirement_name
 
        # Insert the requirement with the fixed proposal_id
        requirement_id = insert_requirement(concat, proposal_id, parent_id)
        print(f"Inserted level {level} requirement: '{concat}' with ID: {requirement_id}" +
              (f" (parent ID: {parent_id})" if parent_id else ""))
 
        # Process descriptions if available
        if "description" in req_data:
            for desc_item in req_data["description"]:
                if "description_detail" in desc_item:
                    description = desc_item["description_detail"]
                    insert_detail_requirement(requirement_id, description)
                    print(f"  - Added description: {description[:50]}...")
 
        # Process sub-requirements recursively, passing the same fixed proposal_id
        if "sub_requirements" in req_data:
            for sub_req in req_data["sub_requirements"]:
                process_requirement(sub_req, level + 1,
                                    proposal_id, requirement_id)
    else:
        # Handle requirements at higher levels
        for key in requirement:
            if key.startswith("requirement_level_"):
                level_num = int(key.split("_")[-1])
                process_requirement(
                    {key: requirement[key]}, level_num, proposal_id, parent_id)
 
 
def insert_technical(data, proposal_id):
    # Load JSON data
    try:
        """ with open('result.json', 'r', encoding='utf-8') as file:
            data = json.load(file) """
 
        try:
            # Insert to technical requirement json
            r = json.dumps(data)
            #loaded_r = json.loads(r)
            executeSQL("INSERT INTO technical_requirement_json (proposal_id,requirement_json) VALUES (%s,%s)",(proposal_id,r))
            
            # Process the root requirement with the fixed proposal_id
            for key, value in data.items():
                if key.startswith("requirement_level_"):
                    level_num = int(key.split("_")[-1])
                    process_requirement(
                        {key: value}, level_num, proposal_id)
            print("All requirements inserted successfully.")

        except Exception as e:
            print(f"Error processing requirements: {e}")
    except FileNotFoundError:
        print("Error: result.json file not found")
    except json.JSONDecodeError:
        print("Error: Invalid JSON format in result.json")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")