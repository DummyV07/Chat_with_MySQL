import streamlit as st
from pymysql import Connection
from openai import OpenAI
from dotenv import load_dotenv,find_dotenv

load_dotenv(find_dotenv())


client = OpenAI()

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

with st.sidebar:
    st.title("数据库的连接信息")
    st.subheader("这是一个NLP2MYSQLDB的Demo程序，请先连接mysql，再进行提问")

    st.text_input("Host",value="localhost",key="host")
    st.text_input("Port",value="3306",key="port")
    st.text_input("User",value="root",key="user")
    st.text_input("Password",value="1029Eason",key="password",type="password")
    st.text_input("DatabaseName",value="chat_mysql",key="databasename")

    if st.button("连接数据库"):
        with st.spinner("连接中..."):
            dbConnection = init_db(st.session_state.host,st.session_state.port,st.session_state.user,st.session_state.password,st.session_state.databasename)
            if 'dbConnection'  not in st.session_state:
                # 以便让LLM模型可以访问数据库
                st.session_state.dbConnection = dbConnection
            st.success("数据库连接成功")

            # 提示词没必要刻意去学，都是根据任务一点一点修改出来的(我这里是照搬博主的)
            promptTemplate = """
            你是一位专业的DBA，根据以下<schema>中的表结构，根据用户的问题编写SQL语句，所有的表没有关联关系，不要使用join等表关联语法。
            只返回sql语句即可，不需要其他内容，需要考虑对话的历史记录，sql语句最后不要加分号。
            <schema> {schema} </schema>
            举例：
            问题：一共有多少老师
            回答：SELECT COUNT(*) FROM teachers;
            问题：1号学生的姓名
            回答：SELECT student_name FROM students WHERE student_id = 1
            """
            st.session_state.chat_history.append(
                {"role":"system","content":promptTemplate.format(schema=get_db_schema(st.session_state.dbConnection,st.session_state.databasename))}
                )
            
            promptTemplate_final = """
            你是一位专业的DBA，您正与一位用户进行交互，该用户向您询问有关数据库的问题。
            根据下面的表结构、问题、SQL查询和SQL响应，编写自然语言的响应。最终的响应需要表达完整，让用户可以清晰的看清楚结果
            <schema> {schema} </schema>

            举例：
            用户查询：一共有多少老师
            SQL查询：SELECT COUNT(*) FROM teachers;
            SQL响应：20
            回答：一共有20位老师
            """

            st.session_state.final_chat_history.append(
                {"role":"system","content":promptTemplate_final.format(schema=str(get_db_schema(st.session_state.dbConnection,st.session_state.databasename)))}
                )
for message in st.session_state.chat_history:
    if message["role"] == "assistant":
        with st.chat_message("assistant"):
            st.markdown(message["content"])
    if message["role"] == "user":
        with st.chat_message("user"):
            st.markdown(message["content"])

for message in st.session_state.final_chat_history:
    if message["role"] == "assistant":
        with st.chat_message("assistant"):
            st.markdown(message["content"])

userQuery = st.chat_input("请输入您的问题")
if userQuery is not None and userQuery.strip() != "":
    st.session_state.chat_history.append({"role":"user","content":userQuery})
    st.session_state.final_chat_history.append({"role":"user","content":userQuery})
    # 显示用户的问题
    with st.chat_message("user"):
        st.markdown(userQuery)
    # 调用openai的api生成sql语句
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=st.session_state.chat_history,
        temperature=0.5
    )
    

    sql = response.choices[0].message.content
    

    with st.chat_message("assistant"):
        st.markdown(sql)

    st.session_state.chat_history.append({"role":"assistant","content":sql})
    st.session_state.final_chat_history.append({"role":"user","content":sql})

    sql_result = execute_sql(st.session_state.dbConnection,sql)
    st.session_state.final_chat_history.append({"role":"assistant","content":str(sql_result)})

    final_response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=st.session_state.final_chat_history,
        temperature=0.5
    )
    with st.chat_message("assistant"):
        st.markdown(final_response.choices[0].message.content)

    st.session_state.final_chat_history.append({"role":"assistant","content":final_response.choices[0].message.content})
