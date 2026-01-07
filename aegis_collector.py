import requests
import json
import os
import re
import time
from github import Github, Auth
from datetime import datetime

# --- 配置区 ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = os.getenv("GITHUB_REPOSITORY")
FILE_JSON = "ip_pool.json"
FILE_TXT = "ips_txt_view.txt"

WORKER_URL = "https://你的自定义域名.com/push-pool"
WORKER_AUTH_KEY = "my-secret-aegis"

def extract_ips(text):
    # 提取 IP 并过滤掉 1.0.1.1, 1.1.1.1, 0.0.0.0 等占位符
    found = re.findall(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b', text)
    blacklist = {"1.0.1.1", "1.1.1.1", "1.0.0.1", "0.0.0.0", "127.0.0.1"}
    return {ip for ip in found if ip not in blacklist}

def fetch_ips():
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
            print(f"✅ 抓取 {url} 获得 {len(ips)} 个有效 IP")
        except: pass
    return all_found

def update_repo(found_ips):
    auth = Auth.Token(GITHUB_TOKEN)
    g = Github(auth=auth)
    repo = g.get_repo(REPO_NAME)
    now_ts = int(time.time())
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 1. 读取旧数据库
    db = {"last_update": "", "pool": {}}
    try:
        contents = repo.get_contents(FILE_JSON)
        db = json.loads(contents.decoded_content.decode())
        json_sha = contents.sha
    except:
        json_sha = None

    # 2. 逻辑处理：解封与合并
    new_pool = {}
    # 保留旧库中未到期的封禁 IP
    if "pool" in db:
        for ip, info in db["pool"].items():
            if info.get("ban_until", 0) > now_ts:
                new_pool[ip] = info # 还在禁闭期，保留状态

    # 加入新抓取的 IP
    for ip in found_ips:
        if ip not in new_pool: # 如果不在禁闭期
            new_pool[ip] = {
                "added_at": update_time,
                "ban_until": 0,
                "fail_count": 0
            }

    # 3. 准备输出
    active_ips = [ip for ip, info in new_pool.items() if info["ban_until"] <= now_ts]
    
    # 保证至少有一个保底 IP（如果抓取全失败）
    display_ips = sorted(active_ips) if active_ips else ["1.1.1.1"]

    db_to_save = {
        "last_update": update_time,
        "total_active": len(display_ips),
        "pool": new_pool
    }

    # 4. 同步 GitHub
    json_str = json.dumps(db_to_save, indent=2)
    txt_content = f"# Aegis 更新: {update_time}\n" + "\n".join(display_ips)

    if json_sha:
        repo.update_file(FILE_JSON, f"Update DB {update_time}", json_str, json_sha)
    else:
        repo.create_file(FILE_JSON, "Init DB", json_str)

    try:
        txt_sha = repo.get_contents(FILE_TXT).sha
        repo.update_file(FILE_TXT, f"Update TXT {update_time}", txt_content, txt_sha)
    except:
        repo.create_file(FILE_TXT, "Init TXT", txt_content)

    return display_ips

def push_to_workers(active_ips):
    headers = {"Authorization": WORKER_AUTH_KEY, "Content-Type": "application/json"}
    try:
        # 注意这里推送给 Worker 的字段名要统一为 ips
        requests.post(WORKER_URL, json={"ips": active_ips}, headers=headers, timeout=10)
        print(f"🚀 已推送 {len(active_ips)} 个 IP 到 Workers 大脑")
    except Exception as e:
        print(f"❌ 推送失败: {e}")

if __name__ == "__main__":
    found = fetch_ips()
    active = update_repo(found)
    push_to_workers(active)
