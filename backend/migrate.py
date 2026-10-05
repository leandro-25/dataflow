#!/usr/bin/env python3
"""
Database migration script to add missing columns
"""
import sqlite3
import sys
from pathlib import Path

def get_db_path():
    """Get the database path"""
    return Path(__file__).parent.parent / "data" / "metadata.db"

def migrate_database():
    """Add missing columns to the database"""
    db_path = get_db_path()
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        sys.exit(1)
    
    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Check existing columns in ingestions table
    cursor.execute("PRAGMA table_info(ingestions)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    print(f"Existing columns in ingestions: {existing_columns}")
    
    # Define missing columns to add
    columns_to_add = {
        'ingestions': [
            ('schedule_enabled', 'BOOLEAN DEFAULT 0'),
            ('schedule_timezone', 'VARCHAR DEFAULT "America/Sao_Paulo"'),
            ('validation_status', 'VARCHAR'),
            ('validation_message', 'TEXT'),
            ('progress_percent', 'INTEGER'),
            ('progress_rows_processed', 'INTEGER'),
            ('progress_rows_total', 'INTEGER'),
            ('progress_stage', 'VARCHAR'),
            ('progress_speed_rows_per_sec', 'INTEGER'),
            ('progress_eta_seconds', 'INTEGER'),
            ('is_favorite', 'BOOLEAN DEFAULT 0'),
            ('column_mapping', 'JSON DEFAULT "{}"'),
            ('filters', 'JSON DEFAULT "[]"'),
            ('selected_columns', 'JSON DEFAULT "[]"'),
            ('incremental_config', 'JSON DEFAULT "{}"'),
            ('advanced_options', 'JSON DEFAULT "{}"'),
            ('tags', 'JSON DEFAULT "[]"'),
            ('description', 'TEXT'),
            ('last_run_duration_ms', 'INTEGER'),
            ('last_run_error', 'TEXT'),
            ('total_runs', 'INTEGER DEFAULT 0'),
            ('total_rows_ingested', 'INTEGER DEFAULT 0'),
            ('avg_rows_per_run', 'INTEGER'),
            ('avg_duration_ms', 'INTEGER'),
            ('current_execution_id', 'VARCHAR'),
        ],
        'stagings': [
            ('schedule', 'VARCHAR'),
            ('schedule_enabled', 'BOOLEAN DEFAULT 0'),
        ],
        'dimensions': [
            ('schedule', 'VARCHAR'),
            ('schedule_enabled', 'BOOLEAN DEFAULT 0'),
        ],
        'facts': [
            ('schedule', 'VARCHAR'),
            ('schedule_enabled', 'BOOLEAN DEFAULT 0'),
        ],
    }
    
    # Add missing columns
    for table, columns in columns_to_add.items():
        print(f"\nProcessing table: {table}")
        
        # Check table exists
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if not cursor.fetchone():
            print(f"  Table {table} does not exist, skipping...")
            continue
        
        # Get existing columns for this table
        cursor.execute(f"PRAGMA table_info({table})")
        table_columns = {row[1] for row in cursor.fetchall()}
        
        for column_def in columns:
            column_name = column_def[0]
            
            if column_name in table_columns:
                print(f"  Column {column_name} already exists, skipping...")
                continue
            
            # Add the column
            try:
                sql = f"ALTER TABLE {table} ADD COLUMN {column_name} {column_def[1]}"
                print(f"  Adding column: {sql}")
                cursor.execute(sql)
                print(f"  [OK] Successfully added {column_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    print(f"  [SKIP] Column {column_name} already exists")
                else:
                    print(f"  [ERROR] Error adding {column_name}: {e}")
                    raise
    
    # Check and add ingestion_orders table if missing
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ingestion_orders'")
    if not cursor.fetchone():
        print("\nCreating ingestion_orders table...")
        cursor.execute("""
            CREATE TABLE ingestion_orders (
                id VARCHAR PRIMARY KEY,
                ingestion_id VARCHAR NOT NULL UNIQUE,
                user_id VARCHAR DEFAULT 'default',
                sort_order INTEGER DEFAULT 0,
                folder VARCHAR,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("  [OK] Created ingestion_orders table")
    
    # Check and add keyboard_shortcuts table if missing
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='keyboard_shortcuts'")
    if not cursor.fetchone():
        print("\nCreating keyboard_shortcuts table...")
        cursor.execute("""
            CREATE TABLE keyboard_shortcuts (
                id VARCHAR PRIMARY KEY,
                user_id VARCHAR DEFAULT 'default',
                shortcut_key VARCHAR NOT NULL,
                action VARCHAR NOT NULL,
                description VARCHAR,
                enabled BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("  [OK] Created keyboard_shortcuts table")
    
    # Check and add execution_progress table if missing
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='execution_progress'")
    if not cursor.fetchone():
        print("\nCreating execution_progress table...")
        cursor.execute("""
            CREATE TABLE execution_progress (
                id VARCHAR PRIMARY KEY,
                execution_id VARCHAR NOT NULL UNIQUE,
                resource_id VARCHAR NOT NULL,
                resource_type VARCHAR NOT NULL,
                percent_complete INTEGER DEFAULT 0,
                rows_processed INTEGER DEFAULT 0,
                rows_total INTEGER,
                stage VARCHAR DEFAULT 'connecting',
                speed_rows_per_second INTEGER,
                eta_seconds INTEGER,
                current_batch INTEGER DEFAULT 0,
                total_batches INTEGER,
                batch_size INTEGER,
                status VARCHAR DEFAULT 'running',
                message TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("  [OK] Created execution_progress table")
    
    conn.commit()
    conn.close()
    
    print("\n[MIGRATION COMPLETE]")
    print("Missing columns and tables have been added to the database.")

if __name__ == "__main__":
    try:
        migrate_database()
    except Exception as e:
        print(f"\n[MIGRATION FAILED]: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
