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
              

from PET_UTILS import *
# TOOLS 功能
def search_mysql(schema,dbConnection,question:str) -> str:

    print(f"初始问题{question}")

    PET = PET_SQL(client,question,dbConnection,schema)

    return PET.main()