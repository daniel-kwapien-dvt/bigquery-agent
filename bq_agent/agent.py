import os
import datetime
from decimal import Decimal
from dotenv import load_dotenv
from google.cloud import bigquery
from google.adk.agents import Agent
import vertexai
from vertexai.preview import reasoning_engines
from vertexai import agent_engines # Updated import

# Load environment variables from .env file
load_dotenv()

# Default BigQuery Project and Dataset IDs loaded from environment variables
DEFAULT_PROJECT_ID = os.getenv("DEFAULT_PROJECT_ID")
DEFAULT_DATASET_ID = os.getenv("DEFAULT_DATASET_ID")

if not DEFAULT_PROJECT_ID or not DEFAULT_DATASET_ID:
    raise ValueError(
        "DEFAULT_PROJECT_ID and DEFAULT_DATASET_ID must be set in the .env file or environment."
    )

# It's good practice to define the ADK tools as functions.
# These functions will be registered with the ADK agent.

def list_dataset_tables() -> list[str]:
    """
    Lists all tables within the default BigQuery project and dataset.
    The default project and dataset are determined by DEFAULT_PROJECT_ID
    and DEFAULT_DATASET_ID environment variables.

    Returns:
        A list of table ID strings.
        Returns an empty list if an error occurs or no tables are found.
    """
    try:
        client = bigquery.Client(project=DEFAULT_PROJECT_ID)
        dataset_ref = client.dataset(DEFAULT_DATASET_ID)
        tables = client.list_tables(dataset_ref)
        table_ids = [table.table_id for table in tables]
        if not table_ids:
            print(f"No tables found in dataset {DEFAULT_PROJECT_ID}.{DEFAULT_DATASET_ID}.")
            return []
        return table_ids
    except Exception as e:
        print(f"Error listing tables for {DEFAULT_PROJECT_ID}.{DEFAULT_DATASET_ID}: {e}")
        return []

def get_bigquery_table_schema(table_id: str) -> list[dict]:
    """
    Retrieves the schema of a specific table in the default BigQuery project and dataset.
    The default project and dataset are determined by DEFAULT_PROJECT_ID
    and DEFAULT_DATASET_ID environment variables.

    Args:
        table_id: The BigQuery table ID.

    Returns:
        A list of dictionaries, where each dictionary represents a field
        in the table schema (e.g., {'name': field.name, 'type': field.field_type, 'mode': field.mode}).
        Returns an empty list if an error occurs.
    """
    try:
        client = bigquery.Client(project=DEFAULT_PROJECT_ID)
        table_ref = client.dataset(DEFAULT_DATASET_ID).table(table_id)
        table = client.get_table(table_ref)
        schema_info = []
        for field in table.schema:
            schema_info.append({
                "name": field.name,
                "type": field.field_type,
                "mode": field.mode
            })
        if not schema_info:
            print(f"Schema not found or empty for table {DEFAULT_PROJECT_ID}.{DEFAULT_DATASET_ID}.{table_id}.")
            return []
        return schema_info
    except Exception as e:
        print(f"Error getting schema for {DEFAULT_PROJECT_ID}.{DEFAULT_DATASET_ID}.{table_id}: {e}")
        return []

def run_bigquery_sql_query(query: str) -> list[dict]:
    """
    Executes a given SQL query against BigQuery using the default project ID for billing.
    The default project is determined by the DEFAULT_PROJECT_ID environment variable.

    Args:
        query: The SQL query string to execute.

    Returns:
        A list of dictionaries, where each dictionary represents a row
        from the query result. Returns an empty list if an error occurs or
        the query returns no results.
    """
    try:
        client = bigquery.Client(project=DEFAULT_PROJECT_ID)
        query_job = client.query(query)  # API request
        results = query_job.result()  # Waits for the job to complete.

        # Process rows to ensure all data is JSON serializable
        processed_rows = []
        for row in results:
            processed_row = {}
            for key, value in row.items():
                if isinstance(value, (datetime.date, datetime.datetime)):
                    processed_row[key] = value.isoformat()
                elif isinstance(value, Decimal):
                    processed_row[key] = str(value) # Convert Decimal to string
                else:
                    processed_row[key] = value
            processed_rows.append(processed_row)
        
        if not processed_rows:
            print(f"Query returned no results: {query}")
            return []
        return processed_rows
    except Exception as e:
        print(f"Error running query '{query}': {e}")
        return []

def insert_bigquery_rows(table_id: str, rows: list[dict]) -> str:
    """
    Inserts one or more rows into a specific table in the default BigQuery project and dataset.
    The default project and dataset are determined by DEFAULT_PROJECT_ID
    and DEFAULT_DATASET_ID environment variables.

    Args:
        table_id: The BigQuery table ID (short name, not fully qualified).
        rows: A list of dictionaries, where each dictionary represents a row to be inserted.
              Keys in the dictionary should correspond to column names in the table.
              Example: [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 24}]

    Returns:
        A string message indicating the outcome of the insert operation.
        Example: "Successfully inserted 2 rows into table your_table_id."
        Returns an error message string if the insert fails, including details of any errors.
    """
    if not rows:
        return "Error: 'rows' list cannot be empty."
    try:
        client = bigquery.Client(project=DEFAULT_PROJECT_ID)
        table_ref = client.dataset(DEFAULT_DATASET_ID).table(table_id)
        
        # Convert Decimal to string and datetime objects to ISO format strings for JSON compatibility
        processed_rows_for_json = []
        for row in rows:
            processed_row = {}
            for key, value in row.items():
                if isinstance(value, Decimal):
                    processed_row[key] = str(value)
                elif isinstance(value, (datetime.date, datetime.datetime, datetime.time)):
                    processed_row[key] = value.isoformat()
                else:
                    processed_row[key] = value
            processed_rows_for_json.append(processed_row)

        errors = client.insert_rows_json(table_ref, processed_rows_for_json)  # API request
        if not errors:
            return f"Successfully inserted {len(rows)} rows into table {table_id}."
        else:
            error_details = []
            for error_entry in errors:
                error_details.append(f"Row index {error_entry['index']}: {error_entry['errors']}")
            return f"Error inserting rows into table {table_id}: {'; '.join(error_details)}"
    except Exception as e:
        return f"Error inserting rows into table {table_id}: {e}"

def update_bigquery_records(table_id: str, set_values: dict[str, any], where_clause: str) -> str:
    """
    Updates records in a specific table in the default BigQuery project and dataset.
    The default project and dataset are determined by DEFAULT_PROJECT_ID
    and DEFAULT_DATASET_ID environment variables.

    Args:
        table_id: The BigQuery table ID (short name, not fully qualified).
        set_values: A dictionary where keys are column names to be updated
                    and values are the new values for these columns.
                    Example: {"status": "completed", "score": 100}
        where_clause: An SQL WHERE clause string to specify which records to update.
                      Example: "user_id = 'user123' AND attempt_date < '2024-01-01'"
                      IMPORTANT: Ensure values in the where_clause are properly quoted if they are strings,
                                 and that column names and values in set_values are valid.

    Returns:
        A string message indicating the outcome of the update operation,
        including the number of rows affected if successful.
        Example: "Successfully updated 5 rows in table your_table_id."
        Returns an error message string if the update fails.
    """
    try:
        client = bigquery.Client(project=DEFAULT_PROJECT_ID)
        
        if not set_values:
            return "Error: set_values dictionary cannot be empty."

        set_clauses = []
        query_params = []
        
        for idx, (col, val) in enumerate(set_values.items()):
            param_name = f"p_set_val_{idx}"
            # Ensure column names are backticked if they contain special characters or are keywords.
            # For simplicity, always backtick here.
            set_clauses.append(f"`{col}` = @{param_name}")
            
            bq_type = None
            if isinstance(val, str): bq_type = "STRING"
            elif isinstance(val, bytes): bq_type = "BYTES"
            elif isinstance(val, int): bq_type = "INT64"
            elif isinstance(val, float): bq_type = "FLOAT64"
            elif isinstance(val, bool): bq_type = "BOOL"
            elif isinstance(val, datetime.datetime): bq_type = "TIMESTAMP"
            elif isinstance(val, datetime.date): bq_type = "DATE"
            elif isinstance(val, datetime.time): bq_type = "TIME"
            elif isinstance(val, Decimal): bq_type = "NUMERIC"
            
            if bq_type is None:
                raise TypeError(
                    f"Unsupported data type '{type(val).__name__}' for column '{col}'. "
                    f"Supported types: str, bytes, int, float, bool, datetime.datetime, "
                    f"datetime.date, datetime.time, Decimal."
                )
            query_params.append(bigquery.ScalarQueryParameter(param_name, bq_type, val))

        sql_set_clause = ", ".join(set_clauses)
        
        # Construct the fully qualified table name
        full_table_name = f"`{DEFAULT_PROJECT_ID}.{DEFAULT_DATASET_ID}.{table_id}`"
        
        query = f"UPDATE {full_table_name} SET {sql_set_clause} WHERE {where_clause}"
        
        job_config = bigquery.QueryJobConfig(query_parameters=query_params)
        query_job = client.query(query, job_config=job_config)
        query_job.result()  # Wait for the job to complete

        if query_job.errors:
            error_details = "; ".join([err['message'] for err in query_job.errors])
            return f"Error updating table {table_id}: {error_details}"

        return f"Successfully updated {query_job.num_dml_affected_rows} rows in table {table_id}."

    except Exception as e:
        return f"Error updating table {table_id}: {e}"

def delete_bigquery_records(table_id: str, where_clause: str) -> str:
    """
    Deletes records from a specific table in the default BigQuery project and dataset
    based on a WHERE clause.
    The default project and dataset are determined by DEFAULT_PROJECT_ID
    and DEFAULT_DATASET_ID environment variables.

    Args:
        table_id: The BigQuery table ID (short name, not fully qualified).
        where_clause: An SQL WHERE clause string to specify which records to delete.
                      Example: "user_id = 'user123' AND status = 'inactive'"
                      IMPORTANT: If the where_clause is empty or too broad, it could lead to
                                 unintended data loss. Be very specific.
                                 To delete all rows, explicitly pass "1=1" or a similar tautology,
                                 but this is highly discouraged without safeguards.

    Returns:
        A string message indicating the outcome of the delete operation,
        including the number of rows affected if successful.
        Example: "Successfully deleted 3 rows from table your_table_id."
        Returns an error message string if the delete fails.
    """
    if not where_clause or not where_clause.strip():
        return "Error: where_clause cannot be empty. To delete all rows, explicitly provide a condition like '1=1' (use with extreme caution)."
    try:
        client = bigquery.Client(project=DEFAULT_PROJECT_ID)
        full_table_name = f"`{DEFAULT_PROJECT_ID}.{DEFAULT_DATASET_ID}.{table_id}`"
        query = f"DELETE FROM {full_table_name} WHERE {where_clause}"
        
        query_job = client.query(query)  # API request
        query_job.result()  # Wait for the job to complete

        if query_job.errors:
            error_details = "; ".join([err['message'] for err in query_job.errors])
            return f"Error deleting from table {table_id}: {error_details}"

        return f"Successfully deleted {query_job.num_dml_affected_rows} rows from table {table_id}."
    except Exception as e:
        return f"Error deleting from table {table_id}: {e}"

# Define the ADK Agent
# Dynamically create the instruction string with the actual default project and dataset IDs
agent_instruction = (
    f"You are an assistant that queries Google BigQuery from a pre-configured project and dataset. "
    f"The default project ID is '{DEFAULT_PROJECT_ID}' and the default dataset ID is '{DEFAULT_DATASET_ID}'. "
    f"Your workflow is as follows:\n"
    f"1. When asked to find information, first call `list_dataset_tables` to see available tables from the default dataset (which is {DEFAULT_PROJECT_ID}.{DEFAULT_DATASET_ID}).\n"
    f"2. Based on the user's request and the list of tables, identify the most relevant `table_id`.\n"
    f"3. Call `get_bigquery_table_schema` with the selected `table_id` to understand its structure (this table will be in {DEFAULT_PROJECT_ID}.{DEFAULT_DATASET_ID}).\n"
    f"4. Construct a SQL query based on the user's request and the table schema. CRITICALLY IMPORTANT: When constructing the SQL query, you MUST use the fully qualified table name in the format `{DEFAULT_PROJECT_ID}.{DEFAULT_DATASET_ID}.selected_table_id` (e.g., 'SELECT * FROM `{DEFAULT_PROJECT_ID}.{DEFAULT_DATASET_ID}.my_table` ...'). Ensure backticks are used around the full path if it contains special characters, or around each component if necessary.\n"
    f"5. Call `run_bigquery_sql_query` with the fully constructed SQL query.\n"
    f"6. Present the results or insights derived from the query to the user.\n"
    f"\nIn addition to querying, you can perform updates:\n"
    f"- To update records, use the `update_bigquery_records` tool. Provide the `table_id` (short name), "
    f"a `set_values` dictionary (e.g., {{'column_name': 'new_value', 'another_column': 123}}), "
    f"and a `where_clause` string (e.g., \"id = 'abc' AND count > 10\"). "
    f"This tool operates on tables within the default project (`{DEFAULT_PROJECT_ID}`) and dataset (`{DEFAULT_DATASET_ID}`). "
    f"Ensure string values within the `set_values` dictionary are of supported types, and values in the `where_clause` are correctly quoted if they are strings.\n"
    f"- To insert new records, use the `insert_bigquery_rows` tool. Provide the `table_id` (short name) and a list of `rows` (dictionaries), where each dictionary represents a row to insert (e.g., `[{{\"col1\": \"valA\", \"col2\": 10}}, {{\"col1\": \"valB\", \"col2\": 20}}]`).\n"
    f"- To delete records, use the `delete_bigquery_records` tool. Provide the `table_id` (short name) and a `where_clause` string (e.g., \"status = 'archived'\"). Be very careful with the `where_clause` to avoid unintended data loss.\n"
    f"\nYou do not need to ask for project_id or dataset_id as they are pre-configured with the values '{DEFAULT_PROJECT_ID}' and '{DEFAULT_DATASET_ID}' respectively."
)

root_agent = Agent(
    name="BigQueryAssistant",
    model="gemini-2.5-flash-preview-05-20", # Or your preferred Gemini model
    instruction=agent_instruction,
    description=(
        "An agent that lists tables from a default BigQuery dataset, "
        "selects a table, gets its schema, and runs SQL queries."
    ),
    tools=[
        list_dataset_tables,
        get_bigquery_table_schema,
        run_bigquery_sql_query,
        insert_bigquery_rows,
        update_bigquery_records,
        delete_bigquery_records,
    ],
    # Enable code execution if you plan to use tools that require it,
    # or if the agent needs to generate and execute code.
    # enable_code_execution=True
)

if __name__ == '__main__':
    # This is a simple example of how you might test the tools.
    # Ensure your .env file has DEFAULT_PROJECT_ID and DEFAULT_DATASET_ID set.
    # You might also want to set TEST_TABLE_ID in .env for the schema/query tests.
    
    print(f"Using default project: {DEFAULT_PROJECT_ID}")
    print(f"Using default dataset: {DEFAULT_DATASET_ID}")

    # Load a specific table ID for testing schema and query, can be from .env or hardcoded for test
    TEST_TABLE_ID_FOR_SCHEMA_QUERY = os.getenv("TEST_TABLE_ID", "your_specific_test_table_id")


    if not DEFAULT_PROJECT_ID or DEFAULT_PROJECT_ID == "your-gcp-project-id" or \
       not DEFAULT_DATASET_ID or DEFAULT_DATASET_ID == "your_dataset_id":
        print("\n--- PLEASE CONFIGURE DEFAULT_PROJECT_ID and DEFAULT_DATASET_ID in .env file for testing ---")
    else:
        print("\n--- Testing list_dataset_tables ---")
        tables = list_dataset_tables()
        if tables:
            print(f"Tables in {DEFAULT_PROJECT_ID}.{DEFAULT_DATASET_ID}: {tables}")
            
            # Use the first table for further tests if available, otherwise use TEST_TABLE_ID_FOR_SCHEMA_QUERY
            if isinstance(tables, list) and len(tables) > 0:
                 actual_test_table_id = tables[0]
                 print(f"(Using first table found for next tests: {actual_test_table_id})")
            elif TEST_TABLE_ID_FOR_SCHEMA_QUERY != "your_specific_test_table_id":
                 actual_test_table_id = TEST_TABLE_ID_FOR_SCHEMA_QUERY
                 print(f"(Using TEST_TABLE_ID from .env for next tests: {actual_test_table_id})")
            else:
                 actual_test_table_id = None
                 print(f"(No tables found and TEST_TABLE_ID not configured in .env, skipping schema/query tests)")

            if actual_test_table_id:
                print(f"\n--- Testing get_bigquery_table_schema for table: {actual_test_table_id} ---")
                schema = get_bigquery_table_schema(table_id=actual_test_table_id)
                if schema:
                    print(f"Schema for {DEFAULT_PROJECT_ID}.{DEFAULT_DATASET_ID}.{actual_test_table_id}:")
                    for field_info in schema:
                        print(f"  - {field_info['name']} ({field_info['type']}), Mode: {field_info['mode']}")
                
                print(f"\n--- Testing run_bigquery_sql_query (SELECT * FROM ... LIMIT 2) on table: {actual_test_table_id} ---")
                test_query = f"SELECT * FROM `{DEFAULT_PROJECT_ID}.{DEFAULT_DATASET_ID}.{actual_test_table_id}` LIMIT 2"
                print(f"Executing query: {test_query}")
                query_results = run_bigquery_sql_query(query=test_query)
                if query_results:
                    print(f"Query results (first 2 rows of {actual_test_table_id}):")
                    for res_row in query_results:
                        print(f"  {res_row}")
                else:
                    print("Query returned no results or an error occurred.")

                # Test for update_bigquery_records
                if schema: # Ensure schema was fetched successfully for the selected table
                    print(f"\n--- Testing update_bigquery_records (safe update with WHERE 1=0) on table: {actual_test_table_id} ---")
                    first_field = schema[0]
                    first_field_name = first_field['name']
                    # BigQuery schema field_type is already uppercase (e.g., STRING, INTEGER, TIMESTAMP)
                    first_field_type = first_field['type']

                    # Determine a safe dummy value based on type
                    dummy_value = "test_update_val" # Default for STRING or unknown
                    if first_field_type in ("INTEGER", "INT64", "INT", "SMALLINT", "BIGINT"):
                        dummy_value = 12345
                    elif first_field_type in ("FLOAT", "FLOAT64", "DOUBLE", "REAL"):
                        dummy_value = 123.45
                    elif first_field_type in ("NUMERIC", "BIGNUMERIC"): # BIGNUMERIC also
                        dummy_value = Decimal("123.456") # Ensure Decimal is imported
                    elif first_field_type == "BOOLEAN":
                        dummy_value = True
                    elif first_field_type == "DATE":
                        dummy_value = datetime.date.today() # Ensure datetime is imported
                    elif first_field_type == "DATETIME":
                        # DATETIME is timezone-naive in BQ
                        dummy_value = datetime.datetime.now().replace(microsecond=0)
                    elif first_field_type == "TIMESTAMP":
                         # TIMESTAMP is timezone-aware (UTC) in BQ
                        dummy_value = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
                    elif first_field_type == "BYTES":
                        dummy_value = b"testbytes"
                    elif first_field_type == "TIME":
                        dummy_value = datetime.datetime.now().time().replace(microsecond=0)
                    elif first_field_type == "STRING":
                        dummy_value = "test_string_update"
                    # Add other types if necessary, e.g., GEOGRAPHY, JSON. Default is string.
                    
                    print(f"Attempting to 'update' column '{first_field_name}' (type: {first_field_type}) to value '{dummy_value}' (type: {type(dummy_value).__name__}) where 1=0 (no rows should be affected).")
                    try:
                        update_result_msg = update_bigquery_records(
                            table_id=actual_test_table_id,
                            set_values={first_field_name: dummy_value},
                            where_clause="1=0"  # This ensures no actual data is changed
                        )
                        print(f"Update result: {update_result_msg}")
                    except Exception as e_update:
                        print(f"Error during update_bigquery_records test: {e_update}")

                    # Test for insert_bigquery_rows
                    # IMPORTANT: This test performs a real insertion.
                    # Ensure the table structure matches or use a dedicated test table.
                    print(f"\n--- Testing insert_bigquery_rows on table: {actual_test_table_id} ---")
                    sample_row_to_insert = {}
                    for field_s in schema:
                        s_name = field_s['name']
                        s_type = field_s['type']
                        s_mode = field_s['mode']
                        
                        if s_type in ("INTEGER", "INT64"): sample_row_to_insert[s_name] = 0
                        elif s_type in ("FLOAT", "FLOAT64"): sample_row_to_insert[s_name] = 0.0
                        elif s_type == "NUMERIC": sample_row_to_insert[s_name] = Decimal("0.0")
                        elif s_type == "BOOLEAN": sample_row_to_insert[s_name] = False
                        elif s_type == "STRING": sample_row_to_insert[s_name] = f"test_insert_{s_name}"
                        elif s_type == "BYTES": sample_row_to_insert[s_name] = b"testbytes"
                        elif s_type == "DATE": sample_row_to_insert[s_name] = datetime.date(2000, 1, 1)
                        elif s_type == "DATETIME": sample_row_to_insert[s_name] = datetime.datetime(2000, 1, 1, 0, 0, 0)
                        elif s_type == "TIME": sample_row_to_insert[s_name] = datetime.time(0, 0, 0)
                        elif s_type == "TIMESTAMP": sample_row_to_insert[s_name] = datetime.datetime(2000, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
                        elif s_type == "GEOGRAPHY": sample_row_to_insert[s_name] = "POINT(0 0)"
                        elif s_mode == "NULLABLE":
                             sample_row_to_insert[s_name] = None
                    
                    if sample_row_to_insert:
                        print(f"Attempting to insert 1 sample row: {sample_row_to_insert}")
                        print("WARNING: This test performs a real data insertion. It's recommended to run against a test table or ensure the schema allows these values.")
                        try:
                            insert_result_msg = insert_bigquery_rows(
                                table_id=actual_test_table_id,
                                rows=[sample_row_to_insert]
                            )
                            print(f"Insert result: {insert_result_msg}")
                            # Consider adding a cleanup step here if the insert is successful for testing purposes
                            # e.g., delete the inserted row based on a unique key if possible.
                            # For example, if there's a unique ID field 'id_field' in sample_row_to_insert:
                            # if "Successfully inserted" in insert_result_msg and 'id_field' in sample_row_to_insert:
                            #     print(f"Attempting to clean up inserted test row with id_field = {sample_row_to_insert['id_field']}...")
                            #     cleanup_where_clause = f"id_field = '{sample_row_to_insert['id_field']}'" # Adjust quoting based on type
                            #     cleanup_msg = delete_bigquery_records(actual_test_table_id, cleanup_where_clause)
                            #     print(f"Cleanup result: {cleanup_msg}")
                        except Exception as e_insert:
                            print(f"Error during insert_bigquery_rows test: {e_insert}")
                    else:
                        print("Could not construct a sample row for insertion based on the schema, skipping insert test.")

                    # Test for delete_bigquery_records
                    print(f"\n--- Testing delete_bigquery_records (safe delete with WHERE 1=0) on table: {actual_test_table_id} ---")
                    print("Attempting to 'delete' records where 1=0 (no rows should be affected).")
                    try:
                        delete_result_msg = delete_bigquery_records(
                            table_id=actual_test_table_id,
                            where_clause="1=0"  # This ensures no actual data is deleted
                        )
                        print(f"Delete result: {delete_result_msg}")
                    except Exception as e_delete:
                        print(f"Error during delete_bigquery_records test: {e_delete}")
                else:
                    print("\nSkipping update, insert, and delete tests as table schema could not be fetched or was empty.")
        else:
            print(f"Could not retrieve tables to proceed with further tests for {DEFAULT_PROJECT_ID}.{DEFAULT_DATASET_ID}.")

    # --- Deploy to Vertex AI Agent Engine ---
    print("\n--- Attempting to deploy to Vertex AI Agent Engine ---")

    # Initialization for Vertex AI
    # GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION are already loaded from .env by load_dotenv()
    # and should be accessible via os.getenv()
    AGENT_ENGINE_PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
    AGENT_ENGINE_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION")
    # Staging bucket as provided by the user
    AGENT_ENGINE_STAGING_BUCKET = "gs://dvt-sp-agentspace-agent-engine-staging"

    if not AGENT_ENGINE_PROJECT_ID or not AGENT_ENGINE_LOCATION or not AGENT_ENGINE_STAGING_BUCKET:
        print("Error: GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION (from .env), and STAGING_BUCKET (hardcoded or user-provided) must be set for Agent Engine deployment.")
    else:
        print(f"Using Project ID for Agent Engine: {AGENT_ENGINE_PROJECT_ID}")
        print(f"Using Location for Agent Engine: {AGENT_ENGINE_LOCATION}")
        print(f"Using Staging Bucket for Agent Engine: {AGENT_ENGINE_STAGING_BUCKET}")

        try:
            vertexai.init(
                project=AGENT_ENGINE_PROJECT_ID,
                location=AGENT_ENGINE_LOCATION,
                staging_bucket=AGENT_ENGINE_STAGING_BUCKET,
            )
            print("Vertex AI initialized successfully.")

            # Prepare your agent for Agent Engine (as per guide, though agent_engines.create uses root_agent directly)
            # This step is good for consistency with the guide's local testing flow if desired.
            app = reasoning_engines.AdkApp(
                agent=root_agent,
                enable_tracing=True,
            )
            print("ADK App wrapped successfully (for potential local testing and deployability).")

            # Deploy your agent to Agent Engine
            print("Deploying agent to Agent Engine... This may take several minutes.")
            # Prepare environment variables for Agent Engine
            # These DEFAULT_PROJECT_ID and DEFAULT_DATASET_ID are loaded from .env
            # at the top of this script (lines 12 & 13 of the original file structure).
            env_vars_for_agent_engine = {}
            if DEFAULT_PROJECT_ID and DEFAULT_DATASET_ID:
                env_vars_for_agent_engine["DEFAULT_PROJECT_ID"] = DEFAULT_PROJECT_ID
                env_vars_for_agent_engine["DEFAULT_DATASET_ID"] = DEFAULT_DATASET_ID
                print(f"Prepared environment variables for Agent Engine: {env_vars_for_agent_engine}")
            else:
                print("Warning: DEFAULT_PROJECT_ID or DEFAULT_DATASET_ID not found from .env. Agent Engine environment variables might be incomplete.")
                # The agent code itself has a check and raises ValueError if these are not set,
                # so deployment might succeed but agent might fail at runtime if these are truly missing.

            remote_app = agent_engines.create(
                agent_engine=root_agent,
                display_name="BigQuery Assistant Agent",
                requirements=[
                    "google-cloud-aiplatform[adk,agent_engines]",
                    "python-dotenv", # For load_dotenv() within the agent if it still uses it
                    "google-cloud-bigquery"  # For bigquery.Client()
                ],
                env_vars=env_vars_for_agent_engine
            )
            print("Agent deployment to Agent Engine initiated.")
            print(f"Successfully deployed agent. Resource name: {remote_app.resource_name}")
            print("You can now interact with your remote agent.")
            print("To clean up the deployed agent and associated resources on Google Cloud, you can later run the following Python code:")
            print(f"# import os")
            print(f"# import vertexai")
            print(f"# from vertexai import agent_engines")
            print(f"# from dotenv import load_dotenv")
            print(f"# load_dotenv() # Ensure .env is loaded if running separately")
            print(f"# AGENT_ENGINE_PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT', '{AGENT_ENGINE_PROJECT_ID}')")
            print(f"# AGENT_ENGINE_LOCATION = os.getenv('GOOGLE_CLOUD_LOCATION', '{AGENT_ENGINE_LOCATION}')")
            print(f"# DEPLOYED_AGENT_RESOURCE_NAME = '{remote_app.resource_name}' # Replace if needed")
            print(f"# vertexai.init(project=AGENT_ENGINE_PROJECT_ID, location=AGENT_ENGINE_LOCATION)")
            print(f"# try:")
            print(f"#   remote_app_to_delete = agent_engines.get(DEPLOYED_AGENT_RESOURCE_NAME)")
            print(f"#   if remote_app_to_delete:")
            print(f"#     print(f'Attempting to delete agent: {{DEPLOYED_AGENT_RESOURCE_NAME}}')")
            print(f"#     remote_app_to_delete.delete(force=True)")
            print(f"#     print(f'Successfully initiated deletion of agent: {{DEPLOYED_AGENT_RESOURCE_NAME}}')")
            print(f"#   else:")
            print(f"#     print(f'Agent not found: {{DEPLOYED_AGENT_RESOURCE_NAME}}')")
            print(f"# except Exception as e_delete:")
            print(f"#   print(f'Error deleting agent {{DEPLOYED_AGENT_RESOURCE_NAME}}: {{e_delete}}')")

        except Exception as e:
            print(f"An error occurred during Vertex AI Agent Engine operations: {e}")
            print("Please ensure the following:")
            print("1. You have authenticated with Google Cloud (e.g., `gcloud auth application-default login`).")
            print("2. The Vertex AI API (aiplatform.googleapis.com) is enabled for your project.")
            print(f"3. The GCS staging bucket '{AGENT_ENGINE_STAGING_BUCKET}' exists and your account has 'Storage Object Admin' permissions on it.")
            print("4. The Python version being used is >=3.9 and <=3.12.")
            print("5. The necessary libraries (`google-cloud-aiplatform[adk,agent_engines]`, `python-dotenv`, `google-cloud-bigquery`) are installed in the Python environment where this script is executed.")
            print("6. Environment variables GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION are correctly set in your .env file.")

    print("\nAgent definition completed. To run the agent, use the ADK CLI (e.g., 'adk run bq_agent/agent.py').")
    print("Make sure you have python-dotenv, google-cloud-bigquery, and google-adk installed.")
    print("And that your Google Cloud credentials (ADC) are set up, and .env is configured.")