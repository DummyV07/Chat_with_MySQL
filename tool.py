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
import datetime
def get_date_time():
    return datetime.datetime.now()
              

from PET_UTILS import *
# TOOLS 功能
def search_mysql(dbConnection,question:str,selected_sql_model:str,selected_nl_model:str) -> str:
    # 读取 schema_ouput.txt 文件获取 schema 信息
    with open('schema_output.txt', 'r', encoding='utf-8') as file:
        schema = file.read()
    print(f"初始问题{question}")

    PET = PET_SQL(client,question,dbConnection,schema,selected_sql_model,selected_nl_model)

    return PET.main()