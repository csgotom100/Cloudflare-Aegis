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

# Cloudflare Workers 配置
WORKER_URL = "https://nameless-cherry-bb9c.2412.workers.dev/push-pool"
# 注意：这里的 AUTH_KEY 必须和你在 Workers 脚本里定义的 authKey 完全一致
WORKER_AUTH_KEY = "my-secret-aegis" 

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def extract_ips(text):
    """从文本中提取所有 IPv4 地址"""
    return set(re.findall(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b', text))

def fetch_ips():
    """从 sources.txt 列表抓取 IP"""
    all_found = set()
    if not os.path.exists("sources.txt"):
        print("❌ 未找到 sources.txt，请创建并填入数据源链接")
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
    """更新 GitHub 仓库中的 JSON 和 TXT 文件"""
    if not ips_list:
        return []

    auth = Auth.Token(GITHUB_TOKEN)
    g = Github(auth=auth)
    repo = g.get_repo(REPO_NAME)
    now_ts = int(time.time())
    
    # 1. 获取现有数据库
    json_sha = None
    db = {"last_update": "", "pool": {}}
    try:
        contents = repo.get_contents(FILE_JSON)
        db = json.loads(contents.decoded_content.decode())
        json_sha = contents.sha
        if not isinstance(db.get('pool'), dict):
            db['pool'] = {}
    except:
        print(f"ℹ️ 未发现现有数据库，将创建新库文件")

    # 2. 逻辑 A：处理禁闭到期与解封 (安全检查)
    for ip, info in list(db['pool'].items()):
        ban_until = info.get('ban_until', 0)
        if ban_until > 0 and now_ts > ban_until:
            print(f"✨ IP {ip} 禁闭期满，已从黑名单释放。")
            db['pool'][ip]['score'] = 100
            db['pool'][ip]['fail_count'] = 0
            db['pool'][ip]['ban_until'] = 0

    # 3. 逻辑 B：合并新抓取的 IP
    for ip in ips_list:
        if ip not in db['pool']:
            db['pool'][ip] = {
                "score": 100, 
                "fail_count": 0, 
                "ban_until": 0,
                "added_at": datetime.now().strftime("%Y-%m-%d")
            }
        elif db['pool'][ip].get('ban_until', 0) == 0:
            db['pool'][ip]['score'] = 100
    
    db['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # 4. 生成活跃 IP 列表 (只包含未被禁闭的)
    active_ips = [ip for ip, info in db['pool'].items() if info.get('ban_until', 0) == 0]
    txt_content = f"# Aegis 活跃 IP 列表 (更新: {db['last_update']})\n"
    txt_content += "\n".join(sorted(active_ips))

    # 5. 提交回 GitHub
    print(f"🚀 正在同步至 GitHub 仓库...")
    json_str = json.dumps(db, indent=2)
    
    if json_sha:
        repo.update_file(FILE_JSON, "Collector Sync", json_str, json_sha)
    else:
        repo.create_file(FILE_JSON, "Collector Init", json_str)

    try:
        txt_file = repo.get_contents(FILE_TXT)
        repo.update_file(FILE_TXT, "Update View", txt_content, txt_file.sha)
    except:
        repo.create_file(FILE_TXT, "Create View", txt_content)
    
    return active_ips

def push_to_workers(active_ips):
    """将过滤后的活跃 IP 同步到 Cloudflare Workers KV"""
    if not active_ips:
        print("⚠️ 没有活跃 IP 需要推送至 Workers")
        return

    payload = {"ips": active_ips}
    headers = {
        "Authorization": WORKER_AUTH_KEY,
        "Content-Type": "application/json"
    }

    try:
        print(f"📡 正在推送 {len(active_ips)} 个 IP 到 Cloudflare Workers 大脑...")
        response = requests.post(WORKER_URL, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            print(f"✅ Workers 同步成功: {response.text}")
        else:
            print(f"❌ Workers 同步失败，状态码: {response.status_code}, 详情: {response.text}")
    except Exception as e:
        print(f"❌ 推送 Workers 时发生异常: {e}")

if __name__ == "__main__":
    # 1. 抓取新弹药
    found_raw_ips = fetch_ips()
    
    # 2. 更新仓库并获取处理后的活跃 IP 列表
    active_list = update_repo(found_raw_ips)
    
    # 3. 同步到 Cloudflare Workers
    push_to_workers(active_list)
    
    print("🔥 所有同步任务已完成！")
