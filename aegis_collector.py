import requests
import json
import os
import re
from github import Github, Auth
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
        return

    auth = Auth.Token(GITHUB_TOKEN)
    g = Github(auth=auth)
    repo = g.get_repo(REPO_NAME)
    
    # 1. 尝试获取旧数据及其 SHA
    json_sha = None
    db = {"last_update": "", "pool": {}}
    
    try:
        contents = repo.get_contents(FILE_JSON)
        db = json.loads(contents.decoded_content.decode())
        json_sha = contents.sha
        if not isinstance(db.get('pool'), dict):
            db['pool'] = {}
    except:
        print(f"ℹ️ {FILE_JSON} 不存在，将创建新文件")

    # 2. 合并新 IP
    for ip in ips_list:
        if ip not in db['pool']:
            db['pool'][ip] = {
                "score": 100, 
                "fail_count": 0, 
                "added_at": datetime.now().strftime("%Y-%m-%d")
            }
    
    db['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M")
    json_str = json.dumps(db, indent=2)

    # 3. 准备 TXT 预览
    txt_content = f"# 弹药库预览 (更新日期: {db['last_update']})\n# 总计: {len(db['pool'])}\n\n"
    txt_content += "\n".join(sorted(db['pool'].keys()))

    # 4. 提交数据
    print(f"🚀 准备同步到 GitHub...")
    
    # 提交 JSON
    if json_sha:
        repo.update_file(FILE_JSON, "Sync JSON Pool", json_str, json_sha)
    else:
        repo.create_file(FILE_JSON, "Init JSON Pool", json_str)

    # 提交 TXT (获取最新的 TXT SHA)
    try:
        txt_file = repo.get_contents(FILE_TXT)
        repo.update_file(FILE_TXT, "Sync TXT View", txt_content, txt_file.sha)
    except:
        repo.create_file(FILE_TXT, "Init TXT View", txt_content)
    
    print("🔥 大功告成！")

if __name__ == "__main__":
    found_list = fetch_ips()
    update_repo(found_list)
