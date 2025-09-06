import pandas as pd
import json
from typing import Dict, List

class SchemaProcessor:
    def __init__(self, csv_file_path: str):
        self.csv_file_path = csv_file_path
        self.schema_data = []
    
    def process_csv_schema(self) -> List[Dict]:
        """
        Process CSV file containing table schema information
        Expected CSV columns: Column Name, Description (for enhanced_db_schema.csv format)
        Or: table_name, column_name, data_type, description (for standard format)
        """
        try:
            df = pd.read_csv(self.csv_file_path)
            
            # Check the CSV format and adapt accordingly
            if 'Column Name' in df.columns and 'Description' in df.columns:
                # Enhanced format - create both UserRecords and Licenses tables
                tables = {
                    "UserRecords": {
                        'table_name': "UserRecords",
                        'columns': [],
                        'description': f"User records data table"
                    },
                    "Licenses": {
                        'table_name': "Licenses",
                        'columns': [],
                        'description': f"License information table"
                    }
                }
                
                # Define which columns belong to which table based on actual database schema
                license_columns = ['Id', 'Name', 'ActualCost', 'PartnerCost', 'TenantCode', 
                                 'ConsumedUnits', 'Status', 'TotalUnits', 'IsTrial', 'IsPaid', 
                                 'LicenceExpirationDate', 'CreateDateTime', 'IsAddOn']
                
                for _, row in df.iterrows():
                    column_name = row['Column Name']
                    column_info = {
                        'column_name': column_name,
                        'data_type': 'string',  # Default type
                        'description': row['Description']
                    }
                    
                    # Determine which table this column belongs to
                    # Only license-specific columns should go to Licenses table
                    is_license_column = False
                    
                    # Exact matches for license columns
                    if column_name in ['LicenseId', 'LicenseName', 'ActualCost', 'PartnerCost', 
                                     'ConsumedUnits', 'Status', 'TotalUnits', 'IsTrial', 'IsPaid', 
                                     'LicenceExpirationDate', 'CreateDateTime', 'IsAddOn']:
                        is_license_column = True
                        # Map CSV column names to actual database column names
                        if column_name == 'LicenseId':
                            column_info['column_name'] = 'Id'
                        elif column_name == 'LicenseName':
                            column_info['column_name'] = 'Name'
                    
                    if is_license_column:
                        tables['Licenses']['columns'].append(column_info)
                    else:
                        tables['UserRecords']['columns'].append(column_info)
            
            elif 'table_name' in df.columns and 'column_name' in df.columns:
                # Standard format - multiple tables
                tables = {}
                for _, row in df.iterrows():
                    table_name = row['table_name']
                    if table_name not in tables:
                        tables[table_name] = {
                            'table_name': table_name,
                            'columns': [],
                            'description': f"Table: {table_name}"
                        }
                    
                    column_info = {
                        'column_name': row['column_name'],
                        'data_type': row['data_type'],
                        'description': row.get('description', '')
                    }
                    tables[table_name]['columns'].append(column_info)
            else:
                raise ValueError("Unsupported CSV format. Expected either 'Column Name, Description' or 'table_name, column_name, data_type, description'")
            
            # Convert to list and create text representations for vector search
            for table_name, table_info in tables.items():
                columns_text = ", ".join([
                    f"{col['column_name']}: {col['description']}" 
                    for col in table_info['columns']
                ])
                
                schema_text = f"Table: {table_name}. Columns: {columns_text}"
                
                self.schema_data.append({
                    'table_name': table_name,
                    'schema_info': table_info,
                    'search_text': schema_text
                })
            
            print(f"Processed {len(self.schema_data)} tables from CSV")
            return self.schema_data
            
        except Exception as e:
            print(f"Error processing CSV: {str(e)}")
            return []
    
    def get_table_schema_text(self, table_name: str) -> str:
        """Get formatted schema text for a specific table"""
        for schema in self.schema_data:
            if schema['table_name'] == table_name:
                table_info = schema['schema_info']
                columns_detail = []
                for col in table_info['columns']:
                    if col['data_type'] and col['data_type'] != 'string':
                        col_text = f"  - {col['column_name']} ({col['data_type']})"
                    else:
                        col_text = f"  - {col['column_name']}"
                    
                    if col['description']:
                        col_text += f": {col['description']}"
                    columns_detail.append(col_text)
                
                return f"Table: {table_name}\nColumns:\n" + "\n".join(columns_detail)
        return f"Table: {table_name} (schema not found)"
    
    def save_processed_data(self, output_file: str):
        """Save processed schema data to JSON file"""
        with open(output_file, 'w') as f:
            json.dump(self.schema_data, f, indent=2)
        print(f"Saved processed schema data to {output_file}")
    
    def load_processed_data(self, input_file: str):
        """Load processed schema data from JSON file"""
        try:
            with open(input_file, 'r') as f:
                self.schema_data = json.load(f)
            print(f"Loaded {len(self.schema_data)} schemas from {input_file}")
        except FileNotFoundError:
            print(f"File {input_file} not found. Please process CSV first.")