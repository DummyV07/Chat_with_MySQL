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

        你是一位经验丰富的 DBA，请全面理解以下 <schema> 提供的表结构信息，并确保准确无误。根据用户的问题，基于 <schema> 中的实际表和字段，编写精确的 SQL 查询语句。

        仅使用 <schema> 中存在的表和字段。
        仅使用 <schema> 中存在的表和字段。
        仅使用 <schema> 中存在的表和字段。
        仅使用 <schema> 中存在的表和字段。
        当涉及模糊匹配时，使用 LIKE 操作符。
        不附加任何额外说明或格式化标记，SQL 语句末尾不加分号。
        <schema> {schema} </schema>

        """
    print(sql_system_prompt)
    response = client.chat.completions.create(
        model="qwen2.5-14b-instruct",
        messages=[{"role":"system","content":sql_system_prompt},{"role":"user","content":question}],

    )
    sql = response.choices[0].message.content

    print(sql)

    # 使用大模型对sql语句进行检查修正？ 这一步有没有必要 自己对自己纠错？
    sql_result = execute_sql(dbConnection,sql)


    
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

def cheak_sql(sql:str)->bool:
    # 使用大模型检查sql语句的合法性，以及使用的字段是否在schema中
    
    pass