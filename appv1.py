import streamlit as st
from pymysql import Connection
from openai import OpenAI
from dotenv import load_dotenv,find_dotenv

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
        
        # 设置提示词
        promptTemplate = """
        你是一位专业的DBA，根据以下<schema>中的表结构，根据用户的问题编写SQL语句，允许使用模糊匹配 LINK操作符。
        只返回sql语句即可，不需要其他内容，不需要考虑对话的历史记录，sql语句最后不要加分号，不要带入格式标记。
        <schema> {schema} </schema>
        举例：
        问题：一共有多少老师
        回答：SELECT COUNT(*) FROM teachers;
        问题：1号学生的姓名
        回答：SELECT student_name FROM students WHERE student_id = 1
        """
        st.session_state.chat_history.append(
            {"role":"system","content":promptTemplate.format(schema=get_db_schema(dbConnection, DATABASENAME))}
        )
        
        promptTemplate_final = """
        你是一位专业的DBA，您正与一位用户进行交互，该用户向您询问有关数据库的问题。
        根据下面的表结构、问题、SQL查询和SQL响应，编写自然语言的响应。最终的响应需要表达完整，让用户可以清晰的看清楚结果。
        注意我确认我的sql语句是对的，你不需要对我的sql语句进行验证，只需要根据我的sql语句的返回结果给出回答。
        <schema> {schema} </schema>

        举例：
        用户查询：一共有多少老师
        SQL查询：SELECT COUNT(*) FROM teachers;
        SQL响应：20
        回答：一共有20位老师
        """
        st.session_state.final_chat_history.append(
            {"role":"system","content":promptTemplate_final.format(schema=str(get_db_schema(dbConnection, DATABASENAME)))}
        )
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
        # 只显示最新的assistant回复
        with st.chat_message("assistant"):
            st.markdown(message["content"])
    if message["role"] == "user":
        with st.chat_message("user"):
            st.markdown(message["content"])

for message in st.session_state.final_chat_history:
    if message["role"] == "assistant":
        # 只显示最新的assistant回复
        with st.chat_message("assistant"):
            st.markdown(message["content"])

userQuery = st.chat_input("请输入您的问题")
if userQuery is not None and userQuery.strip() != "":
    print(userQuery)

    # 将用户的问题添加到聊天历史中
    st.session_state.chat_history.append({"role":"user","content":userQuery})
    # 将用户的问题添加到最终的聊天历史中
    st.session_state.final_chat_history.append({"role":"user","content":userQuery})
    # 显示用户的问题
    with st.chat_message("user"):
        st.markdown(userQuery)

    # SQL生成使用选择的模型
    response = client.chat.completions.create(
        model=selected_sql_model,  # 使用选择的SQL模型
        messages=st.session_state.chat_history,
        temperature=0.7
    )
    
    print('response')
    sql = response.choices[0].message.content

    with st.chat_message("assistant"):
        st.markdown(sql)

    # 清空之前的 assistant 信息，只保留最新生成的 SQL
    st.session_state.chat_history = [{"role": "user", "content": userQuery}, {"role": "assistant", "content": sql}]

    st.session_state.final_chat_history.append({"role":"user","content":sql})

    sql_result = execute_sql(st.session_state.dbConnection, sql)
    
    st.session_state.final_chat_history.append({"role":"user","content":sql})
    st.session_state.final_chat_history.append({"role":"assistant","content":str(sql_result)})
    print(str(sql_result))

    # 自然语言响应生成使用选择的模型
    final_response = client.chat.completions.create(
        model=selected_nl_model,  # 使用选择的自然语言模型
        messages=st.session_state.final_chat_history,
        temperature=0.7
    )
    
    with st.chat_message("assistant"):
        st.markdown(final_response.choices[0].message.content)

    # 更新 final_chat_history，确保它只保存最新的内容
    st.session_state.final_chat_history = [
        {"role": "user", "content": userQuery},
        {"role": "assistant", "content": final_response.choices[0].message.content}
    ]
