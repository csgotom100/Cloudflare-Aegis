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

# --- Cloudflare Workers 配置 (根据你的代码修正) ---
WORKER_URL = "https://nameless-cherry-bb9c.2412.workers.dev/push-pool"
WORKER_AUTH_KEY = "my-secret-aegis"  # 必须与 Worker 中的 authKey 完全一致

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def extract_ips(text):
    return set(re.findall(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b', text))

def fetch_ips():
    all_found = set()
    # 尝试从不同的源抓取
    sources = [
        "https://api.uouin.com/cloudflare.html",
        "https://stock.hostmonit.com/CloudFlareYes"
    ]
    
    for url in sources:
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
        return []

    auth = Auth.Token(GITHUB_TOKEN)
    g = Github(auth=auth)
    repo = g.get_repo(REPO_NAME)
    
    # 简单的仓库更新逻辑，确保文件存在
    db = {"last_update": datetime.now().strftime("%Y-%m-%d %H:%M"), "pool": ips_list}
    json_str = json.dumps(db, indent=2)
    
    try:
        contents = repo.get_contents(FILE_JSON)
        repo.update_file(FILE_JSON, "Collector Sync", json_str, contents.sha)
    except:
        repo.create_file(FILE_JSON, "Collector Init", json_str)
        
    return ips_list

def push_to_workers(active_ips):
    """关键推送函数"""
    print(f"DEBUG: 开始执行推送逻辑，IP总数: {len(active_ips)}")
    if not active_ips:
        print("⚠️ 没有 IP 需要推送")
        return

    payload = {"ips": active_ips}
    headers = {
        "Authorization": WORKER_AUTH_KEY,
        "Content-Type": "application/json"
    }

    try:
        print(f"📡 正在推送数据至: {WORKER_URL}")
        response = requests.post(WORKER_URL, json=payload, headers=headers, timeout=10)
        print(f"DEBUG: Workers 返回状态码: {response.status_code}")
        if response.status_code == 200:
            print(f"✅ Workers 大脑同步成功: {response.text}")
        elif response.status_code == 401:
            print("❌ 同步失败: 鉴权无效 (Auth Key 不匹配)")
        else:
            print(f"❌ 同步失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 网络推送异常: {e}")

if __name__ == "__main__":
    # 1. 抓取
    ips = fetch_ips()
    
    # 2. 更新仓库
    active_ips = update_repo(ips)
    
    # 3. 强制推送到 Workers (确保这一行没有被注释)
    push_to_workers(active_ips)
    
    print("🔥 脚本运行结束")
