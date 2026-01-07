import requests
import json
import os
import re
import time
from github import Github, Auth
from datetime import datetime

# ================= 配置区 =================
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = os.getenv("GITHUB_REPOSITORY")
FILE_JSON = "ip_pool.json"
FILE_TXT = "ips_txt_view.txt"

# ！！！请确保这里是你真实的 Worker 地址 ！！！
WORKER_URL = "https://nameless-cherry-bb9c.2412.workers.dev/push-pool"
WORKER_AUTH_KEY = "my-secret-aegis" 
# ==========================================

def extract_ips(text):
    """提取 IP 并过滤垃圾占位符"""
    found = re.findall(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b', text)
    # 彻底排除这些无效 IP
    blacklist = {"1.0.1.1", "1.1.1.1", "1.0.0.1", "0.0.0.0", "127.0.0.1"}
    return {ip for ip in found if ip not in blacklist}

def fetch_ips():
    """爬取优选源"""
    all_found = set()
    sources = [
        "https://api.uouin.com/cloudflare.html",
        "https://stock.hostmonit.com/CloudFlareYes"
    ]
    for url in sources:
        try:
            resp = requests.get(url, timeout=15)
            ips = extract_ips(resp.text)
            all_found.update(ips)
            print(f"✅ 抓取 {url} 成功，获得 {len(ips)} 个 IP")
        except Exception as e:
            print(f"⚠️ 抓取 {url} 失败: {e}")
    return all_found

def update_repo(found_ips):
    """更新 GitHub 仓库文件"""
    if not found_ips:
        print("❌ 未发现任何有效 IP，跳过更新")
        return []

    auth = Auth.Token(GITHUB_TOKEN)
    g = Github(auth=auth)
    repo = g.get_repo(REPO_NAME)
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 1. 尝试读取旧数据库以保留状态
    db = {"last_update": "", "pool": {}}
    try:
        contents = repo.get_contents(FILE_JSON)
        db = json.loads(contents.decoded_content.decode())
        json_sha = contents.sha
    except:
        json_sha = None

    # 2. 合并新老数据 (保留旧 IP 的信息，加入新 IP)
    old_pool = db.get("pool", {})
    new_pool = {}
    
    for ip in found_ips:
        if ip in old_pool:
            new_pool[ip] = old_pool[ip] # 保留原有的 added_at 等信息
        else:
            new_pool[ip] = {
                "added_at": update_time,
                "fail_count": 0
            }

    # 3. 生成输出列表
    active_ips = sorted(list(new_pool.keys()))

    db_to_save = {
        "last_update": update_time,
        "total_active": len(active_ips),
        "pool": new_pool
    }

    # 4. 更新 JSON 文件
    json_str = json.dumps(db_to_save, indent=2, ensure_ascii=False)
    if json_sha:
        repo.update_file(FILE_JSON, f"Sync DB {update_time}", json_str, json_sha)
    else:
        repo.create_file(FILE_JSON, "Init DB", json_str)
    print(f"✅ {FILE_JSON} 已更新")

    # 5. 更新 TXT 文件
    txt_content = f"# Aegis 优选 IP 列表\n# 更新时间: {update_time}\n\n" + "\n".join(active_ips)
    try:
        txt_contents = repo.get_contents(FILE_TXT)
        repo.update_file(FILE_TXT, f"Sync TXT {update_time}", txt_content, txt_contents.sha)
    except:
        repo.create_file(FILE_TXT, "Init TXT", txt_content)
    print(f"✅ {FILE_
