# 读取table的schema信息然后生成可供llm选择的table description

import json
from openai import OpenAI
from config import *


client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
    api_key = DASHSCOPE_API_KEY, 
    base_url = BASE_URL_BAILIAN,
)

system_prompt = """
    你是一个智能助手，你
    """
def get_llm_response(line: str) -> str:
    # 构造 response_format 字典，确保 'type' 和 'json_schema' 是其直接的键

    system_prompt = """
    你是一个专业的智能助手，精通自然语言处理和数据库知识
    你的任务是根据用户提供的表格描述，生成高质量的 JSON 对象
    输出的 JSON 描述将用于帮助大模型在用户提问时，快速匹配答案可能存在的表单
    你的输出必须符合以下要求：
    1. 格式必须严格遵守 JSON 标准，确保解析无误
    2. 语言简洁精准，描述清楚表格的功能和内容重点
    3. 避免多余的标点符号或不相关信息
    """

    user_prompt = f"""
    请根据以下表格描述生成一个标准的 JSON 对象
    你的目标是创建一个清晰、简洁的表格描述，帮助大模型根据用户问题匹配到正确的表单

    表格描述重点包括表格的名称、用途、核心字段或主要内容
    你的输出必须准确反映表格的功能及数据范围，不包含任何多余标点符号或冗余信息

    表格描述：{line}

    返回格式如下：
    {{
        "table_name": "<表格的英文名>",
        "table_description": "<用于匹配的高质量中文描述>"
    }}

    注意事项：
    1. "table_name" 应为表格的标准英文名称或合理推测的英文名
    2. "table_description" 应精炼清晰，包含表格功能、核心字段或数据特点，帮助快速判断与用户问题的相关性
    3. 请严格按照上述格式返回 JSON，并确保描述内容与表格描述语义一致
    """

    response = client.chat.completions.create(
        model="qwen2.5-7b-instruct",
        messages=[{"role": "system", "content": system_prompt}, 
                {"role": "user", "content": user_prompt}],
        max_tokens=1024,
        temperature=0.5,
    )

    # 提取返回内容
    response_content = response.choices[0].message["content"]
    print(response_content)
    
    return response.choices[0].message.content


def get_table_description(txt_path: str, output: str) -> str:
    with open(txt_path, "r", encoding='UTF-8') as f:
        for line in f.readlines():
            json_str = get_llm_response(line)
            try:
                # 将大模型生成的json字符串转换为字典
                data_dict = json.loads(json_str)
                print(data_dict)
                # 将字典存入json文件中
                with open(output, "a", encoding='UTF-8') as outfile:
                    json.dump(data_dict, outfile, ensure_ascii=False, indent=4)
                    outfile.write("\n")  # 添加换行符以便多个条目之间有分隔
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from line: {line}. Error: {e}")
            


if __name__ == "__main__":
    txt_path = "schema_output.txt"
    output = "./data/table_description_llm.txt"
    get_table_description(txt_path,output)