import requests, json, os, re, time
from github import Github, Auth
from datetime import datetime

# ================= 配置区 =================
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = os.getenv("GITHUB_REPOSITORY")
FILE_JSON = "ip_pool.json"
WORKER_URL = "https://nameless-cherry-bb9c.2412.workers.dev/push-pool"
WORKER_AUTH_KEY = "my-secret-aegis"
HARD_BLACKLIST = {"1.0.1.1", "1.2.1.1", "1.1.1.1", "0.0.0.0"}
# ==========================================

def extract_ips(text):
    found = re.findall(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b', text)
    return {ip for ip in found if ip not in HARD_BLACKLIST}

def fetch_ips():
    all_found = set()
    sources = ["https://api.uouin.com/cloudflare.html", "https://stock.hostmonit.com/CloudFlareYes"]
    for url in sources:
        try:
            resp = requests.get(url, timeout=15)
            all_found.update(extract_ips(resp.text))
        except: pass
    return all_found

def update_and_push():
    found_ips = fetch_ips()
    if not found_ips: return
    
    auth = Auth.Token(GITHUB_TOKEN)
    repo = Github(auth=auth).get_repo(REPO_NAME)
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 更新 JSON 数据库
    active_ips = sorted(list(found_ips))
    db_to_save = {"last_update": update_time, "pool": active_ips}
    json_str = json.dumps(db_to_save, indent=2)
    
    try:
        contents = repo.get_contents(FILE_JSON)
        repo.update_file(FILE_JSON, f"Sync {update_time}", json_str, contents.sha)
    except:
        repo.create_file(FILE_JSON, "Init DB", json_str)

    # 推送给 Worker
    requests.post(WORKER_URL, json={"ips": active_ips}, headers={"Authorization": WORKER_AUTH_KEY})
    print(f"🚀 已推送 {len(active_ips)} 个 IP")

if __name__ == "__main__":
    update_and_push()
