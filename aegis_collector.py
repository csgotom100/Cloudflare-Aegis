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

# ！！！永久黑名单：1.0.1.1, 1.2.1.1 以及其他垃圾占位符 ！！！
HARD_BLACKLIST = {"1.0.1.1", "1.2.1.1", "1.1.1.1", "1.0.0.1", "0.0.0.0", "127.0.0.1"}

WORKER_URL = "https://nameless-cherry-bb9c.2412.workers.dev/push-pool"
WORKER_AUTH_KEY = "my-secret-aegis" 
# ==========================================

def extract_ips(text):
    """提取 IP 并物理过滤硬黑名单"""
    found = re.findall(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b', text)
    # 只要在黑名单里，直接踢出
    return {ip for ip in found if ip not in HARD_BLACKLIST}

def fetch_ips():
    all_found = set()
    sources = ["https://api.uouin.com/cloudflare.html", "https://stock.hostmonit.com/CloudFlareYes"]
    for url in sources:
        try:
            resp = requests.get(url, timeout=15)
            ips = extract_ips(resp.text)
            all_found.update(ips)
            print(f"✅ 抓取 {url} 成功，获得 {len(ips)} 个有效 IP")
        except: pass
    return all_found

def update_repo(found_ips):
    if not found_ips: return []
    
    auth = Auth.Token(GITHUB_TOKEN)
    g = Github(auth=auth)
    repo = g.get_repo(REPO_NAME)
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 读取旧数据库
    db = {"pool": {}}
    try:
        contents = repo.get_contents(FILE_JSON)
        db = json.loads(contents.decoded_content.decode())
        json_sha = contents.sha
    except:
        json_sha = None

    # 合并数据：只保留不在黑名单里的 IP
    old_pool = db.get("pool", {})
    new_pool = {}
    for ip in found_ips:
        if ip in HARD_BLACKLIST: continue
        new_pool[ip] = old_pool.get(ip, {"added_at": update_time, "fail_count": 0})

    active_ips = sorted(list(new_pool.keys()))
    db_to_save = {"last_update": update_time, "total_active": len(active_ips), "pool": new_pool}

    # 更新 GitHub
    json_str = json.dumps(db_to_save, indent=2, ensure_ascii=False)
    if json_sha:
        repo.update_file(FILE_JSON, f"🛡️ Purge Blacklist & Sync {update_time}", json_str, json_sha)
    else:
        repo.create_file(FILE_JSON, "Init DB", json_str)

    txt_content = f"# Aegis 优选 IP (已过滤黑名单)\n# 更新: {update_time}\n\n" + "\n".join(active_ips)
    try:
        txt_sha = repo.get_contents(FILE_TXT).sha
        repo.update_file(FILE_TXT, f"Sync TXT {update_time}", txt_content, txt_sha)
    except:
        repo.create_file(FILE_TXT, "Init TXT", txt_content)

    return active_ips

def push_to_workers(active_ips):
    headers = {"Authorization": WORKER_AUTH_KEY, "Content-Type": "application/json"}
    try:
        requests.post(WORKER_URL, json={"ips": active_ips}, headers=headers, timeout=20)
        print(f"🚀 已推送 {len(active_ips)} 个干净 IP 到 Workers")
    except Exception as e:
        print(f"🛑 推送失败: {e}")

if __name__ == "__main__":
    found = fetch_ips()
    active = update_repo(found)
    push_to_workers(active)
