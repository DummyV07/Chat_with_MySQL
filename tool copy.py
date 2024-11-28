# TOOLS 描述
TOOLS = [
    {
        "type":"function",
        "function":{
            "name":"search_mysql",
            "description":"根据用户的问题生成sql语句,并执行sql语句，得到sql语句的执行结果，再根据返回结果生成自然语言的回答",
            "parameters":{
                "type":"object",
                "properties":{
                    "question":{
                        "type":"string",
                        "description":"用户的问题"
                    }
                },
                "required":["question"]
            }
        }
    }
]

from openai import OpenAI
from config import *

# 调用百炼的api
client = OpenAI(
    base_url=BASE_URL_BAILIAN,
    api_key=DASHSCOPE_API_KEY,

)
from pymysql import Connection
def execute_sql(conn:Connection,sql:str) ->str:
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        return cursor.fetchall()
    except Exception as e:
        return str(e)
    finally:
        cursor.close() 

# TOOLS 功能
def search_mysql(schema,dbConnection,question:str) -> str:
    # 根据用户的问题生成sql语句
    # 优化方向 1. prompt的修改 2. schema 格式的优化
    if schema is None:
        return "数据库连接失败，请重新连接数据库"
        
    sql_system_prompt = f"""

        你是一位经验丰富的 DBA，请根据用户问题编写的 SQL 查询语句。
        自行判断是否使用模糊匹配，允许使用LIKE操作符。
        不附加任何额外说明或格式化标记，SQL 语句末尾不加分号。

        """
    print(sql_system_prompt)
    response = client.chat.completions.create(
        model="qwen2.5-14b-instruct",
        messages=[{"role":"system","content":sql_system_prompt},{"role":"user","content":question}],

    )

    sql = response.choices[0].message.content
    print(f"初始：{sql}")
    
    # 使用大模型对sql语句进行检查修正？ 这一步有没有必要 自己对自己纠错？
    sql = cheak_sql(schema,sql,question)
    print(f"修正：{sql}")


    sql_result = execute_sql(dbConnection,sql)
    print(sql_result)
    print('*'*40)
    if check_sql_result(sql_result):

        finally_response = client.chat.completions.create(
            model="qwen2.5-14b-instruct",
            messages=[{"role":"user","content":f"""
                请根据以下的sql查询的原问题，以及sql查询的结果，生成合适的自然语言回答,若sql查询结果为错误信息，则输出:抱歉查询失败，请检查查询字段或者重新尝试查询
                问题：{question}
                sql语句：{sql}  
                sql查询结果：{sql_result}
                """}],
            )

        return finally_response.choices[0].message.content
    else:
        if cheak_fuzzy_match(sql):
            print(sql)
            # 使用模糊匹配且查询失败
            return "抱歉，查询失败，请检查查询字段是否合法"
        else:
            # 未使用模糊匹配，则尝试使用模糊匹配
            sql_system_prompt = f"""

            请将下列sql语句，使用LINK操作符修改为模糊匹配的格式。
            不附加任何额外说明或格式化标记，SQL 语句末尾不加分号。
            sql语句：{sql}

            """

            response = client.chat.completions.create(
                model="qwen2.5-14b-instruct",
                messages=[{"role":"system","content":sql_system_prompt},{"role":"user","content":question}],

            )
            new_sql = response.choices[0].message.content
            sql_result = execute_sql(dbConnection,new_sql)
            
            finally_response = client.chat.completions.create(
            model="qwen2.5-14b-instruct",
            messages=[{"role":"user","content":f"""
                请根据以下的sql查询的原问题，以及sql查询的结果，生成合适的自然语言回答,若sql查询结果为错误信息，则输出:抱歉查询失败，请检查查询字段或者重新尝试查询
                问题：{question}
                sql语句：{new_sql}  
                sql查询结果：{sql_result}
                """}],
            )
            print(new_sql)
            print(sql_result)
            return finally_response.choices[0].message.content

    

    # 使用大模型对sql语句进行检查修正？ 这一步有没有必要 自己对自己纠错？
    # sql_result = execute_sql(dbConnection,sql)
def check_sql_result(sql_result: str) -> bool:
    response = client.chat.completions.create(
        model="qwen2.5-14b-instruct",
        messages=[{"role":"user","content":f"""
            判断结果是否为报错信息，如果是则返回false，否则返回true。
            结果：{sql_result}
            示例：

            结果：(1064, "You have an error in your SQL syntax; check the manual that corresponds to your MySQL server version for the right syntax to use near
            输出：false

            结果：(('13981796416', '高新区天府大道北段966号天府国际金融中心11号楼1单元4楼及57楼'),)
            输出：true
            
            """
                   
                   }],

    )
    return response.choices[0].message.content
def cheak_sql(schema,sql:str,question)->bool:
    # 使用大模型检查sql语句的合法性，以及使用的字段是否在schema中
    sql_user_prompt = f"""

        你是一位经验丰富的数据库管理员 (DBA)。请根据以下 <schema> 提供的表结构信息，仔细审查 <sql> 查询中的字段和表名，确保所有字段和表都正确无误。
        若发现问题，请根据表结构修正错误并返回修改后的 SQL 语句。

        要求：

        仅使用 <schema> 中存在的表和字段。
        若由于原始查询意图不明确，可根据用户问题<question>查询语句修改，返回粗略查询的sql语句,
        但必须确保语句的合法性，以及返回结果的合理性。
        SQL 语句末尾不加分号。
        不附加任何额外说明或格式化标记。
        输入： 
        <schema> {schema} </schema> 
        <sql> {sql} </sql>
        <question> {question}<question> 


    """

    response = client.chat.completions.create(
        model="qwen2.5-14b-instruct",
        messages=[{"role":"user","content":sql_user_prompt}],

    )
    return response.choices[0].message.content

def cheak_fuzzy_match(sql:str)->bool:
    # 检查模型是否使用了模糊匹配
    if "LIKE" in sql:
        return True
    else:   
        return False
def post_consistency(finally_result:str)->str:
    pass