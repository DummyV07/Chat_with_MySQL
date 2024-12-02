# 借鉴了PET_SQL的思路进行代码结构优化

from pymysql import Connection

# 最大迭代次数
max_iterate  = 5

import datetime
date_time = datetime.datetime.now()

class PET_SQL:
    def __init__(self,client,question:str,dbConnection:Connection,schema:str,selected_sql_model:str,selected_nl_model:str):
        self.client = client
        self.question = "当前日期及时间：" + str(date_time) + "请问" + question # 这里做里一个quary优化，以告诉模型当前时间
        self.schema = schema
        self.dbConnection = dbConnection
        self.selected_sql_model = selected_sql_model
        self.selected_nl_model = selected_nl_model
        self.final_sql = ''
        self.iterate = 0
        self.final_result = ''
        
    def Pre_Process(self)->str:
        # 首先生成一个粗略的sql语句
        sql_system_prompt = f"""

        你是一位经验丰富的 DBA，请根据用户问题编写的 SQL 查询语句。
        自行判断是否使用模糊匹配，允许使用LIKE操作符。
        不附加任何额外说明或格式化标记，SQL 语句末尾不加分号。

        """
        
        response = self.client.chat.completions.create(
            model=self.selected_sql_model,
            messages=[{"role":"system","content":sql_system_prompt},{"role":"user","content":self.question}],

        )

        pre_sql = response.choices[0].message.content

        print(f"初始：{pre_sql}")
        
        return pre_sql

    def Sql_Generate(self,pre_sql:str,)->str:
        # 根据表结构进行实体链接 生成final_sql
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
            <schema> {self.schema} </schema> 
            <sql> {pre_sql} </sql>
            <question> {self.question}<question> 


        """

        response = self.client.chat.completions.create(
            model=self.selected_sql_model,
            messages=[{"role":"user","content":sql_user_prompt}],

        )
        self.final_sql = response.choices[0].message.content
        print(f"修改：{self.final_sql}")
        return self.final_sql


    def Post_Calibation(self,final_sql:str)->str:
        
        sql_result = self.execute_sql(final_sql)
        print(f"执行结果：{sql_result}")

        if self.check_sql_result(sql_result):
            
            if not self.check_fuzzy_match(final_sql):
                fuzzy_sql = self.fuzzy_sql(final_sql)
                print(f"模糊匹配：{fuzzy_sql}")
                return self.Post_Calibation(fuzzy_sql)
            else:
                if self.iterate >= max_iterate:
                    print("迭代次数过多，无法解决")
                    self.final_result = "很抱歉无法解决您的问题，您可以尝试换个问法或再试一次。"
                    return str("很抱歉无法解决您的问题，您可以尝试换个问法或再试一次。")
                else:
                    self.iterate += 1
                    self.main()
        else:
            self.final_result = self.NL_LLM(sql_result)
            return self.final_result
            
    def check_fuzzy_match(self,sql:str)->bool:
        # 检查模型是否使用了模糊匹配
        if "LIKE" in sql:
            return True
        else:   
            return False
    def fuzzy_sql(self,sql:str)->str:
        # 未使用模糊匹配，则尝试使用模糊匹配
    
        response = self.client.chat.completions.create(
            model=self.selected_sql_model,
            messages=[{"role":"user","content":f"""

            请将下列sql语句，使用LIKE操作符修改为模糊匹配的格式。
            不附加任何额外说明或格式化标记，SQL 语句末尾不加分号。
            sql语句：{sql}

            """
            }],

        )
        new_sql = response.choices[0].message.content
        self.final_sql = new_sql
        return self.final_sql

    def execute_sql(self,sql:str) ->str:
        cursor = self.dbConnection.cursor()
        try:
            cursor.execute(sql)
            return cursor.fetchall()
        except Exception as e:
            return str(e)
        finally:
            cursor.close() 

    def check_sql_result(self,sql_result: str) -> bool:
        # 检查结果是否报错
        response = self.client.chat.completions.create(
            model=self.selected_nl_model,
            messages=[{"role":"user","content":f"""
                
                判断
                判断结果是否为报错信息，如果是则返回true，否则返回false。
                注意你只能返回true或者false，不要返回其他内容。
                
    
                结果：{sql_result}

                示例：

                结果：(1064, "You have an error in your SQL syntax; check the manual that corresponds to your MySQL server version for the right syntax to use near
                输出：true

                结果：((15515.26,1),)
                输出：false
                
                """
                    
                    }],

        )
        content = response.choices[0].message.content.strip().lower()
        if content == 'true':
            return True
        elif content  == 'false':
            return False
        else:
            return self.check_sql_result(sql_result)
        

    def NL_LLM(self,sql_result:str)->str:
        system_prompt = f"""
        你是一位专业的DBA，您正与一位用户进行交互，该用户向您询问有关数据库的问题。
        根据下面的表结构、问题、SQL查询和SQL响应，编写自然语言的响应。最终的响应需要表达完整，让用户可以清晰的看清楚结果。
        注意我确认我的sql语句是对的，你不需要对我的sql语句进行验证，只需要根据我的sql语句的返回结果给出回答。
        <schema> {self.schema} </schema>

        举例：
        用户查询：哪个合同的租期最长，该合同的租赁面积是好多，客户是哪个？
        SQL查询：SELECT T1.rent_period, T1.total_room_build_square, T2.cust_name FROM assets_room_rent_app AS T1 JOIN assets_cust_info AS T2 ON T1.cust_id = T2.id ORDER BY T1.rent_period DESC LIMIT 1
        SQL响应：((200, 1000.0, 'ABCDE咖啡有限公司'),)
        回答：租期最长的合同租期为200个月，该合同的总租赁面积为1000.0平方米，合同涉及的客户是“ABCDE咖啡有限公司”。
        """

        user_prompt = f"""
        用户查询：{self.question}
        SQL查询：{self.final_sql}
        SQL响应：{sql_result}
        """

        finally_response = self.client.chat.completions.create(
            model=self.selected_nl_model,
            messages=[{"role":"system","content":system_prompt},
                       {"role":"user","content":user_prompt}],

        )
        
        print("*"*40)
        print(finally_response.choices[0].message.content)
        print("*"*40)
        
        return finally_response.choices[0].message.content 
    def main(self):
        pre_sql = self.Pre_Process()
        self.final_sql = self.Sql_Generate(pre_sql)
        
        temp = self.Post_Calibation(self.final_sql)

        if temp == None:
            return self.final_result
        else:
            return temp
        


