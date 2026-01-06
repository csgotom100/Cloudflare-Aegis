import requests
import json
import os
import re
import time
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
    now_ts = int(time.time())
    
    # 1. 获取旧数据
    json_sha = None
    db = {"last_update": "", "pool": {}}
    try:
        contents = repo.get_contents(FILE_JSON)
        db = json.loads(contents.decoded_content.decode())
        json_sha = contents.sha
        if not isinstance(db.get('pool'), dict):
            db['pool'] = {}
    except:
        print(f"ℹ️ 创建新库文件")

    # 2. 逻辑 A：处理禁闭到期与解封 (增加安全检查)
    for ip, info in list(db['pool'].items()):
        # 使用 .get(key, default) 防止 KeyError
        ban_until = info.get('ban_until', 0)
        if ban_until > 0 and now_ts > ban_until:
            print(f"✨ IP {ip} 禁闭期满，已恢复。")
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
        # 修复此处：使用 .get() 安全判断是否在禁闭期
        elif db['pool'][ip].get('ban_until', 0) == 0:
            db['pool'][ip]['score'] = 100
    
    db['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # 4. 生成预览列表 (只包含活跃且未禁闭的 IP)
    active_ips = [ip for ip, info in db['pool'].items() if info.get('ban_until', 0) == 0]
    txt_content = f"# 活跃弹药库 (更新: {db['last_update']})\n# 总活跃数: {len(active_ips)}\n\n"
    txt_content += "\n".join(sorted(active_ips))

    # 5. 提交
    print(f"🚀 正在同步至仓库...")
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
    
    print(f"🔥 完成！当前活跃 IP: {len(active_ips)}")

if __name__ == "__main__":
    found_list = fetch_ips()
    update_repo(found_list)
