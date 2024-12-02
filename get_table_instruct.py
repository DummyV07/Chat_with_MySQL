# 通过sql命令获取表结构
import csv
from config import *
from pymysql import Connection

# Function to read the first column of a CSV file and return it as a list
def read_first_column_from_csv(file_path: str) -> list:
    first_column_values = []
    with open(file_path, mode='r', encoding='utf-8') as file:
        csv_reader = csv.reader(file)
        next(csv_reader)  # Skip the header row
        for row in csv_reader:
            first_column_values.append(row[0].lower())
    return first_column_values

first_column_values = read_first_column_from_csv('database_name.csv')

def init_db(host:str, port:str, user:str, password:str, database:str) -> Connection:
    return Connection(host=host, port=int(port), user=user, password=password, database=database)

def create_sql(table):
    sql_table = f"""
    SELECT 
        TABLE_NAME,
        TABLE_COMMENT
    FROM 
        information_schema.TABLES
    WHERE
        TABLE_SCHEMA = '{DATABASENAME}' 
        AND TABLE_NAME = '{table}';
    """

    sql_column = f"""
    SELECT 
        COLUMN_NAME,
            COLUMN_COMMENT
    FROM 
        information_schema.COLUMNS
    WHERE 
        TABLE_SCHEMA = '{DATABASENAME}' 
        AND TABLE_NAME = '{table}';
    """

    
    return sql_table, sql_column

def get_db_schema(conn:Connection, db_name:str):
    save_tables = []
    sql = f"show tables from {db_name}"

    with conn.cursor() as cursor:
        cursor.execute(sql)
        tables = cursor.fetchall()
        tables_schema = []
        for table in tables:
            
            sql_table,sql_column = create_sql(table[0])

            if table[0].lower() in first_column_values:
                save_tables.append(table[0].lower() )
                cursor.execute(sql_table)
                table = cursor.fetchone()
                cursor.execute(sql_column)
                column = cursor.fetchall()
                info = f" 表名及注释：{table}  字段及注释：{column}"
                
                tables_schema.append(info)
                
  
        # Find the differences between the two lists
        missing_tables = list(set(first_column_values) - set(save_tables))
        # print(missing_tables)
        print(f"共找到{len(save_tables)}个表")
        return tables_schema





if __name__ == "__main__":
    # Example usage
    host = HOST
    port = PORT     
    user = USER
    password = PASSWORD
    database = DATABASENAME

    dbConnection = init_db(host, port, user, password, database)
    schema = get_db_schema(dbConnection, database)
    # Write the schema content to a txt file
    with open("schema_output.txt", "w", encoding="utf-8") as file:
        for table_schema in schema:
            file.write(table_schema + "\n")