import requests
import json
import os
import re
from github import Github, Auth  # 修复警告
from datetime import datetime

# --- 配置 ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = os.getenv("GITHUB_REPOSITORY")
FILE_JSON = "ip_pool.json"
FILE_TXT = "ips_txt_view.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def extract_ips(text):
    return set(re.findall(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b', text))

def fetch_ips():
    all_found = set()
    if not os.path.exists("sources.txt"):
        return []
    with open("sources.txt", "r") as f:
        urls = [line.strip() for line in f if line.strip()]
    for url in urls:
        try:
            print(f"🌐 正在爬取: {url}")
            resp = requests.get(url, headers=HEADERS, timeout=15)
            ips = extract_ips(resp.text)
            if ips:
                all_found.update(ips)
                print(f"✅ 抓取成功: 获得 {len(ips)} 个 IP")
        except Exception as e:
            print(f"❌ 请求失败: {url} -> {e}")
    return sorted(list(all_found))

def update_repo(ips_list):
    if not ips_list:
        print("停止更新：本次未获取到任何 IP")
        return

    # 修复 DeprecationWarning
    auth = Auth.Token(GITHUB_TOKEN)
    g = Github(auth=auth)
    repo = g.get_repo(REPO_NAME)
    
    # 获取旧数据
    try:
        contents = repo.get_contents(FILE_JSON)
        db = json.loads(contents.decoded_content.decode())
        # 核心修复：确保 db['pool'] 是字典而不是列表
        if not isinstance(db.get('pool'), dict):
            print("⚠️ 检测到旧版格式，正在重置为字典格式...")
            db['pool'] = {}
    except:
        db = {"last_update": "", "pool": {}}

    # 更新数据
    for ip in ips_list:
        if ip not in db['pool']:
            db['pool'][ip] = {
                "score": 100, 
                "fail_count": 0, 
                "added_at": datetime.now().strftime("%Y-%m-%d")
            }
    
    db['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M")
    json_str = json.dumps(db, indent=2)

    # 生成文本清单
    txt_content = f"# 弹药库预览 (最后更新: {db['last_update']})\n"
    txt_content += f"# 总计数量: {len(db['pool'])}\n\n"
    txt_content += "\n".join(sorted(db['pool'].keys()))

    # 提交
    print(f"🚀 准备提交至仓库...")
    
    # 提交 JSON
    try:
        repo.update_file(FILE_JSON, "Update JSON Pool", json_str, contents.sha)
    except Exception as e:
        print(f"JSON 提交失败: {e}")
        repo.create_file(FILE_JSON, "Create JSON Pool", json_str)

    # 提交 TXT
    try:
        txt_file = repo.get_contents(FILE_TXT)
        repo.update_file(FILE_TXT, "Update TXT View", txt_content, txt_file.sha)
    except:
        repo.create_file(FILE_TXT, "Create TXT View", txt_content)
    
    print("🔥 成功！请刷新仓库页面查看 ips_txt_view.txt")

if __name__ == "__main__":
    found_list = fetch_ips()
    update_repo(found_list)
