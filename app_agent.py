import streamlit as st
from pymysql import Connection
from openai import OpenAI
from dotenv import load_dotenv,find_dotenv
from tool import *
import json

from config import *

client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
    api_key= DASHSCOPE_API_KEY, 
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

def init_db(host:str,port:str,user:str,password:str,database:str) -> Connection:
    return Connection(host=host,port=int(port),user=user,password=password,database=database)


def get_db_schema(conn:Connection,db_name:str):
    sql = f"show tables from {db_name}"
    with conn.cursor() as cursor:
        cursor.execute(sql)
        tables = cursor.fetchall()
        tables_schema = []
        for table in tables:
            sql = f"show create table {table[0]}"
            cursor.execute(sql)
            create_table_sql = cursor.fetchone()
            tables_schema.append(create_table_sql)
        return tables_schema
    
def execute_sql(conn:Connection,sql:str) ->str:
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        return cursor.fetchall()
    except Exception as e:
        return str(e)
    finally:
        cursor.close() 

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
    st.session_state.chat_history.append({"role":"assistant","content":"你好，我是您的mysql数据库助手，请问有什么可以帮您？"})
if "final_chat_history" not in st.session_state:
    st.session_state.final_chat_history = []

st.set_page_config(page_title="chat with SQL",page_icon=':books:')
st.title("LLM_SQL")

# 在函数定义部分添加自动连接数据库的函数
def auto_connect_db():
    """自动尝试连接数据库，成功返回True，失败返回False"""
    try:
        if 'dbConnection' in st.session_state:
            return True
            
        # 使用config.py中的默认配置尝试连接
        dbConnection = init_db(HOST, PORT, USER, PASSWORD, DATABASENAME)
        
        # 保存连接信息到session state
        st.session_state.host = HOST
        st.session_state.port = PORT
        st.session_state.user = USER
        st.session_state.password = PASSWORD
        st.session_state.databasename = DATABASENAME
        
        # 测试连接
        dbConnection.ping(reconnect=True)
        
        # 保存连接并设置提示词
        st.session_state.dbConnection = dbConnection
        
        return True
        
    except Exception as e:
        if 'dbConnection' in st.session_state:
            del st.session_state.dbConnection
        return False

with st.sidebar:
    st.title("数据库的连接信息")
    
    # 自动尝试连接数据库
    if not auto_connect_db():
        st.error("数据库连接失败，请检查连接信息")
        st.subheader("请修改数据库连接信息")
        
        st.text_input("Host", value=st.session_state.get('host', HOST), key="host")
        st.text_input("Port", value=st.session_state.get('port', PORT), key="port")
        st.text_input("User", value=st.session_state.get('user', USER), key="user")
        st.text_input("Password", value="", key="password", type="password")
        st.text_input("DatabaseName", value=st.session_state.get('databasename', DATABASENAME), key="databasename")
        
        if st.button("连接数据库"):
            with st.spinner("正在连接数据库..."):
                try:
                    dbConnection = init_db(
                        st.session_state.host,
                        st.session_state.port,
                        st.session_state.user,
                        st.session_state.password,
                        st.session_state.databasename
                    )
                    st.session_state.dbConnection = dbConnection
                    if auto_connect_db():
                        st.success("数据库连接成功！")
                        st.rerun()
                    else:
                        st.error("连接失败，请检查连接信息")
                except Exception as e:
                    st.error(f"连接失败：{str(e)}")
    else:
        st.success("数据库已连接")
        with st.expander("查看连接信息"):
            st.write(f"Host: {st.session_state.get('host', HOST)}")
            st.write(f"Port: {st.session_state.get('port', PORT)}")
            st.write(f"User: {st.session_state.get('user', USER)}")
            st.write(f"Database: {st.session_state.get('databasename', DATABASENAME)}")

    if st.button("清除聊天记录"):
        st.session_state.chat_history = []
        st.session_state.final_chat_history = []
        st.rerun()

    st.divider()  # 添加分隔线
    
    # 模型选择部分
    st.subheader("模型配置")
    
    # SQL生成模型选择
    selected_sql_model = st.selectbox(
        "SQL生成模型",
        options=MODELS_SQL,
        key="sql_model"
    )
    
    # 自然语言模型选择
    selected_nl_model = st.selectbox(
        "自然语言模型",
        options=MODELS_NL,
        key="nl_model"
    )

for message in st.session_state.chat_history:
    if message["role"] == "assistant":
        with st.chat_message("assistant"):
            st.markdown(message["content"])
    if message["role"] == "user":
        with st.chat_message("user"):
            st.markdown(message["content"])

# for message in st.session_state.final_chat_history:
#     if message["role"] == "assistant":
#         with st.chat_message("assistant"):
#             st.markdown(message["content"])

userQuery = st.chat_input("请输入您的问题")
if userQuery is not None and userQuery.strip() != "":

    # 将用户的问题添加到聊天历史中
    st.session_state.chat_history.append({"role":"user","content":userQuery})

    # 显示用户的问题
    with st.chat_message("user"):
        st.markdown(userQuery)

    # 将用户的问题添加到最终的聊天历史中

    system_prompt = """
    你是一位专业的DBA，根据以下<schema>中的表结构，根据用户的问题编写SQL语句，允许使用模糊匹配 LINK操作符。
    <schema> {schema} </schema>
    """

    response = client.chat.completions.create(
        model=selected_sql_model,
        messages=[{"role":"system","content":system_prompt},{"role":"user","content":userQuery}],
        tools=TOOLS,
        tool_choice="auto",
    )

    if response.choices[0].finish_reason == "tool_calls":
        for tool_call in response.choices[0].message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            if function_name == "search_mysql":
                final_response = search_mysql(get_db_schema(st.session_state.dbConnection, DATABASENAME),st.session_state.dbConnection,function_args["question"])
                print(function_name)
    else:
        final_response = response.choices[0].message.content
        
    with st.chat_message("assistant"):
        st.markdown(final_response)

    
    st.session_state.chat_history.append({"role":"assistant","content":final_response})
    # print(final_response.choices[0].message.content)