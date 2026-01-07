import requests
import json
import os
import re
import time
from github import Github, Auth
from datetime import datetime

# --- 配置区 ---
# 这些变量会从 GitHub Actions 的环境变量中自动读取
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = os.getenv("GITHUB_REPOSITORY")
FILE_JSON = "ip_pool.json"
FILE_TXT = "ips_txt_view.txt"

# --- Cloudflare Workers 配置 ---
# 必须与你的 Worker 脚本中设置的 authKey 保持完全一致
WORKER_URL = "https://nameless-cherry-bb9c.2412.workers.dev/push-pool"
WORKER_AUTH_KEY = "my-secret-aegis" 

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def extract_ips(text):
    """从文本中提取所有标准 IPv4 地址"""
    return set(re.findall(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b', text))

def fetch_ips():
    """多源爬取 IP"""
    all_found = set()
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
                print(f"✅ 成功抓取 {len(ips)} 个 IP")
        except Exception as e:
            print(f"❌ 抓取失败 {url}: {e}")
    return sorted(list(all_found))

def update_repo(ips_list):
    """同步更新 GitHub 仓库的 JSON 和 TXT 文件"""
    if not ips_list:
        print("⚠️ IP 列表为空，跳过仓库更新")
        return []

    # 初始化 GitHub 客户端
    auth = Auth.Token(GITHUB_TOKEN)
    g = Github(auth=auth)
    repo = g.get_repo(REPO_NAME)
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # 1. 构建文件内容
    db_content = {
        "last_update": update_time,
        "total_count": len(ips_list),
        "ips": ips_list
    }
    json_str = json.dumps(db_content, indent=2, ensure_ascii=False)
    
    txt_content = f"# Aegis 优选 IP 列表\n# 更新时间: {update_time}\n# IP 总数: {len(ips_list)}\n\n"
    txt_content += "\n".join(ips_list)

    # 2. 更新或创建 JSON 文件
    try:
        contents = repo.get_contents(FILE_JSON)
        repo.update_file(FILE_JSON, f"🚀 Sync JSON {update_time}", json_str, contents.sha)
        print(f"✅ 仓库文件已更新: {FILE_JSON}")
    except Exception:
        repo.create_file(FILE_JSON, "🎁 Init JSON", json_str)
        print(f"🆕 仓库文件已创建: {FILE_JSON}")

    # 3. 更新或创建 TXT 视图文件 (本次修正重点)
    try:
        contents_txt = repo.get_contents(FILE_TXT)
        repo.update_file(FILE_TXT, f"📝 Sync TXT {update_time}", txt_content, contents_txt.sha)
        print(f"✅ 仓库文件已更新: {FILE_TXT}")
    except Exception:
        repo.create_file(FILE_TXT, "🆕 Init TXT", txt_content)
        print(f"🆕 仓库文件已创建: {FILE_TXT}")
        
    return ips_list

def push_to_workers(active_ips):
    """将 IP 推送给 Cloudflare Workers 大脑"""
    print(f"DEBUG: 准备推送 {len(active_ips)} 个 IP 到 Workers...")
    if not active_ips: return

    payload = {"ips": active_ips}
    headers = {
        "Authorization": WORKER_AUTH_KEY, 
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(WORKER_URL, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            print(f"✅ Workers 大脑同步成功: {response.text}")
        else:
            print(f"❌ Workers 同步失败，状态码: {response.status_code}，响应: {response.text}")
    except Exception as e:
        print(f"❌ 网络异常，无法连接至 Workers: {e}")

if __name__ == "__main__":
    # 执行全流程
    raw_ips = fetch_ips()
    active_ips = update_repo(raw_ips)
    push_to_workers(active_ips)
    print(f"🔥 所有任务执行完毕！当前有效弹药: {len(active_ips)}")
