import json
import os
import difflib
from json import JSONDecodeError

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],  # 允许的源
    allow_credentials=True,
    allow_methods=["*"],  # 允许的方法，如：GET, POST, OPTIONS 等
    allow_headers=["*"],  # 允许的头
)


def get_all_json_files_content(directory):
    json_files_content = {}
    for filename in os.listdir(directory):
        if filename.endswith(".json") and filename != "result.json":
            file_path = os.path.join(directory, filename)
            try:
                print(file_path)
                with open(file_path, 'r', encoding='utf-8') as file:
                    # 尝试解析为 JSON
                    try:
                        content = json.load(file)
                        if isinstance(content, dict):
                            json_files_content[filename] = content
                        else:
                            print(f"文件 {filename} 格式不正确，跳过。")
                    except JSONDecodeError:
                        print(f"文件 {filename} 不是有效的 JSON，跳过。")
            except Exception as e:
                print(f"读取文件 {filename} 时发生错误: {e}")
    return json_files_content


def is_more_complete(option1, option2):
    """
    比较两个选项，返回 True 如果 option1 的属性比 option2 更全。
    """
    for key in option1:
        if key not in option2:
            return True
        if isinstance(option1[key], list) and len(option1[key]) > len(option2[key]):
            return True
        if option1[key] != option2[key]:
            return True
    return False


def generate_bank(directory='.'):
    final_result = {}
    old_result_count = 0
    json_contents = get_all_json_files_content(directory)
    json_data_list = {}

    # 读取原有题库
    with open("QuestionBank/result.json", 'r', encoding='utf8') as f:
        try:
            final_result = json.loads(f.read())
            old_result_count = len(final_result)
        except JSONDecodeError:
            print("原有题库文件无法解析，开始创建新的题库。")

    # 遍历读取的 JSON 文件内容
    for filename, content in json_contents.items():
        try:
            # 如果文件内容包含 'data' 和 'questions'，才处理
            if 'data' in content and 'questions' in content['data']:
                json_data_list[filename] = content['data']['questions']
            else:
                print(f"文件 {filename} 缺少 'data' 或 'questions' 键，跳过。")
        except KeyError as e:
            print(f"文件 {filename} 中缺少键 {e}，跳过。")

    # 开始合并题目
    for filename, data in json_data_list.items():
        print(f"文件 {filename} 中的题目数量: {len(data)}")
        for item in data:
            title = item['title']
            options = item['optionList']

            # 使用字典去重选项，确保每个选项的 content 唯一，并且保留信息最全的选项
            unique_options_dict = {}
            for option in options:
                content = option['content']
                if content not in unique_options_dict:
                    unique_options_dict[content] = option
                else:
                    existing_option = unique_options_dict[content]
                    if is_more_complete(option, existing_option):
                        unique_options_dict[content] = option

            unique_options = list(unique_options_dict.values())

            if title not in final_result:
                # 如果题目标题不存在，则添加新题目及其选项
                final_result[title] = {
                    'optionList': unique_options
                }
            else:
                # 如果题目标题已存在，则检查选项是否相同
                existing_options = final_result[title]['optionList']

                # 使用字典去重现有选项，确保每个选项的 content 唯一
                existing_options_dict = {option['content']: option for option in existing_options}

                # 将现有选项和新的选项合并
                all_options_dict = existing_options_dict.copy()
                for option in unique_options:
                    content = option['content']
                    if content in all_options_dict:
                        if is_more_complete(option, all_options_dict[content]):
                            all_options_dict[content] = option
                    else:
                        all_options_dict[content] = option

                final_result[title]['optionList'] = list(all_options_dict.values())

    print(f"旧题库总数:{old_result_count}\n")

    with open(f"{directory}/result.json", 'w', encoding='utf-8') as f:
        print("已更新题库\n")
        f.write(json.dumps(final_result, indent=4, ensure_ascii=False))
        print(f"当前题库总数:{len(final_result)}\n")


bank_obj = {}


@app.get("/answer/{question}")
async def get_answer(question: str):
    for i in bank_obj:
        if question in i:
            return {'question': i, 'msg': bank_obj[i]}
    closest_match = difflib.get_close_matches(question, bank_obj.keys(), n=1, cutoff=0.6)
    if closest_match:
        return {'question': closest_match[0], 'msg': bank_obj[closest_match[0]]}
    else:
        return {'msg': '题目不存在'}
    # return {'code': 200, 'msg': bank_obj.get(question, "题目不存在")}


def main():
    generate_bank(directory=os.getcwd() + "/QuestionBank")
    with open("QuestionBank/result.json", 'r') as f:
        global bank_obj
        bank_obj = json.load(f)
    uvicorn.run(app, host="127.0.0.1", port=8080)


if __name__ == '__main__':
    main()
